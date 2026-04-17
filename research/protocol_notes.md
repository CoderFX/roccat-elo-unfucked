# Protocol Notes — Roccat Elo Wireless Headset

## Overview

HID communication for the headset uses a **64-byte report** format on **Report ID `0x06`**, sent
to Interface 6 of device `26CE:0A0B`. The report layout as decoded from `HidP_GetValueCaps`:

```
Byte 0:      Report ID = 0x06
Bytes 1–63:  Payload (63 bytes, UsagePage=0xFFC1, Usage=0x00F0, each byte BitSize=8)
```

Output reports are only **2 bytes** total (1 byte report ID + 1 byte payload), not 64. This is a
crucial difference from the reference Elo 7.1 Air protocol where full 64-byte writes are used for
commands. The asymmetry (64 B in, 2 B out) suggests that commands may be sent via a different
mechanism (e.g., the Audio Control interface) while the HID interface is read-only for status.

**Inter-command delay:** 75 ms required (from original Elo 7.1 Air; assumed to apply here).

---

## Reference Protocol: Original Roccat Elo 7.1 Air

**Applies to:** VID `0x1E7D` / PID `0x3A37`, `0x3A39`
**Sources:** HeadsetControl (`roccat_elo_71_air.c`), eruption project Rust implementation

These commands are documented as a baseline for comparison with the `26CE:0A0B` device. They are
**not confirmed** to work on the device under investigation.

### Battery Query (Push-Based)

Battery level reporting is **not polled**. The headset pushes the value after a trigger command.

**Step 1 — Trigger (host → headset, 64 bytes):**
```
[0xFF, 0x01, 0x00, 0x00, 0x00, ...]  (bytes 2–63 = 0x00)
```

**Step 2 — Headset response (async HID input report):**
```
[0xE6, 0x06, 0x03, 0x00, LEVEL, 0x00, ...]
```

| `LEVEL` (byte 4) | Battery percentage |
|-----------------|-------------------|
| `0x04`          | 100%              |
| `0x03`          | 75%               |
| `0x02`          | 50%               |
| `0x01`          | 25%               |
| `0x00`          | 0%                |

Granularity is **quartile only** (steps of 25%). This matches user-reported complaints about
Roccat Swarm showing coarse battery readings.

**Confidence on `26CE:0A0B`:** speculative — trigger byte may differ

#### Inactive Timeout

```
[0xA1, 0x04, 0x06, 0x54, HI, LO, 0x00, ...]  (64 bytes total)
```

`HI:LO` = big-endian 16-bit timeout in minutes.

Examples:
- 20 minutes: `HI=0x00, LO=0x14`
- 60 minutes: `HI=0x00, LO=0x3C`
- Disabled (0): `HI=0x00, LO=0x00`

**Confidence on `26CE:0A0B`:** speculative

#### LED Control

A 4-command sequence, each 64 bytes, starting with `0xFF`. Full LED sequence details from
eruption source:

```
Command 1: [0xFF, ...]
Command 2: [...]
Command 3: [...]
Command 4: [...]
```

75 ms delay required **between each command**.

**Confidence on `26CE:0A0B`:** speculative — LED may be handled by `26CE:01A2` instead

---

## LED Controller Protocol — `26CE:01A2`

### Response Pattern Analysis

From a full 256-command single-byte scan. Responsive ranges only:

**Range 0x00–0x10: Generic acknowledgement**
```
CMD 0x00: [00 00 00 07 02 00 00 00 ...]   ← unique response, byte[4]=0x02
CMD 0x01–0x10: [00 00 00 07 00 00 00 00 ...]   ← generic ACK, byte[3]=0x07
```

**Range 0xA0–0xAA: Configuration readback (echoes command + returns value)**
```
CMD 0xA0: [a0 00 00 00 04 00 00 00 ...]
CMD 0xA1: [a1 00 00 00 06 00 00 00 ...]
CMD 0xA2: [a2 00 00 00 08 00 00 00 ...]
CMD 0xA3: [a3 00 00 00 0a 00 00 00 ...]
CMD 0xA4: [a4 00 00 00 01 00 00 00 ...]
CMD 0xA5: [a5 00 00 00 03 00 00 00 ...]
CMD 0xA6: [a6 00 00 00 05 00 00 00 ...]
CMD 0xA7: [a7 00 00 00 07 00 00 00 ...]
CMD 0xA8: [a8 00 00 00 09 00 00 00 ...]
CMD 0xA9: [a9 00 00 00 0b 00 00 00 ...]
CMD 0xAA: [aa 00 00 00 0d 00 00 00 ...]
```

Response structure: `[CMD, 0x00, 0x00, 0x00, VALUE, 0x00, ...]`

**VALUE sequence** across `0xA0`–`0xAA`: `04 06 08 0A 01 03 05 07 09 0B 0D`

- `0xA0`–`0xA3`: values `04, 06, 08, 0A` — even, incrementing by 2
- `0xA4`–`0xA6`: values `01, 03, 05` — odd, incrementing by 2 (counter resets)
- `0xA7`–`0xAA`: values `07, 09, 0B, 0D` — odd, continuing increment

The even/odd split at `0xA4` suggests two separate register banks being interleaved in address
space. The value at byte[4] may represent a hardware register index, a PWM duty cycle step, or
an LED effect parameter index.

**Confidence:** speculative — visual LED correlation test needed

### Hypothesized Command Structure

Based on the echo pattern, these are likely **read** commands. Corresponding write commands
probably have a different opcode (e.g., `0xA0 | 0x80` = `0x20`, or a separate range).

The `0x00` command response (`byte[4]=0x02`) may be a device identity or mode byte.

---

## HID Output Report Ambiguity

The output report for `26CE:0A0B` Interface 6 is only **2 bytes** (1 byte report ID + 1 byte
payload). This does not match the 64-byte command format of the reference protocol. Possible
interpretations:

1. **Commands go via Audio Control interface** (`0x89` endpoint), not the HID interface. The
   HID interface is status-only (push from headset → host).
2. **Feature report mechanism**, but feature reports were confirmed as size 0 (not present).
3. **The 2-byte output report is a "wake/trigger" byte** that initiates a headset response
   on the HID IN endpoint.
4. **Direct USB control transfers** (not HID write) are used for longer commands — bypassing
   the Windows HID layer (which enforces report-size matching).

Option 4 is the most likely path for a USB capture approach — use pyusb/libusb to send
`usb.core.Device.ctrl_transfer()` with `bmRequestType=0x21` (HID Set_Report) directly,
bypassing the Windows HID driver.

---

## VID Ownership Context

| VID    | Registered Owner | Notes                                              |
|--------|------------------|----------------------------------------------------|
| `0x1E7D` | ROCCAT GmbH    | All original Roccat peripherals                    |
| `0x26CE` | ASRock Inc.    | Shared with Realtek-based audio chips; multiple OEMs use this VID |
| `0x0E8D` | MediaTek       | BT/WiFi chipsets                                   |

The absence of VID `0x1E7D` and presence of `0x26CE` (with Realtek audio driver `RtkUsbAD_2395`)
strongly suggests this is a post-acquisition hardware revision. Turtle Beach acquired Roccat in
2019; newer Roccat peripherals sometimes appear with different silicon choices.

---

## Revision History

| Date       | Change                                                                      |
|------------|-----------------------------------------------------------------------------|
| 2026-04-17 | Initial protocol notes; reference Elo 7.1 Air protocol documented           |
| 2026-04-17 | Added full LED probe response table with pattern analysis                   |
| 2026-04-17 | Added output report ambiguity analysis; updated HID value caps detail       |
