# HE68 PRO protocol notes

## Verified wired interface

| Field | Value |
| --- | --- |
| VID / PID | `0x0C45` / `0x80CB` |
| Vendor usage page | `0xFF68` |
| Report ID / payload length | `0` / 64 bytes |
| Host prefix | `AA 23 10` |
| ACK prefix | `55 23 10` |
| Footer | `AA 55` |

## Captured 2.4 GHz dongle protocol

| Field | Value |
| --- | --- |
| VID / PID | `0x0C45` / `0xFEFE` |
| Observed vendor usage page / usage | `0xFF60` / `0x61` |
| Captured report ID / payload length | `0` / 32 bytes |
| Static lighting command | Same first 32 bytes as the wired `AA 23 10` command |
| Custom lighting | 128 RGB table split into 22 reports: 21 × 6 entries, then a committing 2-entry report |

The wireless packet format is capture-verified from official-software static and
Q-to-red changes. Reproducing those reports through direct HIDAPI/SignalRGB writes
is still experimental; the exact receiver session/initialization behavior remains
unresolved.

## Captured static-colour baseline

```text
AA2310000000010001FF0000FF000000000404000000AA5500000000000000000000000000000000000000000000000000000000000000000000000000000000
```

The static-colour serializer copies this captured baseline and replaces only bytes
9–12: `R G B FF`.

| Bytes | Status |
| --- | --- |
| `0..2` | Verified `AA 23 10` |
| `3..8` | TODO: observed baseline values only; semantics unknown |
| `9..11` | Verified red, green, blue |
| `12` | Verified captured value `FF`; exact brightness/alpha semantics TODO |
| `13..21` | TODO: observed baseline values only; semantics unknown |
| `22..23` | Verified `AA 55` |
| `24..63` | Verified zero padding |

The device ACK is expected to echo the payload after replacing byte zero (`AA`) with
`55`. The library currently verifies the required `55 23 10` prefix and records the
whole packet in debug logs.

## Capture discipline

For every new feature, capture a known baseline and several controlled changes while
holding all other settings constant. Store the JSON/BIN output from `--capture`,
compare full packets, and document any inferred fields before serializing them.

## Session captures

The transport recorder observes packets at `send_packet()` and `receive_packet()`.
For a command run with `--record-dir`, it stores a single JSON session and companion
binary session file. Each packet has a sequence number, UTC timestamp, direction,
payload, and `paired_sequence`; this field links a validated ACK with the outbound
request that produced it. Malformed or unsolicited incoming packets are retained but
remain unpaired.
