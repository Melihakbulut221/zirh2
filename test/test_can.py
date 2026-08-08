# =============================================================================
# ZIRH-2 - cocotb unit test for zirh_can (CAN 2.0A-lite)
#
# Run:  make -C test -f Makefile.can
#
# An independent Python model of CAN framing (CRC-15 0x4599, bit
# stuffing with stuff-bits-count-toward-history semantics) judges the
# DUT from both sides: the beacon the DUT transmits is captured off the
# wire and decoded bit-exact, and hand-built frames - clean, CRC-broken,
# stuff-violating - are driven into the receiver. The self-ACK property
# (RX pulls the shared wired-AND line dominant in the ACK slot, TX sees
# it) is what a two-node bench reduces to over one loopback wire.
# =============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly, Timer

DIV = 8
BEACON_ID = 0x5A5


def crc15(bits):
    crc = 0
    for b in bits:
        fb = ((crc >> 14) & 1) ^ b
        crc = (crc << 1) & 0x7FFF
        if fb:
            crc ^= 0x4599
    return crc


def body_bits(ident, dlc, data):
    bits = [0]                                        # SOF
    bits += [(ident >> i) & 1 for i in range(10, -1, -1)]
    bits += [0, 0, 0]                                 # RTR IDE r0
    bits += [(dlc >> i) & 1 for i in range(3, -1, -1)]
    for byte in data:
        bits += [(byte >> i) & 1 for i in range(7, -1, -1)]
    crc = crc15(bits)
    bits += [(crc >> i) & 1 for i in range(14, -1, -1)]
    return bits


def stuff(bits):
    out, run, last = [], 0, None
    for b in bits:
        out.append(b)
        if b == last:
            run += 1
        else:
            run, last = 1, b
        if run == 5:
            out.append(1 - b)
            run, last = 1, 1 - b
    return out


def destuff(bits):
    out, run, last, i = [], 0, None, 0
    while i < len(bits):
        b = bits[i]
        if run == 5:
            assert b != last, "stuff violation in captured stream"
            run, last = 1, b
            i += 1
            continue
        out.append(b)
        if b == last:
            run += 1
        else:
            run, last = 1, b
        i += 1
    return out


async def start(dut, loop=True, rx_idle=1):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.rx_i.value = rx_idle
    dut.beacon_i.value = 0
    dut.beacon_data_i.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    if loop:
        cocotb.start_soon(_loopback(dut))
    # bus integration: 11 recessive bits
    await ClockCycles(dut.clk, DIV * 14)


async def _loopback(dut):
    while True:
        await RisingEdge(dut.clk)
        await ReadOnly()
        v = int(dut.tx_o.value)
        await RisingEdge(dut.clk)
        dut.rx_i.value = v


async def send_beacon(dut, data):
    await RisingEdge(dut.clk)
    dut.beacon_data_i.value = data
    dut.beacon_i.value = 1
    await RisingEdge(dut.clk)
    dut.beacon_i.value = 0


async def counters(dut):
    await ReadOnly()
    return (int(dut.tx_cnt_o.value), int(dut.rx_ok_cnt_o.value),
            int(dut.err_cnt_o.value))


async def drive_frame(dut, wire_bits, tail_recessive=14):
    """Bit-bang a stuffed frame body into rx_i; watch the DUT's ACK pull
    on tx_o during the slot. Returns True if the DUT acked."""
    acked = False
    await RisingEdge(dut.clk)
    for b in wire_bits:
        dut.rx_i.value = b
        await ClockCycles(dut.clk, DIV)
    # CRC delimiter, then the ACK slot (recessive from us; DUT may pull)
    dut.rx_i.value = 1
    await ClockCycles(dut.clk, DIV)
    for _ in range(DIV):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.tx_o.value) == 0:
            acked = True
    for _ in range(tail_recessive):
        await RisingEdge(dut.clk)
        dut.rx_i.value = 1
        await ClockCycles(dut.clk, DIV)
    return acked


@cocotb.test()
async def test_beacon_selfacks_over_loopback(dut):
    """One beacon over the loop: transmitted, received clean, self-ACKed -
    tx=1, rx_ok=1, err=0, payload byte lands."""
    await start(dut)
    await send_beacon(dut, 0x3C)
    await ClockCycles(dut.clk, DIV * 80)
    tx, rx, err = await counters(dut)
    assert tx == 1, f"tx_cnt {tx}"
    assert rx == 1, f"rx_ok {rx}"
    assert err == 0, f"err {err} - the self-ACK must have satisfied TX"
    assert int(dut.rx_data_o.value) == 0x3C


@cocotb.test()
async def test_beacon_bitstream_matches_the_standard(dut):
    """Capture the beacon off the wire and decode it with the independent
    model: stuffing legal, fields exact, CRC-15 clean."""
    await start(dut, loop=False)
    dut.rx_i.value = 1

    captured = []

    async def sniff():
        # sample mid-bit on the DUT's own grid
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            if int(dut.divq.value) == DIV // 2:
                captured.append(int(dut.tx_o.value))

    task = cocotb.start_soon(sniff())
    await send_beacon(dut, 0xB7)
    await ClockCycles(dut.clk, DIV * 90)
    task.kill()

    # find SOF, take the stuffed body
    assert 0 in captured, "no SOF ever left the transmitter"
    sof = captured.index(0)
    expect = stuff(body_bits(BEACON_ID, 1, [0xB7]))
    got = captured[sof:sof + len(expect)]
    assert got == expect, (
        f"wire bits differ from the model at offset "
        f"{next(i for i, (a, b) in enumerate(zip(got, expect)) if a != b)}")
    # tail: CRC delimiter recessive, ACK slot recessive (no receiver)
    assert captured[sof + len(expect)] == 1, "CRC delimiter must be recessive"
    body = destuff(got)
    assert crc15(body[:-15]) == int("".join(map(str, body[-15:])), 2), (
        "CRC on the wire does not match the model")


@cocotb.test()
async def test_no_ack_is_counted(dut):
    """Without a receiver the ACK slot stays recessive: the transmitter
    must count the missing ACK as an error."""
    await start(dut, loop=False)
    dut.rx_i.value = 1
    await send_beacon(dut, 0x11)
    await ClockCycles(dut.clk, DIV * 90)
    tx, rx, err = await counters(dut)
    assert tx == 1 and err == 1, f"tx {tx} err {err} - no-ACK must count"


@cocotb.test()
async def test_foreign_frame_received_and_acked(dut):
    """A hand-built frame from a different node: payload lands, rx_ok
    counts, and the DUT pulls the ACK slot dominant."""
    await start(dut, loop=False)
    dut.rx_i.value = 1
    await ClockCycles(dut.clk, DIV * 14)

    wire = stuff(body_bits(0x123, 1, [0x77]))
    acked = await drive_frame(dut, wire)
    tx, rx, err = await counters(dut)
    assert rx == 1, f"rx_ok {rx}"
    assert err == 0, f"err {err}"
    assert int(dut.rx_data_o.value) == 0x77
    assert acked, "receiver never pulled the ACK slot dominant"


@cocotb.test()
async def test_corrupt_crc_counts_and_never_acks(dut):
    """The same frame with one CRC bit flipped: error counted, no ACK, no
    payload delivery."""
    await start(dut, loop=False)
    dut.rx_i.value = 1
    await ClockCycles(dut.clk, DIV * 14)

    body = body_bits(0x123, 1, [0x77])
    body[-3] ^= 1                       # flip a CRC bit
    acked = await drive_frame(dut, stuff(body))
    tx, rx, err = await counters(dut)
    assert rx == 0, "a CRC-broken frame must not count as received"
    assert err == 1, f"err {err}"
    assert not acked, "a CRC-broken frame must never be ACKed"


@cocotb.test()
async def test_stuff_violation_counts(dut):
    """Six equal bits inside the stuffed region: stuff error, resync."""
    await start(dut, loop=False)
    dut.rx_i.value = 1
    await ClockCycles(dut.clk, DIV * 14)

    # SOF then 6 dominant bits: a naked stuff violation
    await RisingEdge(dut.clk)
    for b in [0, 0, 0, 0, 0, 0]:
        dut.rx_i.value = b
        await ClockCycles(dut.clk, DIV)
    dut.rx_i.value = 1
    await ClockCycles(dut.clk, DIV * 16)
    tx, rx, err = await counters(dut)
    assert err == 1, f"err {err} - six equal bits must be a stuff error"
    assert rx == 0


@cocotb.test()
async def test_dominant_bench_stays_silent(dut):
    """RX tied dominant from reset: integration never completes, nothing
    counts - the quiet-bench property."""
    await start(dut, loop=False, rx_idle=0)   # dominant from reset
    await ClockCycles(dut.clk, DIV * 200)
    tx, rx, err = await counters(dut)
    assert (tx, rx, err) == (0, 0, 0), f"counted on a dead bus: {(tx, rx, err)}"


@cocotb.test()
async def test_fsm_traps_and_replica_flips(dut):
    """Illegal encodings on both protocol FSMs trap back to safe states;
    a single-replica flip heals without losing the next frame."""
    await start(dut)

    # trap: force the TX FSM to 6 (double-replica hit)
    await Timer(10, unit="ns")
    for ff in (dut.u_tstate.u_ff_a, dut.u_tstate.u_ff_b):
        ff.q_o.value = Force(6)
    await Timer(1, unit="ns")
    await RisingEdge(dut.clk)
    await Timer(10, unit="ns")
    for ff in (dut.u_tstate.u_ff_a, dut.u_tstate.u_ff_b):
        ff.q_o.value = Release()
    await ClockCycles(dut.clk, 4)
    assert int(dut.u_tstate.q_o.value) == 0, "TX trap must land in idle"

    # trap: RX FSM to 5
    await Timer(10, unit="ns")
    for ff in (dut.u_rstate.u_ff_a, dut.u_rstate.u_ff_b):
        ff.q_o.value = Force(5)
    await Timer(1, unit="ns")
    await RisingEdge(dut.clk)
    await Timer(10, unit="ns")
    for ff in (dut.u_rstate.u_ff_a, dut.u_rstate.u_ff_b):
        ff.q_o.value = Release()
    await ClockCycles(dut.clk, 4)
    assert int(dut.u_rstate.q_o.value) == 0, "RX trap must land in integration"

    # single-replica flip on the RX FSM, then a frame must still work
    await Timer(10, unit="ns")
    dut.u_rstate.u_ff_a.q_o.value = Force(int(dut.u_rstate.q_o.value) ^ 1)
    await Timer(1, unit="ns")
    await RisingEdge(dut.clk)
    await Timer(10, unit="ns")
    dut.u_rstate.u_ff_a.q_o.value = Release()
    await ClockCycles(dut.clk, DIV * 14)   # re-integrate after the trap

    await send_beacon(dut, 0x9E)
    await ClockCycles(dut.clk, DIV * 80)
    tx, rx, err = await counters(dut)
    assert rx >= 1 and int(dut.rx_data_o.value) == 0x9E, (
        "frame lost after FSM faults - the machines did not recover")
