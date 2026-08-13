# ZIRH-2 register map

GENERATED from regmap.yaml by scripts/regmap_gen.py - do not edit. The YAML is the single source; the RTL decode blocks are its ground truth and the R18 access tests are the net between them.

## ROM (0x00000000)

mask ROM, 256x32, synthesized constants; dbus port for

## RAM (0x00001000)

SECDED ECC RAM, 16 words; scrub-on-read; stack top at

## UART (0x00002000)

| offset | register | access |
|---|---|---|
| 0x00 | STATUS | R |
| 0x04 | TXDATA | W |
| 0x08 | RXDATA | R |
| 0x0c | BAUD | RW |

## HK (0x00003000)

| offset | register | access |
|---|---|---|
| 0x00 | ID | R |
| 0x04 | CTRL | RW |
| 0x08 | CPU_SIG | RW |
| 0x0c | INJECT | W |
| 0x10 | CNT_PLAIN | R |
| 0x14 | CNT_RAW_A | R |
| 0x18 | CNT_ESC_A | R |
| 0x1c | CNT_RAW_B | R |
| 0x20 | CNT_ESC_B | R |
| 0x24 | CNT_ECC_C | R |
| 0x28 | CNT_ECC_U | R |
| 0x2c | CNT_BUSTO | R |
| 0x30 | CNT_FERR | R |
| 0x34 | BOOT_CNT | R |
| 0x38 | ENV_RO | RW |
| 0x3c | ENV_SB | RW |

## IFC (0x00003040)

| offset | register | access |
|---|---|---|
| 0x00 | CAN_STAT | R |
| 0x04 | CAN_CTRL | W |
| 0x08 | SPW_STAT | R |
| 0x0c | SPW_CTRL | W |

