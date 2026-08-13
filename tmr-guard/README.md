# tmr-guard

**Independent proof that your TMR survived synthesis.**

Three identical registers driven by identical logic are, to an
optimizer, one register. Yosys merges them, the resulting netlist
simulates IDENTICALLY, and your hardening is simply gone. Measured on
the chip this tool was built for: 79 flip-flops became 26, every test
still green, every replica deleted. Insertion tools verify their own
output; nothing on the market independently checks the netlist you
actually ship. This does.

## Quickstart (yosys + python3, nothing else)

```sh
cd demo
python3 ../tmr_guard.py demo.tmr.json                  # PASS: 3 replicas, 24 FFs
python3 ../tmr_guard.py demo.tmr.json --prove-checker  # and the proof it CAN fail
```

The second command strips the protection attributes from a copy of
the sources and asserts the check then FAILS - a checker that cannot
catch the collapse it exists for is worse than no checker. That
negative control runs in this repository's CI on every push.

## Declare, verify, both directions

A manifest names each block's replica module pattern and the instance
and flip-flop counts that must survive a flatten-and-optimize pass:

```json
{
  "src_dir": ".",
  "replica_pattern": "demo_rep",
  "protection_attribute": "keep_hierarchy",
  "checks": [
    {"name": "demo", "top": "demo_top",
     "sources": ["demo_design.v"],
     "expect_instances": 3, "expect_ffs": 24}
  ]
}
```

No PDK, no liberty files: replica merging happens in the early opt
passes, so the verdict takes seconds. The counting semantics that
bite in practice (paramod definitions vs instantiations, post-techmap
DFF totals) are handled and documented in the tool header - both were
paid for in the field before they became features.

## The flagship user

examples/zirh2.tmr.json is the manifest of ZIRH-2, a radiation-
tolerant experiment chip hardened on the IHP SG13G2 open PDK: ten
blocks, forty-nine replica islands, thirty-seven hundred flip-flops,
checked in CI on every commit alongside formal proofs and a
gate-level fault campaign. This tool exists because that chip's
hardening silently vanished once; it has not vanished unnoticed
since.

## Status and license

The tool lives inside the ZIRH repository (Apache-2.0) while it
earns its first external users; per-project support and integration
into non-yosys flows are conversations - open an issue.
