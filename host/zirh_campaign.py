# =============================================================================
# zirh_campaign - the fault-campaign contract as a library
#
# One outcome taxonomy and one judge for every backend that injects
# faults into a ZIRH-class device: cocotb RTL simulation, cocotb
# gate-level simulation, an FPGA twin on a serial port, silicon on a
# beamline. The campaigns that shaped it are in test/test_campaign.py,
# test/test_storm.py, test/test_mega.py and test/test_gl_campaign.py;
# this module is their shared core, factored out so RTL, gates, twin and
# beam accumulate results in ONE format with ONE set of definitions.
#
# THE CONTRACT (measured, not designed at a whiteboard):
#
#   SURVIVED  - the command path answers after the injection.
#   REBOOTED  - the watchdog fired and counted (BOOT climbed) and the
#               command path answers after recovery; the register file
#               is a RAM the reset does not wipe, so SEVERAL counted
#               reboots before a clean boot are one legitimate REBOOTED
#               outcome, not several failures.
#   ZOMBIE    - the liveness signature keeps moving while the command
#               path stays dead: a corrupted hoisted base pointer feeds
#               the watchdog forever. Signature liveness is NOT command-
#               path liveness. In silicon the firmware's periodic warm
#               restart clears the state at a rate simulation cannot
#               reach, so campaigns COUNT zombies; they do not fail them.
#   SILENT    - signature dead AND no reboot: the one forbidden outcome.
#
# A campaign passes if and only if no trial is SILENT.
#
# The injection DSL (InjectionSpec) describes WHAT to hit in terms every
# backend can honor - a target class and a count - not HOW, so the same
# campaign script drives a cocotb force, a serial command to a twin, or
# a beam-time log annotation. A Backend implements probe/inject/recover
# for its world; run_campaign() is the loop, identical everywhere.
# =============================================================================

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum


class Outcome(str, Enum):
    SURVIVED = "survived"
    REBOOTED = "rebooted"
    ZOMBIE = "zombie"
    SILENT = "silent"


def judge(echo_answered, boot_delta, signature_alive):
    """The contract, as one function.

    echo_answered   - did a command-path probe answer after injection?
    boot_delta      - watchdog BOOT counter increase since injection.
    signature_alive - is the liveness signature still changing?
    """
    if echo_answered:
        return Outcome.REBOOTED if boot_delta > 0 else Outcome.SURVIVED
    # echo dead: a still-moving signature is a zombie (or a machine
    # mid-recovery a caller may re-probe and re-judge); a frozen
    # signature with no reboot is the one forbidden outcome.
    return Outcome.ZOMBIE if signature_alive else Outcome.SILENT


# --- injection DSL -----------------------------------------------------------

class Target(str, Enum):
    RF = "rf"                 # SERV register file - the primary beam target
    REPLICA = "replica"       # one TMR replica (must self-heal)
    CORE = "core"             # anonymous flattened core flop
    RAM = "ram"               # ECC RAM word (must scrub)
    WILD = "wild"             # backend's choice / a real beam's whole die


@dataclass
class InjectionSpec:
    """WHAT to hit, not HOW. count bit-flips into `target` this trial."""
    target: Target = Target.RF
    count: int = 3

    def describe(self):
        return f"{self.count}x {self.target.value}"


@dataclass
class Trial:
    index: int
    injections: list        # list of InjectionSpec.describe() strings
    outcome: str = ""
    boot_delta: int = 0
    notes: str = ""


@dataclass
class CampaignReport:
    """Accumulates trials; JESD57A-shaped bookkeeping fields so a beam
    run's report carries what the standard's data reduction needs."""
    device: str = "ZIRH-2"
    backend: str = "rtl"          # rtl | gl | twin | silicon
    run_id: str = ""
    facility: str = ""            # beam runs: facility / ion / energy
    ion: str = ""
    let_mev_cm2_mg: float = 0.0
    flux_cm2_s: float = 0.0
    fluence_cm2: float = 0.0
    started_utc: str = ""
    trials: list = field(default_factory=list)

    def start(self):
        self.started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return self

    def add(self, trial):
        self.trials.append(trial)
        return trial

    def counts(self):
        c = {o.value: 0 for o in Outcome}
        for t in self.trials:
            c[t.outcome] += 1
        return c

    @property
    def passed(self):
        return all(t.outcome != Outcome.SILENT for t in self.trials)

    def cross_section_cm2(self):
        """Events per unit fluence - the beam number. None until a real
        fluence is set (simulation backends leave it zero); an event here
        is any trial that was not SURVIVED, i.e. the beam changed the
        machine's state observably."""
        if self.fluence_cm2 <= 0:
            return None
        events = sum(1 for t in self.trials
                     if t.outcome != Outcome.SURVIVED.value)
        return events / self.fluence_cm2

    def summary(self):
        c = self.counts()
        line = (f"{self.device}/{self.backend}: "
                f"{c['survived']} survived, {c['rebooted']} rebooted, "
                f"{c['zombie']} zombie, {c['silent']} SILENT "
                f"of {len(self.trials)}")
        xs = self.cross_section_cm2()
        if xs is not None:
            line += f"; cross-section {xs:.3e} cm^2"
        return line

    def to_json(self):
        d = asdict(self)
        d["counts"] = self.counts()
        d["passed"] = self.passed
        xs = self.cross_section_cm2()
        if xs is not None:
            d["cross_section_cm2"] = xs
        return json.dumps(d, indent=2)


# --- backend protocol --------------------------------------------------------

class Backend:
    """A world that can be fault-injected. Subclass and implement the four
    hooks; run_campaign drives them. The same loop serves a cocotb DUT, a
    serial-attached twin, and a beam run whose 'injection' is just the
    ion hitting the die between probes.

    signature_alive(): the liveness signature moved since the last call.
    boot_count():       the watchdog BOOT counter, or -1 if unresolved.
    inject(spec):       apply one InjectionSpec worth of upsets.
    probe():            True if the command path answered.
    recover():          give the device a full recovery window (external
                        reset for sim; a settle delay for a beam)."""

    def signature_alive(self):
        raise NotImplementedError

    def boot_count(self):
        raise NotImplementedError

    def inject(self, spec):
        raise NotImplementedError

    def probe(self):
        raise NotImplementedError

    def recover(self):
        pass


def run_campaign(backend, specs_per_trial, report, recover_between=True,
                 reprobe_on_reboot=2):
    """Run one trial per entry in specs_per_trial (each a list of
    InjectionSpec). Judge each by the contract, record it, and refuse to
    let a SILENT outcome pass silently: the assertion is the product.

    reprobe_on_reboot: a REBOOTED machine may need several counted boot
    cycles before the echo returns (RF is RAM the reset does not wipe);
    re-probe up to this many recovery windows before declaring the echo
    dead."""
    for i, specs in enumerate(specs_per_trial):
        if i and recover_between:
            backend.recover()
        boots_before = backend.boot_count()
        for spec in specs:
            backend.inject(spec)

        echoed = backend.probe()
        boots_after = backend.boot_count()
        boot_delta = (boots_after - boots_before
                      if boots_after >= 0 and boots_before >= 0 else 0)

        if not echoed and boot_delta > 0:
            for _ in range(reprobe_on_reboot):
                backend.recover()
                if backend.probe():
                    echoed = True
                    break

        outcome = judge(echoed, boot_delta, backend.signature_alive())
        report.add(Trial(index=i,
                         injections=[s.describe() for s in specs],
                         outcome=outcome.value, boot_delta=boot_delta))
        assert outcome != Outcome.SILENT, (
            f"trial {i}: SILENT - signature frozen and no reboot, the one "
            f"forbidden outcome (injected {[s.describe() for s in specs]})")
    return report


__all__ = ["Outcome", "judge", "Target", "InjectionSpec", "Trial",
           "CampaignReport", "Backend", "run_campaign"]
