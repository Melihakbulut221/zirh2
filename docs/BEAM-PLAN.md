# The beam campaign plan

PROGRAM.md items B7, G34, G36, G37 and G38, written to be finished
BEFORE any facility application - the brief's own rule. The funding
decision is a GATE and stays with its owner; everything below is the
engineering that makes the funded hour productive, and it is done.

## Campaign shape: protons first (G34)

1. **Protons** - penetrate packaging, no decapsulation, cheapest
   logistics. Candidate facilities: PSI PIF (Villigen), KVI-CART
   (Groningen), TRIUMF PIF (Vancouver); the local option to
   investigate first: the 30 MeV proton line at TAEK/SANAEM
   (Ankara) - if dosimetry and beam structure suit component testing,
   travel and access costs collapse and a domestic-facility line
   appears in the story. Proton runs produce the first real SEU
   rates, exercise the whole telemetry chain under beam, and shake
   out every procedure the ion runs will reuse.
2. **Neutrons** (ChipIr, ISIS) - atmospheric-like spectrum, cheap
   bulk statistics, no vacuum, boards stacked in the beam. Best
   fluence-per-euro for counter statistics once procedures are
   proven.
3. **Heavy ions** (UCL HIF Louvain, RADEF Jyvaskyla, GANIL) - the
   cross-section-vs-LET curve, which is the paper's money plot.
   DECAPSULATION IS MANDATORY: ion ranges are tens of micrometres
   and a QFN lid is opaque; budget several decapped DUTs (decap
   yield is never 100%) plus one control unit kept sealed. At least
   4-5 LET points per the statistics section, tilt runs at fixed LET
   for the charge-sharing footprint (the ESCAPE(B) azimuth
   prediction from the DEF's pair-distance anisotropy).

After the ion campaign: Weibull fit per counter class
(scripts/beam_analysis.py weibull, frozen), then CREME96/OMERE orbit
folding for LEO and GEO upset rates - the number a cubesat OBC
integrator actually asks for.

## Statistics designed first (G37)

Target: >= 30-50 events PER CHAIN for the ESCAPE(A)/ESCAPE(B)
separation (Poisson: ~25 events is ~20% relative error; 50 events is
~14%). Back-computation lives with the live console: the ground
console's fluence/cross-section display tells the operator in real
time when a counter class has banked its event budget, so beam
minutes move to the next LET point exactly on time - no overexposure
past the budget, no thin bins discovered at analysis time.

Flux cap: <= 1 expected event per telemetry readout window (the
65536-cycle frame period), so the burst correlator can separate
pile-up from genuine spatially-correlated bursts. At 20 MHz that is
a ~3.3 ms window; the console computes the cap from the measured
rate and warns when flux should be stepped down.

Event budget per run, the arithmetic the application quotes:
fluence_needed = N_target / (sigma_estimated x bits). The sigma
estimate before any silicon data comes from published 130 nm bulk
flip-flop cross-sections (1e-8 to 1e-7 cm2/bit heavy-ion saturated,
1e-14 cm2/bit proton class); the first proton hour replaces the
estimate with a measurement and the console re-plans the remainder.

## The TT-harness confound (G36)

The beam spot is centimetres; the tile is 0.14 mm2. The unhardened
TinyTapeout mux and carrier logic WILL take hits, and a harness SEFI
can masquerade as a chip ZOMBIE. The protocol, registered here
before any beam:

1. **Control run per session**: beam on, tile DESELECTED - measure
   the harness's own SEFI rate at the same flux. This rate is
   subtracted (scripts/beam_analysis.py confound, with propagated
   uncertainty) before any tile event is claimed.
2. **Attribution rules, written in advance**: an event is
   tile-attributable only if telemetry structure survives (frames
   parse; a dead harness kills frames entirely); harness-class
   events are logged, subtracted and reported separately, never
   silently dropped.
3. **Recovery ladder**: telemetry gap -> power-cycle the carrier ->
   if frames return with BOOT incremented, chip watchdog acted
   (REBOOTED class); if frames return with BOOT unchanged, the
   harness was the casualty (harness SEFI class); if frames do not
   return, escalate to full re-flash and mark the interval
   unattributable. The ladder is exactly the campaign library's
   SURVIVED/REBOOTED/ZOMBIE discipline extended one layer down.

## DUT board requirements (B7)

- Latchup protection: per-rail current monitor with a fast trip
  (SEL is expected at 130 nm bulk; the trip threshold and reaction
  budget come from the SEL experiment design in TID-SEL-PLAN.md),
  automatic logged power-cycle, remote-controlled PSU.
- Remote everything: the DUT room is closed during beam; UART over
  a long-run adapter plus the TLM_MIRROR second voice on a separate
  adapter (the flood-proof channel earns its area here), PSU and
  clock generator on the network.
- Two boards minimum plus spares; decapped units socketed, not
  soldered, so a dead DUT costs minutes.
- The ground console (host/zirh_ground.py) with live
  fluence/cross-section is the shift display; the soak logger
  (host/zirh_bench.py) records between runs; every log lands in the
  repository raw.

## Reporting shape (G38)

SEE results reported against ESCC 25100 / JESD57 structure
(cross-sections with fluence, confidence intervals, test conditions,
part identification); TID against MIL-STD-883 TM1019 structure when
that campaign runs. The registered analysis scripts already emit the
quantities those documents ask for; the report is assembly, not
computation.

## What must exist before the application (checklist)

- [x] Registered prediction (docs/PREDICTION.md)
- [x] Frozen analysis with selftest (scripts/beam_analysis.py)
- [x] Live console with fluence/cross-section (host/zirh_ground.py)
- [x] Bench ladder as code (host/zirh_bench.py)
- [x] Statistics design and flux cap (this document)
- [x] Confound protocol (this document)
- [ ] GATE(decision): silicon in hand (shuttle submission)
- [ ] GATE(money): facility choice and application
- [ ] DUT board schematic and build (engineering, next in queue
      after the QSPI-MRAM controller)
