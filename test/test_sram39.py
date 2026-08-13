# ZIRH-2 program P1 - the sliced 39-bit SRAM word: SECDED behaviour
# proven on the macro-backed storage, corruption injected by poking
# the behavioral macro arrays directly.
import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, NextTimeStep, ReadOnly, RisingEdge


async def bus(dut, adr, we=0, dat=0, sel=0xF, timeout=16):
    await NextTimeStep()
    dut.cyc_i.value = 1
    dut.adr_i.value = adr
    dut.we_i.value = we
    dut.dat_i.value = dat
    dut.sel_i.value = sel
    for _ in range(timeout):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.ack_o.value) == 1:
            v = dut.rdt_o.value
            rdt = int(v) if v.is_resolvable else None
            corr = int(dut.evt_corr_o.value)
            unc = int(dut.evt_uncorr_o.value)
            await NextTimeStep()
            dut.cyc_i.value = 0
            await RisingEdge(dut.clk)
            return rdt, corr, unc
    raise AssertionError(f"no ack at adr {adr:#x}")


def slice_mem(dut, k):
    m = [dut.u_m0, dut.u_m1, dut.u_m2, dut.u_m3, dut.u_m4][k]
    return m.u_macro.i_SRAM_1P_behavioral_bm_bist.memory


async def flip_stored_bit(dut, widx, bitpos):
    """Flip stored codeword bit (0..38) of word widx inside the macros."""
    k, b = bitpos // 8, bitpos % 8
    if bitpos >= 32:
        k, b = 4, bitpos - 32
    mem = slice_mem(dut, k)
    cur = int(mem[widx].value)
    mem[widx].value = cur ^ (1 << b)
    await NextTimeStep()


@cocotb.test()
async def test_sram39_secded(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.cyc_i.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    random.seed(1907)

    # roundtrip across the depth
    words = {a: random.getrandbits(32) for a in (0, 1, 17, 511, 1023)}
    for a, w in words.items():
        await bus(dut, a << 2, we=1, dat=w)
    for a, w in words.items():
        rdt, corr, unc = await bus(dut, a << 2)
        assert rdt == w and corr == 0 and unc == 0, f"roundtrip a={a}"

    # single-bit corruption in EVERY slice: corrected + scrubbed
    for bitpos in (0, 7, 8, 15, 21, 31, 32, 38):
        rdt, corr, unc = await bus(dut, 17 << 2)
        assert corr == 0, "precondition dirty"
        await flip_stored_bit(dut, 17, bitpos)
        rdt, corr, unc = await bus(dut, 17 << 2)
        assert rdt == words[17], f"bit {bitpos}: data corrupted through ECC"
        assert corr == 1 and unc == 0, f"bit {bitpos}: events {corr},{unc}"
        rdt, corr, unc = await bus(dut, 17 << 2)
        assert corr == 0, f"bit {bitpos}: scrub did not clean the word"

    # double-bit: detected uncorrectable
    await flip_stored_bit(dut, 511, 3)
    await flip_stored_bit(dut, 511, 27)
    rdt, corr, unc = await bus(dut, 511 << 2)
    assert unc == 1 and corr == 0, f"double-bit events {corr},{unc}"
    # heal it for the next phase
    await bus(dut, 511 << 2, we=1, dat=words[511])

    # partial write under corruption: corrected old bytes merge with new
    await flip_stored_bit(dut, 1023, 12)
    await bus(dut, 1023 << 2, we=1, dat=0x000000EE, sel=0x1)
    rdt, corr, unc = await bus(dut, 1023 << 2)
    exp = (words[1023] & 0xFFFFFF00) | 0xEE
    assert rdt == exp, f"merge under corruption: {rdt:#x} != {exp:#x}"

    dut._log.info("sram39: roundtrip, per-slice correction, scrub, "
                  "double-bit detection, corrupted-merge all good")
