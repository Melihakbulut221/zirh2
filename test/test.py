# =============================================================================
# ZIRH-2 - integration test through the Tiny Tapeout harness
#
# Run:  make -C test
#
# Runs at SILICON parameters (115.2k-class UART, telemetry every 2^16
# clocks) against the committed mask-ROM contents, and drives nothing but
# the TT pins - so CI runs the same tests against the gate-level netlist.
# =============================================================================

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly

CLK_NS = 40
DIV = 174
FRAME_LEN = 20
TLM_INTERVAL = 1 << 16
ROM_SUM = 0x2B   # XOR-fold of the committed rom_init.vh, computed offline
BOOT_CYCLES = 120_000   # crt0 + the 256-word ROM checksum loop, bit-serial

UART_TX_BIT = 4
CPU_ALIVE_BIT = 1


def bit(dut, i):
    # X-tolerant single-bit read: SERV's MINI reset leaves X on some event
    # nets for the first boot cycles (sim-only); str() is MSB-first
    return 1 if str(dut.uo_out.value)[7 - i] == "1" else 0


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 0x08     # UART RX idles high
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 4)


async def uart_capture(dut, timeout_cycles):
    """Recover one 8N1 byte from UART_TX, sampling mid-bit."""
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if bit(dut, UART_TX_BIT) == 0:
            break
    else:
        raise AssertionError("no start bit on UART_TX")
    await ClockCycles(dut.clk, DIV // 2)
    bits = []
    for _ in range(9):
        await ClockCycles(dut.clk, DIV)
        await ReadOnly()
        bits.append(bit(dut, UART_TX_BIT))
    assert bits[8] == 1, "broken stop bit"
    return sum(b << i for i, b in enumerate(bits[:8]))


async def capture_frame(dut, timeout_cycles=TLM_INTERVAL + 40_000):
    """Hunt for a v2 sync pair, then collect the remaining 15 bytes."""
    while True:
        b0 = await uart_capture(dut, timeout_cycles)
        if b0 != 0x5A:
            continue
        b1 = await uart_capture(dut, 30 * DIV)
        if b1 == 0x33:
            frame = [b0, b1]
            for _ in range(FRAME_LEN - 2):
                frame.append(await uart_capture(dut, 30 * DIV))
            return frame


@cocotb.test()
async def test_frame_carries_a_living_cpu(dut):
    """A v2 frame arrives unprompted with a valid checksum, armed set, all
    beam counters zero - and a NONZERO CPU signature that CHANGES between
    frames: the instrument reports and the computer lives, end to end."""
    await start(dut)
    await ClockCycles(dut.clk, BOOT_CYCLES)

    f1 = await capture_frame(dut)
    chk = 0
    for b in f1[:19]:
        chk ^= b
    assert f1[19] == chk, f"checksum {f1[19]:#04x} != {chk:#04x}"

    status = f1[2]
    assert (status >> 3) & 1 == 1, "armed must be set"
    assert (status >> 2) & 1 == 0, "no infra fault expected"
    assert f1[3:13] == [0] * 10, f"beam counters must be zero: {f1[3:13]}"
    assert f1[13] == 0 and f1[14] == 0, "no ECC events expected"
    assert f1[15] != 0, "CPU signature is zero - firmware never reached hk"
    assert f1[16] == 0, "BOOT must be zero - the watchdog must not have fired"
    assert f1[17] == 0 and f1[18] == 0, "no bus timeouts or frame errors"

    f2 = await capture_frame(dut)
    assert f2[15] != f1[15], (
        "CPU signature frozen across frames - the computer is not alive")
    seq1, seq2 = f1[2] >> 4, f2[2] >> 4
    assert (seq2 - seq1) % 16 >= 1, "sequence must advance"


@cocotb.test()
async def test_cpu_alive_pin_toggles(dut):
    """uo[1] must toggle while firmware writes signatures; HEARTBEAT-vs-
    CPU_ALIVE is the two-LED failure separation on the bench."""
    await start(dut)
    await ClockCycles(dut.clk, BOOT_CYCLES)

    seen = set()
    for _ in range(2_000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        seen.add(bit(dut, CPU_ALIVE_BIT))
        if len(seen) == 2:
            break
    assert seen == {0, 1}, "CPU_ALIVE pin never toggled"


async def _uart_send(dut, value):
    from cocotb.triggers import RisingEdge
    await RisingEdge(dut.clk)
    bits = [0] + [(value >> i) & 1 for i in range(8)] + [1]
    for b in bits:
        cur = int(dut.ui_in.value)
        dut.ui_in.value = (cur & ~0x08) | (b << 3)
        await ClockCycles(dut.clk, DIV)


@cocotb.test()
async def test_echo_plus_one(dut):
    """A byte into UART_RX comes back incremented - RX registers, bus,
    firmware and TX registers proven through the pins alone. Telemetry
    frames share the line; the capture hunts for the answer among them."""
    await start(dut)
    await ClockCycles(dut.clk, BOOT_CYCLES)

    await _uart_send(dut, 0x41)
    for _ in range(40):
        b = await uart_capture(dut, TLM_INTERVAL + 40_000)
        if b == 0x42:
            break
    else:
        raise AssertionError("echo answer 0x42 never appeared on the line")


@cocotb.test()
async def test_uart_commands_drive_the_instrument(dut):
    """The ground command set end to end: injections move exactly the
    right counters in the next frame, clear wipes them, and 'R' answers
    with the ROM checksum of the committed mask contents."""
    await start(dut)
    await ClockCycles(dut.clk, BOOT_CYCLES)

    await _uart_send(dut, ord('1'))     # one A-replica -> RAW_A only
    await _uart_send(dut, ord('4'))     # all-B -> ESC_B only
    f = await capture_frame(dut)
    # let one more frame pass in case the injections landed mid-snapshot
    if (f[5] << 8 | f[6]) == 0:
        f = await capture_frame(dut)
    assert (f[5] << 8 | f[6]) == 1, f"RAW_A: {f[5:7]}"
    assert (f[7] << 8 | f[8]) == 0, "ESC_A must stay zero"
    assert (f[11] << 8 | f[12]) == 1, f"ESC_B: {f[11:13]}"
    assert (f[9] << 8 | f[10]) == 0, "RAW_B must stay zero on an all-B hit"

    await _uart_send(dut, ord('C'))
    f = await capture_frame(dut)
    if f[3:13] != [0] * 10:
        f = await capture_frame(dut)
    assert f[3:13] == [0] * 10, f"clear failed: {f[3:13]}"

    await _uart_send(dut, ord('R'))
    for _ in range(60):
        b = await uart_capture(dut, TLM_INTERVAL + 40_000)
        if b == ROM_SUM:
            break
    else:
        raise AssertionError(
            f"ROM checksum byte {ROM_SUM:#04x} never answered")


@cocotb.test()
async def test_env_commands_read_the_sensors(dut):
    """The environment monitor over the command path: 'E' fires a test
    pulse down the SET chain and acks 'e', 'S' reads the incremented catch
    count, 'B' reads the burst counter, and 'T' (RTL only - the real
    oscillator cannot run in zero-delay simulation) returns a plausible
    window count. Skips itself against a mask that predates the env
    commands: old firmware echoes 'E'+1 instead of the 'e' ack."""
    await start(dut)
    await ClockCycles(dut.clk, BOOT_CYCLES)

    await _uart_send(dut, ord('E'))
    for _ in range(40):
        b = await uart_capture(dut, TLM_INTERVAL + 40_000)
        if b == ord('e'):
            break
        if b == ord('E') + 1:
            cocotb.pass_test("mask predates the env commands")
            return
    else:
        raise AssertionError("'E' neither acked nor echoed")

    await _uart_send(dut, ord('S'))
    for _ in range(40):
        b = await uart_capture(dut, TLM_INTERVAL + 40_000)
        if b == 1:
            break
    else:
        raise AssertionError("SET self-test count of 1 never answered")

    await _uart_send(dut, ord('B'))
    for _ in range(40):
        b = await uart_capture(dut, TLM_INTERVAL + 40_000)
        if b == 0:
            break
    else:
        raise AssertionError("burst count of 0 never answered")

    if os.getenv("GATES") == "yes":
        return   # the cell-level oscillator loop would hang zero-delay sim

    await _uart_send(dut, ord('T'))
    got = []
    for _ in range(40):
        b = await uart_capture(dut, TLM_INTERVAL + 40_000)
        got.append(b)
        if len(got) >= 2 and (got[-2] << 8 | got[-1]) and \
           900 <= (got[-2] << 8 | got[-1]) <= 1100:
            break
    else:
        raise AssertionError(f"no plausible window count in {got}")


@cocotb.test()
async def test_interface_commands_run_the_links(dut):
    """CAN and SpaceWire over the command path with both links looped
    back in the bench topology: 'k' fires a beacon that self-ACKs and
    lands in the receiver, 'w' brings the SpaceWire link to Run and
    round-trips a character. Counters are read hierarchically (RTL);
    under GATES only the command acks are in reach. Skips itself on a
    mask that predates the interface commands ('k' echoes 'l')."""
    await start(dut)

    async def loop_wires():
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            u = int(dut.uio_out.value)
            await RisingEdge(dut.clk)
            # CAN_TX -> CAN_RX, SPW_DOUT/SOUT -> SPW_DIN/SIN
            dut.uio_in.value = ((u >> 1) & 1) | (((u >> 4) & 1) << 2) | \
                               (((u >> 5) & 1) << 3)
    cocotb.start_soon(loop_wires())
    await ClockCycles(dut.clk, BOOT_CYCLES)

    await _uart_send(dut, ord('k'))
    for _ in range(40):
        b = await uart_capture(dut, TLM_INTERVAL + 40_000)
        if b == ord('b'):
            break
        if b == ord('k') + 1:
            cocotb.pass_test("mask predates the interface commands")
            return
    else:
        raise AssertionError("'k' neither acked nor echoed")

    await _uart_send(dut, ord('w'))
    for _ in range(40):
        b = await uart_capture(dut, TLM_INTERVAL + 40_000)
        if b == ord('y'):
            break
    else:
        raise AssertionError("'w' never acked")

    # frame time for the beacon and handshake time for the link
    await ClockCycles(dut.clk, 12_000)

    if os.getenv("GATES") == "yes":
        return   # no hierarchy to peek at in the flattened netlist

    ifc = dut.user_project.u_ifc
    assert int(ifc.u_can.rx_ok_cnt_o.value) >= 1, "CAN beacon never received"
    assert int(ifc.u_can.err_cnt_o.value) == 0, "CAN errors on a clean loop"
    assert int(ifc.u_spw.state_o.value) == 5, (
        f"SpaceWire link not in Run: state "
        f"{int(ifc.u_spw.state_o.value)}")
    assert int(ifc.u_spw.rx_char_o.value) == 0xA5, "SpW char lost"
