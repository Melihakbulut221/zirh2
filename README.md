# ZIRH-2

**Radiation-Tolerant Experiment Chip 2: a computer under the beam**

> Successor to [ZIRH-1](https://github.com/Melihakbulut221/zirh). Where
> ZIRH-1 measures what radiation does to storage, ZIRH-2 measures
> whether a hardened computing element keeps executing - and which of
> its protections earn their area. IHP SG13G2 130 nm, 8x2 Tiny Tapeout
> tile.

## The two experiments

**Placement A/B.** ZIRH-1's layout analysis showed the placer clusters
TMR replicas of the same bit within 4-12 um of their shared voter - one
particle can defeat the vote. ZIRH-2 carries two identical TMR rings:
chain A's replicas are pre-hardened macros pinned 700/680/1380 um
apart; chain B is tool-placed on the same die. ESCAPE(A) vs ESCAPE(B)
in every telemetry frame prices placement separation in one number.

**The computer.** An unhardened SERV RISC-V (its crash rate is itself a
measurement) runs from an SEU-immune mask ROM, keeps state in SECDED
RAM with scrub-on-read, and proves its life every loop iteration with a
rolling signature the telemetry carries. The bus watchdog guarantees a
wedged peripheral costs an event, not the CPU.

## Verified

Eleven cocotb suites (integration through the TT harness at silicon
parameters, gate-level in CI), ten synthesis integrity checks pinning
every block's replica and flop counts in BOTH directions - TMR that
must survive, and the ECC RAM's deliberate zero TMR. Hardened clean on
the 8x2-class die with the bound macros: 81% utilization, setup
+6.5 ns at the 50 MHz constraint (20 MHz nominal), hold +79 ps,
DRC/LVS/antenna zero.

```sh
pip install -r test/requirements.txt
make -C test                  # integration via the TT harness
bash scripts/check_tmr.sh     # hardening survives synthesis, 10 checks
make -C fw                    # firmware (riscv-none-elf-, CI does this)
```

The mask ROM contents are committed as src/rom_init.vh, generated from
the CI firmware build - synthesis needs no toolchain and no parameter
plumbing.

## Documentation

- docs/info.md - datasheet: how it works, bench sequence
- docs/PINMAP.md - frozen pin map and its rationale
- docs/SCOPE.md - the engineering record: every sizing decision with
  the measurement that forced it, including the 8x2 probe that failed
  at 86% density and the shrink that fixed it

## License

Apache-2.0. SERV is vendored unmodified from
[olofk/serv](https://github.com/olofk/serv) (pin in src/serv/VERSION).

---

*Like ZIRH-1: a research vehicle, not flight hardware. It is the chip
you build so that one day you know how to build that one.*
