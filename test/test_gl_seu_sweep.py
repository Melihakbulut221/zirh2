# =============================================================================
# ZIRH-2 - systematic gate-level SEU sweep: the pre-beam prediction
#
# The beam will measure ESCAPE(A) vs ESCAPE(B) - the macro-bound chain
# against the tool-placed chain. This module registers the simulation
# half of that prediction BEFORE any beam time, on the netlist that
# ships (docs/PREDICTION.md holds the combined claim):
#
#   SINGLES (exhaustive) - every replica flop of both chains, every bit
#     of every replica, flipped one at a time in both pattern phases:
#     384 injections. Every one must land as exactly one RAW count and
#     ZERO escapes - the voted feedback heals a lone upset in one cycle,
#     in either chain, at silicon timings.
#
#   PAIRS (the escape window) - cross-replica double flips:
#     same bit, same cycle      -> exactly one escape each (the voter
#                                  majority is broken at that bit)
#     same bit, one cycle apart -> zero escapes (the first flip healed
#                                  before the second landed)
#     different bits, same cycle-> zero escapes (each bit still has a
#                                  2-of-3 majority)
#
# Together: an escape requires the SAME bit hit in TWO replicas in the
# SAME cycle. Simulation says the chains are logically identical - the
# beam escape ratio therefore measures spatial simultaneous-double-upset
# probability alone, which is the layout quantity chain A's macro
# placement floor was bought to suppress. That is the falsifiable claim.
#
# Injection points are the replica output nets at the flattened top
# (u_hk.{a,b}_q{a,b,c}[bit]) - the same discipline the RTL suites and
# test_gl_campaign converged on: Force through exactly one clock edge,
# flush with a timestep, Release after the edge.
#
# Runs inside the gl_test job (GATES=yes); RTL runs pass vacuously.
# =============================================================================

import os

import cocotb
from cocotb.clock import Clock
from cocotb.handle import Force, Release
from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge, Timer

CLK_NS = 40
DIV = 174
BOOT_CYCLES = 120_000
TLM_INTERVAL = 1 << 16
FRAME_LEN = 20
UART_TX_BIT = 4
ARMED_BIT = 7

CHAINS = ("a", "b")
REPLICAS = ("qa", "qb", "qc")
N = 32


def gl_only():
    if os.getenv("GATES") != "yes":
        cocotb.pass_test("gate-level module; RTL runs skip it")


def bit(dut, i):
    return 1 if str(dut.uo_out.value)[7 - i] == "1" else 0


def net_names():
    return [f"u_hk.{c}_{r}[{i}]"
            for c in CHAINS for r in REPLICAS for i in range(N)]


def build_net_map(dut):
    wanted = set(net_names())
    found = {}
    for h in dut.user_project:
        if h._name in wanted:
            found[h._name] = h
    missing = wanted - set(found)
    assert not missing, f"replica nets unresolved: {sorted(missing)[:6]}..."
    return found


async def wait_armed(dut):
    """Firmware mode writes reload the 36-cycle warm-up; land after the
    last one rather than asserting at a fixed cycle."""
    for _ in range(300_000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if bit(dut, ARMED_BIT) == 1:
            await RisingEdge(dut.clk)
            return
    raise AssertionError("monitor never armed after boot")


async def start(dut):
    cocotb.start_soon(Clock(dut.clk, CLK_NS, unit="ns").start())
    dut.ena.value = 1
    dut.ui_in.value = 0x08
    dut.uio_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, BOOT_CYCLES)


async def uart_send(dut, value):
    await RisingEdge(dut.clk)
    bits = [0] + [(value >> i) & 1 for i in range(8)] + [1]
    for b in bits:
        cur = int(dut.ui_in.value)
        dut.ui_in.value = (cur & ~0x08) | (b << 3)
        await ClockCycles(dut.clk, DIV)


async def uart_capture(dut, timeout_cycles):
    for _ in range(timeout_cycles):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if bit(dut, UART_TX_BIT) == 0:
            break
    else:
        return None
    await ClockCycles(dut.clk, DIV // 2)
    bits = []
    for _ in range(9):
        await ClockCycles(dut.clk, DIV)
        await ReadOnly()
        bits.append(bit(dut, UART_TX_BIT))
    if bits[8] != 1:
        return None
    return sum(b << i for i, b in enumerate(bits[:8]))


async def capture_frame(dut):
    while True:
        b0 = await uart_capture(dut, TLM_INTERVAL + 40_000)
        assert b0 is not None, "telemetry went silent mid-sweep"
        if b0 != 0x5A:
            continue
        b1 = await uart_capture(dut, 30 * DIV)
        if b1 == 0x33:
            frame = [b0, b1]
            for _ in range(FRAME_LEN - 2):
                nb = await uart_capture(dut, 30 * DIV)
                if nb is None:
                    break
                frame.append(nb)
            if len(frame) == FRAME_LEN:
                return frame


def counts(frame):
    """(raw_a, esc_a, raw_b, esc_b) from a v2 frame."""
    return (frame[5] << 8 | frame[6], frame[7] << 8 | frame[8],
            frame[9] << 8 | frame[10], frame[11] << 8 | frame[12])


async def settled_counts(dut):
    """Counters after the last injection drained. Injections finish, the
    rings drain in at most N+16 cycles (caller waited), so the NEXT frame
    snapshot after a full interval carries the final counts - discard one
    possibly-straddling frame, read the next. Deterministic two frames."""
    await capture_frame(dut)
    return counts(await capture_frame(dut))


async def clear_counters(dut):
    await uart_send(dut, ord('C'))
    await capture_frame(dut)
    for _ in range(2):
        if counts(await capture_frame(dut)) == (0, 0, 0, 0):
            return
    raise AssertionError("clear never reached the counters")


async def flip(dut, schedule):
    """schedule: list of (cycle_offset, [handles]) - force each handle's
    net inverted across exactly the one capture edge at its offset."""
    await RisingEdge(dut.clk)
    await Timer(10, unit="ns")
    horizon = max(off for off, _ in schedule)
    by_off = {}
    for off, hs in schedule:
        by_off.setdefault(off, []).extend(hs)
    forced = []
    for cycle in range(horizon + 1):
        for h in by_off.get(cycle, []):
            cur = h.value
            v = int(cur) if cur.is_resolvable else 0
            h.value = Force(v ^ 1)
            forced.append(h)
        await Timer(1, unit="ns")
        await RisingEdge(dut.clk)
        await Timer(10, unit="ns")
        for h in forced:
            h.value = Release()
        forced = []


@cocotb.test()
async def test_gl_seu_singles_never_escape(dut):
    """Exhaustive singles: all 192 replica flops of both chains, both
    pattern phases - 384 injections. RAW must count every one; ESC must
    stay EXACTLY zero in both chains. This is the healed-in-one-cycle
    mechanism proven flop by flop at silicon timings."""
    gl_only()
    await start(dut)
    nets = build_net_map(dut)

    await wait_armed(dut)
    await clear_counters(dut)

    for chain in CHAINS:
        for phase in range(2):
            for rep in REPLICAS:
                dut._log.info(
                    f"seu sweep singles: chain {chain} phase {phase} "
                    f"replica {rep} (32 flips)")
                for i in range(N):
                    h = nets[f"u_hk.{chain}_{rep}[{i}]"]
                    await flip(dut, [(phase, [h])])
                    await ClockCycles(dut.clk, 24)

    await ClockCycles(dut.clk, 64)
    raw_a, esc_a, raw_b, esc_b = await settled_counts(dut)
    assert esc_a == 0 and esc_b == 0, (
        f"a single upset ESCAPED a voter: esc_a={esc_a} esc_b={esc_b}")
    assert raw_a == 192, f"RAW_A {raw_a} != 192: injections went unseen"
    assert raw_b == 192, f"RAW_B {raw_b} != 192: injections went unseen"

    await uart_send(dut, 0x70)
    got = await uart_capture(dut, TLM_INTERVAL + 40_000)
    for _ in range(40):
        if got == 0x71:
            break
        got = await uart_capture(dut, TLM_INTERVAL + 40_000)
    assert got == 0x71, "CPU lost after the singles sweep"


@cocotb.test()
async def test_gl_seu_pairs_map_the_escape_window(dut):
    """Cross-replica pairs, all 32 bits of both chains, three geometries:
    same-bit same-cycle MUST escape (exactly once each); same-bit one
    cycle apart and different-bit same-cycle MUST NOT. The escape window
    is one bit, one cycle - so the beam ratio measures spatial
    double-upset probability and nothing else."""
    gl_only()
    await start(dut)
    nets = build_net_map(dut)

    await wait_armed(dut)

    for chain in CHAINS:
        await clear_counters(dut)

        # same bit, same cycle: majority broken -> escape
        dut._log.info(f"seu sweep pairs: chain {chain} same-bit same-cycle")
        for i in range(N):
            a = nets[f"u_hk.{chain}_qa[{i}]"]
            b = nets[f"u_hk.{chain}_qb[{i}]"]
            await flip(dut, [(0, [a, b])])
            await ClockCycles(dut.clk, 48)

        # same bit, one cycle apart: first heals before the second lands
        dut._log.info(f"seu sweep pairs: chain {chain} same-bit staggered")
        for i in range(N):
            a = nets[f"u_hk.{chain}_qa[{i}]"]
            b = nets[f"u_hk.{chain}_qb[{i}]"]
            await flip(dut, [(0, [a]), (1, [b])])
            await ClockCycles(dut.clk, 48)

        # different bits, same cycle: each bit keeps a 2-of-3 majority
        dut._log.info(f"seu sweep pairs: chain {chain} different-bit")
        for i in range(N):
            a = nets[f"u_hk.{chain}_qa[{i}]"]
            b = nets[f"u_hk.{chain}_qb[{(i + 7) % N}]"]
            await flip(dut, [(0, [a, b])])
            await ClockCycles(dut.clk, 48)

        await ClockCycles(dut.clk, 64)
        raw_a, esc_a, raw_b, esc_b = await settled_counts(dut)
        raw, esc = (raw_a, esc_a) if chain == "a" else (raw_b, esc_b)
        other_esc = esc_b if chain == "a" else esc_a
        assert esc == N, (
            f"chain {chain.upper()}: same-bit same-cycle pairs must escape "
            f"exactly once each: esc={esc} != {N}")
        assert raw == 4 * N, (
            f"chain {chain.upper()}: RAW {raw} != {4 * N} "
            "(1 per simultaneous pair, 2 per staggered, 1 per split)")
        assert other_esc == 0, "the untouched chain moved"

    await uart_send(dut, 0x72)
    got = await uart_capture(dut, TLM_INTERVAL + 40_000)
    for _ in range(40):
        if got == 0x73:
            break
        got = await uart_capture(dut, TLM_INTERVAL + 40_000)
    assert got == 0x73, "CPU lost after the pair sweep"
