# The product program: from experiment chip to sellable part

The verification program (ROADMAP cycles 1-11) closed with the chip
green, the prediction registered and the proofs in CI. This document
is the next program: the honest register of what stands between this
technology base and a commercial radiation-tolerant part, and the
workstream plan that attacks it. Items marked GATE need a decision or
money and wait for it; everything else is executable engineering or
research and proceeds autonomously.

## The obstacle register

1. No beam data yet - every value claim is a registered prediction,
   not a measurement. Beam time is ~3k USD/hour and facilities book
   months out. The credibility engine does not start until silicon
   meets beam.
2. A TinyTapeout tile is not a sellable part: external clock, no pad
   ring, no ESD, no POR. A product needs a dedicated design.
3. The qualification wall: QML/ESCC-class customers need lot
   traceability, screening, hermetic packaging, RVT - structurally
   impossible on MPW silicon, millions and years at full depth. The
   real entry niche is rad-tolerant COTS+ with a published evidence
   pack.
4. That niche is already contested (SAMRH71, GR716, VA416xx):
   hundreds of MHz, flight heritage. A ~1 MIPS bit-serial CPU does
   not compete on speed or price - differentiation is open
   methodology + proofs + data, nothing else.
5. No SEL story: 130 nm bulk latches up, TMR does not help, TT flow
   controls no guard rings, no current monitoring exists.
6. TID tolerance unknown: the dosimeter measures dose, it does not
   survive it; SG13G2 cell TID behaviour uncharacterized.
7. Bus factor 1: single developer, no independent review - ECSS-world
   customers do not count self-verification as evidence.
8. Export control (ITAR/EAR/Wassenaar + Turkish regimes) shapes both
   supply and sale; needs legal input before product definition.
9. Sales cycles (18-36 months) precede revenue; Turkish national
   mechanisms (TUBITAK, TUA, defence primes, cubesat ecosystem) are
   the realistic first funding channel.
10. Sequencing risk: the real assets today are the tools, the macro
    kit, the flow recipe, the evidence templates and the (future)
    beam dataset - first revenue comes from those; chip sales build
    on that reputation years later. Skipping this order is the
    largest commercial risk.
11. Performance class: SERV is the right experiment vehicle and the
    wrong product core.
12. Memory is not product-real: 64 B flop RAM + unpatchable mask ROM.
13. Characterization narrow: no temperature/voltage silicon sweep.
14. Program discipline: do not grow the next chip's backlog while
    ZIRH-1/2 decision gates stand open without data.
15. The chip cannot be programmed after the fab: no load path, no
    debug module, no field update, no DFT. Deliberate for an
    experiment, disqualifying for a product.

## Workstreams

### A. Memory (the critical technical workstream)

- A1. RM_IHPSG13 SRAM macro bring-up as P0 of the next chip: LEF/GDS/
  lib/verilog binding with the same discipline the chain-A macros
  proved. The macros ship in the open PDK (256x8 through 2048x64,
  BIST variants included).
- A2. Macro slicing against MBU: build the 32-bit word from four
  1024x8 macros, 8 bits each - a physical multi-bit upset in one
  macro degrades to one logical bit and SECDED absorbs it. Price the
  slicing as a placement-A/B-style experiment.
- A3. System-level EDAC: an independent hardware scrubber (TMR +
  safe-state FSM, from the generator) sweeping the whole address
  space at a fixed rate; scrub period sized against the two-upsets-
  meet-in-one-word probability, and that calculation goes in the
  datasheet.
- A4. Address/control-path protection: fold the address into the ECC
  computation - an address SET writes the right data to the wrong
  word today and no counter sees it (the memory counterpart of the
  ZOMBIE class).
- A5. The updatability story: mask ROM becomes a trusted bootloader
  (the ROM checksum mechanism is its embryo); firmware loads from
  external rad-tolerant MRAM into SRAM under ECC + signature check,
  falling back to the golden ROM copy on failure.
- A6. SRAM DUT experiment: raw SEU/MBU cross-section of the bare
  open-PDK macro - pattern-scan FSM, static and dynamic modes, raw
  address logging for MBU correlation. No published beam data exists
  for these macros; this dataset alone is citable.

### B. Radiation characterization

- B7. GATE(money): plan, fund and run the beam campaign - facility
  matrix (PSI, UCL HIF, ChipIr, GANIL, Turkish proton sources),
  proton vs heavy-ion split, LET scan, DUT card requirements
  (latchup current protection, remote power cycling). Campaign
  design finishes before the facility application.
- B8. SEL as its own experiment: current monitoring + automatic power
  cycle on the DUT card; SEL cross-section and LET threshold in the
  report; well-tap/guard-ring density controlled in the dedicated
  design.
- B9. TID characterization: stepped Co-60/X-ray dose + anneal on
  SG13G2 cells; calibrate the RO dosimeter against a reference.
- B10. GATE(decision): actually submit ZIRH-1/ZIRH-2 silicon to a
  shuttle and close the open decision gates with data before growing
  the next chip's backlog.

### C. The product chip

- C11. Standalone architecture: own pad ring, ESD, POR/brown-out,
  internal clock generation, and the clock-loss observer (RO-clocked
  watchdog that sees an external-clock SEFI) pulled forward.
- C12. Full-parallel core (RV32IMC class) with the same TMR +
  verification methodology; SERV stays as the experiment platform.
  The differentiation is the methodology, never the core.
- C13. Silicon characterization: -55/+125 C and voltage sweep.
- C14. GATE(money): dedicated IHP MPW path and cost study.

### D. Verification-to-certification bridge

- D15. Requirements traceability matrix: bind the existing evidence
  (formal proofs, GL campaign, torture, tmr-guard reports) into a
  requirement -> test -> evidence chain in ECSS/DO-254 language.
- D16. GATE(customer): fill the ECSS evidence-pack templates on a
  real pilot project.
- D17. GATE(partner): independent review - university/institute
  partnership or external reviewer; break the bus factor.

### E. Commercial sequencing

- E18. Tools and data first, chip later (the Gaisler path).
- E19. TMR-Guard as a standalone product with a first external user -
  synthesis silently deleting TMR is a real, sharp pain with no
  independent checker on the market; smallest effort to first
  revenue.
- E20. Package the IP/tool portfolio: hardened-macro kit + proven
  placement recipe, safe-state TMR FSM generator, TMR'd interface IP
  mini-library (CAN/SpW/RS-422 with golden models), the radiation
  canary soft macro (TID RO + SET catcher + burst correlator as
  drop-in RTL), the campaign orchestration library with the
  RTL/GL/beam single classifier.
- E21. Publish the ESCAPE(A/B) beam dataset and finish the paper -
  the number nobody else has, and the reputation engine for the
  whole portfolio.
- E22. Turkish channels: TUBITAK 1512/1507-class grants, TUA,
  TUBITAK UZAY, ASELSAN, the cubesat ecosystem; the domestic
  rad-tolerant supply narrative is more reachable than global VC.
- E23. Export-control law research early - it shapes the product
  definition, not the other way round.
- E24. Position as the open-evidence chip, not the cheap chip: the
  only vendor whose every protection claim carries its formal proof,
  its GL campaign and its beam data in the repository.

### F. Programmability, debug, software

- F25. ROM-as-bootloader: strap-pin boot select; load from external
  NVM (SPI MRAM/flash) or host (UART/CAN/SpaceWire) into SRAM; ECC +
  cryptographic signature; golden-copy fallback.
- F26. In-flight update: A/B dual bank, verify-then-flip boot
  pointer, watchdog reverts a failed boot; CRC + signature +
  interruption tolerance in the protocol (a half-written image must
  never brick the part).
- F27. Debug interface: RISC-V Debug Module + JTAG (riscv-dbg class,
  OpenOCD/GDB); flight-lockable via fuse/pin, and a debug-logic
  upset must not capture the core - the isolation boundary is drawn
  explicitly.
- F28. DFT: scan chains, SRAM BIST (the macros ship BIST variants),
  screening/burn-in test modes - the silicon-side precondition of
  qualification, designed in from the start.
- F29. Software ecosystem: GCC toolchain integration, linker
  scripts, HAL (EDAC counters, scrubber, telemetry, watchdog),
  examples, a dev board; later an RTOS port. Half of what the
  competition actually sells is this ecosystem.

## Execution order (autonomous unless GATEd)

Phase P1 - memory foundation: A1 macro bring-up (simulation binding
first, flow integration after), A2 sliced-word wrapper, A4
address-in-ECC, A3 scrubber FSM; each verified with the house
discipline (cocotb suites, formal where it bites, tmr-guard gates).

Phase P2 - programmability core: A5/F25 bootloader architecture and
RTL, F26 update protocol, F27 debug-module integration study, F28
DFT plan.

Phase P3 - characterization paperwork that needs no silicon: B7 beam
campaign plan, B8 SEL experiment design, B9 TID test plan, C11
clock-loss observer RTL, D15 traceability matrix.

Phase P4 - commercial documents: E19 TMR-Guard productization, E20
portfolio packaging, E22 funding-channel memo, E23 export-control
research memo.

The GATEs (B10 shuttle submission, B7 beam money, C14 dedicated MPW,
D16 pilot customer, D17 review partner) are decisions, not
engineering; they are surfaced, costed where possible, and left to
their owner.
