#!/usr/bin/env python3
# =============================================================================
# ZIRH-2 - random RV32I torture generator with built-in golden model
#
#   python3 scripts/torture_gen.py <outdir> <count> [seed]
#
# The riscv-dv idea sized for a 256-word mask ROM: each program is a
# random straight-line-plus-skips RV32I body (ALU, shifts, forward
# branches, loads/stores confined to the 64-byte ECC RAM) followed by a
# fixed epilogue that folds x1..x15 into a digest and transmits its
# four bytes over the UART registers with status polling. The built-in
# ISS executes the body with the same semantics and predicts the
# digest; the RTL must transmit exactly those bytes through the pins.
#
# What this stresses that the firmware suites cannot: thousands of
# random instruction interleavings through the exact integration we
# modified by hand - the pipelined instruction fetch, the ROM dbus
# port, the bus mux, the ECC RAM write-decode path - judged against an
# independent golden model, at the UART pins.
#
# Output: <outdir>/t<i>.hex (readmemh image) and manifest.json with
# the expected digest bytes per program.
# =============================================================================

import json
import random
import sys
from pathlib import Path

RAM_BASE = 0x1000
RAM_WORDS = 16          # 64 B ECC RAM
UART_BASE = 0x2000
ROM_WORDS = 256
BODY_LEN = 150         # random instructions per program

REGS = [r for r in range(1, 16) if r != 8]   # x8 is the RAM base, never a destination


# --- encoders ----------------------------------------------------------------

def r_type(f7, rs2, rs1, f3, rd, op):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def i_type(imm, rs1, f3, rd, op):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def s_type(imm, rs2, rs1, f3):
    return (((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) \
        | (f3 << 12) | ((imm & 0x1F) << 7) | 0x23


def b_type(imm, rs2, rs1, f3):
    return (((imm >> 12) & 1) << 31) | (((imm >> 5) & 0x3F) << 25) \
        | (rs2 << 20) | (rs1 << 15) | (f3 << 12) \
        | (((imm >> 1) & 0xF) << 8) | (((imm >> 11) & 1) << 7) | 0x63


def u_type(imm20, rd, op):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | op


def jal(rd, imm):
    return (((imm >> 20) & 1) << 31) | (((imm >> 1) & 0x3FF) << 21) \
        | (((imm >> 11) & 1) << 20) | (((imm >> 12) & 0xFF) << 12) \
        | (rd << 7) | 0x6F


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


M32 = 0xFFFFFFFF


# --- the golden model (body semantics only) ----------------------------------

class ISS:
    def __init__(self):
        self.x = [0] * 16
        self.ram = {}

    def step(self, kind, a):
        x = self.x
        if kind == "lui":
            x[a[0]] = (a[1] << 12) & M32
        elif kind == "addi":
            x[a[0]] = (x[a[1]] + a[2]) & M32
        elif kind == "xori":
            x[a[0]] = x[a[1]] ^ (a[2] & M32)
        elif kind == "ori":
            x[a[0]] = x[a[1]] | (a[2] & M32)
        elif kind == "andi":
            x[a[0]] = x[a[1]] & (a[2] & M32)
        elif kind == "slti":
            x[a[0]] = 1 if sx(x[a[1]], 32) < a[2] else 0
        elif kind == "sltiu":
            x[a[0]] = 1 if x[a[1]] < (a[2] & M32) else 0
        elif kind == "slli":
            x[a[0]] = (x[a[1]] << a[2]) & M32
        elif kind == "srli":
            x[a[0]] = x[a[1]] >> a[2]
        elif kind == "srai":
            x[a[0]] = (sx(x[a[1]], 32) >> a[2]) & M32
        elif kind == "add":
            x[a[0]] = (x[a[1]] + x[a[2]]) & M32
        elif kind == "sub":
            x[a[0]] = (x[a[1]] - x[a[2]]) & M32
        elif kind == "sll":
            x[a[0]] = (x[a[1]] << (x[a[2]] & 31)) & M32
        elif kind == "srl":
            x[a[0]] = x[a[1]] >> (x[a[2]] & 31)
        elif kind == "sra":
            x[a[0]] = (sx(x[a[1]], 32) >> (x[a[2]] & 31)) & M32
        elif kind == "slt":
            x[a[0]] = 1 if sx(x[a[1]], 32) < sx(x[a[2]], 32) else 0
        elif kind == "sltu":
            x[a[0]] = 1 if x[a[1]] < x[a[2]] else 0
        elif kind == "xor":
            x[a[0]] = x[a[1]] ^ x[a[2]]
        elif kind == "or":
            x[a[0]] = x[a[1]] | x[a[2]]
        elif kind == "and":
            x[a[0]] = x[a[1]] & x[a[2]]
        elif kind == "lw":
            x[a[0]] = self.ram[a[2]]
        elif kind == "sw":
            self.ram[a[2]] = x[a[1]]
        elif kind == "skip":   # branch taken/not decided by caller
            pass
        x[0] = 0


# --- program generation ------------------------------------------------------

def gen_program(rng):
    words = []
    ops = []            # (kind, args) mirrored into the ISS
    iss = ISS()
    written = []        # RAM offsets already initialized

    def emit(word, kind, args):
        words.append(word)
        ops.append((kind, args))
        iss.step(kind, args)

    # seed registers with random constants: LUI + ADDI pairs, then the
    # RAM base in x8 - which the body never writes
    for rd in REGS:
        hi = rng.getrandbits(20)
        lo = sx(rng.getrandbits(12), 12)
        emit(u_type(hi, rd, 0x37), "lui", (rd, hi))
        emit(i_type(lo, rd, 0, rd, 0x13), "addi", (rd, rd, lo))
    emit(u_type(0x1, 8, 0x37), "lui", (8, 0x1))          # x8 = 0x1000

    alu_r = [("add", 0, 0), ("sub", 0x20, 0), ("sll", 0, 1),
             ("slt", 0, 2), ("sltu", 0, 3), ("xor", 0, 4),
             ("srl", 0, 5), ("sra", 0x20, 5), ("or", 0, 6), ("and", 0, 7)]
    alu_i = [("addi", 0), ("slti", 2), ("sltiu", 3), ("xori", 4),
             ("ori", 6), ("andi", 7)]
    shift_i = [("slli", 1, 0), ("srli", 5, 0), ("srai", 5, 0x20)]

    body = BODY_LEN
    while body > 0:
        roll = rng.random()
        rd = rng.choice(REGS)
        rs1 = rng.choice(REGS)
        rs2 = rng.choice(REGS)
        if roll < 0.35:
            k, f7, f3 = rng.choice(alu_r)
            emit(r_type(f7, rs2, rs1, f3, rd, 0x33), k, (rd, rs1, rs2))
        elif roll < 0.60:
            k, f3 = rng.choice(alu_i)
            imm = sx(rng.getrandbits(12), 12)
            emit(i_type(imm, rs1, f3, rd, 0x13), k, (rd, rs1, imm))
        elif roll < 0.70:
            k, f3, f7 = rng.choice(shift_i)
            sh = rng.getrandbits(5)
            emit(i_type((f7 << 5) | sh, rs1, f3, rd, 0x13), k, (rd, rs1, sh))
        elif roll < 0.80:
            off = 4 * rng.randrange(RAM_WORDS)
            if rng.random() < 0.5 or not written:
                emit(s_type(RAM_BASE + off - RAM_BASE, rs2,  # imm vs x8 base
                            8, 2), "sw", (0, rs2, off))
                written.append(off)
            else:
                off = rng.choice(written)
                emit(i_type(off, 8, 2, rd, 0x03), "lw", (rd, 8, off))
        elif roll < 0.93:
            # compare-and-skip: branch over exactly one ALU instruction
            f3 = rng.choice([0, 1, 4, 5, 6, 7])
            taken = {0: iss.x[rs1] == iss.x[rs2],
                     1: iss.x[rs1] != iss.x[rs2],
                     4: sx(iss.x[rs1], 32) < sx(iss.x[rs2], 32),
                     5: sx(iss.x[rs1], 32) >= sx(iss.x[rs2], 32),
                     6: iss.x[rs1] < iss.x[rs2],
                     7: iss.x[rs1] >= iss.x[rs2]}[f3]
            emit(b_type(8, rs2, rs1, f3), "skip", ())
            k, f7, f3a = rng.choice(alu_r)
            w = r_type(f7, rs2, rs1, f3a, rd, 0x33)
            if taken:
                words.append(w)          # in the image
                ops.append(("skip", ())) # but never executed
            else:
                emit(w, k, (rd, rs1, rs2))
            body -= 1
        else:
            # jal forward skip (rd=x1 exercises the link path)
            rd_l = rng.choice([0, 1])
            link = len(words) * 4 + 4
            emit(jal(rd_l, 8), "skip", ())
            if rd_l:
                iss.x[1] = link
            w = r_type(0, rs2, rs1, 0, rd, 0x33)
            words.append(w)
            ops.append(("skip", ()))
            body -= 1
        body -= 1

    # epilogue: digest = xor of x1..x15 accumulated in x16 - a register
    # OUTSIDE the digest set, so the chain cannot xor itself to zero
    # when it passes its own accumulator - then 4 UART bytes
    epi = []
    epi.append(r_type(0, 2, 1, 4, 16, 0x33))             # xor x16,x1,x2
    for r in range(3, 16):
        epi.append(r_type(0, r, 16, 4, 16, 0x33))        # xor x16,x16,xr
    digest = 0
    for r in range(1, 16):
        digest ^= iss.x[r]
    epi.append(u_type(0x2, 5, 0x37))                     # lui x5,0x2 -> 0x2000
    for _ in range(4):
        epi.append(i_type(0, 5, 2, 7, 0x03))             # lw x7,0(x5)
        epi.append(i_type(1, 7, 7, 7, 0x13))             # andi x7,x7,1
        epi.append(b_type(-8, 0, 7, 0))                  # beq x7,x0,-8
        epi.append(s_type(4, 16, 5, 2))                  # sw x16,4(x5)
        epi.append(i_type(8, 16, 5, 16, 0x13))           # srli x16,x16,8
    epi.append(jal(0, 0))                                # j .

    return words, epi, digest


def assemble(rng):
    while True:
        words, epi, digest = gen_program(rng)
        image = words + epi
        if len(image) <= ROM_WORDS:
            image += [0] * (ROM_WORDS - len(image))
            return image, digest


def main():
    outdir = Path(sys.argv[1])
    count = int(sys.argv[2])
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    outdir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    manifest = {}
    for i in range(count):
        image, digest = assemble(rng)
        hexfile = outdir / f"t{i}.hex"
        hexfile.write_text("\n".join(f"{w:08x}" for w in image) + "\n")
        manifest[f"t{i}.hex"] = [(digest >> (8 * k)) & 0xFF for k in range(4)]
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"{count} programs -> {outdir} (seed {seed})")


if __name__ == "__main__":
    main()
