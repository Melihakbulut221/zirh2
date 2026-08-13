# ZIRH-2 - random-program torture: the digest at the pins must match
# the golden model. GOLDEN env var carries the four expected bytes.
import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge

DIV = 8


async def uart_capture(dut, timeout_cycles=400_000):
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.uart_tx.value) == 0:
            break
    else:
        raise AssertionError("no start bit - the program never spoke")
    await ClockCycles(dut.clk, DIV // 2)
    bits = []
    for _ in range(9):
        await ClockCycles(dut.clk, DIV)
        await ReadOnly()
        bits.append(int(dut.uart_tx.value))
    assert bits[8] == 1, "stop bit corrupt"
    return sum(b << i for i, b in enumerate(bits[:8]))


@cocotb.test()
async def test_torture_digest(dut):
    golden = [int(b) for b in os.environ["GOLDEN"].split(",")]
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rst_n.value = 1

    got = [await uart_capture(dut) for _ in range(4)]
    assert got == golden, f"digest mismatch: rtl {got} != golden {golden}"
