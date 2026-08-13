# ZIRH - corner-timing boot smoke with the X-propagation pin monitor
# (G30). The chip must boot and speak at the spec clock with the
# hardening run's own corner delays annotated, and no X may reach a
# pin after the monitor arms - the voters and the reset tree must
# have swallowed every post-reset unknown by then.
import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, NextTimeStep, ReadOnly, RisingEdge

CLK_NS = 40
DIV = 174
BOOT_CYCLES = 120_000
TLM_INTERVAL = 1 << 16
FRAME_LEN = 20


def bit(dut, i):
    v = str(dut.uo_out.value)[7 - i]
    return None if v in "xz" else int(v)


async def uart_capture(dut, timeout_cycles):
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if bit(dut, 4) == 0:
            break
    else:
        return None
    await ClockCycles(dut.clk, DIV // 2)
    bits = []
    for _ in range(9):
        await ClockCycles(dut.clk, DIV)
        await ReadOnly()
        bits.append(bit(dut, 4))
    if None in bits or bits[8] != 1:
        return None
    return sum(b << i for i, b in enumerate(bits[:8]))


@cocotb.test()
async def test_corner_boot(dut):
    corner = os.getenv("CORNER", "?")
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 0x08
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rst_n.value = 1

    # X-prop monitor: after the arm point, an X on any uo pin fails
    xleaks = [0]
    armed = [False]

    async def xmon():
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            if armed[0] and "x" in str(dut.uo_out.value).lower():
                xleaks[0] += 1
    cocotb.start_soon(xmon())

    await ClockCycles(dut.clk, BOOT_CYCLES)
    armed[0] = True

    # hunt one valid frame: sync, full length, checksum
    got = None
    for _ in range(60):
        b0 = await uart_capture(dut, TLM_INTERVAL + 40_000)
        if b0 != 0x5A:
            continue
        b1 = await uart_capture(dut, 30 * DIV)
        if b1 != 0x33:
            continue
        frame = [b0, b1]
        ok = True
        for _ in range(FRAME_LEN - 2):
            nb = await uart_capture(dut, 30 * DIV)
            if nb is None:
                ok = False
                break
            frame.append(nb)
        if ok and len(frame) == FRAME_LEN:
            chk = 0
            for b in frame[:19]:
                chk ^= b
            if chk == frame[19]:
                got = frame
                break
    assert got is not None, f"[{corner}] no valid frame at corner timing"
    assert (got[2] >> 3) & 1 == 1, f"[{corner}] not armed"
    assert got[15] != 0, f"[{corner}] CPU signature dead"
    assert xleaks[0] == 0, (
        f"[{corner}] {xleaks[0]} X leaks reached the pins after boot")

    dut._log.info(f"corner {corner}: boot, valid frame, living CPU, "
                  "zero pin X after arm - the netlist keeps its word "
                  "at real delays")
