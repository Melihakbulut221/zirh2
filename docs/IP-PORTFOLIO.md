# The IP and tool portfolio (PROGRAM.md E20)

The real assets of this program are not the chip - they are the
verification tools, the hardened-macro kit, the flow recipe and the
reusable IP, each already proven on ZIRH-2 and each licensable before
any silicon sells. This document is the catalogue; each entry names
what exists TODAY in this repository and what productizing it means.

## 1. tmr-guard (shipping as a product already)

Independent proof that synthesis did not delete your TMR. Home in
tmr-guard/, one-pager in docs/TMRGUARD-PRODUCT.md, demo + negative
control in CI. This is the lead asset - smallest effort to first
revenue. See E19.

## 2. The hardened-macro kit + placement recipe

macro/hardened32/ (a placement-constrained 32-flop TMR macro with
LEF/GDS/lib) plus the proven Run-13 placement recipe documented as
the flow default in docs/SCOPE.md. Product form: an SG13G2
rad-hardening starter kit - the macro, the recipe, and check_tmr as
the acceptance test. Buyer: anyone hardening on the IHP open flow
who does not want to rediscover the 680 um replica-separation floor
the hard way.

## 3. The safe-state TMR FSM generator

scripts/tmr_fsm_gen.py: emits a TMR'd FSM whose illegal encodings
trap to a named safe state - the discipline every controller in this
chip uses (boot, BIST, QSPI, the scrubber). Product form: a licensed
generator with the attestation that its output passes tmr-guard and
carries the embedded assertion contract (src/zirh_assert.vh).

## 4. The TMR'd interface IP mini-library

CAN 2.0A-lite (zirh_can.v), SpaceWire-lite (zirh_spw.v), RS-422
framing (zirh_rs422.v), each with its cocotb golden-model suite and
each surviving tmr-guard. Product form: per-project licensed
protocol IP with an attestation report - the golden model IS the
acceptance evidence. Buyer: a NewSpace ASIC team that needs a
hardened link and cannot justify writing and verifying one.

## 5. The radiation-canary soft macro

src/zirh_env.v as a drop-in: a TID ring-oscillator dosimeter, a SET
catcher and a burst correlator behind one register window, ready to
instrument ANY host chip with in-flight radiation telemetry. Now
packaged with a standalone integration guide (docs/CANARY-IP.md) so
it drops into a foreign design without the rest of ZIRH. Product
form: the cheapest way for any chip to gain a radiation self-report.

## 6. The campaign orchestration library

host/zirh_campaign.py + the SURVIVED/REBOOTED/ZOMBIE classifier +
scripts/beam_analysis.py, driving RTL, GL and beam through ONE
taxonomy. Product form: the seed of a qualification-pipeline service -
the ZOMBIE taxonomy (signature-alive but command-dead) is a
distinction most bench setups miss entirely, and it is the unfair
advantage. Buyer: a qual house, or a customer running their own
campaign who wants the analysis frozen and defensible.

## Licensing posture (owner's gate)

Open core for credibility, per-project licenses for the IP with
attestation reports, support engagements for integration. The
attestation-report format already matches the ECSS evidence-pack
templates this program carries - the same artifact serves the IP
sale and the certification bridge. Terms, pricing and the open/
closed line per asset are the owner's decisions; this catalogue
makes them concrete choices rather than abstract ones.
