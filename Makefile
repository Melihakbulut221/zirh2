# =============================================================================
# ZIRH - the single entry point (PROGRAM.md H43: reproducibility)
#
#   make units          every unit suite (needs PDK_ROOT for the SRAM ones)
#   make lint           the verilator gate (scripts/lint.sh)
#   make formal         every formal proof (yosys-smtbmc + z3)
#   make tmr            synthesis-integrity check (tmr-guard)
#   make trace          requirements traceability gate
#   make repro SEED=x   rerun the RV32I torture at a recorded seed -
#                       the same programs, the same golden digests,
#                       bit-identical verdicts (seeds: test/seeds.txt)
#   make everything     all of the above (the full local CI mirror)
#
# Pinning: pip via test/requirements.txt, the IHP PDK via the ciel
# hash in .github/workflows/ci.yaml, GL netlist regeneration via the
# gds workflow's pinned TT action tag. The CI line runs these same
# entry points; green here means green there.
# =============================================================================

PDK_ROOT ?= $(HOME)/.ciel
SEED     ?= 1
COUNT    ?= 50

.PHONY: units lint formal tmr trace repro everything

units:
	$(MAKE) -C test -B -f Makefile.hk
	PDK_ROOT=$(PDK_ROOT) $(MAKE) -C test -B -f Makefile.sram
	PDK_ROOT=$(PDK_ROOT) $(MAKE) -C test -B -f Makefile.sram39
	PDK_ROOT=$(PDK_ROOT) $(MAKE) -C test -B -f Makefile.boot
	PDK_ROOT=$(PDK_ROOT) $(MAKE) -C test -B -f Makefile.bist
	$(MAKE) -C test -B -f Makefile.dbg

lint:
	PDK_ROOT=$(PDK_ROOT) bash scripts/lint.sh

formal:
	bash scripts/formal.sh

tmr:
	bash scripts/check_tmr.sh

trace:
	python3 scripts/trace_check.py

repro:
	bash scripts/torture.sh $(COUNT) $(SEED)

everything: lint trace tmr units formal repro
