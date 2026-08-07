# =============================================================================
# ZIRH-2 - cocotb unit test for zirh_rom
#
# Run:  make -C test -f Makefile.rom
#
# The fixture image is deterministic (word i = i * 2654435761 mod 2^32), so
# both ports are checked against arithmetic, not against the DUT itself.
# =============================================================================

import cocotb
from cocotb.triggers import Timer

GOLD = lambda i: (i * 2654435761) & 0xFFFFFFFF


@cocotb.test()
async def test_instruction_port(dut):
    """Every word readable through the ibus port, combinational."""
    for i in range(256):
        dut.i_adr_i.value = i << 2
        await Timer(1, unit="ns")
        got = int(dut.i_rdt_o.value)
        assert got == GOLD(i), f"ibus word {i}: {got:#010x} != {GOLD(i):#010x}"


@cocotb.test()
async def test_data_port_and_ack(dut):
    """The dbus port serves the same image and acks combinationally."""
    for i in (0, 1, 17, 128, 255):
        dut.adr_i.value = i << 2
        dut.cyc_i.value = 1
        await Timer(1, unit="ns")
        assert int(dut.ack_o.value) == 1, "ROM must ack while cyc is high"
        got = int(dut.rdt_o.value)
        assert got == GOLD(i), f"dbus word {i}: {got:#010x}"
        dut.cyc_i.value = 0
        await Timer(1, unit="ns")
        assert int(dut.ack_o.value) == 0, "ack must fall with cyc"


@cocotb.test()
async def test_ports_are_independent(dut):
    """Different addresses on both ports at once: no interference."""
    dut.i_adr_i.value = 10 << 2
    dut.adr_i.value = 200 << 2
    dut.cyc_i.value = 1
    await Timer(1, unit="ns")
    assert int(dut.i_rdt_o.value) == GOLD(10)
    assert int(dut.rdt_o.value) == GOLD(200)
