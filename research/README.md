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
| Roccat SW on system| Swarm v1.9481 installed — does **not** detect `26CE:0A0B` (F-017) |
| Expected VID       | `0x1E7D` (ROCCAT GmbH) — **not found; this is a new hardware variant** |

## Investigation Status

| Area                           | Status               | Notes                                                             |
|--------------------------------|----------------------|-------------------------------------------------------------------|
| USB enumeration                | Complete             | 7 devices found; no `0x1E7D`                                      |
| Full USB descriptor dump       | Complete             | pyusb + libusb; all 7 interfaces mapped                           |
| Windows HID capability parse   | Complete             | Report ID `0x06`, value caps, endpoint sizes confirmed            |
| Dongle identity confirmation   | Complete             | Confirmed `26CE:0A0B` via unplug test (F-010)                    |
| Scope determination            | Complete             | `26CE:01A2` is out of scope; protocol RE from scratch (F-011)    |
| Known defect characterization  | Complete             | Population-level reliability defect documented (F-012)                    |
| DFU mode characterization      | **Complete**         | "Crashes" are DFU mode entries; report ID 0x06 = DFU trigger (F-026)     |
| Swarm analysis                 | Complete             | Swarm cannot detect `26CE:0A0B`; DLL strings reveal full DFU flow (F-017–F-019, F-026) |
| Dongle recovery                | **CRITICAL BLOCKED** | USB stack not initializing (F-027); hardware button test in progress (F-028, Q-008) |
| Hardware button recovery       | **In progress**      | Physical button held on plug-in — testing ROM bootloader entry (F-028)            |
| Bootloader device identification | Pending            | Blocked until dongle re-enumerates in any mode (Q-011)                            |
| Firmware binary acquisition    | In progress          | CDN URL confirmed (F-024); Elo module ID needed (Q-010)                           |
| HID command format             | Blocked              | Blocked on dongle recovery; report ID `0x06` = DFU trigger (F-026)               |
| Battery reporting              | Not started          | Blocked on app-mode command format (Q-003)                                 |
| Audio control event monitoring | Not started          | Q-006 — elevated priority                                                  |
| USB traffic capture (Swarm)    | CLOSED               | Swarm cannot see `26CE:0A0B`; Swarm II out of scope (F-017, F-023)         |
| Firmware version query         | Not started          | Q-007 — may be answerable via DFU memory readback                          |

## Current Blocker / Next Steps

**Current state (F-027):** The dongle has entered a deeper failure mode than prior DFU
timeouts. LED lights on plug-in (MCU running) but no USB enumeration occurs at all — not
app mode, not DFU bootloader. The application firmware is corrupted to the point where USB
initialization is never reached.

**Active recovery attempt — hardware button (F-028):**
Hold the physical button on the dongle body while plugging in. If the button is wired to a
hardware boot-mode-select pin (analogous to BOOT0 on STM32), it bypasses corrupted
application firmware and enters a factory ROM bootloader. Watch for any new USB VID:PID
appearing on the bus — including previously unseen ones.

**If button recovery works:** Identify and enumerate the ROM bootloader device; flash
known-good firmware via whatever protocol it exposes (DFU, UART, ICSP).

**If button recovery fails:** Acquire a replacement dongle. Capture a USBPcap baseline
with the headset paired and connected before issuing any probe commands on the replacement.

## Documents

| File                  | Contents                                                                        |
|-----------------------|---------------------------------------------------------------------------------|
| `README.md`           | This file — overview, status, key findings summary                              |
| `findings.md`         | Chronological log of all discoveries (F-001 through F-028)                     |
| `usb_descriptor.md`   | Full USB descriptor tables, endpoint map, probe results                         |
| `protocol_notes.md`   | HID command format, reference Elo 7.1 Air protocol, command hypotheses          |
| `open_questions.md`   | Open questions (Q-008 CRITICAL, Q-009 CLOSED, Q-010/Q-011 HIGH)               |

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
    `data/3A37/firmware/`; installing Swarm + USBPcap was identified as the highest-ROI next step.
13. **HID interface was likely inactive because headset was not paired** (F-016) — prior probe
    silence and errors are explained by absence of an active headset connection, not by an
    inherently broken interface. All future command testing must confirm headset pairing first.
14. **Headset beeping was likely a connection failure, not low battery** (F-015/revised F-008)
    — headset is new/unused; charging confirmed at 5V ~400–440 mA; beeping matches connection
    error signaling pattern.

### Session 4 findings (Swarm analysis; dongle response confirmed)
15. **Swarm cannot detect its own updated dongle** (F-017) — Swarm v1.9481 scans for
    `1E7D:3A37` only; the firmware update renamed the dongle to `26CE:0A0B`, orphaning it
    from its own vendor toolchain. USBPcap capture via Swarm is impossible.
16. **Recovery tool detects the device but is blocked by a circular dependency** (F-018) —
    `ROCCAT_RECOVER_TOOL.exe` shows "firmware update required" but the dropdown is inert
    because `firmware/` and `firmware_upgrade.ini` are never created (Swarm can't download
    them without detecting the device).
17. **Swarm installer extracted; PIC32 flash protocol and HIDDLL identified** (F-019) —
    `firmware_upgrade.dll` implements PIC32 erase/write/verify; `HIDDLL.dll` is the HID
    communication layer; device modules including firmware binaries are CDN-downloaded, not
    bundled; dongle likely uses PIC32 as application MCU.
18. **Headset entered pairing mode; dongle did not respond; 60s HID silence** (F-020) —
    headset white LED blinked (pairing mode confirmed); dongle LED stayed solid; no HID
    traffic observed.
19. **CRITICAL: Dongle IS alive and responding — hidapi cannot parse its responses** (F-021)
    — every command from `0x01`–`0xFF` produced a hidapi "read error," meaning the dongle
    sent bytes back but hidapi failed to interpret them. Raw `ReadFile()` or libusb read on
    EP `0x8A` needed to see the actual response data.
20. **Dongle crash threshold confirmed: ~8 commands triggers crash** (F-022) — second crash
    event with 500 ms inter-command delays; trigger is unrecognized command count, not rate;
    all future probe sessions must stay well under 8 commands per power cycle.

### Session 5 findings (crash model refined; CDN URL confirmed)
21. **Swarm II carries no Roccat device modules** (F-023) — Turtle Beach Swarm II v1.0.0.38
    extracted; contains only Qt runtime and Swarm II metadata; no Roccat firmware; dead end
    for firmware acquisition.
22. **CDN URL pattern confirmed** (F-024) — module downloads use
    `https://acpv.prod.turtlebeach.com/swarm1/form/<module_id>` where the module ID is an
    integer from `version.ini`, not the PID; Elo module ID enumeration or community sourcing
    needed to complete firmware acquisition.
23. **Single WriteFile triggers DFU mode entry** (F-025) — `WriteFile` succeeded (2 bytes
    written, no error); dongle dropped off USB immediately. Now understood (F-026) to be a
    successful DFU mode-entry command, not a crash.

### Session 6 findings (CRITICAL REFRAME — DFU mode, not crashes)
24. **Every prior "crash" was DFU mode entry** (F-026) — deep string analysis of
    `firmware_upgrade.dll` confirms: report ID `0x06` output report = DFU mode-entry command
    (`"Try to start DFU mode failed, 0x06 command failed"`); command `0x07` = check DFU
    status / reboot FW. The dongle was obeying every command correctly. It re-enumerates as
    a different VID:PID in bootloader mode — we never scanned for it. The "30s–5min recovery"
    is the DFU bootloader timeout before it reboots to app mode.
25. **Dongle hardware architecture confirmed from DLL strings** (F-026) — `"Elo Air"` and
    `"3A37"` strings present; `Dongle_DFU.dll` handles dongle flashing; nRF DFU handles
    headset RF firmware via USB cable; PIC32/Holtek/CMedia/ATTiny/nRF updaters all present
    for different Roccat peripheral chips.
26. **User-reported field reliability failures (F-012) are reframed** (F-026) — the
    population-level dongle failures in the field are now a credible consequence of DFU mode
    being triggered by software bugs, driver quirks, or malformed HID traffic from third-party
    tools; the dongle enters bootloader mode and the DFU timeout leaves it in an intermediate
    state until power-cycled.

### Session 7 findings (hardware recovery; new failure mode)
27. **Dongle USB stack not initializing — new, deeper failure mode** (F-027) — after cap
    drain and port changes: LED lights (MCU running) but zero USB enumeration, no partial
    or error devices, nothing in PnP/HID/libusb. Distinct from prior DFU timeout states
    which still produced USB enumeration. Application firmware corrupted past USB init.
28. **Physical reset button found on dongle body** (F-028) — pinhole or tactile button;
    may trigger hardware ROM-level boot mode select (analogous to BOOT0 on STM32), bypassing
    corrupted application firmware entirely. Test in progress: hold button while plugging in,
    scan for any new USB VID:PID. If successful: direct path to firmware reflash without
    needing Swarm, CDN firmware, or app-level DFU protocol.

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
| 2026-04-17 | Session 4: Swarm installed — cannot detect 26CE:0A0B (F-017); recovery tool circular dependency (F-018); Swarm extraction/PIC32 finding (F-019); pairing test (F-020); dongle response confirmed via hidapi error (F-021); crash threshold ~8 commands (F-022); Q-009 closed; Q-010/Q-011 added |
| 2026-04-17 | Session 5: Swarm II dead end (F-023); CDN URL pattern confirmed (F-024); crash model revised — single WriteFile crashes firmware (F-025); dongle self-recovers reliably; OVERLAPPED I/O defined as next probe approach; Q-010/Q-011 updated accordingly |
| 2026-04-17 | Session 6: CRITICAL REFRAME — all prior "crashes" are DFU mode entries (F-026); report ID 0x06 = DFU trigger confirmed from firmware_upgrade.dll strings; Elo Air / 3A37 strings confirmed; bootloader device VID:PID scan is now immediate next step; Q-011 reframed; status table updated |
| 2026-04-17 | Session 7: New failure mode (F-027) — USB stack not initializing, only LED active; physical reset button found (F-028) — hardware ROM bootloader entry test in progress; Q-008 updated with revised recovery steps |
