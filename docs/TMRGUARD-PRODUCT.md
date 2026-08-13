# TMR-Guard productization one-pager (PROGRAM.md E19)

**The pain**: synthesis silently deletes TMR. Insertion tools check
their own output; no independent netlist checker exists on the
market. Anyone shipping TMR through yosys/OpenLane flows - TinyTapeout
radiation projects, university groups, NewSpace ASIC teams - is one
optimizer pass away from unhardened silicon that passes every test.

**The product**: tmr-guard/ - manifest-driven, seconds per verdict,
no PDK needed, positive AND negative verification (--prove-checker
demonstrates the catch live). Flagship reference: ZIRH-2's ten-block
manifest running in CI on every commit, with the measured 79-to-26
flop collapse as the origin story.

**Why it can earn first**: smallest asset with a complete story -
real pain, working tool, live demo, reference user, zero deployment
friction (two files, python3 + yosys).

**Delivery ladder** (decisions at each rung are the owner's):
1. Open core in the ZIRH repo - credibility and inbound (now).
2. Per-project support engagements: manifest authoring, CI
   integration, count-semantics consulting (first revenue, no
   licensing machinery needed).
3. Standalone repository + versioned releases when an external user
   exists (the split is an afternoon; do it for a user, not for the
   shelf).
4. Commercial tier only if demand shapes it: non-yosys flows
   (Synopsys/Cadence netlist readers), attestation reports for
   ECSS/DO-254 evidence packs (the report format already matches the
   evidence-pack templates in this program).

**First-user profile**: a team that already has TMR RTL and a yosys
path - TinyTapeout space projects, university cubesat ASIC groups,
open-silicon rad experiments. The outreach artifact is the demo:
one command that passes, one command that proves the catch.

**GATE(owner)**: outreach itself, licensing terms, and the
standalone-repo split decision.
