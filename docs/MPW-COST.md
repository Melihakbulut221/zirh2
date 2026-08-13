# The dedicated-silicon path and its cost structure (PROGRAM.md C14)

Researched 2026-08; primary sources listed at the end. Numbers dated
where the public lists are dated - the checklist item "confirm
current price" is part of the gate, not of this study.

## The ladder, and the surprise on rung two

1. **TinyTapeout tile (today)**: ~hundreds of EUR, zero floorplan
   control, the harness confound, no pad ring of our own. The
   experiment vehicle; never the product.

2. **IHP OpenMPW - 2 mm2 of FREE dedicated silicon.** IHP grants
   community submissions ~2 mm2 INCLUDING sealring on SG13G2 open-PDK
   runs, for open-source, non-economic designs: full open data,
   DRC-clean, open-source tools - which is EXACTLY this repository's
   flow and license posture. That is a dedicated die: our own
   padframe, our own guard-ring and well-tap density (the SEL
   feedback loop from TID-SEL-PLAN), the SRAM macros, the clock-loss
   observer, a real POR - everything obstacle 2 says a product needs
   to rehearse, at zero fabrication cost. THE ZIRH-3 VEHICLE
   DECISION SHOULD START HERE: the dedicated-design step does not
   need to wait behind the money gate; it needs to wait only behind
   the B10 data-discipline gate.
   Constraints to respect: non-economic use (research/education
   posture - fine for ZIRH-3, NOT usable for the sellable part),
   selection criteria favor documentation quality and uniqueness
   (this program's evidence chain IS the application).

3. **Paid EUROPRACTICE/IHP MPW**: the older public list shows
   SG13G2 at ~7,300 EUR/mm2 (discounted ~6,205), minimum charged
   area 0.8 mm2 - a 2-4 mm2 product prototype lands roughly in the
   15-30 kEUR class per spin plus packaging and test. This is the
   commercial-prototype rung: same masks discipline, paying customer
   posture allowed.

4. **Dedicated maskset / volume**: engineering-lot economics
   (six-figure EUR class at 130 nm), justified only behind real
   orders - obstacle 9's sequencing applies in full.

## What this changes in the program

The product ladder was written as TT -> dedicated MPW (money gate).
Rung two splits that: ZIRH-3 as a FREE dedicated open-source die
rehearses the pad ring, POR, guard rings, SRAM macros, QSPI-MRAM
board architecture and DFT hooks with no fabrication budget at all,
while the sellable part keeps its paid path unpolluted. The program
documents (PROGRAM.md C14, BOOT.md integration contract, DEBUG-DFT
order of execution) should treat the OpenMPW submission as the
ZIRH-3 default vehicle, pending the B10 gate.

## Sources

- IHP low-cost open-source MPW access page (2 mm2 community grant,
  selection criteria): ihp-microelectronics.com, services / MPW
  prototyping / low-cost open-source MPW access
- IHP OpenPDK flyer and F-Si/MOS-AK presentations on the OpenMPW
  submission process
- EUROPRACTICE general MPW pricelists (SG13G2 EUR/mm2, 0.8 mm2
  minimum; 2026 schedule page for the current-year confirmation)
