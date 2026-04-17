# Roccat Elo Wireless Headset — Reverse Engineering Investigation

## Goal

Develop open-source driver support for the Roccat Elo wireless gaming headset, targeting
integration with [HeadsetControl](https://github.com/Sapd/HeadsetControl) and/or the
[eruption](https://github.com/X3n0m0rph59/eruption) project.

The original Roccat Elo 7.1 Air is partially supported under VID `0x1E7D` / PID `0x3A37`.
This hardware uses **VID `0x26CE`** (Realtek/ASRock), indicating a newer revision or OEM
re-spin that requires independent protocol documentation.

## Target Hardware

| Field              | Value                                                    |
|--------------------|----------------------------------------------------------|
| Product            | Roccat Elo wireless gaming headset (exact model TBD)    |
| Dongle VID:PID     | `26CE:0A0B` — **CONFIRMED** (unplug test 2026-04-17)   |
| BT adapter VID:PID | `0E8D:0717` (MediaTek RZ717 — separate, unrelated)      |
| `26CE:01A2`        | NOT the headset — separate motherboard peripheral (out of scope) |
| OS / tooling       | Windows 11, MSYS2, pyusb + libusb, Windows HID API      |
| Roccat SW on system| None (no Swarm / NEON installed)                        |
| Expected VID       | `0x1E7D` (ROCCAT GmbH) — **not found; this is a new hardware variant** |

## Investigation Status

| Area                           | Status               | Notes                                                             |
|--------------------------------|----------------------|-------------------------------------------------------------------|
| USB enumeration                | Complete             | 7 devices found; no `0x1E7D`                                      |
| Full USB descriptor dump       | Complete             | pyusb + libusb; all 7 interfaces mapped                           |
| Windows HID capability parse   | Complete             | Report ID `0x06`, value caps, endpoint sizes confirmed            |
| Dongle identity confirmation   | Complete             | Confirmed `26CE:0A0B` via unplug test (F-010)                    |
| Scope determination            | Complete             | `26CE:01A2` is out of scope; protocol RE from scratch (F-011)    |
| Known defect characterization  | Complete             | Population-level reliability defect documented (F-012)            |
| Dongle recovery                | **CRITICAL BLOCKED** | Dongle crashed after write storm; CM_PROB_PHANTOM (Q-008, F-013) |
| HID command format             | Blocked              | Blocked on dongle recovery (Q-008); also needs paired headset (F-016) |
| Battery reporting              | Not started          | Blocked on Q-008, Q-003                                           |
| Audio control event monitoring | Not started          | Q-006 — elevated priority                                        |
| USB traffic capture (Swarm)    | Not started          | Q-009 — high priority once dongle recovered; F-014 documents path |
| Firmware version query         | Not started          | Q-007 — blocked on Q-008                                         |

## Current Blocker

**Q-008** — Dongle crashed after write storm and will not re-enumerate. All active RE work is
halted until the dongle is recovered. Recovery steps (in priority order):

1. Extended power-off (30+ seconds unplugged) to force capacitor discharge and full firmware reset
2. Roccat Swarm `ROCCAT_RECOVER_TOOL.exe` — connect headset first, then dongle; tool reflashes firmware
3. If recovery fails: replace dongle

Once the dongle is recovered, the recommended next step is **Q-009** (install Swarm, capture
USB traffic) rather than continued blind probing.

## Documents

| File                  | Contents                                                                        |
|-----------------------|---------------------------------------------------------------------------------|
| `README.md`           | This file — overview, status, key findings summary                              |
| `findings.md`         | Chronological log of all discoveries (F-001 through F-016)                     |
| `usb_descriptor.md`   | Full USB descriptor tables, endpoint map, probe results                         |
| `protocol_notes.md`   | HID command format, reference Elo 7.1 Air protocol, command hypotheses          |
| `open_questions.md`   | Open questions (Q-001 resolved, Q-005 OOS, Q-008 CRITICAL, Q-009 HIGH)         |

## Key Findings Summary

### Session 1 findings
1. No VID `0x1E7D` — this is a hardware generation not covered by any open-source tool.
2. `26CE:0A0B` is a 7-interface UAC2 composite device with vendor HID on Interface 6.
3. HID Report ID is `0x06`; output report is only **2 bytes** — reference 64-byte command
   path does not directly apply.
4. Device is passive by default; crashes under tight write timing (no 75 ms delay).
5. Reference battery protocol documented from eruption: push-based, quartile granularity.

### Session 2 findings (critical updates)
6. **`26CE:0A0B` CONFIRMED as Roccat Elo dongle** via unplug test (F-010).
7. **`26CE:01A2` is NOT the headset** — it remained after dongle unplug; it is a separate
   motherboard peripheral. All LED controller probe data is out of scope.
8. **Protocol must be RE'd from scratch** (F-011) — no existing tool supports `26CE:0A0B`;
   reference `0x1E7D` protocol is not assumed to apply.
9. Primary RE target confirmed: Interface 6, EP `0x8A`, Report ID `0x06`, 63-byte input
   payload, 1-byte output payload.

### Session 3 findings (crash and recovery)
10. **Population-level dongle reliability defect confirmed** (F-012) — multiple independent
    user reports spanning 2021–2025 document the same crash/non-enumeration pattern we observed;
    thermal issues and pairing failures are widespread.
11. **Dongle crashed after write storm and won't re-enumerate** (F-013) — `CM_PROB_PHANTOM`
    status; device electrically present but not responding to USB enumeration. Likely requires
    extended power-off or firmware recovery via Roccat Swarm.
12. **Roccat Swarm contains a recovery tool and accessible firmware files** (F-014) —
    `ROCCAT_RECOVER_TOOL.exe` can reflash non-enumerating dongles; firmware binaries at
    `data/3A37/firmware/`; installing Swarm + USBPcap is the highest-ROI next step for
    protocol capture.
13. **HID interface was likely inactive because headset was not paired** (F-016) — prior probe
    silence and errors are explained by absence of an active headset connection, not by an
    inherently broken interface. All future command testing must confirm headset pairing first.
14. **Headset beeping was likely a connection failure, not low battery** (F-015/revised F-008)
    — headset is new/unused; charging confirmed at 5V ~400–440 mA; beeping matches connection
    error signaling pattern.

## Related Prior Art

| Project        | File / Path                         | VID covered |
|----------------|-------------------------------------|-------------|
| HeadsetControl | `src/devices/roccat_elo_71_air.c`   | `0x1E7D`    |
| eruption       | Roccat Elo device profiles           | `0x1E7D`    |
| HeadsetControl | GitHub issues — search `26CE`        | Unknown     |

## Revision History

| Date       | Change                                                                                              |
|------------|-----------------------------------------------------------------------------------------------------|
| 2026-04-17 | Initial document creation; full session 1 findings captured                                         |
| 2026-04-17 | Session 2: Q-001 resolved; `26CE:01A2` out of scope; protocol RE scope established                 |
| 2026-04-17 | Session 3: Dongle crash documented (F-013); reliability defect background (F-012); Swarm recovery path (F-014); HID inactive-without-headset hypothesis (F-016); Q-008 and Q-009 added; status table updated to reflect blocked state |
