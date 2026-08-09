# =============================================================================
# ZIRH-2 - gate-level fault campaign: the contract on the netlist that flies
#
# In CI this module runs inside the gl_test job (GATES=yes appends it to
# the module list); in RTL runs it passes vacuously. The RTL campaigns
# proved the SURVIVED/REBOOTED/ZOMBIE contract on the source; only a
# gate-level run proves the hardening AS PLACED - voters, replicas and
# the chain-A macros exactly as they ship.
#
# Injection targets come from the netlist itself: at test start the
# gate_level_netlist.v next to this file is parsed for sg13g2_dfrbpq
# instances, classified by their (preserved) hierarchical name prefixes:
#
#   REPLICA class - flops inside u_ff_a islands (one replica of a TMR
#     register or monitor chain): a single flip must be healed by the
#     voted feedback, visible only as an ERR_TMR pin pulse and, for the
#     chains, exactly one RAW count.
#   CPU class - flops under u_soc (SERV state, RF, bus): the campaign
#     contract judged at the pins, silicon timings.
#
# Injection mechanics: Force/Release on the instance's Q net through one
# clock edge - the same discipline the RTL flip suites converged on
# (deposits on always-driven nets do not stick; forces must be flushed
# a timestep before the edge).
# =============================================================================

import os
import random
import re
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly, Timer

CLK_NS = 40
DIV = 174                    # silicon baud divisor - GL runs the real mask
BOOT_CYCLES = 120_000
FRAME_LEN = 20
UART_TX_BIT = 4


def gl_only():
    if os.getenv("GATES") != "yes":
        cocotb.pass_test("gate-level module; RTL runs skip it")


def load_targets():
    """Parse the netlist: every DFF instance with its Q net, classified by
    the instance name. Flattened core flops carry anonymous _N_ names
    (SERV, RF, glue - their hierarchy dissolved at synthesis); the
    keep_hierarchy islands keep readable prefixes."""
    nl = Path(__file__).parent / "gate_level_netlist.v"
    text = nl.read_text()
    insts = re.findall(
        r"sg13g2_dfrbpq_\d+\s+(\\\S+|\S+)\s*\(([^;]+?)\);",
        text, re.S)
    replica, core = [], []
    for name, body in insts:
        m = re.search(r"\.Q\(\s*(\\)?(\S+?)\s*\)", body)
        if not m:
            continue
        qnet = m.group(2)
        iname = name.lstrip("\\")
        if re.search(r"u_ff_a/", iname) and "u_soc" not in iname:
            replica.append(qnet)
        elif re.fullmatch(r"_\d+_", iname):
            core.append(qnet)
    return replica, core


def build_net_map(dut, wanted):
    """One VPI pass over the flattened module: net name -> handle."""
    wanted = set(wanted)
    found = {}
    for h in dut.user_project:
        n = h._name
        if n in wanted:
            found[n] = h
    return found


def bit(dut, i):
    return 1 if str(dut.uo_out.value)[7 - i] == "1" else 0


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 0x08
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, BOOT_CYCLES)


async def uart_send(dut, value):
    await RisingEdge(dut.clk)
    bits = [0] + [(value >> i) & 1 for i in range(8)] + [1]
    for b in bits:
        cur = int(dut.ui_in.value)
        dut.ui_in.value = (cur & ~0x08) | (b << 3)
        await ClockCycles(dut.clk, DIV)


async def expect_byte(dut, want, timeout_cycles=120_000, tries=40):
    for _ in range(tries):
        for _ in range(timeout_cycles):
            await RisingEdge(dut.clk)
            await ReadOnly()
            if bit(dut, UART_TX_BIT) == 0:
                break
        else:
            return False
        await ClockCycles(dut.clk, DIV // 2)
        bits = []
        for _ in range(9):
            await ClockCycles(dut.clk, DIV)
            await ReadOnly()
            bits.append(bit(dut, UART_TX_BIT))
        if bits[8] == 1 and sum(b << i for i, b in enumerate(bits[:8])) == want:
            return True
    return False


async def flip_q(dut, h):
    await RisingEdge(dut.clk)
    await Timer(10, unit="ns")
    cur = h.value
    v = int(cur) if cur.is_resolvable else 0
    h.value = Force(v ^ 1)
    await Timer(1, unit="ns")
    await RisingEdge(dut.clk)
    await Timer(10, unit="ns")
    h.value = Release()


@cocotb.test()
async def test_gl_replica_flips_heal_on_the_shipped_netlist(dut):
    """Six single-replica flips into as-placed u_ff_a island flops: the
    ERR_TMR pin must pulse (the mismatch was seen), the chip must keep
    answering, and no flip may wedge anything."""
    gl_only()
    replica, _ = load_targets()
    assert len(replica) > 100, f"replica inventory thin: {len(replica)}"
    await start(dut)
    random.seed(9901)
    nets = build_net_map(dut, replica)
    assert len(nets) > 100, f"net handles resolved: {len(nets)}"
    handles = list(nets.values())

    assert await expect_byte(dut, 0x71, tries=40) or True  # drain warmup
    await uart_send(dut, 0x70)
    assert await expect_byte(dut, 0x71), "sanity echo before injection"

    err_pulses = [0]

    async def err_watch():
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            if bit(dut, 3) == 1:            # uo[3] = ERR_TMR
                err_pulses[0] += 1
    cocotb.start_soon(err_watch())

    for trial in range(6):
        before = err_pulses[0]
        await flip_q(dut, random.choice(handles))
        await ClockCycles(dut.clk, 20)
        assert err_pulses[0] > before, (
            f"trial {trial}: replica flip invisible on ERR_TMR - "
            "the as-placed voter did not see it")

    await uart_send(dut, 0x72)
    assert await expect_byte(dut, 0x73), "CPU lost after healed flips"


@cocotb.test()
async def test_gl_cpu_campaign_contract(dut):
    """Two trials of CPU-class flips on the shipped netlist, judged by
    the campaign contract at the pins: echo answers (SURVIVED), or the
    watchdog reboots and echo answers after (REBOOTED), or the signature
    keeps toggling (ZOMBIE class, counted) - permanent silence never."""
    gl_only()
    _, core = load_targets()
    assert len(core) > 500, f"core inventory thin: {len(core)}"
    await start(dut)
    random.seed(9902)
    nets = build_net_map(dut, core)
    assert len(nets) > 500, f"net handles resolved: {len(nets)}"
    handles = list(nets.values())

    outcomes = []
    for trial in range(2):
        if trial:
            await RisingEdge(dut.clk)
            dut.rst_n.value = 0
            await ClockCycles(dut.clk, 8)
            dut.rst_n.value = 1
            await ClockCycles(dut.clk, BOOT_CYCLES)

        for _ in range(3):
            await flip_q(dut, random.choice(handles))

        probe = 0x74 + trial
        await uart_send(dut, probe)
        if await expect_byte(dut, probe + 1, tries=20):
            outcomes.append("survived")
            continue

        # no echo: either a reboot is coming or the loop is a zombie -
        # CPU_ALIVE (uo[1]) toggling separates both from true silence
        toggles = set()
        for _ in range(150_000):
            await RisingEdge(dut.clk)
            await ReadOnly()
            toggles.add(bit(dut, 1))
            if len(toggles) == 2:
                break
        assert len(toggles) == 2, (
            f"trial {trial}: PERMANENT SILENCE on the shipped netlist")
        outcomes.append("recovering-or-zombie")

    dut._log.info(f"gl campaign: {outcomes}")
