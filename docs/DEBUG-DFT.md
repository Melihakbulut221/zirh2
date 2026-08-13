# Debug and DFT: the plan and the isolation boundary

PROGRAM.md items F27 and F28. The experiment chip has neither on
purpose; the product chip cannot ship without both. This document is
the integration plan, and zirh_dbg_gate.v is the one piece worth
building today: the flight lock and isolation boundary that the
rad-hard context adds on top of a stock debug module - buildable and
provable now, before any debug module exists to sit behind it.

## F27: the debug interface

**Stack**: RISC-V Debug Module (spec 0.13.2+) + JTAG TAP, from the
open riscv-dbg implementation (PULP) - OpenOCD/GDB compatible out of
the box. The DM sits on the DMI bus behind the TAP; the SoC side
exposes a debug request to the core and a system-bus-access window
for memory. SERV has no native debug-module hookup, which is fine:
the product core (C12, RV32IMC class) selects for debug support; on
the experiment chip the DM's system-bus access alone (memory and
register visibility without core support) already pays for the pins.

**The two rad-hard requirements the stock module does not have:**

1. **Flight lock.** An open debug port in flight is both an SEU
   surface and a security hole. The lock is a fuse (product) or a
   strap pin latched at POR (experiment): once locked, the debug
   domain must be POWER-EQUIVALENT-DEAD - no DMI transaction, no TAP
   state, no upset inside the debug logic may reach the core or the
   bus. Unlock exists only through the fuse never blowing / the
   strap at the next POR; there is no software unlock, because any
   register that can unlock is a register an upset can flip.

2. **The isolation boundary.** An upset in debug logic must not
   capture the core. The boundary is a gate module OUTSIDE the debug
   domain, TMR'd with the safe-state trap failing TOWARD LOCKED, that
   forces every debug-to-system signal (debug request, halt request,
   bus master valid, write strobes) to its inert value whenever the
   lock is set OR the gate's own voters disagree. The debug module
   is treated as untrusted logic in the fault model - the same
   posture the bus watchdog takes toward peripherals.

zirh_dbg_gate.v implements exactly this boundary and its cocotb suite
proves: locked means inert regardless of debug-side activity; the
POR-latched strap cannot be changed by wiggling it after reset; the
gate fails toward locked from illegal states. The formal harness
proves the inertness invariant by induction - not sampled, proven.

## F28: production test access (DFT)

The qualification wall (obstacle 3) starts at the silicon: screening
and burn-in need test access designed in from the first netlist of
the dedicated chip.

- **Scan.** Full-scan stitching at synthesis (supported in the open
  flow via yosys/OpenROAD scan insertion or vendor flow at the
  dedicated step); the TMR structure needs care - scan chains
  puncture voter feedback loops, so scan-enable must also force
  voter-bypass, and tmr-guard grows a check that scan logic did not
  break replica separation. ATPG target: stuck-at first; transition
  fault at the product node.
- **SRAM BIST.** The RM_IHPSG13 macros ship with a BIST port set
  (A_BIST_*) that zirh_sram39 currently ties off. The plan: a march
  engine (MARCH C- class) driving the BIST ports, runnable at
  screening AND in flight as a commanded self-test (the same engine
  doubles as the A6 pattern-scan front end for the SRAM DUT beam
  experiment - one block, three customers: production, flight
  maintenance, science).
- **Burn-in / screening modes.** A test mode pin family: BIST-all,
  scan access, quiescent-current mode (all rings frozen for IDDQ),
  and the bench characterization hooks from G31 (shmoo automation
  needs deterministic boot and status visibility - the boot
  controller's GOLDEN strap already provides the former, telemetry
  the latter).
- **Boundary scan.** JTAG TAP shared with the debug stack; BSDL file
  ships with the product part.

## Order of execution

1. zirh_dbg_gate.v + suite + formal inertness proof (now, this repo).
2. March/BIST engine over the macro BIST ports (next: serves DFT,
   flight self-test and the A6 beam experiment simultaneously).
3. riscv-dbg vendor-in and DMI integration study on the ZIRH-3
   skeleton; scan insertion and tmr-guard scan checks at the
   dedicated-chip step; BSDL and ATPG at product tape-out.
