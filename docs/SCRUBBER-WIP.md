# Scrubber + address-ECC work in progress: findings register

Branch wip/sram-scrubber holds the A3/A4 build for zirh_sram39. The
design is architecturally sound and MOSTLY proven; one systematic
read-path ghost remains, and main stays green until it is dead.
Everything below is measured, not guessed.

## What is done and proven on the branch

- Registered-decision scrubber (S_SCRUB_RD/S_SCRUB_FIX): the first
  build muxed the macro address combinationally between bus and scrub
  counter, and a bus request landing mid-scrub steered repair writes
  to the WRONG row - silent corruption of fresh words, caught and
  fixed by making every macro control signal derive from registered
  state. The micro scenario (3 rows, beats interleaved with bus
  traffic) is fully clean: row walk, repairs, events all correct.
- scrub_en_i gate (hold until boot init writes every word) - also the
  real product control; sweeping preinitialization garbage is
  pointless and, in simulation, X.
- Address-in-ECC mask (A4): even-weight fold of the row into the
  parity positions and the overall bit; any single-bit address
  mismatch decodes as UNCORRECTABLE by construction. Formal harness
  for the mask is the next task after the ghost dies.

## The open ghost (the reason this is a branch)

Full-suite shape: init 1024 random words (verified clean by direct
pre-enable reads), enable the sweep, read back. The FIRST scrub beat
decodes its row with a phantom correctable error, "repairs" it (thus
corrupting the row), and the NEXT bus read shows the same signature.

The decisive measurement: with the address mask ON the failing beat
was row 0 with syndrome 35; with the mask OFF it was row 1 with
syndrome 34 - in both runs syn XOR row_q == 35. A constant signature
XORed with the row index is a systematic path defect (likely the
sweep read colliding with the preceding transaction's port activity
in the behavioral macro model - write-through and A_DLY semantics
unchecked), not a random corruption. The micro scenario does NOT
reproduce it; 1024-row random-data traffic does, deterministically.

Next session: instrument the exact beat's SCRUB_RD edge (macro REN/
WEN/ADDR and dr_r update), check the model's write-through clause and
A_DLY, and reproduce with a 16-row directed pattern instead of 1024
random words to shrink the trace.
