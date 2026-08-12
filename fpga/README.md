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

## Measured fit (2026-08-09) - the twin needs a bigger board

The bitstream build settled the open feasibility question with a hard
number: the full five-interface ZIRH-2 is **5565 of 5280 iCE40UP5K
logic cells, 105%** - it does not fit. The repository's earlier ~3540
LUT estimate was the pre-interface v2.1 design; CAN, SpaceWire, the
telemetry mirror, the environment instruments and the N=32 A/B chains
added the rest.

The ROM-to-BRAM lever was applied (registered reads under SYNTH map
the 256x32 array to 8 SB_RAM40_4K blocks) and bought only ~20 LCs: the
bulk is logic - TMR triplication, SERV, and the five protocol engines -
not memory, so no memory lever closes a 285-LC gap.

The honest options, a hardware decision for the bench:

1. **A larger iCE40 / ECP5 board.** iCE40HX8K (7680 LCs) fits the whole
   design with margin on the same icestorm/nextpnr flow; an ECP5 board
   (Lattice, ~85k LUT) is generous headroom. Either needs a top wrapper
   outside the TT ASIC-sim flow (the flow is fixed to UP5K), which is
   ~a day of pin-mapping and a constraints file - the eval-kit path the
   commercial analysis wanted anyway.
2. **A twin-lite config on UP5K.** Drop the two interface experiments
   (CAN + SpaceWire are loopback-only on the bench and cost ~600 LCs
   together) and the design fits UP5K comfortably - a valid demo of the
   SEU/TID/SET instruments, the SERV computer, the watchdog and the
   telemetry, just without the two protocol experiments. A SYNTH-time
   `ZIRH_TWIN_LITE` guard would gate them out.

The registered-ROM change stays regardless: it is correct, SYNTH-only,
ASIC-untouched, and it is the right thing for any FPGA target.

## Twin-lite (2026-08-12) - the UP5K configuration, built and green

Option 2 is now implemented and is the DEFAULT whenever SYNTH is
defined: the TT FPGA flow is fixed to the UP5K, the full design
measured over it, so under SYNTH the two interface experiments are
gated out at the top level. A larger-board wrapper defines
`ZIRH_TWIN_FULL` to restore them; the ASIC flow defines neither and is
untouched.

What lite means on the bench: everything in the bring-up procedure
above works except step 3's 'k'/'K'/'w'/'W' - the interface register
window still acks (reads as zero) so those commands are harmless
no-ops, never a bus timeout. CAN idles recessive, SpaceWire idles low.
The SEU/TID/SET instruments, the SERV computer, the watchdog, both
telemetry voices and the whole campaign contract are all present.

Measured (yosys synth_ice40): full 3770 LUT4 / ~1850 FF, lite
3038 LUT4 / ~1640 FF - the experiments cost 733 LUTs, more than the
~600 estimated, and scaling the earlier nextpnr fit by the LUT ratio
puts lite at roughly 4500 of 5280 LCs (~85%). The bitstream CI run is
the definitive fit number.

Building lite exposed a real twin bug, now fixed: the SYNTH ROM
registered its data-port reads (the BRAM lever) but still acked
combinationally, so the CPU sampled dbus reads one cycle early - the
same stale-read command-path corruption the ASIC dbus experiment hit.
Every twin bitstream since the BRAM lever carried it; the full-chip
suite had simply never run under SYNTH until lite forced it. The ack
is now registered to land with the data, and the full suite passes
under SYNTH in both configurations (lite 5/5 with the interface test
excluded by construction, full 6/6 including the CAN/SpaceWire
loopbacks - so the full twin is also proven for a larger board).
