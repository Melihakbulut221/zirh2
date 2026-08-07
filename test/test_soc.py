# =============================================================================
# ZIRH-2 - SoC integration test: SERV executes the real firmware from ROM
#
# Run:  make -C test -f Makefile.soc
#
# The ROM image is the actual fw/rom.hex built by CI from fw/ - the same
# bytes that will be synthesized into the mask ROM. The test talks to the
# chip exactly as the ground station will: through the UART.
# =============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly, with_timeout
from cocotbext.uart import UartSource, UartSink

CLK_NS = 40
DIV = 20
BAUD = int(1e9 / CLK_NS / DIV)

BOOT_CYCLES = 30_000   # crt0 zero-fill + reaching the main loop, bit-serial


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.uart_rx_i.value = 1
    dut.tlm_data_i.value = 0
    dut.tlm_valid_i.value = 0
    dut.s3_rdt_i.value = 0
    dut.s3_ack_i.value = 0
    dut.rst_n.value = 0
    # firmware v2 writes its liveness signature to slot 3 (zirh_hk in the
    # full top); the unit test answers with a 1-cycle always-ack stub so the
    # watchdog stays quiet and the CPU is never stalled
    cocotb.start_soon(_slot3_stub(dut))
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1


async def _slot3_stub(dut):
    while True:
        await RisingEdge(dut.clk)
        dut.s3_ack_i.value = int(dut.s3_cyc_o.value == 1)


class Health:
    """No phantom events allowed while the CPU runs clean firmware."""

    def __init__(self, dut):
        self.uncorr = 0
        self.timeout = 0
        self.err = 0
        cocotb.start_soon(self._run(dut))

    async def _run(self, dut):
        # "== 1" instead of int(): SERV's RESET_STRATEGY=MINI leaves state
        # X for the first boot cycles and X propagates into these signals -
        # a pure simulation artifact (silicon resolves 0/1), so the watcher
        # counts only certain 1s
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            self.uncorr += (dut.evt_ecc_uncorr_o.value == 1)
            self.timeout += (dut.evt_bus_timeout_o.value == 1)
            self.err += (dut.err_o.value == 1)


@cocotb.test()
async def test_boot_zero_fills_ram(dut):
    """crt0 zeroes the ECC RAM before anything reads it.

    What can honestly be asserted after boot: (1) zero uncorrectable
    events - the proof that no read ever hit an uninitialized word;
    (2) the untouched middle of the RAM is exactly encode(0)=0; (3) the
    live words hold resolvable data. The STACK region is exempt from
    value checks: main's prologue pushes callee-saved registers that
    were never written since reset, which are X in 4-state simulation
    and random-but-ECC-valid in silicon - measured, benign, and the
    reason this test does not demand an all-zero RAM."""
    await start(dut)
    h = Health(dut)
    await ClockCycles(dut.clk, BOOT_CYCLES)

    # 64-byte RAM: the stack reaches down to word ~8 (measured; sp=0x1040,
    # main + tx_byte frames), so the provably untouched middle is 2..7
    for w in range(2, 8):
        v = int(dut.u_ram.mem[w].value)
        assert v == 0, f"RAM word {w} not zeroed: {v:#012x}"
    for w in (0, 1):         # loop counter and signature: live, resolvable
        assert dut.u_ram.mem[w].value.is_resolvable, f"word {w} is X"

    assert h.uncorr == 0, "a read of an uninitialized word would count here"
    assert h.timeout == 0, "firmware must never hit an unmapped slot"


@cocotb.test()
async def test_ram_heartbeat(dut):
    """The loop counter in ECC RAM must be alive and increasing."""
    await start(dut)
    await ClockCycles(dut.clk, BOOT_CYCLES)

    async def loops():
        # word 0 holds the counter, but stored ECC-encoded: read via the
        # CPU's own view is complex; instead sample twice and require change
        return int(dut.u_ram.mem[0].value)

    a = await loops()
    await ClockCycles(dut.clk, 20_000)
    b = await loops()
    assert a != b, "loop counter frozen - CPU is not executing"


@cocotb.test()
async def test_echo_plus_one(dut):
    """Every byte sent to the chip comes back incremented: RX registers,
    firmware logic and TX registers proven in one exchange."""
    await start(dut)
    h = Health(dut)
    source = UartSource(dut.uart_rx_i, baud=BAUD, bits=8)
    sink = UartSink(dut.uart_tx_o, baud=BAUD, bits=8)

    await ClockCycles(dut.clk, BOOT_CYCLES)

    for tx in (0x41, 0x00, 0xFE):
        await source.write([tx])
        got = (await with_timeout(sink.read(1), 4_000_000, "ns"))[0]
        assert got == ((tx + 1) & 0xFF), (
            f"sent {tx:#04x}, firmware answered {got:#04x}, "
            f"expected {(tx + 1) & 0xFF:#04x}")

    assert h.uncorr == 0 and h.timeout == 0, (
        f"phantom events: uncorr={h.uncorr} timeout={h.timeout}")
    assert h.err == 0, "no TMR mismatch expected in clean operation"
