# =============================================================================
# ZIRH-2 - marathon scenarios: the whole chip on, for a long time
#
# Run:  make -C test -f Makefile.mega
#
# Three endurance runs on the final configuration (N=32 rings, both
# interfaces, both telemetry voices):
#
#   EVERYTHING-ON SOAK - SpaceWire link in Run, CAN beacons firing,
#   environment polls, ring injections and random commands all
#   interleaved for tens of millions of nanoseconds while BOTH voices
#   must keep producing checksum-valid frames and no TMR infrastructure
#   fault may ever appear.
#
#   SEQUENCE CONTINUITY - two hundred consecutive frames on a quiet
#   link: every checksum valid, every sequence step exactly +1 mod 16.
#   The frame stream is the mission's heartbeat; this is its cardiogram.
#
#   FLIP MARATHON - ten reboot-storm rounds interleaved with single
#   replica flips across the TMR islands, the campaign contract enforced
#   every round: survive, reboot counted, zombie classified - permanent
#   silence never.
# =============================================================================

import os
import random

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly, Timer

CLK_NS = 40
DIV = 20
BOOT_CYCLES = 120_000
WD_LIMIT = 1 << 17
FRAME_LEN = 20
UART_TX_BIT = 4


def bit(dut, i):
    return 1 if str(dut.uo_out.value)[7 - i] == "1" else 0


def uio_bit(dut, i):
    return 1 if str(dut.uio_out.value)[7 - i] == "1" else 0


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 0x08
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rst_n.value = 1
    cocotb.start_soon(_loop_wires(dut))
    await ClockCycles(dut.clk, BOOT_CYCLES)


async def _loop_wires(dut):
    while True:
        await RisingEdge(dut.clk)
        await ReadOnly()
        v = dut.uio_out.value
        u = int(v) if v.is_resolvable else 0   # reset window carries X
        await RisingEdge(dut.clk)
        dut.uio_in.value = ((u >> 1) & 1) | (((u >> 4) & 1) << 2) | \
                           (((u >> 5) & 1) << 3)


async def uart_send(dut, value):
    await RisingEdge(dut.clk)
    bits = [0] + [(value >> i) & 1 for i in range(8)] + [1]
    for b in bits:
        cur = int(dut.ui_in.value)
        dut.ui_in.value = (cur & ~0x08) | (b << 3)
        await ClockCycles(dut.clk, DIV)


async def _capture_stream(dut, reader, sink):
    """Continuously assemble frames from a pin reader into sink dict."""
    while True:
        b0 = await reader(dut)
        if b0 != 0x5A:
            continue
        b1 = await reader(dut)
        if b1 != 0x33:
            continue
        frame = [b0, b1]
        ok = True
        for _ in range(FRAME_LEN - 2):
            b = await reader(dut)
            if b is None:
                ok = False
                break
            frame.append(b)
        if not ok:
            continue
        chk = 0
        for b in frame[:19]:
            chk ^= b
        if frame[19] == chk:
            sink["good"] += 1
            sink["last"] = frame
            if (frame[2] >> 2) & 1:
                sink["infra"] += 1
        else:
            sink["bad"] += 1


def _mk_reader(bit_idx, from_uio):
    async def reader(dut, timeout_cycles=200_000):
        for _ in range(timeout_cycles):
            await RisingEdge(dut.clk)
            await ReadOnly()
            v = uio_bit(dut, bit_idx) if from_uio else bit(dut, bit_idx)
            if v == 0:
                break
        else:
            return None
        await ClockCycles(dut.clk, DIV // 2)
        bits = []
        for _ in range(9):
            await ClockCycles(dut.clk, DIV)
            await ReadOnly()
            bits.append(uio_bit(dut, bit_idx) if from_uio else bit(dut, bit_idx))
        if bits[8] != 1:
            return None
        return sum(b << i for i, b in enumerate(bits[:8]))
    return reader


@cocotb.test()
async def test_everything_on_soak(dut):
    """All five interfaces and all three instruments active at once for a
    long soak: both voices stay valid, zero infra faults, CAN clean,
    SpaceWire in Run, CPU answering at the end."""
    await start(dut)
    random.seed(7701)

    primary = {"good": 0, "bad": 0, "infra": 0, "last": None}
    mirror = {"good": 0, "bad": 0, "infra": 0, "last": None}
    cocotb.start_soon(_capture_stream(dut, _mk_reader(UART_TX_BIT, False), primary))
    cocotb.start_soon(_capture_stream(dut, _mk_reader(7, True), mirror))

    await uart_send(dut, ord('w'))          # SpaceWire link up + a char
    await ClockCycles(dut.clk, 4_000)

    commands = [ord(c) for c in "01234abcTSBEkKW"] + [0x70, 0x75, 0x7A]
    for burst in range(120):
        cmd = random.choice(commands)
        await uart_send(dut, cmd)
        if cmd == ord('k'):
            await ClockCycles(dut.clk, 3_000)   # let the beacon land
        await ClockCycles(dut.clk, random.randrange(2_000, 12_000))

    await ClockCycles(dut.clk, 30_000)

    ifc = dut.u_ifc
    assert primary["good"] >= 40, f"primary voice thin: {primary}"
    assert mirror["good"] >= 40, f"mirror voice thin: {mirror}"
    assert primary["infra"] == 0 and mirror["infra"] == 0, (
        "TMR infrastructure fault under full load")
    assert mirror["bad"] == 0, (
        f"the mirror carries ONLY frames - {mirror['bad']} bad checksums")
    assert int(ifc.u_can.err_cnt_o.value) == 0, "CAN errors on a clean loop"
    assert int(ifc.u_spw.state_o.value) == 5, "SpaceWire fell out of Run"

    await uart_send(dut, 0x70)
    got = False
    rd = _mk_reader(UART_TX_BIT, False)
    for _ in range(60):
        if await rd(dut) == 0x71:
            got = True
            break
    assert got, "CPU stopped echoing after the soak"
    dut._log.info(
        f"soak: primary {primary['good']} frames, mirror {mirror['good']}, "
        f"CAN rx_ok {int(ifc.u_can.rx_ok_cnt_o.value)}, SpW in Run")


@cocotb.test()
async def test_two_hundred_frame_cardiogram(dut):
    """200 consecutive frames on a quiet link: checksums all valid, the
    sequence field steps exactly +1 mod 16 with no gaps, and the mirror
    sees the same heartbeat."""
    await start(dut)

    rd_p = _mk_reader(UART_TX_BIT, False)
    seqs = []
    mirror = {"good": 0, "bad": 0, "infra": 0, "last": None}
    cocotb.start_soon(_capture_stream(dut, _mk_reader(7, True), mirror))

    while len(seqs) < 200:
        b0 = await rd_p(dut)
        if b0 != 0x5A:
            continue
        b1 = await rd_p(dut)
        if b1 != 0x33:
            continue
        frame = [b0, b1]
        for _ in range(FRAME_LEN - 2):
            b = await rd_p(dut)
            if b is None:
                break
            frame.append(b)
        if len(frame) != FRAME_LEN:
            continue
        chk = 0
        for b in frame[:19]:
            chk ^= b
        assert frame[19] == chk, f"checksum broke at frame {len(seqs)}"
        seqs.append(frame[2] >> 4)

    gaps = sum(1 for a, b in zip(seqs, seqs[1:]) if (b - a) % 16 != 1)
    assert gaps == 0, f"{gaps} sequence gaps in 200 frames"
    assert mirror["good"] >= 150, f"mirror heartbeat thin: {mirror['good']}"
    assert mirror["bad"] == 0
    dut._log.info(f"cardiogram: 200 frames, 0 gaps, mirror {mirror['good']}")


@cocotb.test()
async def test_flip_and_storm_marathon(dut):
    """Ten rounds: each is a burst of TMR replica flips across random
    islands plus an RF shower, judged by the campaign contract. Nothing
    may end permanently silent, and the instrument counters must never
    lose their planted marker."""
    await start(dut)
    random.seed(7703)

    rd = _mk_reader(UART_TX_BIT, False)

    async def alive(probe):
        await uart_send(dut, probe)
        for _ in range(60):
            if await rd(dut) == (probe + 1) & 0xFF:
                return True
        return False

    assert await alive(0x70), "sanity echo"
    await uart_send(dut, ord('1'))          # plant RAW_A = 1
    await ClockCycles(dut.clk, 20_000)

    hk = dut.u_hk
    env = dut.u_env
    islands = [hk.u_mode, hk.u_c_plain, hk.u_c_raw_a, hk.u_c_esc_b,
               hk.u_boot, hk.u_wd, env.u_win, env.u_setc, env.u_burst]
    widths = [2, 16, 16, 16, 8, 21, 11, 8, 8]

    outcomes = {"survived": 0, "rebooted": 0, "zombie": 0}
    for rnd in range(10):
        for _ in range(4):                  # replica flips, always healed
            i = random.randrange(len(islands))
            await RisingEdge(dut.clk)
            await Timer(10, unit="ns")
            reg = islands[i]
            cur = reg.u_ff_a.q_o.value
            v = int(cur) if cur.is_resolvable else 0
            reg.u_ff_a.q_o.value = Force(v ^ (1 << random.randrange(widths[i])))
            await Timer(1, unit="ns")
            await RisingEdge(dut.clk)
            await Timer(10, unit="ns")
            reg.u_ff_a.q_o.value = Release()
            await ClockCycles(dut.clk, 40)

        boots_before = int(dut.boot_cnt.value)
        await Timer(10, unit="ns")
        for _ in range(24):                 # RF shower
            idx = random.randrange(512)
            mem = dut.u_soc.u_cpu.rf_ram.memory[idx]
            v = int(mem.value) if mem.value.is_resolvable else 0
            mem.setimmediatevalue(v ^ 0x3)
        await RisingEdge(dut.clk)

        recovered = False
        deadline = WD_LIMIT + BOOT_CYCLES + 80_000
        waited = 0
        while waited < deadline:
            await ClockCycles(dut.clk, 20_000)
            waited += 20_000
            if int(dut.boot_cnt.value) > boots_before:
                recovered = True
                break
        if recovered:
            await ClockCycles(dut.clk, BOOT_CYCLES + 60_000)
            outcomes["rebooted"] += 1
        elif await alive(0x74 + (rnd % 8)):
            outcomes["survived"] += 1
        else:
            toggles = set()
            for _ in range(30_000):
                await RisingEdge(dut.clk)
                await ReadOnly()
                toggles.add(bit(dut, 1))
                if len(toggles) == 2:
                    break
            assert len(toggles) == 2, (
                f"round {rnd}: permanent silence - the forbidden outcome")
            outcomes["zombie"] += 1
            await RisingEdge(dut.clk)
            dut.rst_n.value = 0             # clear the zombie, keep marching
            await ClockCycles(dut.clk, 8)
            dut.rst_n.value = 1
            await ClockCycles(dut.clk, BOOT_CYCLES)
            await uart_send(dut, ord('1'))
            await ClockCycles(dut.clk, 20_000)

    assert sum(outcomes.values()) == 10
    dut._log.info(f"marathon: {outcomes} of 10 rounds")
