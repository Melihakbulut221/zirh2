# =============================================================================
# ZIRH-2 - TMR replica flip campaign: the protection under (simulated) beam
#
# Run:  make -C test -f Makefile.tmrflip
#
# Deposits flip single replica registers across every TMR island on the
# die - housekeeping, telemetry, environment monitor, and both monitor
# chains. Voted feedback must reconverge the replicas within a cycle,
# the chain flips must land in exactly the RAW counters built to count
# them, and a double-replica hit (beyond TMR's guarantee, by definition)
# must corrupt data without killing the chip.
# =============================================================================

import random

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly, Timer

CLK_NS = 40
DIV = 20
BOOT_CYCLES = 120_000
UART_TX_BIT = 4


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


async def expect_byte(dut, want, timeout_cycles):
    for _ in range(60):
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


async def flip_replica(dut, reg, width):
    """One 'particle' into replica A of a zirh_tmr_reg: force the flipped
    value through exactly one clock edge, then release. Force/release
    rather than a deposit - the replica's q_o is an output-reg port, and
    a plain deposit on it neither heals nor registers a mismatch under
    Icarus (measured; the port wire and the inner reg stop agreeing).
    The target is the REPLICA (u_ff_a), never the register's own q_o:
    that wire is the voter output, and forcing it fakes a fault the
    voter can neither see nor heal (measured too - the hard way)."""
    await Timer(10, unit="ns")
    b = random.randrange(width)
    cur = reg.u_ff_a.q_o.value
    v = int(cur) if cur.is_resolvable else 0
    reg.u_ff_a.q_o.value = Force(v ^ (1 << b))
    await Timer(1, unit="ns")   # writes are cached: flush BEFORE the edge
    await RisingEdge(dut.clk)
    await Timer(10, unit="ns")
    reg.u_ff_a.q_o.value = Release()


def replicas_converged(reg):
    a, b, c = reg.u_ff_a.q_o.value, reg.u_ff_b.q_o.value, reg.u_ff_c.q_o.value
    return a.is_resolvable and str(a) == str(b) == str(c)


@cocotb.test()
async def test_every_tmr_island_heals(dut):
    """A single-replica flip in EVERY TMR register on the die reconverges
    within two cycles and pulses the mismatch detector."""
    await start(dut)
    random.seed(3301)

    hk = dut.u_hk
    env = dut.u_env
    tlm = dut.u_tlm
    islands = [
        ("hk.mode",   hk.u_mode,    2),  ("hk.phase",  hk.u_phase,   1),
        ("hk.warm",   hk.u_warm,    7),  ("hk.plain",  hk.u_c_plain, 16),
        ("hk.raw_a",  hk.u_c_raw_a, 16), ("hk.esc_a",  hk.u_c_esc_a, 16),
        ("hk.raw_b",  hk.u_c_raw_b, 16), ("hk.esc_b",  hk.u_c_esc_b, 16),
        ("hk.ecc_c",  hk.u_c_ecc_c, 8),  ("hk.ecc_u",  hk.u_c_ecc_u, 8),
        ("hk.busto",  hk.u_c_busto, 8),  ("hk.ferr",   hk.u_c_ferr,  8),
        ("hk.boot",   hk.u_boot,    8),  ("hk.wd",     hk.u_wd,      21),
        ("tlm.intv",  tlm.u_intv,   13), ("tlm.state", tlm.u_st,     6),
        ("env.win",   env.u_win,    11), ("env.set",   env.u_setc,   8),
        ("env.btim",  env.u_btim,   5),  ("env.burst", env.u_burst,  8),
    ]

    err_pulses = [0]

    async def err_watch():
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            if str(dut.u_hk.err_infra_o.value) == "1" or \
               str(dut.u_env.err_o.value) == "1" or \
               str(dut.u_tlm.err_o.value) == "1":
                err_pulses[0] += 1
    cocotb.start_soon(err_watch())

    for rounds in range(2):
        for name, reg, width in islands:
            before = err_pulses[0]
            await flip_replica(dut, reg, width)
            await ClockCycles(dut.clk, 3)
            assert replicas_converged(reg), (
                f"{name}: replicas did not reconverge after a single flip")
            assert err_pulses[0] > before, (
                f"{name}: no mismatch pulse - the flip went unnoticed")

    # the storm of 40 healed flips must not have hurt the computer
    await uart_send(dut, 0x70)
    assert await expect_byte(dut, 0x71, 60_000), "CPU lost after flip sweep"


@cocotb.test()
async def test_chain_replica_flips_land_in_raw_counters(dut):
    """A flip in one replica of monitor chain A (the macro-bound chain)
    or chain B counts in exactly RAW_A / RAW_B; the voted ring output
    stays clean so the ESCAPE counters must not move."""
    await start(dut)
    random.seed(3302)

    for chain, ff, raw, esc in (
        ("A", dut.u_hk.g_a_macro.u_ff_a.u_core, dut.u_hk.u_c_raw_a,
         dut.u_hk.u_c_esc_a),
        ("B", dut.u_hk.u_ch_b_a, dut.u_hk.u_c_raw_b, dut.u_hk.u_c_esc_b),
    ):
        for trial in range(5):
            raw_before = int(raw.q_o.value)
            esc_before = int(esc.q_o.value)
            await Timer(10, unit="ns")
            v = int(ff.q_o.value)
            ff.q_o.setimmediatevalue(v ^ (1 << random.randrange(64)))
            await ClockCycles(dut.clk, 4)
            assert int(raw.q_o.value) == raw_before + 1, (
                f"chain {chain} trial {trial}: RAW did not count the flip")
            assert int(esc.q_o.value) == esc_before, (
                f"chain {chain} trial {trial}: a voted-out flip escaped")


@cocotb.test()
async def test_double_replica_hit_corrupts_but_does_not_kill(dut):
    """Two replicas of the same counter hit in the same cycle: beyond
    TMR's guarantee, the majority is now wrong - the VALUE may corrupt,
    but the replicas still converge, the chip keeps running, and a clear
    restores ground truth."""
    await start(dut)
    random.seed(3303)

    reg = dut.u_hk.u_c_plain
    await Timer(10, unit="ns")
    b = 1 << random.randrange(16)
    for ff in (reg.u_ff_a, reg.u_ff_b):
        ff.q_o.value = Force(int(ff.q_o.value) ^ b)
    await Timer(1, unit="ns")   # flush the cached forces before the edge
    await RisingEdge(dut.clk)
    await Timer(10, unit="ns")
    for ff in (reg.u_ff_a, reg.u_ff_b):
        ff.q_o.value = Release()
    await ClockCycles(dut.clk, 3)
    assert replicas_converged(reg), "replicas must converge even on the wrong value"

    await uart_send(dut, 0x72)
    assert await expect_byte(dut, 0x73, 60_000), "CPU died on a double hit"

    await uart_send(dut, ord('C'))
    await ClockCycles(dut.clk, 3000)
    assert int(reg.q_o.value) == 0, "clear must restore the corrupted counter"
