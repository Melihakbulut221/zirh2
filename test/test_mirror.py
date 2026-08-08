# =============================================================================
# ZIRH-2 - cocotb unit test for zirh_tlm_mirror
#
# Run:  make -C test -f Makefile.mirror
#
# The mirror's whole contract: every strobed byte leaves the pin as 8N1
# in order at the configured baud, the line idles high, back-to-back
# telemetry pacing survives on the two-byte skid, and an overrun drops
# the OLD byte so the freshest telemetry wins.
# =============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly

DIV = 8


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.tlm_data_i.value = 0
    dut.tlm_strobe_i.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def strobe(dut, byte):
    await RisingEdge(dut.clk)
    dut.tlm_data_i.value = byte
    dut.tlm_strobe_i.value = 1
    await RisingEdge(dut.clk)
    dut.tlm_strobe_i.value = 0


async def capture(dut, timeout_cycles=4000):
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.tx_o.value) == 0:
            break
    else:
        return None
    await ClockCycles(dut.clk, DIV // 2)
    bits = []
    for _ in range(9):
        await ClockCycles(dut.clk, DIV)
        await ReadOnly()
        bits.append(int(dut.tx_o.value))
    if bits[8] != 1:
        return None
    return sum(b << i for i, b in enumerate(bits[:8]))


@cocotb.test()
async def test_idles_high_and_sends_in_order(dut):
    """Quiet line idles high; three paced bytes arrive byte-exact in order."""
    await start(dut)
    await ClockCycles(dut.clk, 50)
    await ReadOnly()
    assert int(dut.tx_o.value) == 1, "serial line must idle high"

    seq = [0x5A, 0x33, 0xC4]
    got = []

    async def rx():
        for _ in seq:
            got.append(await capture(dut))
    task = cocotb.start_soon(rx())

    for b in seq:
        await strobe(dut, b)
        await ClockCycles(dut.clk, DIV * 12)   # telemetry-like pacing
    await ClockCycles(dut.clk, DIV * 12)
    assert got == seq, f"{[hex(g) if g is not None else None for g in got]}"


@cocotb.test()
async def test_back_to_back_rides_the_holding_reg(dut):
    """Two strobes in adjacent cycles: the serializer takes the first as
    the second lands in the holding register - both out, in order."""
    await start(dut)
    got = []

    async def rx():
        for _ in range(2):
            got.append(await capture(dut))
    task = cocotb.start_soon(rx())

    await strobe(dut, 0xA1)
    await strobe(dut, 0xB2)
    await ClockCycles(dut.clk, DIV * 25)
    assert got == [0xA1, 0xB2], f"{[hex(g) if g is not None else None for g in got]}"


@cocotb.test()
async def test_overrun_keeps_the_freshest(dut):
    """Flooding the skid while a byte serializes: the newest bytes win and
    the stream stays parseable (no torn characters)."""
    await start(dut)
    got = []

    async def rx():
        while True:
            b = await capture(dut)
            if b is None:
                break
            got.append(b)
    task = cocotb.start_soon(rx())

    for i in range(8):                      # 8 strobes, skid holds 2
        await strobe(dut, 0x10 + i)
    await ClockCycles(dut.clk, DIV * 40)
    task.kill()

    assert got, "nothing came out at all"
    assert got[-1] == 0x17, f"freshest byte lost: {[hex(g) for g in got]}"
    assert all(0x10 <= g <= 0x17 for g in got), f"torn bytes: {[hex(g) for g in got]}"
