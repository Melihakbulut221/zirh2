#!/usr/bin/env python3
# =============================================================================
# ZIRH - bench tests as code, before silicon (PROGRAM.md H45, G31)
#
#   python3 host/zirh_bench.py smoke --port /dev/ttyUSB0 --baud 115200
#   python3 host/zirh_bench.py soak  --port ... --hours 504 --csv soak.csv
#   python3 host/zirh_bench.py shmoo --port ... --plan shmoo_plan.csv
#   python3 host/zirh_bench.py --selftest
#
# The G31 ladder, written today and tested against a mock of the
# chip's telemetry so silicon day is pressing a key:
#
#   smoke   frames arrive, checksums hold, sequence advances, the CPU
#           signature changes, the echo answers - the five-minute
#           is-it-alive verdict, exit code readable by a bringup rig
#   soak    the long logger: every frame's counters to CSV, drift and
#           event detection, and the FALSE-POSITIVE FLOOR report -
#           "N hours, zero events" is the reliability certificate the
#           beam counters will stand on
#   shmoo   frequency x voltage sweep automation with a pluggable
#           instrument interface; without programmable instruments it
#           prompts the operator per point and still produces the
#           same machine-readable envelope map
#
# Frame format is the v2 telemetry (test/test.py is the reference):
# 20 bytes, sync 5A 33, XOR checksum in byte 19.
# =============================================================================

import argparse
import sys
import time

FRAME_LEN = 20
SYNC0, SYNC1 = 0x5A, 0x33


# --- transport ---------------------------------------------------------------

class MockPort:
    """A software ZIRH-2: valid frames on a timer, echo on demand.
    Used by --selftest and by CI - the bench logic is testable today."""

    def __init__(self, seq_break=False):
        self.rxq = bytearray()
        self.seq = 0
        self.sig = 1
        self.frames = 0
        self.seq_break = seq_break

    def _frame(self):
        f = [SYNC0, SYNC1, (self.seq << 4) | 0x08] + [0] * 10
        f += [0, 0, self.sig & 0xFF, 0, 0, 0]
        chk = 0
        for b in f:
            chk ^= b
        f.append(chk)
        self.seq = (self.seq + (2 if self.seq_break else 1)) % 16
        self.sig = (self.sig * 5 + 1) % 251 or 1
        self.frames += 1
        return bytes(f)

    def read(self, n, timeout=1.0):
        while len(self.rxq) < n:
            self.rxq += self._frame()
        out = bytes(self.rxq[:n])
        del self.rxq[:n]
        return out

    def write(self, data):
        for b in data:
            self.rxq += bytes([(b + 1) & 0xFF])   # firmware echo: b+1


def open_port(args):
    if args.port == "mock":
        return MockPort()
    import serial
    sp = serial.Serial(args.port, args.baud, timeout=1)

    class Wrap:
        def read(self, n, timeout=1.0):
            return sp.read(n)

        def write(self, d):
            sp.write(d)
    return Wrap()


# --- frame machinery ---------------------------------------------------------

def hunt_frame(port, deadline_s=10.0):
    t0 = time.monotonic()
    buf = bytearray()
    while time.monotonic() - t0 < deadline_s:
        buf += port.read(1)
        if len(buf) >= FRAME_LEN and buf[-FRAME_LEN] == SYNC0 \
           and buf[-FRAME_LEN + 1] == SYNC1:
            f = bytes(buf[-FRAME_LEN:])
            chk = 0
            for b in f[:19]:
                chk ^= b
            if chk == f[19]:
                return f
    return None


def fields(f):
    return {
        "seq": f[2] >> 4, "armed": (f[2] >> 3) & 1,
        "plain": f[3] << 8 | f[4], "raw_a": f[5] << 8 | f[6],
        "esc_a": f[7] << 8 | f[8], "raw_b": f[9] << 8 | f[10],
        "esc_b": f[11] << 8 | f[12], "ecc_c": f[13], "ecc_u": f[14],
        "sig": f[15], "boot": f[16], "busto": f[17], "ferr": f[18],
    }


# --- the ladder --------------------------------------------------------------

def smoke(port, n_frames=5, quiet=False):
    say = (lambda *a: None) if quiet else print
    prev = None
    sigs = set()
    for i in range(n_frames):
        f = hunt_frame(port)
        if f is None:
            say(f"SMOKE FAIL: no valid frame ({i} seen)")
            return False
        d = fields(f)
        if prev is not None and (d["seq"] - prev) % 16 != 1:
            say(f"SMOKE FAIL: sequence broke {prev}->{d['seq']}")
            return False
        prev = d["seq"]
        sigs.add(d["sig"])
        if not d["armed"]:
            say("SMOKE FAIL: monitor not armed")
            return False
    if len(sigs) < 2:
        say("SMOKE FAIL: CPU signature frozen - computer dead")
        return False
    port.write(bytes([0x41]))
    t0 = time.monotonic()
    while time.monotonic() - t0 < 5.0:
        b = port.read(1)
        if b and b[0] == 0x42:
            say("SMOKE PASS: frames, checksums, sequence, living "
                "signature, echo")
            return True
    say("SMOKE FAIL: echo never answered")
    return False


def soak(port, hours, csv_path, quiet=False):
    say = (lambda *a: None) if quiet else print
    t_end = time.monotonic() + hours * 3600
    events = 0
    frames = 0
    boots = 0
    last = None
    with open(csv_path, "w") as csv:
        csv.write("t,seq,plain,raw_a,esc_a,raw_b,esc_b,ecc_c,ecc_u,"
                  "sig,boot,busto,ferr\n")
        while time.monotonic() < t_end:
            f = hunt_frame(port)
            if f is None:
                say("SOAK: telemetry gap")
                continue
            d = fields(f)
            frames += 1
            csv.write(f"{time.time():.1f},{d['seq']},{d['plain']},"
                      f"{d['raw_a']},{d['esc_a']},{d['raw_b']},"
                      f"{d['esc_b']},{d['ecc_c']},{d['ecc_u']},"
                      f"{d['sig']},{d['boot']},{d['busto']},{d['ferr']}\n")
            if last is not None:
                for k in ("plain", "raw_a", "esc_a", "raw_b", "esc_b",
                          "ecc_c", "ecc_u"):
                    if d[k] != last[k]:
                        events += 1
                        say(f"SOAK EVENT: {k} {last[k]}->{d[k]}")
                if d["boot"] != last["boot"]:
                    boots += 1
            last = d
    say(f"SOAK REPORT: {hours:g} h, {frames} frames, {events} counter "
        f"events, {boots} reboots")
    say(f"false-positive floor: {events / hours if hours else 0:.4g} "
        "events/hour - this number certifies the beam counters")
    return events


def shmoo(port, plan_path, out_path):
    """plan CSV: freq_mhz,voltage per line; instruments prompt the
    operator unless a driver replaces set_point()."""
    def set_point(f_mhz, volts):
        print(f"SHMOO: set clock={f_mhz} MHz, VDD={volts} V, "
              "then press enter", file=sys.stderr)
        input()
    results = []
    for line in open(plan_path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        f_mhz, volts = (float(x) for x in line.split(","))
        set_point(f_mhz, volts)
        ok = smoke(port, n_frames=3, quiet=True)
        results.append((f_mhz, volts, ok))
        print(f"SHMOO point f={f_mhz} V={volts}: "
              f"{'PASS' if ok else 'FAIL'}")
    with open(out_path, "w") as out:
        out.write("freq_mhz,voltage,pass\n")
        for f_mhz, volts, ok in results:
            out.write(f"{f_mhz},{volts},{int(ok)}\n")
    print(f"SHMOO map -> {out_path}")


# --- selftest ----------------------------------------------------------------

def selftest():
    print("== smoke against the mock chip ==")
    assert smoke(MockPort()), "mock smoke must pass"
    print("== smoke must catch a broken sequence ==")
    assert not smoke(MockPort(seq_break=True), quiet=True), \
        "broken sequence must fail"
    print("== soak: quiet mock has a zero event floor ==")
    n = soak(MockPort(), hours=1e-4, csv_path="/tmp/zirh_soak_self.csv",
             quiet=True)
    assert n == 0, "quiet mock produced events"
    print("selftest: bench logic behaves; silicon day is a key press")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("--selftest", "selftest"):
        selftest()
        sys.exit(0)
    ap = argparse.ArgumentParser()
    ap.add_argument("mode")
    ap.add_argument("--port", default="mock")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--hours", type=float, default=1.0)
    ap.add_argument("--csv", default="soak.csv")
    ap.add_argument("--plan", default="shmoo_plan.csv")
    ap.add_argument("--out", default="shmoo_map.csv")
    args = ap.parse_args()
    if args.mode == "smoke":
        sys.exit(0 if smoke(open_port(args)) else 1)
    elif args.mode == "soak":
        soak(open_port(args), args.hours, args.csv)
    elif args.mode == "shmoo":
        shmoo(open_port(args), args.plan, args.out)
    else:
        sys.exit(f"unknown mode {args.mode}")
