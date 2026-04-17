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
| DFU mode characterization      | Complete             | DFU is radio-only; commands 0x06/0x07; Neon protocol; DFU PID = `1E7D:3A36` (F-026, F-037, F-039) |
| Swarm / DLL analysis           | Complete             | settings.xml decoded; 9 protocols; flash packet 520B; VID change deliberate (F-037–F-039, F-041) |
| Dongle recovery                | **RESOLVED**         | Button-hold on plug-in reliably recovers from any crash state (F-029)            |
| LED state mapping              | Partial              | 4 states catalogued; pink/magenta meaning unconfirmed (F-030)                    |
| USB DFU bootloader             | CLOSED               | No USB bootloader; DFU is 2.4 GHz radio-only (F-032)                            |
| Headset USB data path          | Complete             | USB-C charge-only; no data; headset FW updates via RF only (F-034)              |
| Red-blink mode characterisation| Complete             | HID output disabled (error 31); safe for USB experimentation (F-033)            |
| CDN firmware acquisition       | **CLOSED**           | Hardware CDN decommissioned; all endpoints 404 (F-040); community/JTAG remain   |
| RF pairing                     | **Blocked**          | All modes fail; HID gated on RF link; app-mode + button-press attempt pending (Q-012) |
| HID command format             | Blocked              | Gated on RF pairing (Q-012); report ID `0x06` = DFU trigger (F-026)             |
| Battery reporting              | Not started          | Blocked on app-mode command format (Q-003)                                 |
| Audio control event monitoring | Not started          | Q-006 — elevated priority                                                  |
| USB traffic capture (Swarm)    | CLOSED               | Swarm cannot see `26CE:0A0B`; Swarm II out of scope (F-017, F-023)         |
| Firmware version query         | Not started          | Q-007 — may be answerable via DFU memory readback                          |

## Current Blocker / Next Steps

**Dongle recovery is SOLVED (F-029):** Hold the physical button while plugging in USB.
LED changes to blinking red; device fully enumerates as `26CE:0A0B`. This works from any
observed failure state including the F-027 deep non-enumeration. Procedure is repeatable
and confirmed.

**Official software recovery paths are exhausted.** The complete failure chain (F-038, F-040):

```
Firmware update changes dongle VID: 1E7D:3A37 → 26CE:0A0B
  → Swarm stops detecting the dongle (looks for 0x1E7D only)
  → Recovery tool detects it but needs firmware files
  → Firmware files require Swarm module download
  → Swarm can't download: device not detected
  → Roccat decommissions the hardware CDN: all endpoints 404
  → No official path to obtain firmware or reflash the device
```

**Active blocker — RF pairing (Q-012):** No wireless link established in any tested mode.
HID Interface 6 is silent without an active RF connection. Next attempt: solid-white (app)
mode + headset pairing + short button press (pink/magenta, F-030).

**Remaining paths:**
1. **Community firmware cache** — someone with a pre-update dongle may have `data/3A37/firmware/` cached; worth posting on Roccat forums/Reddit
2. **JTAG/SWD hardware debug** — open the dongle, access PIC32 or nRF debug pins, read flash directly
3. **Pre-update replacement dongle** — a unit still presenting as `1E7D:3A37` would work with Swarm normally

## Documents

| File                  | Contents                                                                        |
|-----------------------|---------------------------------------------------------------------------------|
| `README.md`           | This file — overview, status, key findings summary                              |
| `findings.md`         | Chronological log of all discoveries (F-001 through F-041)                     |
| `usb_descriptor.md`   | Full USB descriptor tables, endpoint map, probe results                         |
| `protocol_notes.md`   | HID command format, reference Elo 7.1 Air protocol, command hypotheses          |
| `open_questions.md`   | Open questions (Q-008/Q-009/Q-010/Q-011 closed; Q-012 active)                  |

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

### Session 8 findings (dongle recovery resolved; pairing failure identified)
29. **Button-hold on plug-in is a reliable recovery method** (F-029, resolves Q-008) —
    holding the physical button while plugging in USB recovers the dongle from any crash
    state including F-027 deep non-enumeration. LED shifts to blinking red; `26CE:0A0B`
    fully enumerates with all interfaces. Repeatable. Users with field reliability issues
    (F-012) can likely recover using the same undocumented procedure.
30. **Dongle LED state map partially decoded** (F-030) — four states confirmed: solid white
    (app mode, no headset), blinking red (recovery/pairing-ready via button-hold), pink/
    magenta (short button press in red-blinking mode, meaning unconfirmed), off/dim (DFU
    mode entry after report ID `0x06` command).
31. **RF pairing fails in all tested modes; HID interface silent throughout** (F-031) —
    60 seconds of dongle blinking-red + headset white-blinking produced no pairing and zero
    HID traffic. HID Interface 6 appears gated on an active RF link — no connection means
    no HID activity regardless of dongle state. Pairing failure is the new primary blocker
    for app-mode protocol RE (Q-012).

### Session 9 findings (DFU is radio-only; red-blink characterised; headset USB charge-only)
32. **No USB DFU bootloader exists** (F-032) — `dfu_probe.py` sent command byte `0x01`
    via report ID `0x06`; dongle dropped at 0.5s; 30-second scan across HID, libusb, Device
    Manager, and `devcon` found zero new devices. DFU is a 2.4 GHz radio protocol only. The
    `firmware_upgrade.dll` "Enum bootloader mode device" strings refer to wireless
    re-enumeration, not USB. Q-011 closed.
33. **Red-blink mode characterised: HID output disabled, USB safe, radio active** (F-033) —
    writes return `ERROR_GEN_FAILURE` (error 31) — endpoint explicitly disabled, dongle does
    not crash from writes; `ReadFile` blocks indefinitely; no input reports. Safe state for
    USB experimentation. The mode activates 2.4 GHz radio while suspending HID protocol.
34. **Headset USB-C is charge-only; no data path** (F-034) — two cables tested, zero USB
    enumeration. Headset firmware updates must go over the RF link from the dongle; no
    independent USB update path exists.
35. **Red-blink USB enumeration is state-dependent** (F-035) — whether USB enumerates in
    red-blink mode depends on entry path; clean power cycle + button-hold is more reliable
    than button-hold after a DFU-induced drop. Practical guidance: unplug 5+ seconds, then
    button-hold on fresh plug-in.
36. **Headset has no hardware recovery mode** (F-036) — no button combination on the headset
    produces a recovery equivalent of the dongle's button-hold. Headset-side recovery is only
    possible via RF link from a working dongle.

### Session 10 findings (Swarm database decoded; VID change deliberate; CDN dead)
37. **settings.xml decoded: complete Roccat device database; Elo DFU PID = `1E7D:3A36`**
    (F-037) — zlib-decompressed (3,212→20,789 bytes); 143 products; Elo Air dongle app PID
    `0x3A37`, DFU/updating PID `0x3A36`; Elo Air headset app `0x3A39`, DFU `0x3A38`; all
    use VID `0x1E7D`. The `data/3A37/firmware/` DLL name field confirmed.
38. **VID `0x26CE` is Savitech (USB audio chip vendor); change was deliberate** (F-038) —
    appears exactly twice in `firmware_upgrade.dll`, INI-loaded at runtime (not hardcoded
    like the 61 `0x1E7D` occurrences). Roccat deliberately changed the dongle's VID to the
    chip vendor's VID in a firmware update, breaking Swarm's device detection.
39. **`firmware_upgrade.dll` fully analysed** (F-039) — 70 exports; 9 distinct update
    protocols (PIC32, Neon 0x06/0x07, Holtek ISP, Klassic, Kain 200, PURE OTA BT, Nordic
    nRF/nrfutil, Khan/CMedia, PXI/Pixart); flash packet = 520 bytes (8B header + 512B data);
    CRC-16 CCITT (poly `0x1021`) and reflected variant; 7 runtime DLLs identified.
40. **CDN hardware firmware endpoints decommissioned** (F-040) — `/swarm1/download/hardware/2/{id}`
    returns 404 for all IDs 1–500+; autoupdate API returns `{"hardware":null,"software":null}`
    universally; Swarm changelog shows Elo fixes through v1.9427, then dropped. No official
    firmware acquisition path remains.
41. **Swarm auto-update log decoded; Elo module ID never transmitted** (F-041) — Swarm logs
    at `AppData\Roaming\ROCCAT\SWARM\log\Auto_Update\`; only AlienFX (`2713`) appears in
    software keys; CDN resolves to Hetzner S3 (`nbg1.your-objectstorage.com/tbnb/...`);
    hardware download path is dead.

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
| 2026-04-17 | Session 8: Q-008 RESOLVED — button-hold recovery confirmed (F-029); LED state map documented (F-030); RF pairing failure documented (F-031); Q-012 added as new blocker; status table updated |
| 2026-04-17 | Session 9: No USB DFU bootloader (F-032, Q-011 closed); red-blink characterised as safe/radio-only (F-033, F-035); headset USB charge-only (F-034); headset no recovery mode (F-036); Q-012 updated; end-of-day summary written |
| 2026-04-18 | Session 10: settings.xml decoded — DFU PID 1E7D:3A36 confirmed (F-037); VID 0x26CE = Savitech, change deliberate (F-038); firmware_upgrade.dll fully analysed — 9 protocols, 520B flash packet (F-039); CDN decommissioned — all hardware endpoints 404 (F-040); Swarm log decoded (F-041); Q-010 CDN path closed; consequence chain documented |
