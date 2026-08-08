# =============================================================================
# ZIRH-2 - cocotb unit test for zirh_env
#
# Run:  make -C test -f Makefile.env
#
# The oscillator and the SET chain are behavioral under ZIRH_SIM_ENV (one
# count per clk cycle while enabled; the chain passes its input through),
# so this suite pins down the control semantics: window length, busy
# protocol, catch-synchronize-count-rearm, burst pairing, clear.
# =============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly

WIN = 1 << 10          # WIN_LOG2 default
SETTLE = 8


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.start_i.value = 0
    dut.test_i.value = 0
    dut.clear_i.value = 0
    dut.evt_i.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    # let the power-on re-arm of the catch latch run out
    await ClockCycles(dut.clk, 10)


async def pulse(dut, sig):
    await RisingEdge(dut.clk)
    sig.value = 1
    await RisingEdge(dut.clk)
    sig.value = 0


async def ro_word(dut):
    await RisingEdge(dut.clk)
    await ReadOnly()
    return int(dut.ro_word_o.value)


async def sb_word(dut):
    await RisingEdge(dut.clk)
    await ReadOnly()
    return int(dut.sb_word_o.value)


@cocotb.test()
async def test_ro_window_counts_and_busy_drops(dut):
    """A window run: busy rises, drops after WIN+SETTLE, and the counter
    reads back about one count per enabled cycle (behavioral model)."""
    await start(dut)
    assert (await ro_word(dut)) >> 31 == 0, "must come up idle"

    await pulse(dut, dut.start_i)
    w = await ro_word(dut)
    assert w >> 31 == 1, "busy must rise with the window"

    await ClockCycles(dut.clk, WIN + SETTLE + 4)
    w = await ro_word(dut)
    assert w >> 31 == 0, "busy must drop after the window"
    cnt = w & 0xFFFF
    assert WIN - 24 <= cnt <= WIN + 24, f"window count {cnt} vs ~{WIN}"


@cocotb.test()
async def test_ro_second_window_recounts(dut):
    """The counter clears at each start: two consecutive windows read the
    same value, not a running sum."""
    await start(dut)
    await pulse(dut, dut.start_i)
    await ClockCycles(dut.clk, WIN + SETTLE + 4)
    first = (await ro_word(dut)) & 0xFFFF

    await pulse(dut, dut.start_i)
    await ClockCycles(dut.clk, WIN + SETTLE + 4)
    second = (await ro_word(dut)) & 0xFFFF
    assert abs(first - second) <= 8, f"windows differ: {first} vs {second}"


@cocotb.test()
async def test_start_ignored_while_busy(dut):
    """A start pulse mid-window must not restart or corrupt the count."""
    await start(dut)
    await pulse(dut, dut.start_i)
    await ClockCycles(dut.clk, WIN // 2)
    await pulse(dut, dut.start_i)          # must be ignored
    await ClockCycles(dut.clk, (WIN // 2) + SETTLE + 8)
    w = await ro_word(dut)
    assert w >> 31 == 0, "window must have ended on the original schedule"
    cnt = w & 0xFFFF
    assert WIN - 24 <= cnt <= WIN + 24, f"count corrupted by mid-window start: {cnt}"


@cocotb.test()
async def test_set_selftest_counts_and_rearms(dut):
    """Each self-test pulse lands exactly one count, and the automatic
    re-arm makes the next pulse countable."""
    await start(dut)
    assert (await sb_word(dut)) & 0xFF == 0

    await pulse(dut, dut.test_i)
    await ClockCycles(dut.clk, 12)
    assert (await sb_word(dut)) & 0xFF == 1, "first self-test must count once"

    await pulse(dut, dut.test_i)
    await ClockCycles(dut.clk, 12)
    assert (await sb_word(dut)) & 0xFF == 2, "latch must have re-armed"


@cocotb.test()
async def test_burst_pairing(dut):
    """Two event onsets within the 16-cycle window count one burst; a
    lone onset counts none; a held-high event counts once, not per cycle."""
    await start(dut)

    # lone event, then quiet: no burst
    await pulse(dut, dut.evt_i)
    await ClockCycles(dut.clk, 40)
    assert (await sb_word(dut)) >> 8 & 0xFF == 0, "lone event must not count"

    # pair 3 cycles apart: one burst
    await pulse(dut, dut.evt_i)
    await ClockCycles(dut.clk, 2)
    await pulse(dut, dut.evt_i)
    await ClockCycles(dut.clk, 4)
    assert (await sb_word(dut)) >> 8 & 0xFF == 1, "pair must count one burst"

    # held-high event long after: onset-filtered, and outside the window
    await ClockCycles(dut.clk, 40)
    await RisingEdge(dut.clk)
    dut.evt_i.value = 1
    await ClockCycles(dut.clk, 10)
    dut.evt_i.value = 0
    await ClockCycles(dut.clk, 4)
    assert (await sb_word(dut)) >> 8 & 0xFF == 1, "held event must not inflate bursts"


@cocotb.test()
async def test_clear_wipes_set_and_burst(dut):
    """clear_i zeroes both counters and nothing phantom-counts after."""
    await start(dut)
    await pulse(dut, dut.test_i)
    await pulse(dut, dut.evt_i)
    await ClockCycles(dut.clk, 2)
    await pulse(dut, dut.evt_i)
    await ClockCycles(dut.clk, 12)
    w = await sb_word(dut)
    assert w & 0xFF == 1 and (w >> 8) & 0xFF == 1

    await pulse(dut, dut.clear_i)
    await ClockCycles(dut.clk, 4)
    assert (await sb_word(dut)) & 0xFFFF == 0, "clear must wipe both"

    await ClockCycles(dut.clk, 60)
    assert (await sb_word(dut)) & 0xFFFF == 0, "phantom counts after clear"
