# =============================================================================
# ZIRH-2 - cocotb unit test for zirh_spw (SpaceWire-lite)
#
# Run:  make -C test -f Makefile.spw
#
# The link talks to itself: a forwarder task copies DOUT/SOUT back into
# DIN/SIN, which is a legal SpaceWire topology (self-loop) and reaches
# Run through the full handshake. The suite pins the six-state FSM to
# the standard's sequence, round-trips a data character, proves parity
# and disconnect errors send the link through ErrorReset AND that it
# climbs back on its own, and drives the two illegal state encodings to
# show the safe-state trap lands in ErrorReset instead of wedging.
# =============================================================================

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly, Timer

S_ERRRST, S_ERRWAIT, S_READY, S_STARTED, S_CONNECT, S_RUN = range(6)
NAMES = ["ErrorReset", "ErrorWait", "Ready", "Started", "Connecting", "Run"]


async def start(dut, loop=True):
    cocotb.start_soon(Clock(dut.clk, 40, unit="ns").start())
    dut.din_i.value = 0
    dut.sin_i.value = 0
    dut.link_en_i.value = 0
    dut.tx_char_i.value = 0
    dut.tx_char_v_i.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    if loop:
        cocotb.start_soon(_loopback(dut))
    await RisingEdge(dut.clk)


async def _loopback(dut):
    while True:
        await RisingEdge(dut.clk)
        await ReadOnly()
        d, s = int(dut.dout_o.value), int(dut.sout_o.value)
        await RisingEdge(dut.clk)
        dut.din_i.value = d
        dut.sin_i.value = s


def state(dut):
    return int(dut.state_o.value)


async def wait_state(dut, want, timeout, seen=None):
    for _ in range(timeout):
        await RisingEdge(dut.clk)
        await ReadOnly()
        s = state(dut)
        if seen is not None:
            seen.append(s)
        if s == want:
            return True
    return False


@cocotb.test()
async def test_fsm_walks_the_standard_sequence(dut):
    """ErrorReset -> ErrorWait -> Ready, hold for link_en, then Started ->
    Connecting -> Run through the NULL/FCT handshake - the six states in
    the standard's order, no skips."""
    await start(dut)

    assert state(dut) == S_ERRRST, "must come up in ErrorReset"
    assert await wait_state(dut, S_ERRWAIT, 200), "never reached ErrorWait"
    assert await wait_state(dut, S_READY, 400), "never reached Ready"

    # Ready holds until the link is enabled
    await ClockCycles(dut.clk, 300)
    assert state(dut) == S_READY, "Ready must hold with link_en low"

    trace = []
    dut.link_en_i.value = 1
    assert await wait_state(dut, S_RUN, 4000, trace), "never reached Run"

    # the sequence must be Started then Connecting then Run, in order,
    # with no illegal codes and no relapse through ErrorReset
    order = [s for i, s in enumerate(trace) if i == 0 or s != trace[i - 1]]
    assert S_STARTED in order and S_CONNECT in order, f"sequence: {order}"
    assert order.index(S_STARTED) < order.index(S_CONNECT) < order.index(S_RUN), (
        f"handshake out of order: {[NAMES[s] for s in order]}")
    assert all(s <= S_RUN for s in trace), "illegal state code observed"
    assert S_ERRRST not in order, "link fell back through ErrorReset"
    assert int(dut.null_cnt_o.value) >= 1, "no NULLs counted on a live link"
    assert int(dut.err_cnt_o.value) == 0, "clean link must count no errors"


@cocotb.test()
async def test_data_char_roundtrip(dut):
    """A queued data character crosses the loop and lands byte-exact."""
    await start(dut)
    dut.link_en_i.value = 1
    assert await wait_state(dut, S_RUN, 4000)

    for byte in (0xA5, 0x0F, 0x81):
        await RisingEdge(dut.clk)
        dut.tx_char_i.value = byte
        dut.tx_char_v_i.value = 1
        await RisingEdge(dut.clk)
        dut.tx_char_v_i.value = 0

        for _ in range(2000):
            await RisingEdge(dut.clk)
            await ReadOnly()
            if int(dut.rx_char_v_o.value) == 1:
                break
        else:
            raise AssertionError(f"char {byte:#04x} never arrived")
        assert int(dut.rx_char_o.value) == byte, (
            f"{int(dut.rx_char_o.value):#04x} != {byte:#04x}")
    assert int(dut.err_cnt_o.value) == 0


@cocotb.test()
async def test_parity_error_resets_and_link_recovers(dut):
    """A glitched data line: parity error counted, FSM through ErrorReset,
    and the link must climb back to Run by itself."""
    await start(dut)
    dut.link_en_i.value = 1
    assert await wait_state(dut, S_RUN, 4000)
    errs = int(dut.err_cnt_o.value)

    # stomp the data input for one bit period against the loopback
    await RisingEdge(dut.clk)   # leave the ReadOnly wait_state ended in
    dut.din_i.value = Force(1)
    await ClockCycles(dut.clk, 8)
    dut.din_i.value = Release()

    assert await wait_state(dut, S_ERRRST, 600), "error must reset the link"
    assert int(dut.err_cnt_o.value) > errs, "the error was not counted"
    assert await wait_state(dut, S_RUN, 6000), "link did not self-recover"


@cocotb.test()
async def test_disconnect_detected(dut):
    """Silence in Run for T_DISC bit periods is a disconnect: counted,
    ErrorReset entered."""
    await start(dut, loop=False)
    cocotb.start_soon(_loopback(dut))
    dut.link_en_i.value = 1
    assert await wait_state(dut, S_RUN, 4000)
    errs = int(dut.err_cnt_o.value)

    # freeze the lines: kill traffic without an edge (disconnect, not parity)
    await RisingEdge(dut.clk)   # leave the ReadOnly wait_state ended in
    dut.din_i.value = Force(0)
    dut.sin_i.value = Force(0)
    ok = await wait_state(dut, S_ERRRST, 2000)
    await RisingEdge(dut.clk)   # wait_state returns in ReadOnly
    dut.din_i.value = Release()
    dut.sin_i.value = Release()
    assert ok, "silence never tripped the disconnect timer"
    assert int(dut.err_cnt_o.value) > errs, "disconnect was not counted"


@cocotb.test()
async def test_illegal_states_trap_to_errorreset(dut):
    """Both unreachable encodings (6 and 7): a double-replica hit parks
    the voted state there, and the trap must fall into ErrorReset next
    cycle and the link must come back - the safe-state property."""
    await start(dut)
    dut.link_en_i.value = 1
    assert await wait_state(dut, S_RUN, 4000)

    for bad in (6, 7):
        await RisingEdge(dut.clk)
        await Timer(10, unit="ns")
        for ff in (dut.u_state.u_ff_a, dut.u_state.u_ff_b):
            ff.q_o.value = Force(bad)
        await Timer(1, unit="ns")
        await RisingEdge(dut.clk)
        await Timer(10, unit="ns")
        for ff in (dut.u_state.u_ff_a, dut.u_state.u_ff_b):
            ff.q_o.value = Release()

        found = False
        for _ in range(20):
            await RisingEdge(dut.clk)
            await ReadOnly()
            if state(dut) == S_ERRRST:
                found = True
                break
        assert found, f"illegal state {bad} did not trap to ErrorReset"
        assert await wait_state(dut, S_RUN, 6000), (
            f"link never recovered after the {bad} trap")


@cocotb.test()
async def test_state_replica_flip_heals_in_place(dut):
    """A single-replica hit on the state register: voted feedback heals it
    without the link ever leaving Run."""
    await start(dut)
    dut.link_en_i.value = 1
    assert await wait_state(dut, S_RUN, 4000)

    for _ in range(5):
        await RisingEdge(dut.clk)
        await Timer(10, unit="ns")
        dut.u_state.u_ff_a.q_o.value = Force(S_RUN ^ 0x3)
        await Timer(1, unit="ns")
        await RisingEdge(dut.clk)
        await Timer(10, unit="ns")
        dut.u_state.u_ff_a.q_o.value = Release()
        await ClockCycles(dut.clk, 3)
        assert state(dut) == S_RUN, "single flip must not leave Run"
        a = str(dut.u_state.u_ff_a.q_o.value)
        b = str(dut.u_state.u_ff_b.q_o.value)
        assert a == b, "replicas did not reconverge"
    # a healed link still moves data
    await RisingEdge(dut.clk)
    dut.tx_char_i.value = 0x42
    dut.tx_char_v_i.value = 1
    await RisingEdge(dut.clk)
    dut.tx_char_v_i.value = 0
    for _ in range(2000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.rx_char_v_o.value) == 1:
            break
    else:
        raise AssertionError("char lost after replica flips")
    assert int(dut.rx_char_o.value) == 0x42
