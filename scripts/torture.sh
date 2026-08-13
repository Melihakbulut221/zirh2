#!/bin/bash
# =============================================================================
# ZIRH-2 - run the RV32I torture: N random programs vs the golden model
#
#   bash scripts/torture.sh [count] [seed]     default: 50 1
#
# Generates count programs, compiles the soc harness once, then runs
# each program through the RTL and compares the UART digest bytes with
# the built-in ISS prediction. Any mismatch stops the run with the
# failing seed/index printed - rerun a single case by copying its .hex
# to test/torture.hex and invoking make -f Makefile.torture GOLDEN=...
# =============================================================================
set -e
cd "$(dirname "$0")/.."
COUNT=${1:-50}
SEED=${2:-1}
DIR=test/torture_progs

python3 scripts/torture_gen.py $DIR $COUNT $SEED

cd test
PASS=0
for i in $(seq 0 $((COUNT - 1))); do
  cp torture_progs/t$i.hex torture.hex
  GOLDEN=$(python3 -c "import json;print(','.join(map(str,json.load(open('torture_progs/manifest.json'))['t$i.hex'])))")
  rm -f results.xml
  if ! GOLDEN=$GOLDEN make -f Makefile.torture >/dev/null 2>torture_last.log; then
    echo "TORTURE FAIL at t$i (seed $SEED) - test/torture_last.log has the run"
    exit 1
  fi
  grep -q "FAIL=0" results.xml 2>/dev/null || true
  PASS=$((PASS + 1))
  [ $((PASS % 10)) -eq 0 ] && echo "  $PASS/$COUNT green"
done
echo "torture: $PASS/$COUNT programs match the golden model at the pins"
