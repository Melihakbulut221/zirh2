# Boot architecture: the mask ROM becomes a trusted loader

PROGRAM.md items A5, F25 and F26. Nobody buys an MCU that cannot be
patched; SG13G2 has no flash, so updatability is an architecture, not
a memory macro. This document is the contract; zirh_boot_ctrl.v is
the first hardware piece and its cocotb suite is the proof of the
claims that can be proven before a next-chip integration exists.

## The shape

The mask ROM stops being the firmware and becomes the thing a flight
part actually needs from mask ROM: an immutable, SEU-immune loader
plus a golden minimal firmware. Application firmware lives in
external NVM (rad-tolerant SPI MRAM is the industry default - MRAM
cells are inherently SEU-immune) or arrives from the host over a
transport (UART/CAN/SpaceWire), and executes from the SECDED SRAM
(zirh_sram39 with its scrubber).

Boot sources, sampled from strap pins at reset:

    strap 00  GOLDEN   run the mask-ROM firmware, load nothing
    strap 01  BANK A   load image A from NVM, verify, run from SRAM
    strap 10  BANK B   load image B from NVM, verify, run from SRAM
    strap 11  HOST     accept an image over the host transport

## Image format

Little-endian, 12-byte header followed by the payload:

    [0]  u32  magic    0x5A495248 ("ZIRH")
    [4]  u16  length   payload length in 32-bit words (1..BANK_WORDS-3)
    [6]  u16  version  monotonic, for ground bookkeeping
    [8]  u32  crc32    IEEE 802.3 (poly 0xEDB88320, reflected) over
                       the payload words in transmission byte order

The controller streams the payload into the INACTIVE bank while
accumulating CRC; the bank valid flag flips only after the stored
image's CRC matches. A half-written bank is therefore never valid and
an interrupted update can never brick the part: the previous bank and
the golden ROM are untouched by construction (F26 interruption
tolerance is a structural property, not a protocol promise).

Cryptographic signature: CRC proves integrity, not authenticity. The
product chip adds a public-key check (Ed25519 verify in the golden
firmware, public key in mask ROM, ~3 kB of code and seconds of SERV
time at boot - acceptable for a boot path) before the valid flag may
flip; a fuse bit hard-disables unsigned HOST loads for flight units.
The experiment-class controller implements the hook (a "signature ok"
strobe port) so the FSM is identical either way.

## A/B update flow (F26)

1. Ground writes the new image to the inactive bank (HOST strap or an
   application-level command path).
2. The controller verifies CRC on what was STORED (read-back pass,
   not the stream) and only then marks the bank valid and flips the
   boot preference to it.
3. Next boot runs the new bank. The firmware must write a BOOT_OK
   signon (a register strobe) within the watchdog window.
4. If the watchdog fires before BOOT_OK, the boot controller - which
   lives OUTSIDE the watchdog reset domain, like the housekeeping
   block - increments the bank's fail counter and reboots from the
   OTHER bank; two consecutive failures on both banks fall back to
   the golden ROM firmware. The revert is automatic hardware, no
   ground contact required.

## Fault model, stated honestly

- Loader state (FSM, flags, counters) is TMR with safe-state traps,
  same discipline as the rest of the chip.
- The image in SRAM is under SECDED + scrubber + address mask after
  load; an upset during execution is the application's problem (the
  same problem it has today), not the loader's.
- The valid/preference flags survive watchdog resets but not power
  loss; NVM bank headers are re-verified on every cold boot, so flag
  loss costs one re-verification, never a brick.
- What this does NOT cover: a corrupted NVM device that serves two
  bad banks (golden ROM covers it), transport-layer attacks on HOST
  loads before the signature hook is armed (product-chip fuse), and
  upsets inside the CRC datapath during the single verification pass
  (probability bounded by exposure time; the read-back pass re-reads
  through the SECDED-corrected port, which is why verification is on
  stored data rather than the stream).

## Integration contract (the ZIRH-3 part)

The controller is transport-agnostic: it consumes a byte stream
(valid/data handshake) from whatever front end exists - the SPI MRAM
reader, the UART bridge, a CAN reassembler. It masters the SRAM bus
port for loading and read-back, and it owns two signals the SoC must
honor: boot_sel (fetch from ROM vs SRAM bank) and bank_base. The SoC
side needs the ibus fetch mux (ROM point-to-point today; ROM-or-SRAM
tomorrow) - that is next-chip integration work and stays out of this
block on purpose.
