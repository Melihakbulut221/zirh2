## How it works

ZIRH-2 is a radiation-hardening experiment chip that carries its own
computer. A TMR-protected-by-measurement SERV RISC-V core (bit-serial
RV32I) runs housekeeping firmware from a 1 KB mask ROM, keeps its live
state in a 64-byte SECDED-protected RAM, and talks to its peripherals
over a single-master bus guarded by a TMR'd watchdog: a slave that never
answers costs one DEADBEEF response and a telemetry event, never a hung
CPU.

The measurement heart is the housekeeping block: three circulating
64-bit rings under the same beam. A PLAIN ring of ordinary flops gives
the cross-section reference. Two identical TMR rings differ in exactly
one thing - chain A's three replicas are pre-hardened macros pinned
hundreds of micrometers apart, chain B's replicas are placed by the
tool, which measurably clusters them within 4-12 um of each other.
ESCAPE(A) versus ESCAPE(B), reported side by side in every telemetry
frame, measures directly what placement separation buys against
multi-cell upsets.

Every 3.3 ms the chip emits a 17-byte telemetry frame ("Z2" sync, all
five ring counters, ECC corrected/uncorrected counts, the firmware's
rolling liveness signature, XOR checksum) - unprompted, CPU-independent
in priority, at 114.9 kBd. A frozen CPU signature in a stream of valid
frames is the chip's core demonstration: the instrument reports while
the computer's death is visible from the ground.

## How to test

Reset, then:

1. HEARTBEAT (uo[0]) blinks at ~1.2 Hz: clock, reset and TMR alive.
2. CPU_ALIVE (uo[1]) toggles rapidly: the firmware is executing and
   writing its signature. HEARTBEAT without CPU_ALIVE = instrument
   alive, computer dead - the chip's two-LED self-diagnosis.
3. Telemetry frames arrive on UART_TX (uo[4]) at 115200 8N1: sync bytes
   5A 32, XOR checksum, CPU signature changing frame to frame. Decode
   with host/zirh_ground.py from the project repository.
4. Send any byte to UART_RX (ui[3]): the firmware answers with byte+1
   between frames - RX, bus, CPU and TX proven in one exchange.
5. Fault injection and pattern control run over the UART command path
   through firmware (housekeeping registers at 0x3000): flip one bit of
   either chain, one replica or all three, and watch exactly the right
   counter move by one in the next frame.

## External hardware

None required - any 3.3 V serial adapter. Optional: LEDs on HEARTBEAT
and CPU_ALIVE, a scope on SEU_EVT (uo[2]) to watch beam events live,
an RS422 transceiver pair for a flight-representative link.
