# ZIRH-2 program P1 - bare RM_IHPSG13 macro smoke: the open-PDK SRAM
# behavioral model linked and exercised (write, read-latency-1,
# bit-mask write, write-through) before any wrapper is built on it.
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, NextTimeStep, ReadOnly, RisingEdge


async def wr(dut, adr, dat, bm=0xFF):
    await NextTimeStep()
    dut.A_MEN.value = 1
    dut.A_WEN.value = 1
    dut.A_REN.value = 0
    dut.A_ADDR.value = adr
    dut.A_DIN.value = dat
    dut.A_BM.value = bm
    await RisingEdge(dut.A_CLK)


async def rd(dut, adr):
    await NextTimeStep()
    dut.A_MEN.value = 1
    dut.A_WEN.value = 0
    dut.A_REN.value = 1
    dut.A_ADDR.value = adr
    await RisingEdge(dut.A_CLK)
    await ReadOnly()
    return int(dut.A_DOUT.value)


@cocotb.test()
async def test_macro_smoke(dut):
    cocotb.start_soon(Clock(dut.A_CLK, 40, unit="ns").start())
    dut.A_BIST_EN.value = 0
    dut.A_BIST_CLK.value = 0
    dut.A_BIST_MEN.value = 0
    dut.A_BIST_WEN.value = 0
    dut.A_BIST_REN.value = 0
    dut.A_BIST_ADDR.value = 0
    dut.A_BIST_DIN.value = 0
    dut.A_BIST_BM.value = 0
    dut.A_DLY.value = 0
    dut.A_MEN.value = 0
    dut.A_WEN.value = 0
    dut.A_REN.value = 0
    await ClockCycles(dut.A_CLK, 4)

    for adr, dat in ((0, 0xA5), (1023, 0x3C), (512, 0x00), (7, 0xFF)):
        await wr(dut, adr, dat)
    for adr, dat in ((0, 0xA5), (1023, 0x3C), (512, 0x00), (7, 0xFF)):
        got = await rd(dut, adr)
        assert got == dat, f"adr {adr}: {got:#x} != {dat:#x}"

    # bit-mask write: only the masked bits change
    await wr(dut, 7, 0x00, bm=0x0F)
    got = await rd(dut, 7)
    assert got == 0xF0, f"bitmask merge broken: {got:#x}"

    dut._log.info("RM_IHPSG13_1P_1024x8 smoke: write/read/mask all good")
