# =============================================================================
# ZIRH-2 - top-level integration: the full chip, real firmware, v2 telemetry
#
# Run:  make -C test -f Makefile.z2
#
# INTERVAL_LOG2 is overridden to 13 (frame every 8192 cycles) and RESET_DIV
# to 20. The ROM carries the committed fw/rom.hex - the actual mask ROM
# contents.
# =============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly

CLK_NS = 40
DIV = 20
FRAME_LEN = 20
BOOT_CYCLES = 120_000  # crt0 + the boot ROM-checksum loop

UART_TX_BIT = 4
CPU_ALIVE_BIT = 1


def bit(dut, i):
    # X-tolerant single-bit read: SERV's MINI reset leaves X on some event
    # nets for the first boot cycles (sim-only); str() is MSB-first
    return 1 if str(dut.uo_out.value)[7 - i] == "1" else 0


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 0x08     # UART RX idles high
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 4)


async def uart_capture(dut, timeout_cycles):
    """Recover one 8N1 byte from UART_TX, sampling mid-bit."""
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if bit(dut, UART_TX_BIT) == 0:
            break
    else:
        raise AssertionError("no start bit on UART_TX")
    await ClockCycles(dut.clk, DIV // 2)
    bits = []
    for _ in range(9):
        await ClockCycles(dut.clk, DIV)
        await ReadOnly()
        bits.append(bit(dut, UART_TX_BIT))
    assert bits[8] == 1, "broken stop bit"
    return sum(b << i for i, b in enumerate(bits[:8]))


async def capture_frame(dut, timeout_cycles=40_000):
    """Hunt for a v2.1 sync pair, then collect the rest of the frame."""
    while True:
        b0 = await uart_capture(dut, timeout_cycles)
        if b0 != 0x5A:
            continue
        b1 = await uart_capture(dut, 30 * DIV)
        if b1 == 0x33:
            frame = [b0, b1]
            for _ in range(FRAME_LEN - 2):
                frame.append(await uart_capture(dut, 30 * DIV))
            return frame


@cocotb.test()
async def test_frame_carries_a_living_cpu(dut):
    """A v2 frame arrives unprompted with a valid checksum, armed set, all
    beam counters zero - and a NONZERO CPU signature that CHANGES between
    frames: the instrument reports and the computer lives, end to end."""
    await start(dut)
    await ClockCycles(dut.clk, BOOT_CYCLES)

    f1 = await capture_frame(dut)
    chk = 0
    for b in f1[:19]:
        chk ^= b
    assert f1[19] == chk, f"checksum {f1[19]:#04x} != {chk:#04x}"

    status = f1[2]
    assert (status >> 3) & 1 == 1, "armed must be set"
    assert (status >> 2) & 1 == 0, "no infra fault expected"
    assert f1[3:13] == [0] * 10, f"beam counters must be zero: {f1[3:13]}"
    assert f1[13] == 0 and f1[14] == 0, "no ECC events expected"
    assert f1[16:19] == [0, 0, 0], "BOOT/BUS_TO/FERR must be zero"
    assert f1[15] != 0, "CPU signature is zero - firmware never reached hk"

    f2 = await capture_frame(dut)
    assert f2[15] != f1[15], (
        "CPU signature frozen across frames - the computer is not alive")
    seq1, seq2 = f1[2] >> 4, f2[2] >> 4
    assert (seq2 - seq1) % 16 >= 1, "sequence must advance"


@cocotb.test()
async def test_cpu_alive_pin_toggles(dut):
    """uo[1] must toggle while firmware writes signatures; HEARTBEAT-vs-
    CPU_ALIVE is the two-LED failure separation on the bench."""
    await start(dut)
    await ClockCycles(dut.clk, BOOT_CYCLES)

    seen = set()
    for _ in range(2_000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        seen.add(bit(dut, CPU_ALIVE_BIT))
        if len(seen) == 2:
            break
    assert seen == {0, 1}, "CPU_ALIVE pin never toggled"


def uio_bit(dut, i):
    return 1 if str(dut.uio_out.value)[7 - i] == "1" else 0


async def mirror_capture(dut, timeout_cycles=40_000):
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if uio_bit(dut, 7) == 0:
            break
    else:
        return None
    await ClockCycles(dut.clk, DIV // 2)
    bits = []
    for _ in range(9):
        await ClockCycles(dut.clk, DIV)
        await ReadOnly()
        bits.append(uio_bit(dut, 7))
    if bits[8] != 1:
        return None
    return sum(b << i for i, b in enumerate(bits[:8]))


@cocotb.test()
async def test_mirror_pin_speaks_pure_frames(dut):
    """The telemetry mirror on uio[7] carries checksum-valid v2.1 frames
    with a living CPU signature - the flood-proof second voice, verified
    at the pin."""
    await start(dut)
    await ClockCycles(dut.clk, BOOT_CYCLES)

    for _ in range(FRAME_LEN * 8):
        b0 = await mirror_capture(dut)
        if b0 != 0x5A:
            continue
        b1 = await mirror_capture(dut, 30 * DIV)
        if b1 != 0x33:
            continue
        frame = [b0, b1]
        for _ in range(FRAME_LEN - 2):
            b = await mirror_capture(dut, 30 * DIV)
            if b is None:
                break
            frame.append(b)
        if len(frame) != FRAME_LEN:
            continue
        chk = 0
        for b in frame[:19]:
            chk ^= b
        if frame[19] == chk:
            assert frame[15] != 0, "mirror frame carries a dead CPU signature"
            return
    raise AssertionError("no valid frame ever crossed the mirror pin")
