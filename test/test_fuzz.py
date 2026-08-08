# =============================================================================
# ZIRH-2 - top-level command fuzzer
#
# Run:  make -C test -f Makefile.fuzz
#
# 400 random bytes down the UART with random inter-byte gaps - the whole
# command set, every illegal byte, back-to-back overruns, commands
# colliding with telemetry. The contract under fire: frames keep flowing
# with valid checksums, no TMR infrastructure fault ever appears, and at
# the end the CPU still answers and a clear returns the instrument to
# zero. Nothing a ground operator can type may wedge the chip.
# =============================================================================

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly

CLK_NS = 40
DIV = 20
BOOT_CYCLES = 120_000
FRAME_LEN = 20
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


async def uart_capture(dut, timeout_cycles):
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if bit(dut, UART_TX_BIT) == 0:
            break
    else:
        return None
    await ClockCycles(dut.clk, DIV // 2)
    bits = []
    for _ in range(9):
        await ClockCycles(dut.clk, DIV)
        await ReadOnly()
        bits.append(bit(dut, UART_TX_BIT))
    if bits[8] != 1:
        return None
    return sum(b << i for i, b in enumerate(bits[:8]))


async def capture_frame(dut, timeout_cycles=60_000):
    """Hunt for a v2.1 sync pair; checksum-verified by the caller."""
    for _ in range(FRAME_LEN * 12):
        b0 = await uart_capture(dut, timeout_cycles)
        if b0 != 0x5A:
            continue
        b1 = await uart_capture(dut, 30 * DIV)
        if b1 != 0x33:
            continue
        frame = [b0, b1]
        for _ in range(FRAME_LEN - 2):
            b = await uart_capture(dut, 30 * DIV)
            if b is None:
                break
            frame.append(b)
        if len(frame) == FRAME_LEN:
            return frame
    raise AssertionError("no telemetry frame while fuzzing")


@cocotb.test()
async def test_command_fuzz(dut):
    """400 random bytes, random pacing; telemetry must stay coherent and
    the instrument must come back clean."""
    await start(dut)
    random.seed(2202)

    bad_chk = 0
    infra_seen = 0
    frames = 0

    for burst in range(25):
        for _ in range(16):
            await uart_send(dut, random.randrange(256))
            gap = random.choice((0, 0, random.randrange(1, 400),
                                 random.randrange(400, 3000)))
            if gap:
                await ClockCycles(dut.clk, gap)

        f = await capture_frame(dut)
        frames += 1
        chk = 0
        for b in f[:19]:
            chk ^= b
        if f[19] != chk:
            bad_chk += 1
        if (f[2] >> 2) & 1:
            infra_seen += 1

    assert bad_chk == 0, f"{bad_chk}/{frames} frames with broken checksums"
    assert infra_seen == 0, (
        f"TMR infrastructure fault flagged in {infra_seen} frames - "
        "commands must never corrupt protected state")

    # the instrument must return to zero on command, and the CPU answer
    await uart_send(dut, ord('C'))
    f = await capture_frame(dut)
    if f[3:15] != [0] * 12:
        f = await capture_frame(dut)   # clear may have landed mid-snapshot
    assert f[3:15] == [0] * 12, f"clear after fuzz failed: {f[3:15]}"

    await uart_send(dut, 0x70)
    for _ in range(40):
        if await uart_capture(dut, 60_000) == 0x71:
            break
    else:
        raise AssertionError("CPU stopped echoing after the fuzz")
