# ZIRH-2 FPGA twin (iCE40UP5K)

The twin exists to answer two questions no simulation can, and to
rehearse an entire beam campaign at zero dollars per hour before the
real one runs at roughly three thousand.

## What only the twin proves

1. **The 2^22 voluntary warm restart.** The firmware jumps to _start
   every 4,194,304 loop iterations to clear a zombie's corrupted
   register state (the finding that signature liveness is not
   command-path liveness). At the silicon clock rate this is minutes;
   in event-driven simulation it is unreachable, so it has never
   executed end to end. On the twin at 12 MHz it fires every few
   minutes - watch BOOT stay flat (a warm restart is not a watchdog
   reboot) while a deliberately induced zombie clears on schedule.

2. **The ECC RAM mapping delta.** In silicon the ECC array reads
   combinationally: `wire raw = mem[idx]` with the decode-correct in
   the same cycle. The iCE40 block RAM (SB_RAM40_4K) is
   synchronous-read only, so yosys maps a 16x39 comb-read array to
   logic (registers plus a read mux), not BRAM - functionally
   identical, more LUTs. The bitstream build settles whether the whole
   design still fits UP5K once the RF file, the ROM and this array
   compete for BRAM; the feasibility estimate was ~3540 LUT. If the
   fit is tight, the documented lever is mapping the ROM to BRAM (it
   is read-only and address-registered-safe) to free logic. Any
   twin-vs-silicon read-timing difference is a TWIN artifact, recorded
   here, never a design change.

## Bring-up procedure

Prerequisites: iCE40UP5K board (Upduino/iCEBreaker class), a 3.3 V
USB-serial adapter on the two serial pins, the bitstream artifact from
the `fpga` CI workflow.

1. Flash the bitstream. Confirm HEARTBEAT (uo[0]) blinks ~1.2 Hz at
   the board clock scaled from 20 MHz - if the board runs 12 MHz the
   rate scales; the point is that it blinks at all.
2. `python3 host/zirh_ground.py --port /dev/ttyUSB0 --baud <rate>` -
   frames must stream, checksums valid, CPU_ALIVE (uo[1]) toggling.
   The `--baud` is the board clock divided by RESET_DIV; print it from
   the build or scan.
3. Command path: send '0'..'4' and watch the RAW/ESC counters move by
   one in the next frame; 'T'/'S'/'B'/'E' for the environment
   instruments; 'k'/'K'/'w'/'W' for CAN and SpaceWire (loop the pins
   with jumper wires - CAN_TX to CAN_RX, SPW_DOUT/SOUT to DIN/SIN).
4. Dual voice: a second serial adapter on TLM_MIRROR (uio[7]) and
   `--mirror-port` proves the flood-proof channel on real hardware.
5. Warm-restart watch: leave it running for ten minutes with `--csv`;
   the log must show the loop counter and signature advancing with no
   BOOT increment - the voluntary restart re-deriving state invisibly.

## Campaign rehearsal

The twin is the SerialBackend target the campaign library was built
for: `run_campaign` with a backend that injects by commanding the
firmware and probes over the same serial link exercises the full
survived/rebooted/zombie contract against real gates before beam time.
The rehearsal that finds a broken script or a miswired counter on the
bench for free is the rehearsal that does not find it at hour three of
eight on the beamline.
