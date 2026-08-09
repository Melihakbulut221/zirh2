# =============================================================================
# Unit tests for zirh_campaign - the contract library, proven on a fake
# backend that can be scripted into every outcome class.
#
#   python3 -m pytest host/test_zirh_campaign.py
#   (or: python3 host/test_zirh_campaign.py)
# =============================================================================

import json

from zirh_campaign import (Outcome, judge, Target, InjectionSpec,
                           CampaignReport, Backend, run_campaign)


def test_judge_covers_every_branch():
    assert judge(True, 0, True) == Outcome.SURVIVED
    assert judge(True, 3, True) == Outcome.REBOOTED
    assert judge(True, 3, False) == Outcome.REBOOTED     # echo wins
    assert judge(False, 0, True) == Outcome.ZOMBIE
    assert judge(False, 0, False) == Outcome.SILENT
    assert judge(False, 2, False) == Outcome.SILENT      # reboot, sig dead
    assert judge(False, 2, True) == Outcome.ZOMBIE


class ScriptedBackend(Backend):
    """Plays a fixed list of (echo, boot_after_inject, sig_alive) per
    trial. reprobe_echo lets a REBOOTED machine 'come back' on re-probe."""
    def __init__(self, script, reprobe_echo=None):
        self.script = script
        self.reprobe_echo = reprobe_echo or {}
        self.i = -1
        self._boots = 0
        self._probe_calls = 0

    def recover(self):
        pass

    def boot_count(self):
        return self._boots

    def inject(self, spec):
        _, boot_after, _ = self.script[self._trial]
        self._boots = boot_after

    def _begin(self, trial):
        self._trial = trial
        self._probe_calls = 0

    def probe(self):
        echo, _, _ = self.script[self._trial]
        self._probe_calls += 1
        if self._probe_calls == 1:
            return echo
        return self.reprobe_echo.get(self._trial, echo)

    def signature_alive(self):
        return self.script[self._trial][2]


def drive(script, reprobe_echo=None):
    """run_campaign needs per-trial begin bookkeeping; wrap it."""
    be = ScriptedBackend(script, reprobe_echo)
    rep = CampaignReport(backend="test").start()
    specs = [[InjectionSpec(Target.RF, 3)] for _ in script]

    # ScriptedBackend needs an explicit per-trial begin() that the generic
    # run_campaign has no hook for, so drive it directly here; the generic
    # loop is exercised end to end by test_run_campaign_loop_end_to_end
    from zirh_campaign import Trial
    for t, s in enumerate(specs):
        be._begin(t)
        boots_before = be.boot_count()
        for spec in s:
            be.inject(spec)
        echoed = be.probe()
        boot_delta = be.boot_count() - boots_before
        if not echoed and boot_delta > 0:
            for _ in range(2):
                if be.probe():
                    echoed = True
                    break
        oc = judge(echoed, boot_delta, be.signature_alive())
        rep.add(Trial(index=t, injections=[x.describe() for x in s],
                      outcome=oc.value, boot_delta=boot_delta))
    return rep


def test_all_survive():
    rep = drive([(True, 0, True)] * 5)
    assert rep.counts()["survived"] == 5
    assert rep.passed


def test_reboot_that_comes_back_on_reprobe():
    # first probe dead, boot climbed, re-probe answers -> REBOOTED
    rep = drive([(False, 2, True)], reprobe_echo={0: True})
    assert rep.counts()["rebooted"] == 1
    assert rep.passed


def test_zombie_is_counted_not_failed():
    rep = drive([(False, 0, True)] * 3)
    assert rep.counts()["zombie"] == 3
    assert rep.passed          # zombies pass; only SILENT fails


def test_silent_is_caught():
    # a frozen signature with no reboot must raise through run_campaign -
    # the one forbidden outcome is an assertion, so it cannot pass quietly
    class Silent(Backend):
        def boot_count(self): return 0
        def inject(self, spec): pass
        def probe(self): return False
        def signature_alive(self): return False
        def recover(self): pass
    rep = CampaignReport(backend="test").start()
    try:
        run_campaign(Silent(), [[InjectionSpec()]], rep)
    except AssertionError:
        return
    raise AssertionError("SILENT outcome did not raise - the guard is off")


def test_cross_section_and_json():
    rep = drive([(True, 0, True), (False, 0, True), (True, 0, True)])
    rep.fluence_cm2 = 1.0e7
    xs = rep.cross_section_cm2()
    assert xs == 1 / 1.0e7          # one non-survived event
    blob = json.loads(rep.to_json())
    assert blob["counts"]["zombie"] == 1
    assert blob["passed"] is True
    assert "cross_section_cm2" in blob


def test_run_campaign_loop_end_to_end():
    # a real run through run_campaign with a minimal live backend
    class Mini(Backend):
        def __init__(s): s.n = 0; s.boots = 0
        def boot_count(s): return s.boots
        def inject(s, spec): s.n += 1
        def probe(s): return True          # always survives
        def signature_alive(s): return True
        def recover(s): pass
    rep = CampaignReport(backend="rtl").start()
    run_campaign(Mini(), [[InjectionSpec(Target.RF, 3)]] * 4, rep)
    assert rep.counts()["survived"] == 4 and rep.passed


if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ok    {fn.__name__}")
        except Exception as e:
            print(f"  FAIL  {fn.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"zirh_campaign self-test: {len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
