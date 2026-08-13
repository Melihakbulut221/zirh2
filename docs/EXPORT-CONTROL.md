# Export-control research memo (PROGRAM.md E23)

Research notes for counsel, 2026-08. THIS IS NOT LEGAL ADVICE; the
brief's own instruction stands - a lawyer shapes the business model,
this memo makes that conversation short. No institution was
contacted in preparing it.

## Where the control lines actually sit

The multilateral baseline (Wassenaar dual-use list, mirrored into
the EU dual-use regulation, the US EAR, and Turkiye's own dual-use
regime - Turkiye is a Wassenaar participating state) controls
integrated circuits "designed or rated as radiation hardened"
around parameter thresholds of roughly this class:

- total dose >= 5x10^3 Gy(Si) = 500 krad(Si)
- dose-rate upset >= 5x10^6 Gy(Si)/s
- neutron fluence (1 MeV eq) >= 5x10^13 n/cm2
- SEU rate better than ~1x10^-8 errors/bit/day
- destructive-SEE LET threshold >= 80 MeV.cm2/mg

(US practice per the 2024 EAR clarification on rad-hard ICs; the
same clarification notes that INCORPORATING a controlled rad-hard
IC into a larger commodity does not by itself make the commodity
controlled.)

## What this means for the positioning - and it is good news

The program's own product thesis is "rad-TOLERANT COTS+": measured,
beam-evidenced, sub-qualification parts. A 130 nm bulk part whose
own documentation claims tens-of-krad TID (to be measured, G35) and
publishes a measured destructive-SEE threshold WELL below the 80
MeV.cm2/mg line sits, on its face, below the classic control
parameters. Three practical consequences to confirm with counsel:

1. **Claims discipline is compliance discipline.** Every datasheet
   number this program publishes is a measured number - that habit
   is also what keeps the part on the right side of "designed or
   rated as". Never rate above what was measured; never use the
   phrase "rad-hard by design" loosely in commercial material. The
   repository's measure-before-believing culture is, accidentally,
   an export-compliance posture.
2. **Supply side**: space-grade MRAM die (the A5 SiP plan) and
   known-good-die sourcing from US/EU vendors will carry THEIR
   export classifications into the SiP; the package's origin story
   needs mapping before the SiP architecture freezes.
3. **Turkiye side**: dual-use export permits route through the
   national regime implementing Wassenaar lists; defense-sales
   channels (the domestic narrative) may pull the product toward
   military-list treatment regardless of parameters - a
   counsel-with-Turkish-practice question, flagged, not answered.

## Open questions for counsel (the actual deliverable)

- Confirmation that a measured-rad-tolerant part below all 3A001
  rad-hard parameters is EAR99/AL-free in the intended markets.
- The SiP question: classification flow-through of a controlled
  MRAM die into the package.
- Whether publishing beam datasets and full RTL (the open-evidence
  positioning) has any deemed-export dimension - expectation: no,
  published open-source is out of scope, but confirm.
- Turkish permit regime timelines for the COTS+ class, and whether
  the domestic-defense channel changes the answer.

## Sources

- US Federal Register, "Clarification of Controls on Radiation
  Hardened Integrated Circuits and Expansion of License Exception
  GOV" (2024-03-13)
- OSTI report "Export Administration Regulations and Radiation
  Tolerant..." (EAR bounding radiation levels)
- Wassenaar dual-use list Category 3 (3A001) parameter texts as
  implemented in the EAR
