# Bench characterization procedure (PROGRAM.md G31)

The ladder from a cold board to a certified false-positive floor,
written so the bench session executes a checklist, not an
improvisation. Every step maps to a tool already in the repository
and tested against the simulation mock (host/zirh_bench.py
--selftest), so silicon day runs the same commands that pass today.

## Order (each gates the next)

1. **Current baseline.** Board powered, chip held in reset, then
   released to the mask-ROM firmware. Record idle and
   under-firmware-load supply current per rail (the DUT board's
   per-rail monitors, DUT-BOARD.md R-P1). This number sets the SEL
   trip threshold (R-P4) and is the TID leakage reference (G35).

2. **Reset / UART / ROM checksum.** `zirh_bench.py smoke` - HEARTBEAT
   blinks, frames parse, the 'R' command returns the ROM checksum
   the firmware build committed. Go/no-go with an exit code.

3. **Block-by-block functional.** Walk the command set: injections
   move the right counters (0-4), environment instruments (T/S/B/E),
   the interface loopbacks (k/K/w/W with the jumpers). Each is a
   line in the existing integration suite; the bench repeats them on
   silicon.

4. **Frequency x voltage shmoo.** `zirh_bench.py shmoo --plan
   host/shmoo_plan.csv` - the operating envelope and its margin. The
   plan's last two rows are the STA/SDF-characterized corners:
   silicon that passes them confirms the timing sign-off the SDF
   sims (Cycle 26) proved in simulation.

5. **Temperature sweep.** The shmoo repeated at chamber temperature
   extremes (-55/+125 the goal, whatever the chamber allows the
   floor). The envelope shrinking with temperature is the datasheet's
   operating-range table.

6. **Soak.** `zirh_bench.py soak --hours <days*24> --csv soak.csv` -
   uninterrupted, logging every frame's counters, reporting the
   FALSE-POSITIVE FLOOR: events per hour with no radiation present.
   "N days, zero events" is the certificate every beam counter
   stands on - a counter that ticks on the bench cannot be trusted
   under the beam.

## What each step produces for the datasheet

- baseline current -> power table + SEL threshold
- shmoo map -> operating envelope figure (freq x voltage pass region)
- temperature shmoo -> operating range table
- soak floor -> the reliability sentence and the beam-counter
  confidence bound

## The discipline

Nothing here is invented at the bench: the plan is a CSV, the tools
have selftests, the outputs are the datasheet's tables. The bench
session is data collection against a fixed procedure - which is
exactly what makes its numbers defensible when a reviewer asks how
they were obtained.
