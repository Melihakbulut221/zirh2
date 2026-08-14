# The SystemVerilog scenario suites

Two self-checking benches in the RTL's own language, runnable with
nothing but `iverilog -g2012` - no cocotb, no Python. They complement
the cocotb suites from a different angle: where a cocotb test proves
one mechanism, a scenario here is a MISSION SLICE - abuse and normal
operation woven together the way a bench day or a beam shift produces
them, judged the same way every time: the chip keeps telling the truth
on its pins.

    make -C test -f Makefile.svs            # both suites
    make -C test -f Makefile.svs boot       # boot stories (seconds)
    make -C test -f Makefile.svs top        # chip slices (minutes)
    make -C test -f Makefile.svs top SCENARIO=cmd_fuzz

## zirh_scenarios_tb.sv - 17 chip-level mission slices

Boot integrity, living-CPU proof, echo paths (including the bytes
that collide with the frame sync), command fuzzing, injection
bookkeeping, ROM checksum, environment chain, CAN/SpaceWire loopback,
mid-frame reset, reset storms, RX runt glitches, +/-5% baud drift,
line-rate floods, single-replica flip storms during traffic, the
registered double-hit failure geometry, and a soak slice that measures
the simulated false-positive floor.

Two disciplines inherited from lessons already paid for:

- Fault forcing targets REPLICAS (`u_ff_a`/`u_ff_b`), never a voter
  output - forcing the voted wire fakes a fault the voter can neither
  see nor heal.
- UART sampling settles `#1` past the clock edge - the end-of-timestep
  discipline cocotb's ReadOnly gives. Sampling raw at the edge reads
  the PREVIOUS bit whenever a transition lands on the sample edge,
  and a desynced stop bit is a resync, not a failure: listening can
  begin mid-byte.

## zirh_boot_scenarios_tb.sv - 8 boot-controller stories

Golden strap, a good image committing, wrong magic, wrong CRC,
oversize length, a stream that dies mid-payload (and the proof a
half-load bricks nothing), the watchdog revert ladder - and
`storage_lie`, the one only a behavioral memory can stage: the wire
image is perfect, the MEMORY corrupts one stored word, and VERIFY
must refuse the bank. That is the read-back-CRC claim tested at the
only boundary that can test it.

Both benches exit nonzero through `$fatal` on the first failed check
and print `SV_*_SCENARIOS: PASS scenarios=N checks=M` on success; CI
runs them in the test workflow's `sv-scenarios` job.
