# =============================================================================
# ZIRH-2 - the programming interface, proven end to end
# test/test_isp.py
#
# The chip's answer to "write any program you want into it": strap
# ui[2], stream a CRC32-sealed image over UART into the ECC RAM bank,
# and the CPU runs it - or the chip proves it refused to. Three
# contracts:
#
#   1. A valid image commits: the loader accepts, the CPU fetches from
#      the bank, and the LOADED program's signature reaches telemetry -
#      arbitrary code, written after tape-out, visibly alive.
#   2. A corrupt image never runs: wrong CRC is refused at the
#      read-back boundary and the chip boots the mask ROM instead -
#      the fallback is the immutable golden firmware, not silence.
#   3. Straps low is yesterday's chip: no loader, ROM boot, the whole
#      legacy suite untouched (regression by the existing suites).
#
# The test carries its own five-instruction flight program and a tiny
# three-format assembler - the whole point of an ISP is that firmware
# is data, so the testbench writes firmware.
# =============================================================================

import zlib

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

CLK_NS = 40
DIV = 20                 # RESET_DIV override in Makefile.isp
WD_LIMIT_LOG2 = 17

MAGIC = 0x5A495248
HK_SIG = 0x3000          # HK_BASE + 0x00, the telemetry signature register


# --- a three-format assembler: exactly what a 13-word bank needs ------------
def lui(rd, imm20):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | 0x37


def addi(rd, rs1, imm):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (rd << 7) | 0x13


def sw(rs2, rs1, off):
    return (((off >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | \
           (0x2 << 12) | ((off & 0x1F) << 7) | 0x23


def jal(rd, off):
    imm = off & 0x1FFFFF
    return (((imm >> 20) & 1) << 31) | (((imm >> 1) & 0x3FF) << 21) | \
           (((imm >> 11) & 1) << 20) | (((imm >> 12) & 0xFF) << 12) | \
           (rd << 7) | 0x6F


# t0=x5 -> HK base, t1=x6 counts; the signature changes every loop pass,
# which is both the sign-on and the liveness proof. CPU_SIG sits at
# HK_BASE+0x08 (zirh_hk reg_sel 2).
PROGRAM = [
    lui(5, HK_SIG >> 12),        # t0 = 0x3000
    addi(6, 0, 1),               # t1 = 1
    sw(6, 5, 8),                 # CPU_SIG = t1
    addi(6, 6, 1),               # t1++
    jal(0, -8),                  # back to the store
]


def image(words, crc=None, magic=MAGIC):
    payload = b''.join(w.to_bytes(4, 'little') for w in words)
    c = zlib.crc32(payload) if crc is None else crc
    return (magic.to_bytes(4, 'little') + len(words).to_bytes(2, 'little')
            + (1).to_bytes(2, 'little') + c.to_bytes(4, 'little') + payload)


async def start_strapped(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 0x0C            # rx idle high + ISP strap on ui[2]
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 50)    # strap sampled, loader in S_HDR


async def uart_send(dut, value):
    await RisingEdge(dut.clk)
    bits = [0] + [(value >> i) & 1 for i in range(8)] + [1]
    for b in bits:
        cur = int(dut.ui_in.value)
        dut.ui_in.value = (cur & ~0x08) | (b << 3)
        await ClockCycles(dut.clk, DIV)
    await ClockCycles(dut.clk, 3 * DIV)   # inter-byte gap


async def stream_image(dut, blob):
    for b in blob:
        await uart_send(dut, b)


@cocotb.test()
async def test_isp_loads_and_runs_arbitrary_code(dut):
    """A five-instruction program written by the testbench is streamed
    over UART, committed by the read-back CRC, and RUNS: the bank is
    selected, the CPU fetches from ECC RAM, and the loaded loop's
    signature marches through telemetry."""
    await start_strapped(dut)

    await stream_image(dut, image(PROGRAM))
    await ClockCycles(dut.clk, 400)       # verify pass + release

    assert int(dut.bl_sel.value) == 1, "valid image must commit the bank"
    assert int(dut.isp_hold.value) == 0, "hold must release after commit"

    # the loaded program's signature must MOVE - twice, to prove a loop
    await ClockCycles(dut.clk, 60_000)
    s1 = int(dut.cpu_sig.value)
    await ClockCycles(dut.clk, 60_000)
    s2 = int(dut.cpu_sig.value)
    await ClockCycles(dut.clk, 60_000)
    s3 = int(dut.cpu_sig.value)
    assert s1 != s2 or s2 != s3, \
        f"loaded program's signature frozen: {s1:02x} {s2:02x} {s3:02x}"
    assert int(dut.bl_sel.value) == 1, "bank must stay selected while alive"


@cocotb.test()
async def test_isp_refuses_corrupt_image_and_boots_rom(dut):
    """The same stream with a wrong CRC: the read-back boundary refuses
    it, the bank is never selected, and the chip falls back to the mask
    ROM - whose firmware then proves itself alive on telemetry."""
    await start_strapped(dut)

    await stream_image(dut, image(PROGRAM, crc=0xDEADBEEF))
    await ClockCycles(dut.clk, 400)

    assert int(dut.bl_sel.value) == 0, "corrupt image must never run"
    assert int(dut.isp_hold.value) == 0, "reject must release the CPU"

    # the fallback is the golden ROM: its firmware signs on eventually
    for _ in range(40):
        await ClockCycles(dut.clk, 20_000)
        if int(dut.cpu_sig.value) != 0:
            break
    else:
        raise AssertionError("ROM fallback never signed on after reject")


@cocotb.test()
async def test_isp_bad_magic_refused_at_header(dut):
    """A wrong magic never even reaches the bank: refused at the header,
    ROM fallback, CPU alive."""
    await start_strapped(dut)

    await stream_image(dut, image(PROGRAM, magic=0x4B41525A))
    await ClockCycles(dut.clk, 400)

    assert int(dut.bl_sel.value) == 0, "wrong magic must never run"
    for _ in range(40):
        await ClockCycles(dut.clk, 20_000)
        if int(dut.cpu_sig.value) != 0:
            break
    else:
        raise AssertionError("ROM fallback never signed on after bad magic")
