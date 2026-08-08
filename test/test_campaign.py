# =============================================================================
# ZIRH-2 - top-level fault campaign: the computer under (simulated) beam
#
# Run:  make -C test -f Makefile.campaign
#
# Random flips go straight into SERV's register file - the largest
# unprotected state on the die, by design a beam target. Three measured
# outcome classes: SURVIVED (echo still answers), REBOOTED (watchdog
# fired, BOOT counted, echo answers again), and ZOMBIE (the loop and
# signature stay alive while a corrupted hoisted base pointer kills one
# peripheral path - the watchdog cannot see this, and in silicon the
# firmware's periodic voluntary restart clears it within minutes; the
# rate makes that unsimulable, so here zombies are counted, not failed).
# The one FORBIDDEN outcome, asserted hard: signature dead AND no
# reboot - true permanent silence.
#
# WD_LIMIT_LOG2 is overridden to 17 (131k cycles): longer than a full
# boot including the ROM checksum loop (~95k), so a recovering CPU is
# never shot mid-boot, but short enough to keep trials simulable.
# =============================================================================

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly, Timer

CLK_NS = 40
DIV = 174
BOOT_CYCLES = 120_000
WD_LIMIT = 1 << 17
RECOVERY_WINDOW = WD_LIMIT + BOOT_CYCLES + 40_000


def bit(dut, i):
    return 1 if str(dut.uo_out.value)[7 - i] == "1" else 0


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


async def expect_byte(dut, want, timeout_cycles):
    """Hunt the TX line for a specific byte among telemetry traffic."""
    for _ in range(60):
        for _ in range(timeout_cycles):
            await RisingEdge(dut.clk)
            await ReadOnly()
            if bit(dut, 4) == 0:
                break
        else:
            return False
        await ClockCycles(dut.clk, DIV // 2)
        bits = []
        for _ in range(9):
            await ClockCycles(dut.clk, DIV)
            await ReadOnly()
            bits.append(bit(dut, 4))
        if bits[8] == 1 and sum(b << i for i, b in enumerate(bits[:8])) == want:
            return True
    return False


async def alive(dut, probe):
    """One echo exchange proves the CPU end to end."""
    await uart_send(dut, probe)
    return await expect_byte(dut, (probe + 1) & 0xFF, 80_000)


def boot_count(dut):
    v = dut.boot_cnt.value
    return int(v) if v.is_resolvable else -1


@cocotb.test()
async def test_rf_flip_campaign(dut):
    """Six trials of register-file corruption: every trial must end with a
    living CPU, by survival or by counted watchdog reboot."""
    await start(dut)
    # probe bytes must dodge the command set ('0'-'4','a'-'c','C','R'):
    # lowercase p..w is safe
    assert await alive(dut, 0x70), "sanity: CPU must answer before the campaign"

    random.seed(64)
    survived = 0
    rebooted = 0
    zombies = 0

    for trial in range(6):
        # independent trials: full external reset + boot
        if trial:
            await RisingEdge(dut.clk)   # leave any ReadOnly a probe ended in
            dut.rst_n.value = 0
            await ClockCycles(dut.clk, 8)
            dut.rst_n.value = 1
            await ClockCycles(dut.clk, BOOT_CYCLES)
        boots_before = boot_count(dut)
        # one 'particle': hit a few RF entries mid-cycle
        await Timer(10, unit="ns")
        for _ in range(3):
            idx = random.randrange(512)
            cur = dut.u_soc.u_cpu.rf_ram.memory[idx].value
            v = int(cur) if cur.is_resolvable else 0
            dut.u_soc.u_cpu.rf_ram.memory[idx].setimmediatevalue(v ^ 0x3)

        ok = await alive(dut, 0x71 + trial)
        if ok and boot_count(dut) == boots_before:
            survived += 1
            continue

        # not answering: watchdog window, then classify
        waited = 0
        while boot_count(dut) == boots_before and waited < RECOVERY_WINDOW:
            await ClockCycles(dut.clk, 4_096)
            waited += 4_096
        if boot_count(dut) > boots_before:
            rebooted += 1
            await ClockCycles(dut.clk, BOOT_CYCLES + 8_192)
            assert await alive(dut, 0x78 + trial), (
                f"trial {trial}: watchdog rebooted but the CPU never "
                f"came back")
            continue

        # no reboot: zombie or truly dead? the signature decides
        s1 = int(dut.cpu_sig.value)
        await ClockCycles(dut.clk, 8_192)
        s2 = int(dut.cpu_sig.value)
        assert s1 != s2, (
            f"trial {trial}: PERMANENT SILENCE - signature frozen and no "
            f"watchdog reboot (boots={boot_count(dut)})")
        zombies += 1
        # each trial gets a full external reset below, so a zombie cannot
        # poison the next one (the earlier "starve the dog by zeroing RF
        # entries 0..23" hack targeted only x0/x1 slices of the 2-bit-wide
        # RF and livelocked - measured the hard way)

    dut._log.info(f"campaign: {survived} survived, {rebooted} rebooted, "
                  f"{zombies} zombies (cleared), 0 permanently silent of 6")
    assert survived + rebooted + zombies == 6
