# radiation-canary: drop-in radiation self-report for any chip

A standalone integration guide for src/zirh_env.v (PROGRAM.md E20
asset 5). The block gives ANY host design an in-flight radiation
telemetry channel - dose, single-event transients, and burst
clustering - behind one small register window, with no dependency on
the rest of ZIRH.

## What you get

- **TID dosimeter**: an enable-gated ring oscillator counted over a
  fixed window; the count drifts with total ionizing dose. Repeated
  reads plot the mission dose curve with zero analog circuitry.
- **SET catcher**: a quiet inverter chain watched by a catch latch;
  a particle strike anywhere in the chain sets it, is synchronized,
  counted and re-armed. Combinational transients are a different
  observable than flop upsets - this is the third detector.
- **burst correlator**: counts event onsets arriving within a short
  window of a prior onset - clustered strikes against the Poisson
  background, a statistic the ground cannot recover after the fact.

## Integration contract

Ports: clk, rst_n, start_i (one-shot: run a dose window), test_i
(one-shot: fire the SET self-test), clear_i, evt_i (any host event
to correlate), ro_word_o / sb_word_o (the two 32-bit read words),
err_o (own TMR mismatch). Wire the two words into two registers of
your bus; drive the strobes from writes. That is the whole
integration - the block is self-contained and TMR-internal.

## The three build modes (already parameterized)

- `ZIRH_SIM_ENV`: behavioral models for zero-delay simulation (the
  real oscillator loop would hang an event simulator).
- `SYNTH`: FPGA-safe behavioral stand-ins (the analog structures do
  not exist on an FPGA; the control path still verifies).
- default (ASIC): the real hand-instantiated SG13G2 cells inside
  keep_hierarchy islands with (* keep *) on every instance - the
  synthesis-survival discipline tmr-guard enforces.

Retarget to another PDK by swapping the cell names in the default
branch (sg13g2_inv_1, sg13g2_nand2_1) for the host process
equivalents; the control logic and the register interface are
process-independent.

## Acceptance evidence

test/test_env.py is the golden-model suite (arm/hold/re-arm of the
catch latch, window counting, burst logic); it ships as the
integration's acceptance test. The block survives tmr-guard as
"env" in the flagship manifest. That pair - a passing golden suite
and a synthesis-survival attestation - is the deliverable a buyer
verifies against.
