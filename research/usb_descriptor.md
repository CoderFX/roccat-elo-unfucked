# USB Descriptor Analysis — Roccat Elo Wireless Headset

## System Context

- **OS:** Windows 11 (MSYS2 environment)
- **Roccat software:** None installed (no Roccat Swarm / NEON on this system)
- **USB enumeration tools:** Windows HID API (HidP_GetCaps, HidP_GetValueCaps), pyusb + libusb
  (`C:\msys64\mingw64\bin\libusb-1.0.dll`)

---

## Full USB Device Inventory

All USB devices found on the system at time of investigation:

| VID:PID     | Description                                | Notes                                   |
|-------------|--------------------------------------------|-----------------------------------------|
| `26CE:0A0B` | "Realtek USB Audio" / "USB Audio"          | Composite device — dongle or onboard?   |
| `26CE:01A2` | "LED Controller"                           | HID device                              |
| `0E8D:0717` | MediaTek RZ717 Bluetooth Adapter           | Separate BT dongle                      |
| `046D:082D` | Logitech                                   | Webcam                                  |
| `04D9:A09E` | (keyboard)                                 | HID keyboard                            |
| `0D8C:013C` | C-Media audio                              | Onboard or USB audio                    |
| `1532:0203` | Razer                                      | Gaming peripheral                       |

VID `0x1E7D` (ROCCAT GmbH, expected for Elo 7.1 Air) **was not found on this system**.

---

## Device 1: `26CE:0A0B` — "Realtek USB Audio" Composite

**Confidence of headset identity:** likely — pending unplug/replug confirmation (see [open_questions.md Q-001](open_questions.md))

### Device Descriptor

| Field              | Value                                      |
|--------------------|--------------------------------------------|
| VID:PID            | `26CE:0A0B`                                |
| Product string     | "USB Audio"                                |
| Manufacturer string| "Generic"                                  |
| USB version        | USB 2.0                                    |
| bDeviceClass       | `0xEF` (Miscellaneous)                     |
| bDeviceSubClass    | `0x02`                                     |
| bDeviceProtocol    | `0x01` (IAD — Interface Association Descriptor) |
| bcdDevice          | `0x0002` (Device revision 0.02)            |
| Power              | Bus Powered, 100 mA max                    |

### Windows Driver Bindings

| Interface  | Driver              | Notes                                         |
|------------|---------------------|-----------------------------------------------|
| MI_00      | `RtkUsbAD_2395`     | **Custom Realtek audio driver** — not generic Windows USB Audio |
| MI_06      | `HidUsb`            | Standard Windows HID driver                   |

The custom Realtek driver (`RtkUsbAD_2395`) is significant — it means the audio path uses a
Realtek-specific driver stack, not the generic Windows USB Audio class driver. This is consistent
with a headset dongle using Realtek USB audio silicon.

### Interface Layout (from pyusb full descriptor dump)

All audio interfaces use **USB Audio Class 2.0** (`bInterfaceProtocol = 0x20`).

| Intf | Class        | SubClass | Protocol | Alt Settings | Endpoint(s)                        | Purpose                  |
|------|--------------|----------|----------|--------------|------------------------------------|--------------------------|
| 0    | Audio (0x01) | 0x01     | 0x20     | 1            | EP `0x89` IN Interrupt 16B         | Audio Control + UAC2 status notifications |
| 1    | Audio (0x01) | 0x02     | 0x20     | 8            | EP `0x83` IN Isochronous 124–186B  | Microphone capture       |
| 2    | Audio (0x01) | 0x02     | 0x20     | 8            | EP `0x84` IN Isochronous           | Second capture channel   |
| 3    | Audio (0x01) | 0x02     | 0x20     | 9            | EP `0x05` OUT Isochronous 124–744B | Speaker playback         |
| 4    | Audio (0x01) | 0x02     | 0x20     | 18           | EP `0x06` OUT Isochronous 124–558B | Second playback channel  |
| 5    | Audio (0x01) | 0x02     | 0x20     | 9            | EP `0x08` OUT Isochronous          | Third playback channel   |
| 6    | HID (0x03)   | 0x00     | 0x00     | 1            | EP `0x8A` IN Interrupt 16B int=4   | Vendor HID control       |

### Interface 6 — Vendor HID (Full Detail)

#### HID Capabilities (`HidP_GetCaps`)

| Field             | Value                  |
|-------------------|------------------------|
| Usage             | `0x0001`               |
| UsagePage         | `0xFFC0` (vendor-defined) |
| Input Report size | 64 bytes               |
| Output Report size| 2 bytes                |
| Feature Report    | 0 bytes (none)         |
| Input Value Caps  | 1                      |
| Output Value Caps | 1                      |

#### HID Value Caps (`HidP_GetValueCaps`)

| Direction | ReportID | UsagePage | Usage   | BitSize | Count | LogMin | LogMax |
|-----------|----------|-----------|---------|---------|-------|--------|--------|
| Input     | `0x06`   | `0xFFC1`  | `0x00F0`| 8       | 63    | 0      | 255    |
| Output    | `0x06`   | `0xFFC1`  | `0x00F1`| 8       | 1     | 0      | 255    |

**Critical:** Report ID is `0x06`, **not** `0x00` or `0xFF`. All initial probes that used
report ID `0x00` were using the wrong ID. The 63-byte input payload (+ 1 byte report ID = 64 bytes
total) matches the 64-byte packet format of the original Elo 7.1 Air.

#### Probe Results on Interface 6

| Probe                                  | Result                                                |
|----------------------------------------|-------------------------------------------------------|
| Passive listen, 30 seconds             | Zero input reports received                           |
| Write with report ID `0x00`            | Silently accepted; no response                        |
| Write with report ID `0x06`, byte 0x00–0xFF | Every command caused "read error" on next read   |
| `HidD_GetInputReport` (ID `0x06`)      | Error 87 (`INVALID_PARAMETER`)                        |
| `HidD_SetOutputReport` (ID `0x06`)     | Error 87 (`INVALID_PARAMETER`)                        |
| Aggressive write storm                 | Device dropped off USB enumeration; required re-plug  |

The `INVALID_PARAMETER` errors from the Windows HID API suggest the 2-byte output report format
does not match a simple write of a full 64-byte buffer. The output report is only 1 byte of payload
(1 byte report ID + 1 byte data = 2 bytes total).

#### Interrupt Endpoints Summary

| Endpoint | Direction | Type      | Size  | Interval | Interface | Purpose                    |
|----------|-----------|-----------|-------|----------|-----------|----------------------------|
| `0x89`   | IN        | Interrupt | 16 B  | —        | 0 (Audio Control) | UAC2 status notifications |
| `0x8A`   | IN        | Interrupt | 16 B  | 4 ms     | 6 (HID)   | HID input reports          |
| `0x83`   | IN        | Isochronous| 124–186B | —   | 1         | Mic audio                  |
| `0x84`   | IN        | Isochronous| —    | —        | 2         | Second capture             |
| `0x05`   | OUT       | Isochronous| 124–744B | —   | 3         | Speaker audio              |
| `0x06`   | OUT       | Isochronous| 124–558B | —   | 4         | Second playback            |
| `0x08`   | OUT       | Isochronous| —    | —        | 5         | Third playback             |

---

## Device 2: `26CE:01A2` — LED Controller

**Confidence of headset identity:** likely (shares VID with `26CE:0A0B`); function confirmed via probe

### Descriptor Summary

| Field       | Value                              |
|-------------|------------------------------------|
| VID:PID     | `26CE:01A2`                        |
| Product     | "LED Controller"                   |
| Class       | HID (0x03)                         |
| Interface 0 | Usage Page: `0x0001`, Usage: `0x0000` |

### Full Probe Response Table (256-command scan)

All responses are 8+ bytes; full packet is zero-padded beyond last non-zero byte shown.

| CMD (hex) | Response bytes [0..7]               | Notes                              |
|-----------|-------------------------------------|------------------------------------|
| `0x00`    | `00 00 00 07 02 00 00 00`            | Unique: byte[4]=0x02               |
| `0x01`–`0x10` | `00 00 00 07 00 00 00 00`       | Generic ACK pattern                |
| `0x11`–`0x9F` | `00 00 00 00 00 00 00 00`       | Null (no response)                 |
| `0xA0`    | `a0 00 00 00 04 00 00 00`           | Echoes CMD at byte[0]              |
| `0xA1`    | `a1 00 00 00 06 00 00 00`           | Echoes CMD at byte[0]              |
| `0xA2`    | `a2 00 00 00 08 00 00 00`           | Echoes CMD at byte[0]              |
| `0xA3`    | `a3 00 00 00 0a 00 00 00`           | Echoes CMD at byte[0]              |
| `0xA4`    | `a4 00 00 00 01 00 00 00`           | Echoes CMD at byte[0]              |
| `0xA5`    | `a5 00 00 00 03 00 00 00`           | Echoes CMD at byte[0]              |
| `0xA6`    | `a6 00 00 00 05 00 00 00`           | Echoes CMD at byte[0]              |
| `0xA7`    | `a7 00 00 00 07 00 00 00`           | Echoes CMD at byte[0]              |
| `0xA8`    | `a8 00 00 00 09 00 00 00`           | Echoes CMD at byte[0]              |
| `0xA9`    | `a9 00 00 00 0b 00 00 00`           | Echoes CMD at byte[0]              |
| `0xAA`    | `aa 00 00 00 0d 00 00 00`           | Echoes CMD at byte[0]              |
| `0xAB`–`0xFF` | `00 00 00 00 00 00 00 00`       | Null (no response)                 |

No feature reports found on this device.

#### Pattern Analysis (speculative)

The `0xA0`–`0xAA` range (11 commands) echoes the command byte at position [0] and returns an
incrementing even value at byte [4] for `0xA0`–`0xA3`/`0xA7`–`0xA9` and odd values for
`0xA4`–`0xA6`/`0xAA`. The alternating odd/even pattern suggests these are readbacks from a
configuration register bank (e.g., LED profile slots, brightness presets, or effect parameters).

Byte [4] sequence across `0xA0`–`0xAA`: `04 06 08 0A 01 03 05 07 09 0B 0D`

This is not a simple sequential counter. The pattern splits at `0xA4` where even→odd, then
continues odd, suggesting two interleaved register sets. More probing with multi-byte payloads
needed.

---

## Device 3: `0E8D:0717` — MediaTek RZ717 Bluetooth Adapter

This is a standard standalone Bluetooth adapter; not involved in the headset HID protocol.

| Field   | Value                             |
|---------|-----------------------------------|
| VID:PID | `0E8D:0717`                       |
| Chip    | MediaTek RZ717                    |
| Class   | Bluetooth (0xE0)                  |

---

## Revision History

| Date       | Change                                                                  |
|------------|-------------------------------------------------------------------------|
| 2026-04-17 | Initial descriptor capture from session 1; full pyusb dump incorporated |
| 2026-04-17 | Added full LED controller probe response table; updated HID value caps  |
