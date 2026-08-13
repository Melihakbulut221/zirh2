#!/usr/bin/env python3
# =============================================================================
# ZIRH - the registered beam analysis (PROGRAM.md H48, G37, G36)
#
#   python3 scripts/beam_analysis.py --selftest
#   python3 scripts/beam_analysis.py escapes  <nA> <fluA> <nB> <fluB>
#   python3 scripts/beam_analysis.py confound <n_dut> <t_dut> <n_ctl> <t_ctl>
#   python3 scripts/beam_analysis.py weibull  <csv: LET,events,fluence per line>
#
# Frozen BEFORE any beam exposure, tested against synthetic data in CI
# (--selftest), and run UNMODIFIED when real data arrives - the
# registered-prediction discipline extended to the analysis itself
# (docs/PREDICTION.md governs what may be edited when: nothing, here).
#
# Methods, chosen for zero dependencies beyond the standard library:
#   escapes   exact conditional (binomial) test for a Poisson rate
#             ratio ESCAPE(B)/ESCAPE(A) with fluence normalization,
#             plus a Clopper-Pearson-style interval on the ratio -
#             the G37 statistics design executed
#   confound  TT-harness SEFI subtraction (G36): control-run rate
#             (beam on, tile deselected) subtracted with propagated
#             Poisson uncertainty
#   weibull   cross-section vs LET fit sigma(L) = sat *
#             (1 - exp(-((L-L0)/W)^s)) by coarse-to-fine grid search
#             (no scipy: reproducibility beats elegance in a frozen
#             script), with per-point Poisson errors reported
# =============================================================================

import math
import sys


# --- small numerics ----------------------------------------------------------

def log_choose(n, k):
    return (math.lgamma(n + 1) - math.lgamma(k + 1)
            - math.lgamma(n - k + 1))


def binom_cdf(k, n, p):
    if p <= 0:
        return 1.0
    if p >= 1:
        return 1.0 if k >= n else 0.0
    s = 0.0
    for i in range(0, k + 1):
        s += math.exp(log_choose(n, i) + i * math.log(p)
                      + (n - i) * math.log(1 - p))
    return min(s, 1.0)


def poisson_ci(n, cl=0.95):
    """Garwood exact interval for a Poisson count via chi-square
    quantiles, computed by bisection on the gamma CDF."""
    def gamma_cdf(x, k):
        # regularized lower incomplete gamma via series (x < k+1) or
        # continued fraction (x >= k+1); adequate for count statistics
        if x <= 0:
            return 0.0
        if x < k + 1:
            term = 1.0 / k
            total = term
            a = k
            for _ in range(500):
                a += 1
                term *= x / a
                total += term
                if term < total * 1e-12:
                    break
            return total * math.exp(-x + k * math.log(x) - math.lgamma(k))
        b0, c0 = x + 1 - k, 1e300
        d0 = 1.0 / b0
        h = d0
        for i in range(1, 500):
            an = -i * (i - k)
            b0 += 2
            d0 = an * d0 + b0
            d0 = 1.0 / (d0 if abs(d0) > 1e-300 else 1e-300)
            c0 = b0 + an / (c0 if abs(c0) > 1e-300 else 1e-300)
            h *= d0 * c0
        q = math.exp(-x + k * math.log(x) - math.lgamma(k)) * h
        return 1.0 - q

    def solve(target, k):
        lo, hi = 0.0, max(10.0, 5 * k + 20)
        for _ in range(200):
            mid = 0.5 * (lo + hi)
            if gamma_cdf(mid, k) < target:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    a = (1 - cl) / 2
    lo = 0.0 if n == 0 else solve(a, n)
    hi = solve(1 - a, n + 1)
    return lo, hi


# --- analyses ----------------------------------------------------------------

def escapes(n_a, flu_a, n_b, flu_b, cl=0.95):
    """Exact rate-ratio inference for ESC(B)/ESC(A), fluence-normalized."""
    n = n_a + n_b
    w = flu_b / (flu_a + flu_b)
    # conditional test: under equal per-fluence rates, n_b | n ~ Bin(n, w)
    p_hi = 1.0 - binom_cdf(n_b - 1, n, w) if n_b > 0 else 1.0
    sig_a = n_a / flu_a
    sig_b = n_b / flu_b
    a_lo, a_hi = poisson_ci(n_a, cl)
    b_lo, b_hi = poisson_ci(n_b, cl)
    ratio = (sig_b / sig_a) if n_a > 0 else float('inf')
    r_lo = (b_lo / flu_b) / (a_hi / flu_a) if a_hi > 0 else float('inf')
    r_hi = (b_hi / flu_b) / (a_lo / flu_a) if a_lo > 0 else float('inf')
    print(f"ESC(A): {n_a} in {flu_a:g} -> sigma {sig_a:.3e} "
          f"[{a_lo / flu_a:.3e}, {a_hi / flu_a:.3e}]")
    print(f"ESC(B): {n_b} in {flu_b:g} -> sigma {sig_b:.3e} "
          f"[{b_lo / flu_b:.3e}, {b_hi / flu_b:.3e}]")
    print(f"ratio B/A: {ratio:.3g}  {int(cl*100)}% CI "
          f"[{r_lo:.3g}, {r_hi:.3g}]")
    print(f"one-sided p (B not elevated): {p_hi:.3e}")
    return ratio, p_hi


def confound(n_dut, t_dut, n_ctl, t_ctl):
    """G36: subtract the harness's own SEFI rate, measured with the
    tile deselected, from the DUT-attributed event rate."""
    r_dut = n_dut / t_dut
    r_ctl = n_ctl / t_ctl
    r_net = r_dut - r_ctl
    var = n_dut / t_dut**2 + n_ctl / t_ctl**2
    err = math.sqrt(var)
    print(f"DUT rate {r_dut:.4g}/s, harness control {r_ctl:.4g}/s")
    print(f"net attributable rate: {r_net:.4g} +/- {err:.4g} /s")
    if r_net < 2 * err:
        print("VERDICT: net rate not significant at ~2 sigma - events "
              "are attributable to the harness, not the tile")
    return r_net, err


def weibull(points):
    """Fit sigma(L) = sat*(1-exp(-((L-L0)/W)^s)) to (LET, n, fluence)
    triples by coarse-to-fine grid search on (sat, L0, W, s)."""
    data = [(let, n / flu, n, flu) for let, n, flu in points]
    smax = max(d[1] for d in data)

    def model(let, sat, l0, w, s):
        if let <= l0:
            return 0.0
        return sat * (1 - math.exp(-(((let - l0) / w) ** s)))

    def chi2(sat, l0, w, s):
        c = 0.0
        for let, sig, n, flu in data:
            m = model(let, sat, l0, w, s)
            var = max(n, 1) / flu**2
            c += (sig - m) ** 2 / var
        return c

    best = None
    grid = dict(
        sat=[smax * f for f in (0.8, 1.0, 1.2, 1.5)],
        l0=[min(d[0] for d in data) * f for f in (0.0, 0.3, 0.6, 0.9)],
        w=[(max(d[0] for d in data)) * f for f in (0.1, 0.3, 0.6, 1.0)],
        s=[0.5, 1.0, 1.5, 2.0, 3.0])
    for sat in grid['sat']:
        for l0 in grid['l0']:
            for w in grid['w']:
                for s in grid['s']:
                    c = chi2(sat, l0, w, s)
                    if best is None or c < best[0]:
                        best = (c, sat, l0, w, s)
    # refine around the winner, three passes
    c, sat, l0, w, s = best
    for _ in range(3):
        for name, cur in (('sat', sat), ('l0', l0), ('w', w), ('s', s)):
            for f in (0.85, 0.95, 1.0, 1.05, 1.15):
                trial = dict(sat=sat, l0=l0, w=w, s=s)
                trial[name] = cur * f if cur else 0.05 * f
                cc = chi2(**trial)
                if cc < c:
                    c, sat, l0, w, s = (cc, trial['sat'], trial['l0'],
                                        trial['w'], trial['s'])
    print(f"weibull fit: sat={sat:.4g} cm2, L0={l0:.4g}, W={w:.4g}, "
          f"s={s:.3g}, chi2={c:.3g} over {len(data)} points")
    for let, sig, n, flu in data:
        lo, hi = poisson_ci(n)
        print(f"  LET {let:6g}: sigma {sig:.3e} "
              f"[{lo / flu:.3e}, {hi / flu:.3e}]  model "
              f"{model(let, sat, l0, w, s):.3e}")
    return sat, l0, w, s


# --- self-test (runs in CI: the frozen analysis must stay runnable) ----------

def selftest():
    print("== escapes: B elevated 10x over A, same fluence ==")
    ratio, p = escapes(4, 1e10, 40, 1e10)
    assert ratio > 5 and p < 1e-6, "known-elevated case must flag"
    print("\n== escapes: identical rates must NOT flag ==")
    ratio, p = escapes(20, 1e10, 20, 1e10)
    assert p > 0.01, "identical rates flagged as elevated"
    print("\n== confound: all events from the harness ==")
    net, err = confound(12, 3600, 11, 3600)
    assert abs(net) < 2 * err, "pure-harness case must be insignificant"
    print("\n== weibull: recover a synthetic curve ==")
    import random
    random.seed(38)
    sat, l0, w, s = 1e-6, 2.0, 10.0, 1.5
    pts = []
    for let in (3, 5, 8, 12, 20, 40, 60):
        sig = sat * (1 - math.exp(-(((let - l0) / w) ** s))) if let > l0 else 0
        flu = 1e8
        n = max(0, int(sig * flu + random.gauss(0, max(1, (sig*flu)**0.5))))
        pts.append((let, n, flu))
    fsat, fl0, fw, fs = weibull(pts)
    assert 0.5 * sat < fsat < 2 * sat, f"sat recovery off: {fsat}"
    print("\nselftest: all analyses behave on synthetic truth")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "--selftest":
        selftest()
    elif sys.argv[1] == "escapes":
        escapes(int(sys.argv[2]), float(sys.argv[3]),
                int(sys.argv[4]), float(sys.argv[5]))
    elif sys.argv[1] == "confound":
        confound(int(sys.argv[2]), float(sys.argv[3]),
                 int(sys.argv[4]), float(sys.argv[5]))
    elif sys.argv[1] == "weibull":
        pts = []
        for line in open(sys.argv[2]):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            let, n, flu = line.split(',')
            pts.append((float(let), int(n), float(flu)))
        weibull(pts)
    else:
        sys.exit(f"unknown mode {sys.argv[1]}")
