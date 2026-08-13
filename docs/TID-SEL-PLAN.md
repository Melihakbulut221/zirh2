# TID and SEL campaign plans

PROGRAM.md items B8, B9 and G35. Separate campaigns from the SEE
beam by physics and by procedure; written now so the facility
conversations start from a plan, not a wish.

## TID (B9, G35)

**Question the product needs answered**: at how many krad(Si) do the
SG13G2 standard cells start leaking and shifting, and how much of it
anneals back. Nobody has published this for the open PDK - like the
SRAM cross-section, the answer is citable by itself.

**Flow**: MIL-STD-883 TM1019 / ESCC 22900 shaped - Co-60 (or
calibrated X-ray) stepped dose: 5, 10, 20, 30, 50, 75, 100 krad
steps; at each step, powered and biased at nominal, then the
parametric set within the standard's time window:

- supply current at idle and under the marathon firmware load (the
  leakage signal)
- ring-oscillator dosimeter count (the on-chip dose curve - THIS is
  the calibration run that turns the RO from a relative into an
  absolute instrument, plotted against the facility's reference
  dosimetry)
- full bench smoke (host/zirh_bench.py) and the frequency shmoo at
  three voltages: the operating envelope shrinking with dose IS the
  degradation measurement
- SEU counter false-positive check: a TID-degraded voter that starts
  self-reporting is a failure mode the beam data must be able to
  exclude

**Anneal**: 24 h room-temperature biased anneal, re-measure; then
168 h at 100 C per TM1019 rebound screening if the budget allows.

**Units**: minimum 3 irradiated + 1 control kept in the drawer;
control measured at every step time to separate drift from dose.

## SEL (B8, G35)

**Why separate**: latchup is a destructive, current-signature event;
its test wants the WORST case while SEU statistics want the nominal
case - hot, Vmax, and an instrumented supply.

**Conditions**: junction temperature at the rated maximum (die
heater or chamber), VDD at maximum rating, heavy ions at the highest
available LET first (a screening run: no SEL at 60+ MeV.cm2/mg and
125 C bounds the threshold above the practical spectrum).

**Board machinery** (shared with the SEE DUT card): per-rail current
monitoring at >= 10 kS/s, a fast electronic trip well under the
metallization damage budget, automatic power-cycle with event
logging (timestamp, rail, peak current, LET, fluence at trip), and a
current-waveform capture around each trip so microlatch vs full
latchup is distinguishable in the report.

**Reported**: SEL cross-section vs LET (or the bounding statement),
threshold LET if found, and the derating guidance a user needs
(voltage/temperature margins). ESCC 25100 shape.

**Design feedback loop**: whatever the TT-flow silicon shows, the
dedicated chip (C11/C14) carries the counters: well-tap and guard
ring density become controlled floorplan parameters, and the SEL
result decides how aggressive they must be.

## Sequencing against the money

TID does not need the beam facilities - a Co-60 cell or a calibrated
X-ray irradiator is a different (cheaper, more available) booking,
so TID can run FIRST and its RO-dosimeter calibration then rides
along in every later beam shift as a live dose cross-check. SEL
piggybacks on the heavy-ion SEE campaign (same facility, same decap
units, one hot run at the end of the shift so a destructive event
cannot cost SEE statistics).
