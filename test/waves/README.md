# Waveform policy (PROGRAM.md H40)

Raw VCD/FST dumps are NEVER committed: they belong in CI artifacts,
release attachments or git-lfs. What lives here instead is the
where-to-look knowledge, codified:

- `.gtkw` save files per testbench: open any locally produced dump
  (`WAVES=1 make -C test -f Makefile.<x>`) with
  `gtkwave -a test/waves/<x>.gtkw <dump>` and the signals that tell
  the story are already placed and formatted.
- Annotated PNG/SVGs of the critical moments live in `docs/fig/`:
  the escape witness (formal cover trace), the SEU-into-one-replica
  heal (`seu_voter_mask.png` - replica A hit, voted output never
  moves, mismatch detector pulses, output pins keep their rhythm;
  from the tmrflip suite via `waves/tmrflip.gtkw`), the double-bit
  uncorrectable detection (`uncorrectable_detect.png` - nonzero
  syndrome, uncorr flag, event pulse; from the sram39 suite) and the
  tmr-guard catch (`tmrguard_catch.svg` - the same netlist before
  and after synthesis strips the TMR, and which one the checker
  fails). README, paper and customer-deck figures, generated from
  the suites' own dumps, cropped, captioned.
- Curated mini-dumps (a few hundred KB, evidence slices only) may be
  added under this directory when a figure needs its raw source
  preserved; anything larger goes to a release attachment.
