# =============================================================================
# ZIRH-2 - cocotb unit test for zirh_hk (housekeeping / SEU monitor v2)
#
# Run:  make -C test -f Makefile.hk
#
# Everything is driven through the bus registers, exactly as firmware will.
# N is overridden to 16 so warm-up is 20 cycles and a flip crosses a ring
# in at most 16.
# =============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly, Timer

N = 16
WARMUP = N + 4

R_SIG, R_CTRL, R_CPUSIG, R_INJECT = 0x00, 0x04, 0x08, 0x0C
R_PLAIN, R_RAW_A, R_ESC_A, R_RAW_B, R_ESC_B = 0x10, 0x14, 0x18, 0x1C, 0x20
R_ECC_C, R_ECC_U = 0x24, 0x28

INJ_PLAIN, INJ_A_ONE, INJ_A_ALL, INJ_B_ONE, INJ_B_ALL = range(5)


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.cyc_i.value = 0
    dut.adr_i.value = 0
    dut.dat_i.value = 0
    dut.we_i.value = 0
    dut.ecc_corr_i.value = 0
    dut.ecc_uncorr_i.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, WARMUP + 4)


async def rd(dut, adr):
    await RisingEdge(dut.clk)
    dut.adr_i.value = adr
    dut.we_i.value = 0
    dut.cyc_i.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    val = int(dut.rdt_o.value)
    await RisingEdge(dut.clk)
    dut.cyc_i.value = 0
    return val


async def wr(dut, adr, dat):
    await RisingEdge(dut.clk)
    dut.adr_i.value = adr
    dut.dat_i.value = dat
    dut.we_i.value = 1
    dut.cyc_i.value = 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.cyc_i.value = 0
    dut.we_i.value = 0


async def counters(dut):
    return [await rd(dut, a)
            for a in (R_PLAIN, R_RAW_A, R_ESC_A, R_RAW_B, R_ESC_B)]


@cocotb.test()
async def test_signature_and_quiet(dut):
    """SIG carries the v2 ID; no injections means all counters stay zero."""
    await start(dut)
    sig = await rd(dut, R_SIG)
    assert (sig >> 24) == 0x5A and ((sig >> 16) & 0xFF) == 0x32, (
        f"ID bytes wrong: {sig:#010x}")
    assert (sig >> 3) & 1 == 1, "armed must be set after warm-up"
    await ClockCycles(dut.clk, 4 * N)
    assert await counters(dut) == [0, 0, 0, 0, 0], "phantom counts"


@cocotb.test()
async def test_bus_injection_all_five_paths(dut):
    """Each INJECT code moves exactly its own counter by one."""
    await start(dut)

    await wr(dut, R_INJECT, INJ_PLAIN)
    await ClockCycles(dut.clk, 2 * N)
    assert await counters(dut) == [1, 0, 0, 0, 0], "plain injection"

    await wr(dut, R_INJECT, INJ_A_ONE)
    await ClockCycles(dut.clk, 2 * N)
    assert await counters(dut) == [1, 1, 0, 0, 0], (
        "A single-replica: RAW_A only, voter must mask")

    await wr(dut, R_INJECT, INJ_A_ALL)
    await ClockCycles(dut.clk, 2 * N)
    assert await counters(dut) == [1, 1, 1, 0, 0], (
        "A all-replica: ESC_A only, no disagreement to see")

    await wr(dut, R_INJECT, INJ_B_ONE)
    await ClockCycles(dut.clk, 2 * N)
    assert await counters(dut) == [1, 1, 1, 1, 0], "B single-replica"

    await wr(dut, R_INJECT, INJ_B_ALL)
    await ClockCycles(dut.clk, 2 * N)
    assert await counters(dut) == [1, 1, 1, 1, 1], "B escape"


@cocotb.test()
async def test_chains_a_and_b_are_equivalent(dut):
    """The constrained and tool-placed chains are logically identical: the
    same injection sequence produces the same counts on both."""
    await start(dut)
    for _ in range(3):
        await wr(dut, R_INJECT, INJ_A_ONE)
        await wr(dut, R_INJECT, INJ_B_ONE)
        await ClockCycles(dut.clk, 2 * N)
    c = await counters(dut)
    assert c[1] == c[3] == 3, f"RAW_A/RAW_B diverge: {c}"
    assert c[2] == c[4] == 0, f"phantom escapes: {c}"


@cocotb.test()
async def test_ecc_event_counters(dut):
    """ECC pulses count into their own 8-bit counters."""
    await start(dut)
    for _ in range(3):
        await RisingEdge(dut.clk)
        dut.ecc_corr_i.value = 1
        await RisingEdge(dut.clk)
        dut.ecc_corr_i.value = 0
    await RisingEdge(dut.clk)
    dut.ecc_uncorr_i.value = 1
    await RisingEdge(dut.clk)
    dut.ecc_uncorr_i.value = 0

    await ClockCycles(dut.clk, 2)
    assert await rd(dut, R_ECC_C) == 3, "corrected events"
    assert await rd(dut, R_ECC_U) == 1, "uncorrectable events"


@cocotb.test()
async def test_cpu_sig_and_alive_pulse(dut):
    """CPU_SIG stores the byte; each write pulses cpu_alive_o exactly once."""
    await start(dut)
    pulses = 0

    async def watch():
        nonlocal pulses
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            pulses += (dut.cpu_alive_o.value == 1)

    w = cocotb.start_soon(watch())
    await wr(dut, R_CPUSIG, 0xA7)
    await wr(dut, R_CPUSIG, 0x33)
    await ClockCycles(dut.clk, 3)
    w.kill()

    assert await rd(dut, R_CPUSIG) == 0x33
    assert pulses == 2, f"alive pulses {pulses}, expected exactly 2"


@cocotb.test()
async def test_clear_and_mode_rearm(dut):
    """CTRL clear zeroes everything; a mode change re-arms the warm-up."""
    await start(dut)
    await wr(dut, R_INJECT, INJ_PLAIN)
    await wr(dut, R_INJECT, INJ_B_ALL)
    await ClockCycles(dut.clk, 2 * N)
    assert (await counters(dut))[0] == 1, "setup"

    await wr(dut, R_CTRL, (1 << 8) | 0)      # clear, keep mode 0
    assert await counters(dut) == [0, 0, 0, 0, 0], "clear failed"

    await wr(dut, R_CTRL, 0x1)               # mode change -> re-arm
    sig = await rd(dut, R_SIG)
    assert (sig >> 3) & 1 == 0, "warm-up must re-arm on mode change"
    await ClockCycles(dut.clk, WARMUP + N + 8)
    assert await counters(dut) == [0, 0, 0, 0, 0], (
        "mode change fabricated counts")


@cocotb.test()
async def test_counter_replica_upset_flags_infra(dut):
    """Flip a counter replica: infra_seen sets in SIG, measurement clean."""
    await start(dut)
    await Timer(10, unit="ns")
    val = int(dut.u_c_raw_a.u_ff_c.q_o.value)
    dut.u_c_raw_a.u_ff_c.q_o.setimmediatevalue(val ^ 0x10)
    await ClockCycles(dut.clk, 4)

    sig = await rd(dut, R_SIG)
    assert (sig >> 2) & 1 == 1, "infra_seen must flag the instrument upset"
    assert await counters(dut) == [0, 0, 0, 0, 0], (
        "instrument upset must not poison the measurement")
