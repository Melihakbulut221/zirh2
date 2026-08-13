# Positioning: the open-evidence chip (PROGRAM.md E24)

The brief's sharpest strategic instruction: do NOT position on price.
A 130 nm ~1 MIPS part loses a price war to SAMRH71/GR716/VA416xx on
day one. Position instead on the one thing no competitor offers and
this program already has - every protection claim carries its formal
proof, its gate-level fault campaign and (soon) its beam data, in a
public repository anyone can audit.

## The defensible difference, stated as a promise

"Every number in our datasheet is measured, every protection is
proven, and the proof is in the open." Concretely, today, in this
repository:

- the escape-window claim is a machine-checked theorem
  (formal/f_ring.sv), not an assertion
- the SECDED contract is exhaustively proven (formal/f_ecc.sv)
- the TMR survives synthesis and a tool proves it independently on
  every commit (tmr-guard)
- the pre-beam prediction is registered with a timestamp nobody can
  backdate (docs/PREDICTION.md, git history)
- the analysis that will judge the beam data is frozen and tested
  before the data exists (scripts/beam_analysis.py)

No incumbent publishes any of this. Their heritage is a moat against
newcomers; radical transparency is the moat a newcomer can build that
the incumbents cannot copy without dismantling their own secrecy.

## Who this wins, and who it does not

WINS: the buyer who has been burned by a datasheet number that did
not survive their own test; the university or NewSpace team that
needs to SHOW their reviewer the hardening is real; the integrator
who values auditability over flight heritage because their mission
is a cubesat, not a flagship. The COTS+ niche is full of exactly
these buyers.

DOES NOT WIN: the prime who requires QML-V flight heritage - that
buyer needs the qualification wall (obstacle 3), which this
positioning explicitly does not climb. Naming that boundary is part
of the honesty: open-evidence is a different product than
qualified-heritage, sold to a different buyer, and pretending
otherwise would be the one dishonest number in the pitch.

## How the whole portfolio reinforces it

Every asset in docs/IP-PORTFOLIO.md is evidence FIRST and product
second: tmr-guard proves a competitor's hidden failure mode; the
canary macro gives any chip a public radiation self-report; the
campaign library's ZOMBIE taxonomy names a failure others miss. The
reputation engine (docs/PAPER.md, the ESCAPE(A/B) dataset) is not
marketing adjacent to the products - it IS the product's proof, and
the products are its instruments. Sell the evidence; the silicon is
how the evidence was gathered.

## The one-line version

Not "the cheap rad-tolerant chip". "The rad-tolerant chip whose every
claim you can check yourself." Price is a race to the bottom;
checkable truth is a position an incumbent structurally cannot take.
