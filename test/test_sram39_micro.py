import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, NextTimeStep, ReadOnly, RisingEdge


async def bus(dut, adr, we=0, dat=0, sel=0xF):
    await NextTimeStep()
    dut.cyc_i.value = 1
    dut.adr_i.value = adr
    dut.we_i.value = we
    dut.dat_i.value = dat
    dut.sel_i.value = sel
    for _ in range(16):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.ack_o.value) == 1:
            v = dut.rdt_o.value
            r = (int(v) if v.is_resolvable else None,
                 int(dut.evt_corr_o.value), int(dut.evt_uncorr_o.value))
            await NextTimeStep()
            dut.cyc_i.value = 0
            await RisingEdge(dut.clk)
            return r
    raise AssertionError("no ack")


@cocotb.test()
async def micro(dut):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.cyc_i.value = 0
    dut.scrub_en_i.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)

    async def stspy():
        prev = (None, None, None)
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            cur = (str(dut.state.value), str(dut.row_q.value),
                   str(dut.sadr_q.value))
            if cur != prev:
                dut._log.info(
                    f"ST t={cocotb.utils.get_sim_time('ns'):.0f} "
                    f"st={cur[0]} row_q={int(cur[1],2) if 'x' not in cur[1] else cur[1]} "
                    f"sadr={int(cur[2],2) if 'x' not in cur[2] else cur[2]} "
                    f"take={dut.scrub_take.value} pend={dut.pend_q.value} "
                    f"cyc={dut.cyc_i.value}")
                prev = cur
    cocotb.start_soon(stspy())

    async def m4spy():
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            if str(dut.u_m4.wen.value) == '1' or str(dut.u_m4.ren.value) == '1':
                dut._log.info(
                    f"M4 t={cocotb.utils.get_sim_time('ns'):.0f} "
                    f"wen={dut.u_m4.wen.value} ren={dut.u_m4.ren.value} "
                    f"adr={int(dut.u_m4.adr.value)} d={dut.u_m4.d.value} "
                    f"q={dut.u_m4.q.value} st={int(dut.state.value)}")
    cocotb.start_soon(m4spy())

    for a in range(3):
        await bus(dut, a << 2, we=1, dat=0x11111111 * (a + 1))
    dut._log.info("MICRO init bitti, scrub aciliyor")
    dut.scrub_en_i.value = 1
    await ClockCycles(dut.clk, 40)   # birkac beat
    for a in range(3):
        rdt, corr, unc = await bus(dut, a << 2)
        dut._log.info(f"MICRO row{a}: {rdt:#010x} corr={corr} unc={unc}")
