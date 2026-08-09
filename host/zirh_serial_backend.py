# =============================================================================
# SerialBackend - the campaign contract against real hardware
#
# The twin and, later, silicon on a beamline are the same thing to the
# campaign library: a device on a serial port that answers commands and
# emits telemetry. This backend implements the four Backend hooks over
# that link, so run_campaign() drives an iCE40 twin exactly as it drives
# a cocotb DUT - the rehearsal the FPGA twin exists for.
#
# Injection on real hardware is not a Force on a net; it is whatever the
# firmware exposes. The command set already carries fault injection
# ('0'..'4' hit the monitor rings) - a beam does the RF corruption for
# free. So `inject` here commands the firmware's own injection path for
# a bench rehearsal, and a real beam run uses NullInjector: the ion is
# the injector and the backend only probes and classifies.
#
#   from zirh_campaign import run_campaign, CampaignReport, InjectionSpec
#   from zirh_serial_backend import SerialBackend
#   import serial
#   sp = serial.Serial("/dev/ttyUSB0", baud, timeout=0.2)
#   be = SerialBackend(sp)
#   run_campaign(be, [[InjectionSpec()]] * 30, CampaignReport(backend="twin"))
# =============================================================================

import time

from zirh_ground import Decoder


class SerialBackend:
    """Backend over a ZIRH serial link. probe echoes a byte the command
    set leaves alone (lowercase p..w, minus the taken ones); boot_count
    and signature come from decoded telemetry frames; inject either
    commands the firmware's injection path (bench) or does nothing (beam,
    where the beam is the injector)."""

    def __init__(self, sp, inject_cmd=b"1", beam_mode=False,
                 recover_s=2.0, probe_bytes=(0x70, 0x72, 0x74, 0x76)):
        self.sp = sp
        self.inject_cmd = inject_cmd
        self.beam_mode = beam_mode
        self.recover_s = recover_s
        self.probe_bytes = list(probe_bytes)
        self._pi = 0
        self.dec = Decoder()
        self._last_sig = None
        self._last_boot = 0

    def _pump(self, seconds):
        end = time.time() + seconds
        frames = []
        while time.time() < end:
            data = self.sp.read(256)
            for ev, pl in self.dec.feed(data):
                if ev == "frame":
                    frames.append(pl)
        return frames

    def _latest(self, seconds=1.5):
        frames = self._pump(seconds)
        return frames[-1] if frames else None

    def signature_alive(self):
        f = self._latest()
        if f is None or f.cpu_sig is None:
            return False
        alive = self._last_sig is not None and f.cpu_sig != self._last_sig
        self._last_sig = f.cpu_sig
        return alive

    def boot_count(self):
        f = self._latest()
        if f is None or f.boot is None:
            return self._last_boot
        self._last_boot = f.boot
        return f.boot

    def inject(self, spec):
        if self.beam_mode:
            return                       # the ion is the injector
        for _ in range(spec.count):
            self.sp.write(self.inject_cmd)
            time.sleep(0.02)

    def probe(self):
        b = self.probe_bytes[self._pi % len(self.probe_bytes)]
        self._pi += 1
        self.sp.reset_input_buffer()
        self.sp.write(bytes([b]))
        want = (b + 1) & 0xFF
        end = time.time() + 2.0
        while time.time() < end:
            for byte in self.sp.read(64):
                if byte == want:
                    return True
        return False

    def recover(self):
        time.sleep(self.recover_s)
