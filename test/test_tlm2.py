# =============================================================================
# ZIRH-2 - cocotb unit test for zirh_tlm2 (frame v2.1)
#
# Run:  make -C test -f Makefile.tlm2
#
# INTERVAL_LOG2 is overridden to 8 (frame every 256 cycles). The consumer is
# a ready/valid sink driven from Python, including a backpressure pattern.
# =============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly

INTERVAL = 256   # 2^8, must match Makefile.tlm2 override
FRAME_LEN = 20


async def start(dut, plain=0, raw_a=0, esc_a=0, raw_b=0, esc_b=0,
                armed=1, mode=0, sig=0, boot=0, busto=0, ferr=0):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.cnt_plain_i.value = plain
    dut.cnt_raw_a_i.value = raw_a
    dut.cnt_esc_a_i.value = esc_a
    dut.cnt_raw_b_i.value = raw_b
    dut.cnt_esc_b_i.value = esc_b
    dut.cnt_ecc_c_i.value = 0
    dut.cnt_ecc_u_i.value = 0
    dut.cpu_sig_i.value = sig
    dut.boot_cnt_i.value = boot
    dut.cnt_bus_to_i.value = busto
    dut.cnt_ferr_i.value = ferr
    dut.armed_i.value = armed
    dut.mode_i.value = mode
    dut.err_infra_i.value = 0
    dut.tx_ready_i.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 4)
    dut.rst_n.value = 1
    await RisingEdge(dut.clk)


async def collect_frame(dut, ready_duty=1, timeout=8 * INTERVAL):
    """Wait for a frame and collect its bytes. ready_duty=n keeps tx_ready
    high one cycle in n (n=1: always ready)."""
    frame = []
    cycle = 0
    while len(frame) < FRAME_LEN:
        cycle += 1
        assert cycle < timeout, f"frame stalled: got {len(frame)} bytes"
        await RisingEdge(dut.clk)
        ready = 1 if cycle % ready_duty == 0 else 0
        dut.tx_ready_i.value = ready
        await ReadOnly()
        if dut.tx_valid_o.value == 1 and ready:
            frame.append(int(dut.tx_data_o.value))
    await RisingEdge(dut.clk)
    dut.tx_ready_i.value = 1
    return frame


def check_frame(frame, plain=None, raw=None, esc=None, armed=None,
                infra=None, mode=None, sig=None, boot=None, busto=None,
                ferr=None):
    assert frame[0] == 0x5A and frame[1] == 0x33, (
        f"bad sync: {frame[0]:#04x} {frame[1]:#04x}")
    chk = 0
    for b in frame[:19]:
        chk ^= b
    assert frame[19] == chk, f"checksum {frame[19]:#04x}, computed {chk:#04x}"
    if sig is not None:
        assert frame[15] == sig, "CPU_SIG field wrong"
    if boot is not None:
        assert frame[16] == boot, "BOOT field wrong"
    if busto is not None:
        assert frame[17] == busto, "BUS_TO field wrong"
    if ferr is not None:
        assert frame[18] == ferr, "RX_FERR field wrong"

    status = frame[2]
    if armed is not None:
        assert (status >> 3) & 1 == armed, "armed bit wrong"
    if infra is not None:
        assert (status >> 2) & 1 == infra, "infra bit wrong"
    if mode is not None:
        assert status & 3 == mode, "mode bits wrong"
    if plain is not None:
        assert (frame[3] << 8) | frame[4] == plain, "PLAIN field wrong"
    if raw is not None:
        assert (frame[5] << 8) | frame[6] == raw, "RAW field wrong"
    if esc is not None:
        assert (frame[7] << 8) | frame[8] == esc, "ESCAPE field wrong"
    return (status >> 4) & 0xF  # seq


@cocotb.test()
async def test_frame_contents_and_checksum(dut):
    """One frame: sync, status, counter fields and checksum all correct."""
    await start(dut, plain=0x1234, raw_a=0x0056, esc_a=0x0001, armed=1, mode=2,
                sig=0xBE, boot=2, busto=1, ferr=3)
    frame = await collect_frame(dut)
    check_frame(frame, plain=0x1234, raw=0x0056, esc=0x0001, armed=1,
                infra=0, mode=2, sig=0xBE, boot=2, busto=1, ferr=3)


@cocotb.test()
async def test_seq_increments_and_interval(dut):
    """Three consecutive frames: seq increments by one, spacing = INTERVAL."""
    await start(dut)
    seqs = []
    starts = []
    cycle = 0

    for _ in range(3):
        frame = []
        while len(frame) < FRAME_LEN:
            cycle += 1
            assert cycle < 5 * INTERVAL, "frames not arriving"
            await RisingEdge(dut.clk)
            await ReadOnly()
            if dut.tx_valid_o.value == 1:
                if not frame:
                    starts.append(cycle)
                frame.append(int(dut.tx_data_o.value))
        seqs.append(check_frame(frame))

    assert (seqs[1] - seqs[0]) % 16 == 1, f"seq gap: {seqs}"
    assert (seqs[2] - seqs[1]) % 16 == 1, f"seq gap: {seqs}"
    spacing = starts[2] - starts[1]
    assert spacing == INTERVAL, f"frame spacing {spacing}, expected {INTERVAL}"


@cocotb.test()
async def test_snapshot_is_atomic(dut):
    """Counters changed right after the snapshot must not leak into the
    frame in flight - every frame is internally consistent."""
    await start(dut, plain=0x00AA, raw_a=0x0BB0, esc_a=0x0C0C)

    # hold ready low so no byte is consumed while waiting for the frame start
    dut.tx_ready_i.value = 0
    for _ in range(3 * INTERVAL):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if dut.tx_valid_o.value == 1:
            break
    await RisingEdge(dut.clk)
    dut.cnt_plain_i.value = 0xFFFF
    dut.cnt_raw_a_i.value = 0xFFFF
    dut.cnt_esc_a_i.value = 0xFFFF
    dut.boot_cnt_i.value = 0xFF

    frame = await collect_frame(dut)
    check_frame(frame, plain=0x00AA, raw=0x0BB0, esc=0x0C0C)


@cocotb.test()
async def test_infra_sticky_bit(dut):
    """An err_infra pulse between frames sets the infra bit in the NEXT
    frame only; the frame after that must be clean again."""
    await start(dut)
    frame = await collect_frame(dut)
    check_frame(frame, infra=0)

    await ClockCycles(dut.clk, 10)
    dut.err_infra_i.value = 1
    await RisingEdge(dut.clk)
    dut.err_infra_i.value = 0

    frame = await collect_frame(dut)
    check_frame(frame, infra=1)

    frame = await collect_frame(dut)
    check_frame(frame, infra=0)


@cocotb.test()
async def test_backpressure(dut):
    """With tx_ready high one cycle in three, the frame must still come out
    intact and in order."""
    await start(dut, plain=0x0102, raw_a=0x0304, esc_a=0x0506)
    frame = await collect_frame(dut, ready_duty=3)
    check_frame(frame, plain=0x0102, raw=0x0304, esc=0x0506)


@cocotb.test()
async def test_tmr_upset_mid_frame(dut):
    """Flip one replica of the byte-index register mid-frame: err_o pulses,
    the frame still completes with a valid checksum."""
    await start(dut, plain=0x0011, raw_a=0x0022, esc_a=0x0033)

    # catch the frame start without consuming byte 0
    dut.tx_ready_i.value = 0
    for _ in range(3 * INTERVAL):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if dut.tx_valid_o.value == 1:
            break

    # collect bytes, corrupting one state replica after the third
    frame = []
    injected = False
    saw_err = False
    cycle = 0
    while len(frame) < FRAME_LEN:
        cycle += 1
        assert cycle < 4 * INTERVAL, "frame stalled after upset"
        await RisingEdge(dut.clk)
        dut.tx_ready_i.value = 1
        if len(frame) == 3 and not injected:
            val = int(dut.u_st.u_ff_b.q_o.value)
            dut.u_st.u_ff_b.q_o.value = val ^ 0x02
            injected = True
        await ReadOnly()
        if dut.tx_valid_o.value == 1:
            frame.append(int(dut.tx_data_o.value))
        if dut.err_o.value == 1:
            saw_err = True

    assert injected, "never reached the injection point"
    assert saw_err, "err_o must pulse after a state replica flip"
    check_frame(frame, plain=0x0011, raw=0x0022, esc=0x0033)
