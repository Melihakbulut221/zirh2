# The product core selection study (PROGRAM.md C12)

SERV stays the experiment platform; the product chip needs an
RV32IMC-class core at tens of effective MHz with the SAME TMR and
verification methodology. The differentiation is the methodology,
never the core - which makes this a sourcing decision with hard
criteria, not a design adventure.

## Criteria, in order

1. **Flow compatibility**: must synthesize through yosys/OpenLane
   (or via sv2v) - the whole evidence chain (tmr-guard, formal,
   GL campaign, the placement recipe) lives on that flow.
2. **TMR-ability**: state that can be found and replicated. Small
   register count, clean module boundaries, no vendor RAM
   primitives in the core proper. The chain-A macro discipline
   must be applicable to its critical registers.
3. **Verification carry-over**: the arch-test harness, the torture
   generator and RISCOF must retarget with days, not months, of
   work; a core with upstream riscv-arch-test/RISCOF support wins.
4. **Performance**: >= 1 CoreMark/MHz class, RV32IMC, so 25-50 MHz
   silicon lands in the competitors' conversational range.
5. **Heritage and license**: permissive license, alive upstream,
   silicon proven somewhere.

## Candidates

| core | lang/flow | perf class | TMR-ability | notes |
|---|---|---|---|---|
| Hazard3 | clean Verilog-2005-subset SV | ~3 CoreMark/MHz, RV32IMC+Zb* | good: compact, flat state | RP2350-proven mass silicon; designed for open flows |
| Ibex | SystemVerilog (sv2v needed) | ~0.9-2.5 CM/MHz configs | good; lowRISC verif culture | strongest upstream DV; sv2v step adds flow risk |
| VexRiscv | SpinalHDL-generated Verilog | 1.2+ CM/MHz | harder: generated names churn per build | efabless-proven; generator pin required for reproducibility |
| picorv32 | Verilog-2005 | ~0.3-0.5 CM/MHz | excellent: tiny, stable | conservative fallback; perf near the floor of "tens of MHz effective" |
| cv32e40p | heavy SystemVerilog | ~1.5 CM/MHz | moderate | sv2v + size make it the heaviest lift on this flow |

## Recommendation

**Primary: Hazard3.** Clean-Verilog flow fit (criterion 1 without
sv2v), mass-production silicon heritage via RP2350, RV32IMC-plus at
a performance class that puts 40 MHz silicon at ~120 CoreMark -
conversational against GR716-class parts. Its compact, flat state
is the best TMR-ability profile after picorv32, and its interfaces
are simple enough that the arch harness retarget is bounded work.

**Fallback: picorv32** if Hazard3's TMR instrumentation surprises -
picorv32's tininess makes full-state TMR almost free, buying the
methodology story at the cost of the performance story.

**Watch: Ibex** if lowRISC's DV assets prove importable through
sv2v with acceptable friction; its verification culture is the
closest match to this program's.

## Verify-before-commit list (knowledge dated early 2026)

- Hazard3 license/upstream state and any RP2350-era errata list
- sv2v fidelity on current Ibex (known good historically; re-prove)
- VexRiscv generator pinning story under our reproducibility bar
- CoreMark/MHz numbers re-measured on OUR flow at OUR corner, not
  quoted from readmes - the shmoo harness exists for exactly this

## The decision gate

The selection LANDS when the ZIRH-3 scope freezes (B10 gate
first - measure before believing applies to program sequencing
too). This study exists so that decision is a day, not a month.
