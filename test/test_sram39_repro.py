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
    raise AssertionError("no ack")


@cocotb.test()
async def repro(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.cyc_i.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    random.seed(1907)
    words = {}
    for a in range(8):
        words[a] = random.getrandbits(32)
        await NextTimeStep()
        dut.cyc_i.value = 1
        dut.adr_i.value = a << 2
        dut.we_i.value = 1
        dut.dat_i.value = words[a]
        dut.sel_i.value = 0xF
        await ReadOnly()
        if a < 3:
            dut._log.info(
                f"WCYC row{a}: wrnow={dut.wr_now.value} "
                f"wrfull={dut.wr_full.value} ack_q={dut.ack_o.value} "
                f"state={dut.state.value} "
                f"enc_hi={str(dut.enc_wr.value)[:7]} "
                f"m4d={dut.u_m4.d.value} m4wen={dut.u_m4.wen.value} "
                f"m0d={dut.u_m0.d.value}")
        for _ in range(16):
            await RisingEdge(dut.clk)
            await ReadOnly()
            if int(dut.ack_o.value) == 1:
                break
        await NextTimeStep()
        dut.cyc_i.value = 0
        await RisingEdge(dut.clk)
    for a in range(8):
        rdt, corr, unc = await bus(dut, a << 2)
        who = [b for b in range(8) if rdt == words[b]]
        dut._log.info(f"REPRO row{a}: corr={corr} unc={unc} "
                      f"ok={rdt == words[a]} matches_row={who}")
