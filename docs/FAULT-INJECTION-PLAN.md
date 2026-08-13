# Radiation-free fault injection and laser TPA plans

PROGRAM.md items G32 and G33: the rungs of the test ladder that
validate the detect-recover machine on real silicon BEFORE spending
beam money, and image the placement hypothesis physically. Both are
design documents - the equipment bookings are gates, the procedures
are engineering and belong here.

## G32: clock/voltage glitch injection

**Purpose**: fire the chip's detect-recover machine - watchdog,
safe-state traps, the signature telemetry, the clock-loss observer -
on real silicon, and confirm the GL campaign's
SURVIVED/REBOOTED/ZOMBIE classification reproduces on hardware. A
glitch is not a particle, but it exercises the SAME recovery logic;
if the taxonomy holds under glitching it is far more likely to hold
under beam, at a fraction of the cost.

**Rig**: a ChipWhisperer-class platform, or a bench equivalent -
a fast DAC/comparator on the tile core rail for voltage glitches,
and a clock mux that can inject a runt or a gap on the external
clock line (the DUT board already isolates and remotes the clock,
G31/DUT-BOARD.md - the glitch injector taps there).

**Campaign, mapped to the existing taxonomy**:
- clock gap of increasing width -> expect the clock-loss observer
  to flag (evt_loss, clk_ok drop) and BOOT to stay flat if the SoC
  survives, or increment if the watchdog reboots. The observer
  built in Cycle 23 is the instrument under test here.
- voltage droop of increasing depth/duration -> walk from SURVIVED
  (telemetry continues) through REBOOTED (BOOT increments, frames
  resume) to the ZOMBIE corner (signature toggles, command path
  dead) - the same three-way the GL campaign asserts, now on silicon.
- glitch DURING a known bus transaction -> target the ECC RAM RMW
  and the boot verify window specifically, the paths simulation
  proved fragile; confirm the hardware recovers as modeled.

**Analysis**: reuse host/zirh_campaign.py unchanged - it already
classifies from telemetry, and a glitch trial produces the same
telemetry a beam trial does. The classifier does not care what
caused the upset, which is exactly why it retargets for free.

**Pre-registration**: glitch parameters and expected classifications
are recorded before the run, PREDICTION.md style - a glitch that
produces an UNexpected class is a finding about the recovery logic,
not a nuisance.

## G33: laser two-photon absorption (TPA) mapping

**Purpose**: image the placement-A/B hypothesis PHYSICALLY before
beam. Two-photon absorption deposits charge at a focused point
inside the die from the backside; scanning the focus node by node
maps which strikes cause upsets and which the voter absorbs. The
prediction (docs/PREDICTION.md): chain A's 680 um replica separation
makes a same-bit double-strike geometrically impossible for one
spot, while chain B's 3.78 um closest pair is reachable - TPA can
show this directly, cheaper and more repeatably than beam, and with
a spatial resolution beam does not have.

**Preconditions**: backside access (the DUT board's flip-riser,
DUT-BOARD.md R-M3, exists for this), backside thinning/polish per
the facility's TPA requirement, and the die coordinates of both
chains' replicas - which the layout analysis already extracted
(scripts/seu_predict.py reads the exact flop positions from the
DEF; the same coordinates target the laser).

**Scan plan**:
- calibrate on the PLAIN ring first: an unprotected flop, every
  strike an upset, establishes the charge threshold and the
  stage-to-die coordinate transform.
- raster chain B's replica field: expect isolated upsets healed by
  the vote (RAW increments, ESC does not) UNTIL the focus can
  couple two same-bit replicas - the 3.78 um pairs from the DEF
  are the coordinates to dwell on; an ESC there confirms the
  same-bit-same-cycle escape window physically.
- raster chain A's replica field at the same LET-equivalent: expect
  NO escapes anywhere - the macros are 680 um apart, no single
  focus reaches two. This is the placement floor, imaged.

**Output**: an upset map in die coordinates overlaid on the layout -
the figure that turns the registered prediction into a picture, and
a strong pre-beam result in its own right (docs/PAPER.md gains a
TPA section alongside the beam section). The analysis coordinates
come from seu_predict.py; the map generation is a plotting script to
write when the stage log format is known.

## Sequencing

G32 needs only the DUT board and a glitch rig - it runs FIRST, on
the bench, and its taxonomy confirmation de-risks every later
campaign. G33 needs backside prep and a TPA facility booking (the
one institution-contact gate in this document, flagged not pursued)
but produces the placement image that is the paper's centerpiece
before a single beam hour is bought.
