# The DUT board specification

PROGRAM.md B7's hardware deliverable and the last engineering box on
the BEAM-PLAN checklist. This is a build-ready specification: every
requirement traces to a campaign document (BEAM-PLAN.md,
TID-SEL-PLAN.md) or a lesson already paid for in simulation. The
board exists to make a beam hour productive and a latchup survivable;
nothing on it is decorative.

## Architecture

```
  beam ->  [ TT carrier on riser ]     <- tile at window center
               |  (socketed, backside-accessible riser for TPA)
   +-----------+-------------------------------------------+
   |  DUT MOTHERBOARD                                      |
   |                                                       |
   |  power in <- remote PSU (network) --------------+     |
   |    |                                            |     |
   |  [per-rail sense: carrier 3v3, tile 1v8]        |     |
   |    INA-class monitor >=10 kS/s  --> MCU logger  |     |
   |    fast comparator trip --> p-FET rail switch --+     |
   |                                                       |
   |  UART  --> RS-422 driver --> 20 m twisted pair --> host
   |  MIRROR--> RS-422 driver --> second pair -------> host
   |  strap/reset/clock-sel --> opto-isolated remote lines |
   |  ext clock <- networked generator (SMA)               |
   |  [onboard XO fallback, jumpered]                      |
   |  temp sensor on carrier underside --> logger          |
   +-------------------------------------------------------+
```

## Requirements, each with its source

### Power and SEL machinery (TID-SEL-PLAN, BEAM-PLAN)

- R-P1: independent rails for carrier logic and tile core, each with
  a shunt + INA-class current monitor sampled at >= 10 kS/s - the
  SEL current signature (microlatch vs full latchup) must be
  reconstructible from the log (TID-SEL-PLAN "current-waveform
  capture around each trip").
- R-P2: hardware trip - analog comparator, threshold set by DAC or
  trimmer, driving a p-FET rail switch with < 10 us reaction. The
  trip is AUTONOMOUS: it must fire with the host software dead,
  because a latched DUT cooking during a network hiccup is how beam
  campaigns lose their silicon.
- R-P3: automatic logged power-cycle after trip: fixed dead-time,
  reapply, count. Trip count and timestamps stream to the host; the
  recovery ladder (BEAM-PLAN G36) consumes them to separate SEL
  events from harness SEFI power-cycles.
- R-P4: trip thresholds derive from the bench current baseline
  (G31, host/zirh_bench.py soak logs) plus margin - a number
  measured before the campaign, not guessed at the facility.
- R-P5: remote PSU (SCPI over Ethernet) sets rails and hard-cycles
  the whole board; the local trip handles microseconds, the PSU
  handles operator decisions.

### Telemetry and control (BEAM-PLAN "remote everything")

- R-T1: the chip's UART and the TLM_MIRROR each get their OWN
  RS-422 differential driver and their own twisted pair for the
  20+ m run to the control room - the mirror's whole purpose is to
  survive what kills the primary voice, so it shares no driver, no
  cable and no USB adapter with it. (This is the bench realization
  of the RS-232/RS-422 transceiver decision documented at the
  interface freeze.)
- R-T2: straps (boot mode, debug lock), reset and clock-select are
  opto-isolated remote lines - re-strapping must not require room
  entry between runs.
- R-T3: external clock arrives on SMA from the networked generator
  (the shmoo axis, G31); an onboard XO is the jumpered fallback so
  a generator failure does not end a shift.
- R-T4: a temperature sensor under the carrier logs die-adjacent
  temperature - the TID and SEL analyses both condition on it.

### Mechanics and beam geometry (BEAM-PLAN G36, G33)

- R-M1: the TT carrier mounts on a socketed riser, tile centered in
  a marked beam window; fiducials on the motherboard corners for
  facility alignment lasers.
- R-M2: everything except the carrier keeps clear of the beam axis:
  the motherboard electronics sit outside the spot so the harness
  confound stays confined to the carrier itself (the G36 control
  run measures exactly that remainder).
- R-M3: the riser is backside-accessible: the same board serves the
  laser TPA session (G33) by flipping the carrier, no redesign.
- R-M4: two complete boards plus a spare carrier riser; decapped
  units socketed, never soldered - a dead DUT costs minutes
  (BEAM-PLAN DUT budget).

### Host integration (H45 - all of it already written and tested)

- R-H1: host/zirh_ground.py is the shift display (live fluence and
  cross-section per counter class, the G37 event-budget planner).
- R-H2: host/zirh_bench.py smoke is the go/no-go between runs; its
  soak mode logs continuously between beam spills.
- R-H3: the campaign library (host/zirh_campaign.py) drives trial
  classification with the same SURVIVED/REBOOTED/ZOMBIE taxonomy
  the GL campaign proved; the board's trip log is its SEL input.
- R-H4: every log lands in the repository raw (BEAM-PLAN); the
  frozen analysis (scripts/beam_analysis.py) consumes them
  unmodified.

## Board bring-up test plan (before any facility)

1. Current baseline of a healthy carrier at nominal clock (feeds
   R-P4 thresholds).
2. Trip rehearsal: electronic load pulls a step overcurrent; verify
   < 10 us trip, dead-time, auto-recovery, log integrity.
3. Long-cable rehearsal: full smoke + soak over the 20 m RS-422
   pairs at the campaign baud - bit errors here are cheaper than at
   the facility.
4. Remote-only drill: one full mock shift (strap change, power
   cycle, shmoo point, soak segment) with the board in another room
   and the door shut. If anything needs a hand, fix the board, not
   the procedure.
5. Confound dry run: carrier deselected, counters logged - the G36
   control-run procedure executed once on the bench so the facility
   version is muscle memory.

## Deliberately out of scope

Flux instrumentation and dosimetry belong to the facility; the
board carries alignment fiducials and geometry, not detectors.
Cooling beyond passive spreaders waits for the SEL hot runs
(TID-SEL-PLAN), where the chamber provides the temperature.
