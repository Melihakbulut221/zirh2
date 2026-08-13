#!/bin/bash
# =============================================================================
# ZIRH - riscv-arch-test runner (H46): the I-did-not-break-the-core proof
#
#   ARCH_TEST=<riscv-arch-test 2.7.4 checkout> \
#   CROSS=riscv-none-elf- bash scripts/archtest.sh [test-name ...]
#
# Builds every rv32i_m/I test against the ZIRH target model
# (test/arch/), runs it on the integrated serv_rf_top in tb_arch, and
# diffs the dumped signature against the suite's reference. Any
# mismatch fails; the summary line is the evidence artifact.
# =============================================================================
set -eo pipefail
cd "$(dirname "$0")/.."

ARCH=${ARCH_TEST:?point ARCH_TEST at a riscv-arch-test 2.7.4 checkout}
CROSS=${CROSS:-riscv-none-elf-}
SUITE=$ARCH/riscv-test-suite/rv32i_m/I
ENVD=$ARCH/riscv-test-suite/env
OUT=test/arch/out
mkdir -p $OUT

iverilog -g2012 -o $OUT/tb_arch.vvp -s tb_arch \
    src/serv/serv_*.v test/arch/tb_arch.v

TESTS="${@:-$(ls $SUITE/src | sed 's/\.S$//')}"
pass=0; fail=0
mkdir -p $OUT/src
for t in $TESTS; do
  # newer binutils rejects the suite's 'la x0, <label>' idiom (it
  # reaches gas through the TEST_JALR_OP macro). The value lands in
  # x0 and is discarded, so an equal-size pair of x0 writes is
  # semantics- and layout-preserving; preprocess first so the fix
  # sees the EXPANDED text, then assemble the patched result.
  if ! ${CROSS}gcc -E -x assembler-with-cpp \
      -I test/arch -I $ENVD -DXLEN=32 \
      $SUITE/src/$t.S -o $OUT/src/$t.pre.s 2> $OUT/$t.cc.log; then
    echo "FAIL $t (preprocess)"; fail=$((fail+1)); continue
  fi
  sed 's/la x0, *\([0-9]*[bf]\)/auipc x0, 0; addi x0, x0, 0/g' \
      $OUT/src/$t.pre.s > $OUT/src/$t.s
  if ! ${CROSS}gcc -march=rv32i_zicsr -mabi=ilp32 -static -mcmodel=medany \
      -fvisibility=hidden -nostdlib -nostartfiles \
      -T test/arch/link.ld \
      $OUT/src/$t.s -o $OUT/$t.elf 2>> $OUT/$t.cc.log; then
    echo "FAIL $t (compile)"; fail=$((fail+1)); continue
  fi
  ${CROSS}objcopy -O binary $OUT/$t.elf $OUT/$t.bin
  python3 - "$OUT/$t.bin" "$OUT/$t.hex" <<'PY'
import sys
b = open(sys.argv[1], 'rb').read()
b += b'\x00' * (-len(b) % 4)
with open(sys.argv[2], 'w') as f:
    for i in range(0, len(b), 4):
        f.write(f"{int.from_bytes(b[i:i+4], 'little'):08x}\n")
PY
  vvp -n $OUT/tb_arch.vvp +HEX=$OUT/$t.hex +SIG=$OUT/$t.sig \
      > $OUT/$t.log 2>&1 || { echo "FAIL $t (sim)"; fail=$((fail+1)); continue; }
  ref=$SUITE/references/$t.reference_output
  if diff -q <(tr 'A-F' 'a-f' < "$ref") $OUT/$t.sig > /dev/null; then
    pass=$((pass+1))
  else
    echo "FAIL $t (signature)"
    fail=$((fail+1))
  fi
done
echo "archtest: $pass passed, $fail failed of $((pass+fail))"
[ $fail -eq 0 ]
