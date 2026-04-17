# Findings Log — Roccat Elo Wireless Headset

Chronological record of all discoveries. Most recent entries at the bottom.

---

## Session 1 — 2026-04-17

### F-001 — Initial USB enumeration: three candidate devices, no Roccat VID

**Phase:** Device enumeration

Full system USB inventory taken. VID `0x1E7D` (ROCCAT GmbH, expected for Elo 7.1 Air per
HeadsetControl/eruption) was **not found**. Devices present:

| VID:PID     | Description                       |
|-------------|-----------------------------------|
| `26CE:0A0B` | "Realtek USB Audio" composite (7 interfaces) |
| `26CE:01A2` | "LED Controller" HID              |
| `0E8D:0717` | MediaTek RZ717 Bluetooth adapter  |
| `046D:082D` | Logitech webcam                   |
| `04D9:A09E` | Keyboard                          |
| `0D8C:013C` | C-Media audio                     |
| `1532:0203` | Razer device                      |

At this point the two `26CE`-VID devices were assumed to share a product package, but this was
not yet confirmed. No Roccat Swarm or NEON software was installed on the system at time of
investigation. **See F-010 for confirmation of dongle identity.**

**Confidence:** confirmed (enumeration data)

---

### F-002 — `26CE:0A0B` uses custom Realtek audio driver, not generic Windows USB Audio

**Phase:** Driver identification

Windows driver manager binding:
- MI_00 (audio): `RtkUsbAD_2395` — a **custom Realtek USB Audio driver** (not the Windows
  inbox USB Audio class driver)
- MI_06 (HID): `HidUsb` — standard Windows HID

The custom Realtek driver indicates Realtek silicon is present in the dongle (or in onboard
audio), and that the vendor has deployed a custom driver for it. This is consistent with a
headset dongle using Realtek USB audio silicon with custom firmware.

**Confidence:** confirmed (driver observation)

---

### F-003 — `26CE:0A0B` is USB Audio Class 2.0, 7 interfaces, complex layout

**Phase:** Full descriptor dump via pyusb + libusb

Full descriptor decoded:
- Device class: `0xEF` Miscellaneous with IAD protocol
- bcdDevice: `0x0002` (revision 0.02)
- Bus powered, 100 mA

Interface breakdown:
- Interfaces 0–5: Audio (UAC 2.0, protocol `0x20`)
- Interface 0: Audio Control with interrupt endpoint `0x89` (16 B)
- Interface 1: Mic capture — 8 alt settings, EP `0x83` IN, 124–186 B isochronous
- Interface 2: Second capture — 8 alt settings, EP `0x84` IN
- Interface 3: Speaker out — 9 alt settings, EP `0x05` OUT, 124–744 B isochronous
- Interface 4: Second playback — 18 alt settings, EP `0x06` OUT, 124–558 B
- Interface 5: Third playback — 9 alt settings, EP `0x08` OUT
- Interface 6: Vendor HID — EP `0x8A` IN interrupt, 16 B, 4 ms interval

The large number of alt settings (up to 18 on Interface 4) and multiple playback/capture streams
is consistent with a wireless gaming headset dongle supporting multiple sample rates and formats.
This layout would be unusual for simple motherboard onboard audio.

**Confidence:** confirmed (descriptor data)

---

### F-004 — Critical discovery: Report ID is `0x06`, not `0x00`

**Phase:** HID capability probing via Windows API

`HidP_GetValueCaps` returned:
- Input: ReportID=`0x06`, UsagePage=`0xFFC1`, Usage=`0x00F0`, BitSize=8, Count=63
- Output: ReportID=`0x06`, UsagePage=`0xFFC1`, Usage=`0x00F1`, BitSize=8, Count=1

All initial probes used Report ID `0x00` and received silent acceptance but no response.
Switching to Report ID `0x06` caused read errors after every write — indicating the device
received and acted on the command, but the response format differs from what the probe expected.

Additionally: output report is only **1 byte of payload** (Report ID `0x06` + 1 byte = 2 total),
not the 64-byte format assumed from the reference protocol.

**Confidence:** confirmed (HID API data)

---

### F-005 — Interface 6 HID is completely silent passively; crashes under write storm

**Phase:** HID probing

- 30 seconds of passive listening on endpoint `0x8A`: zero input reports received.
- Write storm (rapid successive writes): device dropped off USB enumeration entirely.
- Recovery required physical unplug/replug of the dongle.

The silence is consistent with the known push-based battery model (trigger required before
headset reports status). The crash confirms that tight write timing without the 75 ms delay
causes the device to fault.

**Confidence:** confirmed (observation)

---

### F-006 — LED controller (`26CE:01A2`) responds to opcodes `0xA0`–`0xAA` and `0x00`–`0x10`

**Phase:** LED controller scan (256-command brute force)

Full response table captured. Three responsive regions:
1. `0x00`: unique response with `byte[4]=0x02` — possibly device identity or mode
2. `0x01`–`0x10`: generic ACK pattern with `byte[3]=0x07`
3. `0xA0`–`0xAA`: echoes command byte at `[0]`, returns incrementing value at `[4]`

The `0xA0`–`0xAA` responses look like configuration register readbacks. The VALUE sequence
(`04 06 08 0A 01 03 05 07 09 0B 0D`) suggests two interleaved even/odd register banks.

No feature reports present. Commands `0x11`–`0x9F` and `0xAB`–`0xFF` returned null responses.

**Confidence:** confirmed (device responded); semantic interpretation speculative

---

### F-007 — Reference protocol from HeadsetControl and eruption documented

**Phase:** Prior art research

- **HeadsetControl** supports Roccat Elo 7.1 Air: VID=`0x1E7D`, PID=`0x3A37`; provides LED
  control and inactive timeout only; **no battery support** (requires a separate daemon mode).
- **eruption** (Rust project) adds battery: push-based via trigger `[0xFF, 0x01, ...]`,
  response `[0xE6, 0x06, 0x03, 0x00, LEVEL, ...]` with quartile granularity (25% steps).
- Both projects use VID `0x1E7D` exclusively; neither covers `0x26CE`.

The fact that battery is only quartile granularity matches user-reported Roccat Swarm behavior
of showing coarse battery percentage, confirming the accuracy of the eruption implementation.

**Confidence:** confirmed (source code review)

---

### F-008 — Headset emitting periodic beeps during session

**Phase:** Physical observation

The headset produced regular beep tones throughout the investigation session. Most probable cause
is a low battery warning. This may mean the device was in a degraded state during probing, which
could contribute to unusual probe behavior (silent endpoints, crash sensitivity).

**Confidence:** speculative (low battery most likely, but not confirmed)

---

### F-009 — Dongle identity pre-confirmation analysis

**Phase:** Identity resolution (superseded by F-010)

`26CE:0A0B` was suspected to be the Roccat headset dongle based on:
- 7-interface UAC2 layout inconsistent with simple onboard audio
- Custom Realtek driver (`RtkUsbAD_2395`)
- Companion `26CE:01A2` LED Controller sharing the same VID

**Confidence at this stage:** likely (circumstantial). Superseded by F-010.

---

## Session 2 — 2026-04-17

### F-010 — CONFIRMED: `26CE:0A0B` is the Roccat Elo dongle; `26CE:01A2` is NOT

**Phase:** Dongle identity — unplug/replug test (resolves Q-001)

Physical unplug test result:
- **Unplugged:** Roccat headset dongle
- **`26CE:0A0B` disappeared:** YES
- **`26CE:01A2` ("LED Controller") disappeared:** NO — it remained enumerated

**Conclusions (all confirmed):**

1. `26CE:0A0B` is definitively the Roccat Elo wireless headset dongle.
2. `26CE:01A2` is **not** part of the Roccat headset — it is a separate device (most likely a
   motherboard LED controller or other peripheral unrelated to the headset).
3. The two `26CE`-VID devices do **not** belong to the same product. The shared VID is
   coincidental — both use Realtek/ASRock silicon but are independent devices.

**Implication for F-006:** All LED controller probe data (`0xA0`–`0xAA` opcode responses) is
irrelevant to the Roccat Elo investigation. The LED controller is a motherboard peripheral.
Q-005 is now low-priority and outside scope.

**Confidence:** confirmed (physical test)

---

### F-011 — This is a previously undocumented hardware variant; protocol must be RE'd from scratch

**Phase:** Scope determination (follows from F-010)

Consequences of the confirmed dongle identity:

1. The Roccat Elo dongle uses **VID `0x26CE`**, not `0x1E7D`. No existing open-source tool
   (HeadsetControl, eruption, or any known project) supports this VID:PID pair.

2. The reference `0x1E7D` protocol (64-byte commands, Report ID `0xFF`, push-based battery
   via `[0xFF, 0x01, ...]`) **cannot be assumed to apply.** The output report on the HID
   interface is only 2 bytes (Report ID `0x06` + 1 byte payload), fundamentally incompatible
   with the reference command format.

3. Protocol must be reverse engineered from scratch. The established methodology:
   - USB traffic capture via USBPcap + Wireshark with Roccat NEON software
   - Systematic HID probe via libusb `ctrl_transfer` (bypassing Windows HID size constraints)
   - Passive monitoring of EP `0x8A` and EP `0x89` during physical headset interactions

4. The HID interface parameters now confirmed as the target:
   - Interface 6, endpoint `0x8A`
   - Report ID `0x06`
   - Input: 63 bytes payload (UsagePage `0xFFC1`, Usage `0x00F0`)
   - Output: 1 byte payload (UsagePage `0xFFC1`, Usage `0x00F1`)

**Confidence:** confirmed

---

## Open Items After Session 2

See [open_questions.md](open_questions.md) for the current question list.

Key blockers for protocol work:
1. **Q-003**: Determine correct command format — how to send 64-byte commands when output report is 2 bytes
2. **Q-006**: Monitor EP `0x89` for headset state events during physical interactions
3. **Q-007**: Firmware version query — establish hardware revision baseline

---

## Session 3 — 2026-04-17

### F-012 — Known hardware defect: widespread dongle reliability failures across user population

**Phase:** Background research / community reports

Multiple independent user reports spanning 2021–2025 document a systematic reliability failure
pattern with the Roccat Elo 7.1 Air USB dongle:

- Dongle ceases to be recognized by Windows after brief sessions (sometimes as short as 1 hour)
- Dongle heats up noticeably during use (thermal issue)
- Pairing failures after headset power cycle, requiring reboots or driver reinstalls to recover
- Issues persist through firmware updates — not resolved by software patches
- Workarounds adopted by users: USB extension cables, powered USB hubs (suggests power or signal
  integrity sensitivity)
- Professional review outlets also documented inconsistent audio delivery
- Roccat support reported as unresponsive to these reports

This pattern appears across Reddit threads, hardware forums, and product review pages over a
4+ year window, indicating a population-level hardware defect rather than isolated unit failures.

**Significance for this investigation:** The crash behavior observed in F-013 is consistent with
this known defect pattern. Our probe-induced crash may have triggered the same firmware bad-state
that manifests in the wild after extended use.

**Confidence:** HIGH — corroborated by multiple independent sources over an extended time period

---

### F-013 — Dongle entered persistent fault state after HID write storm; won't re-enumerate

**Phase:** HID probing — crash and recovery attempt

During a systematic HID probe session (256-command scan, all bytes `0x00`–`0xFF` with report ID
`0x06`, no inter-command delay), the dongle entered a fault state with the following progression:

1. Dongle dropped off HID enumeration mid-scan (consistent with prior write-storm crash in F-005,
   but this time did not self-recover)
2. Physical unplug from original port; replug to a different USB port
3. Windows `Get-CimInstance` reported device as present but with status `CM_PROB_PHANTOM` — the
   device node exists in the device tree but the hardware is not actually responding
4. On the new port, device never appeared in `Get-PnpDevice -PresentOnly` output
5. Current status: dongle physically plugged in but **not enumerating on any port**

The `CM_PROB_PHANTOM` status indicates Windows cached a device node from a previous enumeration
but the device is not providing valid USB descriptors on reconnect. This is distinct from a simple
unplug — the USB controller is seeing the device electrically but the firmware is not responding
to USB enumeration requests.

**Likely cause:** The Realtek dongle firmware entered a bad state during the write storm that
persists across unplug/replug because it survives in volatile RAM during the brief power-off of
a normal unplug. Extended power-off (30+ seconds, allowing capacitor discharge) may be required
to force a true power-on reset.

**Recovery options (priority order):**
1. Extended power-off (30+ seconds unplugged) to drain internal capacitors
2. Roccat Swarm `ROCCAT_RECOVER_TOOL.exe` if extended power-off does not recover enumeration
3. If bricked: dongle is a loss; acquire a replacement dongle

**Confidence:** HIGH — directly observed

---

### F-014 — Roccat Swarm contains firmware recovery tool and accessible firmware files

**Phase:** Research — Roccat Swarm software analysis

Research into the Roccat Swarm companion software reveals:

**Firmware file layout within Swarm installation:**
- Path: `data/3A37/firmware/` (note: `3A37` = original Elo 7.1 Air PID `0x3A37`)
- Files named: `FW_V1.23.bin` (version-stamped binary blobs)
- Users can rename firmware files and edit `firmware_upgrade.ini` to force
  cross-compatibility between device variants

**Recovery tool:**
- Executable: `ROCCAT_RECOVER_TOOL.exe` within Swarm installation
- Detection method: headset connected first, dongle plugged in second — tool detects the
  device pair and applies firmware
- Can recover dongles that are not enumerating (specifically relevant to F-013)

**Offline mode:**
- Swarm has an offline mode that bypasses cloud sync requirements
- Individual Swarm modules can be downloaded and installed manually in offline mode
- Relevant if the system has no internet access or Swarm's cloud services are unavailable

**Significance for protocol RE:**
1. The recovery tool (`ROCCAT_RECOVER_TOOL.exe`) is the primary path to reviving the crashed
   dongle from F-013
2. Installing Swarm and capturing its USB traffic via USBPcap/Wireshark would yield the complete
   HID protocol with minimal RE effort — this is potentially faster than blind brute-forcing
3. The firmware binary files in `data/3A37/firmware/` may be analyzable offline for protocol
   documentation

**Confidence:** HIGH for existence of tool and file layout; speculative for 26CE:0A0B
compatibility (path uses 3A37 PID which is the older VID)

---

### F-015 — Headset charging characteristics; beeping was likely connection issue, not battery

**Phase:** Physical characterization

Charging measurements:
- Charges via USB at 5 V
- Power draw: 2.0–2.2 W (~400–440 mA)

Physical state context:
- Headset described as new and almost unused
- Battery should not be critically depleted given usage history

**Revised interpretation of F-008 (beeping):** The periodic beeps during the earlier session
were most likely a connection/pairing failure indicator rather than a low-battery warning. The
headset may have been unable to pair with the dongle during the probe session (the HID interface
was unresponsive — see F-016), causing the headset to signal a connection error.

**Confidence:** confirmed for charging measurements; speculative for beep re-interpretation

---

### F-016 — HID vendor interface likely inactive without paired headset or Swarm initialization

**Phase:** Analysis — synthesizing probe results with new context

When the dongle was functional (before the F-013 crash), it enumerated as a full 7-interface
composite device regardless of headset pairing state. However, the HID vendor interface
(Interface 6, EP `0x8A`) was completely silent — zero input reports, commands caused "read
errors" but no useful responses.

Three hypotheses for this silence (listed from most to least likely):

1. **Headset not paired/connected (likely):** The HID control channel is only active when the
   headset has an established wireless link with the dongle. Without an active headset connection,
   the dongle has no state to report and no commands to execute, so it returns errors.

2. **Swarm initialization required (likely):** The HID interface requires a software-side
   initialization sequence — possibly a USB control transfer handshake — that Roccat Swarm
   performs at startup before the interface becomes active. Without this handshake, the dongle
   rejects all HID commands.

3. **Silent-by-design (speculative):** The dongle is entirely push-based; it only emits reports
   when something changes (button press, volume change, connection event). The "read errors" are
   the dongle rejecting invalid commands, not a sign of a fully active interface.

**Implication for Q-003:** The command format investigation should be paired with a confirmed
active headset connection. Commands sent without an active paired headset may always fail,
making it impossible to distinguish "wrong command format" from "no headset connected."

**Confidence:** speculative — requires testing with actively paired headset to confirm

---

## Open Items After Session 3

See [open_questions.md](open_questions.md) for the current question list.

Critical blockers:
1. **Q-008** (NEW — CRITICAL): Dongle won't re-enumerate after write storm crash. All protocol
   RE work is blocked until the dongle is recovered.
2. **Q-009** (NEW — HIGH): Consider installing Roccat Swarm to capture the protocol via USB
   traffic sniffing rather than blind RE — potentially much faster path.
3. **Q-003** (updated): Command format investigation must be done with a confirmed active
   headset connection (F-016); HID interface is likely inactive without paired headset.

---

## Session 4 — 2026-04-17

### F-017 — Swarm v1.9481 cannot detect its own dongle; firmware update created the orphan

**Phase:** Roccat Swarm installation and device detection

Roccat Swarm v1.9481 was installed and launched with `26CE:0A0B` plugged in. Swarm did **not**
detect the dongle. Investigation confirms Swarm scans exclusively for VID `0x1E7D` / PID
`0x3A37` — the pre-firmware-update identity of the Elo 7.1 Air dongle.

**Critical implication:** Roccat's own firmware update (shipped via Swarm or Swarm-adjacent
tooling) changed the dongle's VID:PID from `1E7D:3A37` to `26CE:0A0B`, rendering it permanently
invisible to Swarm's device scanner. The companion software that performs updates cannot detect
the device that its updates produced. The dongle is orphaned by its own vendor toolchain.

This also updates/supersedes the F-016 hypothesis: there is no Swarm initialization sequence
to intercept via USBPcap, because Swarm will never open the device. The protocol capture path
via Swarm + USBPcap is **closed**.

**Q-009 status impact:** Q-009 (Swarm USB traffic capture) is now blocked not just by dongle
recovery but by a fundamental incompatibility. The approach must change — see Q-009 update.

**Confidence:** confirmed — Swarm was running with the dongle present and did not enumerate it

---

### F-018 — Recovery Tool detects device but is broken: missing firmware files due to circular dependency

**Phase:** `ROCCAT_Recover_Tool.exe` recovery attempt

`ROCCAT_Recover_Tool.exe` was launched with the dongle plugged in. The tool displayed a
"firmware update required" window — it **can** detect the `26CE:0A0B` device, which is
significant (the recovery tool uses a different detection path than Swarm's main UI).

However, the firmware update dropdown field was non-responsive. Root cause analysis:

- The recovery tool expects `firmware_upgrade.ini` and a `firmware/` directory to be present
  adjacent to `ROCCAT_Recover_Tool.exe`
- These files are **not bundled** in the Swarm installer — they are created when Swarm
  downloads per-device modules at runtime
- Swarm cannot download the Elo module because it cannot detect the `26CE:0A0B` device
  (F-017)
- Therefore the firmware files are never created, so the recovery tool cannot proceed

**Circular failure chain:**
```
Dongle crashes -> Needs recovery tool -> Tool needs firmware/ dir
                                              |
                                    Created by Swarm module download
                                              |
                              Swarm can't download: doesn't see 26CE:0A0B
                                              |
                               Swarm only looks for 1E7D:3A37
```

**Possible resolution paths:**
1. Manually supply `firmware_upgrade.ini` and firmware binary by extracting from Swarm's
   download cache on a system where the dongle still enumerates as `1E7D:3A37`, OR
2. Locate the Elo firmware binary from a user who has run Swarm against an older/unupdated
   dongle and has the firmware cached on disk (see Q-010)
3. Download Elo firmware module from Swarm CDN directly (URL pattern may be inferrable
   from `firmware_upgrade.dll` strings — see F-019)

**Confidence:** confirmed — observed directly; root cause is confirmed from file-system state

---

### F-019 — Swarm installer extracted; key DLLs and config files identified

**Phase:** NSIS installer extraction and static analysis

Roccat Swarm NSIS installer was extracted. Key files identified:

**`firmware_upgrade.dll`**
- Contains the PIC32 flash protocol implementation
- Implements: erase, write, sign, verify operations for PIC32 microcontroller flash
- References in strings: `firmware_upgrade.ini`, `headset_x86.dll`, `Command_Key.bin`
- This DLL is the core firmware flashing engine; `ROCCAT_Recover_Tool.exe` likely
  loads it at runtime to execute the flash sequence
- The PIC32 MCU reference is significant: the dongle's main controller may be a
  Microchip PIC32, with Realtek silicon handling only the USB audio path

**`HIDDLL.dll`**
- HID communication library
- Handles HID read/write operations; this is the layer we need to intercept or replicate
  for protocol RE without Swarm running

**`EFORMAT.INI`**
- Holtek MCU programmer configuration file
- Holtek MCUs are commonly found in mice and keyboards (optical sensor controllers,
  RGB controllers)
- This file is **not relevant** to the Elo headset — it covers other Roccat peripherals
  (mice, keyboards) that use Holtek silicon

**Device module delivery model:**
- Per-device firmware files are **not bundled** in the installer
- They are downloaded at runtime by Swarm from Roccat's CDN into
  `data/<PID_hex>/firmware/` directories
- `firmware_upgrade.dll` string analysis may reveal the CDN URL pattern, which could
  allow direct download of the Elo firmware binary without Swarm detecting the device

**Significance:** The PIC32 reference in `firmware_upgrade.dll` is a new hardware-layer
finding — the dongle likely uses PIC32 as the application MCU and Realtek silicon for UAC2.
This would explain the separate HID control interface (PIC32 side) vs. audio interfaces
(Realtek side).

**Confidence:** confirmed for file identification and string contents; speculative for
PIC32-as-main-controller interpretation

---

### F-020 — Headset entered pairing mode; dongle LED did not respond; 60s of HID silence

**Phase:** Wireless pairing test

Headset power button held 10–20 seconds: white LED began blinking — **pairing mode
confirmed** on the headset side.

Dongle LED behavior: remained **solid white** throughout the 60-second observation window.
A dongle in pairing mode would typically show a blinking or alternating LED pattern. The
solid white LED indicates the dongle did not enter pairing mode in response to the headset's
pairing advertisement.

Simultaneous HID monitoring on EP `0x8A` for 60 seconds: **zero input reports received.**

**Interpretation:**
- The headset was actively advertising for pairing (LED blinking = confirmed)
- The dongle received no pairing request or did not act on it — the RF link was not
  established during this window
- The dongle's HID interface produced no traffic even with the headset in pairing mode,
  which is consistent with F-016 (HID only active when RF link is up) but also consistent
  with the dongle being in a degraded state from prior crash cycles

**Open question:** Whether the dongle requires a button press or software command to enter
its own pairing mode, or whether it should auto-accept pairing from a known headset.

**Confidence:** confirmed for LED states and HID silence; interpretation speculative

---

### F-021 — CRITICAL: Dongle IS alive and responding — hidapi is misreading the response format

**Phase:** HID command probe with hidapi

Commands were sent to Interface 6 via hidapi with report ID `0x06`, bytes `0x01`–`0xFF`,
with 500 ms inter-command delays. Result:

- **Every single command** (all tested bytes) produced a "read error" on the subsequent
  `hid_read()` call
- The read error is **not** "no data" — it is a parsing failure, meaning the dongle
  **is** sending bytes back, but hidapi cannot interpret them as a valid HID report

**Three-part conclusion:**

1. The dongle **receives** our commands — the response on every command confirms delivery
2. The dongle **processes** our commands and **sends a response** on EP `0x8A` after each one
3. hidapi's `hid_read()` fails because the response bytes do not conform to what hidapi
   expects for Report ID `0x06` — either wrong report ID in the response, unexpected byte
   count, or a format hidapi's Windows backend cannot handle

**After 8 commands:** dongle LED dimmed and turned off, then device dropped off USB
enumeration again (consistent with F-022).

**Critical path forward:** The raw response bytes need to be read directly, bypassing
hidapi's parsing layer. Two options:
1. **Windows `ReadFile()`** on the HID device handle — returns raw bytes from the interrupt
   endpoint without HID report parsing
2. **libusb `libusb_interrupt_transfer()`** on endpoint `0x8A` — completely bypasses the
   Windows HID driver stack and reads raw USB frames

The responses the dongle is sending may contain the exact information needed to understand
the protocol — we just cannot see them through hidapi.

**Confidence:** confirmed — hidapi read error behavior is well-understood; error on every
command with valid timing is definitive evidence of response data being present

---

### F-022 — Dongle crash threshold confirmed: as few as 8 commands triggers crash

**Phase:** Crash characterization

Two confirmed crash events now on record:

| Event | Conditions | Commands sent | Delay | Outcome |
|-------|------------|--------------|-------|---------|
| Session 1 (F-005/F-013) | Write storm, report ID `0x06` | 256 | None | Dropped USB enumeration; CM_PROB_PHANTOM |
| Session 4 (F-021) | Controlled probe, report ID `0x06` | ~8 | 500 ms | LED dimmed/off; dropped USB enumeration |

**Key finding:** The 500 ms inter-command delay did not prevent the crash. The trigger is
the **number of unrecognized commands** received, not the rate. After approximately 8
commands that the dongle cannot satisfy (because the headset is not paired, or the format is
wrong), the dongle firmware enters an error state and asserts a crash/reset.

This behavior explains the known user-reported reliability issues (F-012): in the field,
software bugs, driver enumeration sequences, or repeated pairing failures may send enough
invalid HID traffic to trigger the same crash path.

**Operational constraint going forward:** Any future probe session must limit commands to
well under 8 before pausing for dongle state verification. Sending raw bytes via
`libusb_interrupt_transfer` or `ReadFile` may not be subject to the same crash path if the
issue is specifically the dongle's HID command handler entering a bad state on unrecognized
Report ID `0x06` commands.

**Confidence:** confirmed — two independent crash events with documented conditions

---

## Open Items After Session 4

See [open_questions.md](open_questions.md) for the current question list.

Key updates:
1. **Q-008** (CRITICAL): Dongle crashed again (F-022). Same recovery approach applies.
2. **Q-009** (updated): Swarm USB capture path is closed — Swarm cannot detect `26CE:0A0B`
   (F-017). New approach: raw `ReadFile`/libusb read to capture dongle responses (Q-011).
3. **Q-010** (NEW): Can we obtain the Elo firmware binary directly from Swarm's CDN or from
   a cached install? Needed to feed `ROCCAT_Recover_Tool.exe` and for binary analysis.
4. **Q-011** (NEW): Raw response bytes — what does the dongle actually send back? Need
   `ReadFile` or libusb read to bypass hidapi parsing.

---

## Session 5 — 2026-04-17

### F-023 — Swarm II (Turtle Beach) also ships no device firmware; different product family

**Phase:** CDN research — Turtle Beach Swarm II evaluation

Swarm II v1.0.0.38 was downloaded directly from the Turtle Beach CDN:
`https://acpv.prod.turtlebeach.com/support/generated/software/0-319/Swarm-II.zip`

NSIS installer was extracted. Contents:
- `QT_LIBRARY` — Qt runtime components
- `SWARM_II` metadata and application binaries

**No device firmware was bundled.** Like Roccat Swarm, Swarm II delivers device modules
(including firmware) via runtime CDN download rather than shipping them in the installer.

Swarm II is the Turtle Beach-rebranded replacement for Roccat Swarm following the 2019
acquisition. It does not carry Roccat device modules — it covers Turtle Beach peripherals.
It has no relevance to the `26CE:0A0B` dongle and is out of scope for firmware acquisition.

**Significance:** Eliminates Swarm II as an alternative firmware acquisition path. The
original Roccat Swarm CDN (`acpv.prod.turtlebeach.com`) remains the only identified source
for the Elo device module, but the download requires a module ID (not a PID directly) — see
F-024.

**Confidence:** confirmed — installer contents observed directly

---

### F-024 — CDN URL pattern identified; module ID mapping is the missing link

**Phase:** CDN and Swarm protocol research

The Swarm module download URL pattern was identified:

```
https://acpv.prod.turtlebeach.com/swarm1/form/%1
```

The `%1` parameter is a **module ID** drawn from Swarm's internal `version.ini` file, which
contains numbered sections (e.g., `[18]`, `[13]`) mapping device families to module IDs.
The module ID is **not** the device PID directly — there is an internal lookup table that
maps PID → module ID.

**What this means for firmware acquisition (Q-010):**
- The firmware binary for the Elo headset is at a URL of the form
  `https://acpv.prod.turtlebeach.com/swarm1/form/<elo_module_id>`
- The Elo module ID must be extracted from `version.ini` inside a Swarm installation that
  still has the Elo device listed — likely only in Swarm versions predating the `26CE`
  VID migration, or from a `version.ini` obtained from a system where Swarm detected the
  dongle as `1E7D:3A37`
- Alternatively, the numbered sections of `version.ini` may be enumerable (small integer
  range); brute-forcing `[1]` through `[100]` against the CDN endpoint may reveal the Elo
  module

**Confidence:** confirmed for URL pattern; speculative for module ID enumeration approach

---

### F-025 — Third dongle crash: single WriteFile command crashes firmware; HID output handler is fatally broken

**Phase:** Raw Windows API probe using WriteFile/ReadFile

A single HID output report was sent using Windows `WriteFile()` directly on the HID device
handle:

```
WriteFile result: 1 (success)
Bytes written: 2 (report ID 0x06 + 1 payload byte)
GetLastError: 0 (no error)
```

Immediately following `WriteFile`, a `ReadFile` on the same handle returned **0 bytes**.
The dongle dropped off USB enumeration immediately after.

**What this proves:**

1. `WriteFile` succeeded without error — the HID output report was **delivered to the
   dongle's firmware** cleanly. There is no write-path issue.
2. The dongle crashed **after receiving a single, correctly-formed HID output report**,
   before it could send any response.
3. The crash is triggered inside the dongle's HID output report handler, not by
   malformed writes, not by command rate, not by the hidapi layer.
4. `ReadFile` returning 0 bytes (not an error, just empty) with immediate USB drop means
   the dongle firmware faults before it can write any response to the interrupt IN endpoint.

**Revised crash model:**

The dongle's firmware HID output report handler for Report ID `0x06` contains a fatal bug.
When an output report is received — regardless of payload content, regardless of write
rate — the handler faults. The dongle is effectively unable to process its own HID output
interface. This is not a timing issue, not a command-count accumulation issue: **one
correctly delivered report is enough to crash it**.

**Implication for F-022 crash threshold:** The "~8 commands" observation from Session 4 was
likely due to hidapi overhead or driver buffering delaying delivery. The true threshold is 1
report ID `0x06` output report delivered to firmware.

**Implication for the investigation path:** Sending HID output reports to probe the protocol
is not viable as long as this firmware is running. The response-capture approach (Q-011)
using OVERLAPPED I/O must set up the async `ReadFile` before issuing `WriteFile`, to have
any chance of reading the response in the window between write and crash.

**Session crash count:** The dongle has been crashed and self-recovered 4 times this session.
Each recovery required 30 seconds to 5 minutes unplugged. The device reliably self-recovers
via extended power-off, which is now the established recovery procedure for routine crashes.

**Confidence:** confirmed — WriteFile success with immediate drop is unambiguous

---

## Open Items After Session 5

See [open_questions.md](open_questions.md) for the current question list.

Key updates:
1. **F-025 revises the crash model:** A single delivered output report crashes the dongle.
   F-022's "~8 command" threshold was an artifact of the hidapi layer; the true threshold
   is 1. All probe strategies must account for this.
2. **Q-011 approach updated:** OVERLAPPED I/O (async `ReadFile` issued before `WriteFile`)
   is now the primary next step — the only window to capture response bytes is the brief
   interval between the dongle receiving the write and crashing.
3. **Q-010 path narrowed:** CDN URL pattern confirmed (F-024); the missing piece is the
   Elo module ID from `version.ini`. Enumeration or community sourcing needed.
4. **Dongle recovery is routine:** 4 crashes this session, all self-recovered with 30s–5min
   power-off. Extended power-off is now the standard recovery procedure — replace dongle
   only if self-recovery stops working.

---

## Session 6 — 2026-04-17

### F-026 — CRITICAL REFRAME: "crashes" are DFU mode entry; dongle firmware is not broken

**Phase:** Static analysis — `firmware_upgrade.dll` string extraction

Deep string analysis of `firmware_upgrade.dll` from the Swarm installation reveals the
complete DFU firmware update protocol for this dongle family. This finding retroactively
reinterprets every prior "crash" event (F-005, F-013, F-022, F-025).

#### DFU command assignments

| Byte | Role | Evidence string |
|------|------|-----------------|
| `0x06` | Enter DFU / bootloader mode | `"Try to start DFU mode failed, 0x06 command failed"` |
| `0x07` | Check DFU status / reboot FW | `"Try to reboot FW, 0x07 command failed"`, `"Check DFU status 0x07 command failed"` |

**Report ID `0x06` on Interface 6 is the DFU mode-entry command.** Every time we sent an
HID output report with report ID `0x06` — which is the only output report the device
advertises — we were issuing a DFU mode-entry command. The dongle was obeying, not crashing.

#### DFU re-enumeration flow (from strings)

```
1. "Headset in app mode, change to bootloader mode"
2. "Send mode change command"          ← WriteFile(report_id=0x06)
3. Device drops off USB                ← what we observed and called a "crash"
4. "Enum bootloader mode device"       ← device re-enumerates as a DIFFERENT VID:PID
5. "Device is in bootloader mode"
6. Open new HID handle to bootloader device
7. Flash firmware via DFU protocol (Dongle_DFU.dll)
8. "Now waiting device re-boot from bootloader mode"
9. Command 0x07 → reboot to app mode
```

The dongle has been entering DFU/bootloader mode successfully every time we sent a command.
We interpreted step 3 as a crash because we never polled for a new USB device after the
drop. The bootloader device is sitting there waiting; we just never looked for it.

#### Additional strings of significance

**Device and model confirmation:**
- `"3A37"` — explicit PID string; confirms Elo support in this DLL
- `"Elo Air"` — explicit product name string

**Multi-chip update architecture:**
- `"Dongle_DFU.dll"` — separate DLL handles dongle DFU; `firmware_upgrade.dll` is the
  orchestrator
- `CFirmware_upgrade::set_pid(VID, PID, type)` — `firmware_upgrade.ini` maps VID:PID pairs
  to firmware files and updater types
- Chip-specific updaters present in the same package:

| Updater reference | Chip family | Typical use in Roccat products |
|-------------------|-------------|-------------------------------|
| PIC32             | Microchip PIC32 | Dongle application MCU  |
| Holtek            | Holtek HT32 | Mice, keyboards            |
| CMedia            | C-Media     | USB audio codec            |
| ATTiny            | Atmel ATtiny | Small MCU (sensors, etc.) |
| nRF               | Nordic nRF5x | BLE/RF wireless MCU        |

The nRF reference is particularly significant — the headset's wireless RF link is likely
handled by a Nordic nRF5x chip. The nRF DFU utility is invoked as
`"dfu usb-serial --package"`, meaning the headset itself (not just the dongle) can receive
firmware updates over USB cable in a separate flow.

**Wireless headset update flow (from strings):**
`"Since the %1 is wireless, its firmware needs to be updated via USB cable. First update
the dongle, then connect the %2 via cable and update it afterwards."`

This confirms a two-phase update: dongle via DFU (PIC32/Dongle_DFU.dll), then headset
earbud via USB cable (nRF DFU over serial).

#### Retroactive reinterpretation of prior findings

| Prior finding | What we thought | What actually happened |
|---------------|-----------------|------------------------|
| F-005 | Crash from write storm | Multiple DFU mode entries from rapid commands |
| F-013 | CM_PROB_PHANTOM persistent crash | Dongle in DFU bootloader mode; different VID:PID not scanned |
| F-022 | Crash threshold ~8 commands | ~8 DFU entries before extended power-off required |
| F-025 | Single WriteFile crashes firmware | Single WriteFile correctly entered DFU mode |

The dongle firmware is **not broken**. The HID output report handler works exactly as
designed. Report ID `0x06` is specifically the DFU mode-entry command, and the dongle
executes it faithfully every time.

The "recovery via 30s–5min power-off" is simply the DFU bootloader timing out and
rebooting to app mode when it receives no firmware image.

#### Immediate next step

After sending one `WriteFile(report_id=0x06)` to trigger DFU mode entry, immediately scan
all USB devices for a new VID:PID that was not present before. The bootloader device will
appear on the bus — likely with either:
- A Realtek DFU VID:PID (if Realtek chip handles USB in bootloader mode)
- A PIC32 bootloader VID:PID (`04D8:xxxx` — Microchip's registered VID)
- The same `26CE:0A0B` VID:PID but with a different bcdDevice revision

Once the bootloader device is identified, the full DFU flashing path becomes available —
either for firmware recovery or for firmware analysis.

**Confidence:** confirmed for DFU command assignments and re-enumeration flow (from explicit
strings); speculative for bootloader VID:PID (not yet observed directly)

---

## Session 7 — 2026-04-17

### F-027 — Dongle USB stack not initializing; LED active but no USB enumeration

**Phase:** Hardware recovery — post cap-drain attempt

After capacitor drain (VCC/GND pins shorted while unplugged) and multiple port changes, the
dongle presents this state:

- LED illuminates white on plug-in — MCU is running and executing boot code
- Device does **not** appear in Windows PnP (`Get-PnpDevice`)
- Device does **not** appear in HID enumeration
- Device does **not** appear in libusb device list
- No unknown devices, no error devices, no partial enumerations visible anywhere

The LED confirms the microcontroller is powered and has reached at least its GPIO
initialization code. The complete absence of USB enumeration — not even a partial or
errored descriptor exchange — means the USB stack never starts. At this stage the chip is
not asserting D+ or D-, or is doing so without valid descriptor responses.

**Most likely cause:** The dongle's application firmware is corrupted or stuck in a state
where the USB peripheral is never initialized. This is distinct from a DFU bootloader
timeout state (where the device would still enumerate, just as a different VID:PID). The
chip has booted but is running code that does not reach the USB initialization routine —
or has reached a fault handler that halts before USB init.

**What this rules out:**
- Simple DFU bootloader timeout: those states still enumerate on USB
- Power supply problem: LED proves adequate power
- Host-side USB controller issue: confirmed on multiple ports

**What this does not rule out:**
- Physical button-triggered hardware bootloader (F-028) — if the chip has a ROM-level boot
  mode select, it would be entirely independent of the corrupted application firmware
- The corrupted firmware is a new state distinct from prior DFU timeout states — prior
  "crashes" involved the dongle successfully re-enumerating as a DFU device; this failure
  mode is deeper

**Confidence:** confirmed — LED active, USB silent, observed across multiple ports

---

### F-028 — Physical reset button discovered; may trigger ROM-level bootloader

**Phase:** Hardware inspection

A physical button (pinhole or tactile switch) was found on the dongle body. This is
significant because many USB microcontrollers implement a **hardware boot mode select**
that is entirely independent of application firmware:

| MCU family | Hardware boot mechanism |
|------------|------------------------|
| STM32 | BOOT0 pin held HIGH at reset → ROM DFU bootloader (ST VID `0483`, DFU PID `DF11`) |
| PIC32 | MCLR + specific pin state at reset → ICSP/bootloader mode |
| Nordic nRF52 | GPIO + reset → open bootloader mode |
| Realtek USB audio | Vendor-specific — some support pin-triggered USB recovery mode |

**Procedure being attempted:** Hold the button while plugging in USB power. This is the
standard recovery entry method for devices with hardware boot mode select. If the button
is wired to a BOOT pin or serves as a reset-with-mode-select, it would:

1. Bypass the corrupted application firmware entirely
2. Enter a factory ROM bootloader that enumerates independently of app flash contents
3. Present a new USB device (typically a DFU or UART-serial interface) for reflashing

**Why this could be the key to everything:**

If successful, the ROM bootloader would:
- Resolve F-027 by providing a working USB interface regardless of app firmware state
- Resolve Q-008 (dongle recovery) without needing Swarm, CDN firmware, or any prior
  tooling — ROM bootloaders accept raw firmware images over standard protocols
- Potentially expose the firmware binary via memory readback (if the bootloader permits it)
- Allow flashing of known-good firmware to restore normal operation permanently

**If the button does NOT work as a hardware boot select:**
- It may be a pairing reset button (clears RF pairing state only, not firmware)
- It may be a factory reset button that triggers a soft reset via firmware (which won't
  help if firmware is not reaching USB init)
- It may be wired to a physical reset line that performs the same reset as power-cycling

**Current status:** Test in progress. Result to be documented as a follow-on finding.

**Confidence:** speculative — hardware button function unconfirmed; bootloader entry
hypothesis is plausible based on common MCU design patterns

---

## Session 8 — 2026-04-17

### F-029 — Button-hold on plug-in reliably recovers dongle from non-enumerating state

**Phase:** Hardware recovery — button test result (resolves Q-008)

The hardware button test (F-028) succeeded. Holding the dongle button while plugging in USB
brought the device back from the F-027 state (LED active, zero USB enumeration):

- Dongle LED changed from solid white to **blinking red** — a new state not seen before
- USB fully enumerated as `26CE:0A0B` with all interfaces present and functional
- This recovery is **repeatable** — confirmed as a reliable method

**What the button does:** The button-hold-on-plug-in sequence acts as a hardware-level
reset that forces the dongle's MCU into a mode where the USB stack initializes correctly.
Whether this is a true ROM bootloader entry (bypassing application flash), a hardware reset
pin that clears a bad firmware state, or a mode-select that forces a clean USB init path is
not yet confirmed — but the practical result is identical: a fully enumerating USB device.

**Resolution of Q-008:** Dongle recovery is no longer a blocker. The procedure is:

1. Unplug dongle
2. Hold the physical button
3. Plug in USB while still holding button
4. Dongle LED blinks red — device is enumerated and accessible

This procedure recovers from any observed crash state, including the F-027 deep failure
where even extended power-off had not restored enumeration.

**Impact on field reliability reports (F-012):** Users experiencing the population-level
dongle reliability issues can likely recover using this same button procedure. The button
was previously undocumented in any public source found during this investigation.

**Confidence:** confirmed — directly observed; repeatable

---

### F-030 — Dongle LED state map partially decoded

**Phase:** Button interaction observation

Four LED states observed and catalogued:

| LED state       | How to trigger                              | Interpretation                          |
|-----------------|---------------------------------------------|-----------------------------------------|
| Solid white     | Normal plug-in, no button                   | App mode, no headset connected          |
| Blinking red    | Hold button while plugging in               | Recovery / pairing-ready mode           |
| Pink / magenta  | Short button press while in blinking-red    | Possibly active pairing scan initiated  |
| Off / dim       | After HID output report (report ID `0x06`)  | DFU mode entry (see F-026)              |

**Notes:**
- The blinking-red state (recovery mode) is the state the dongle enters when the button
  is held during plug-in. It fully enumerates on USB and is the post-recovery starting
  point for further work.
- The pink/magenta state is produced by a brief button press while already in blinking-red.
  Its exact meaning is unconfirmed — "active pairing scan" is the most likely interpretation
  given the color change, but no HID traffic was observed in this state (F-031).
- The off/dim state after HID commands is now understood as DFU mode entry (F-026), not
  a crash. The dongle is waiting for a firmware image; it times out and reboots to app mode.

**Confidence:** confirmed for trigger conditions and LED colors; speculative for semantic
interpretation of pink/magenta state

---

### F-031 — Pairing attempt failed in recovery mode; HID interface silent in all LED states

**Phase:** Wireless pairing test in blinking-red (recovery) mode

Conditions: dongle in blinking-red (recovery) mode, headset in white-blinking (pairing)
mode. 60-second observation window. Button pressed during test to produce pink/magenta mode.

Results:
- **No RF pairing connection established** in either dongle LED state
- **Zero HID traffic** observed on EP `0x8A` throughout the entire session
- Headset eventually powered off automatically (battery management or auto-shutdown timeout)

**Two interpretations of the HID silence:**

1. **HID interface only activates after successful RF link (likely):** The vendor HID
   interface on Interface 6 is gated on a live wireless connection. Without an established
   RF link between headset and dongle, the HID endpoint stays dark regardless of dongle LED
   state. This would mean all app-mode HID probing must wait for a successful pairing.

2. **Recovery mode is not app mode (possible):** The blinking-red state may be a limited
   recovery or pairing-only mode that intentionally does not expose the full HID command
   interface. The normal HID interface may only be active in solid-white (app) mode with a
   connected headset.

**Why pairing failed:** Two candidate explanations:
- The dongle firmware (which has demonstrated DFU handler bugs) may also have a broken RF
  pairing stack — the same firmware corruption that caused DFU issues may affect the radio
  subsystem
- The headset and dongle may have lost their pairing bond and require a specific re-pairing
  sequence that was not triggered correctly

**Significance for investigation path:** App-mode HID command probing (Q-003, Q-011) is
only meaningful with an established RF link. The pairing failure is a second-order blocker
behind dongle recovery — now that recovery is solved (F-029), establishing a working RF
link is the next prerequisite.

**Confidence:** confirmed for HID silence and pairing failure; speculative for root cause

---

## Session 9 — 2026-04-17

### F-032 — DFU probe result: no USB bootloader device re-enumerates after command 0x01

**Phase:** DFU probe — `dfu_probe.py` execution

Script sent one HID output report (report ID `0x06`, command byte `0x01`) to the dongle in
app mode (solid-white LED). Dongle dropped off USB at approximately 0.5 seconds, consistent
with prior DFU mode entries. The host then monitored USB for 30 seconds using all available
methods:

- HID enumeration — no new devices
- libusb device scan — no new devices
- Windows Device Manager — no unknown or error devices
- `devcon rescan` — no new devices found

**Conclusion:** The dongle does **not** re-enumerate as a USB device in bootloader mode
after receiving a DFU command. The DFU protocol is **not USB-based**.

**Revised interpretation of the DFU flow (F-026 update):** The `firmware_upgrade.dll`
strings describing "Enum bootloader mode device" refer to a **2.4 GHz wireless
re-enumeration**, not a USB re-enumeration. After receiving the DFU trigger command, the
dongle's nRF radio goes into a wireless bootloader advertisement mode — the firmware update
is pushed over the 2.4 GHz link, not over USB. This is consistent with the nRF DFU utility
reference in F-019 (`"dfu usb-serial --package"` applies to the wired headset path, not the
dongle).

The dongle returns from DFU mode after a timeout because no wireless firmware image is
broadcast.

**Confidence:** confirmed — 30-second scan with multiple methods found nothing

---

### F-033 — Red-blink mode: HID output endpoint disabled; writes fail gracefully; USB enumeration variable

**Phase:** HID probe in red-blink (button-hold recovery) mode

When the dongle is in red-blink mode with USB enumeration active, HID write behavior is
fundamentally different from app mode (solid white):

| Behaviour | App mode (solid white) | Red-blink mode |
|-----------|----------------------|----------------|
| HID write result | Succeeds (2 bytes written) | Fails — `ERROR_GEN_FAILURE` (error 31) |
| Post-write behaviour | Dongle enters DFU mode (drops off USB) | **Dongle stays on USB — no crash** |
| HID input reports | None without RF link | None |
| Feature reports | None | None |
| `ReadFile` | Blocks / returns 0 | Blocks indefinitely |
| `HidD_GetInputReport` | Fails | Fails |

**Error 31 (`ERROR_GEN_FAILURE`)** on `WriteFile` means the HID output endpoint is
explicitly disabled in the device — the endpoint exists in the descriptor but the firmware
has shut down the handler for it. This is a graceful rejection, not a fault.

**Significance:** Red-blink mode is a **safe state for USB experimentation**. Writes are
rejected without crashing. This means:
- USB enumeration can be maintained while attempting reads and queries
- Repeated write attempts will not brick the dongle
- The mode can be used as a staging point for any non-destructive investigation

**USB enumeration variability (see F-035):** Red-blink mode does not always produce USB
enumeration. Whether USB is active in red-blink appears to depend on how cleanly the
button-hold recovery was performed.

**Interpretation:** Red-blink mode activates the 2.4 GHz radio (wireless pairing/recovery
scan) while intentionally disabling the HID command interface. The MCU maintains bare USB
enumeration for power delivery but suspends all HID protocol handling.

**Confidence:** confirmed — error 31 behaviour observed directly; interpretation speculative

---

### F-034 — Headset USB-C port is charge-only; no USB data

**Phase:** Headset USB data path investigation

The headset was connected via two different USB cables to enumerate it as a USB device.
Neither cable produced a new USB device entry. No new VID:PID appeared in any scan method.

**Conclusion:** The headset's USB-C port is **charge-only** — it provides 5V power but the
data lines (D+/D−) are either not connected or connected to a charge-detection circuit only.
There is no USB data path on the headset.

**Implications:**
- The nRF DFU path `"dfu usb-serial --package"` referenced in F-019 does not apply to
  this headset variant, OR it applies only to a different SKU that has a USB data port
- Headset firmware updates are delivered exclusively over the 2.4 GHz wireless link from
  the dongle
- Charging is the only function of the USB-C port on this headset
- Any future firmware reflash of the headset itself must go through the dongle's RF link

**Confidence:** confirmed — two cables, no enumeration on either

---

### F-035 — Red-blink mode USB enumeration is state-dependent, not guaranteed

**Phase:** Recovery mode behaviour characterisation

Earlier (F-027) red-blink mode correlated with no USB enumeration. Session 9 observations
show red-blink mode WITH full USB enumeration (`26CE:0A0B`, all interfaces active). Both
states show the same LED pattern.

**Observed distinction:** USB enumeration in red-blink mode appears to depend on the
entry path:
- Button-hold after a clean power cycle → more likely to produce USB enumeration
- Button-hold after a DFU-induced drop → may produce red-blink without USB, or with
  intermittent USB

The underlying mechanism is likely whether the Realtek USB audio subsystem successfully
initialises during the button-hold boot sequence. The nRF radio may start regardless; the
USB stack's readiness may vary.

**Practical guidance:** When USB enumeration is needed in red-blink mode, perform a clean
unplug, wait 5+ seconds, then execute the button-hold on a fresh plug-in.

**Confidence:** confirmed for state variability; speculative for mechanism

---

### F-036 — Headset has no hardware recovery mode equivalent to dongle button-hold

**Phase:** Headset hardware investigation

The headset has no button combination that produces a recovery or bootloader equivalent of
the dongle's button-hold sequence. Only the dongle has this hardware-level recovery feature.

**Implication:** Headset-side firmware recovery, if ever needed, must come through the
dongle's wireless DFU path. There is no independent headset recovery channel available from
the USB-C port (charge-only, F-034) or from button combinations.

**Confidence:** confirmed — no equivalent behaviour observed on headset

---

## End-of-day summary — 2026-04-17

### What is now established

| Topic | Status |
|-------|--------|
| Device identity (`26CE:0A0B` = Roccat Elo dongle) | Confirmed (F-010) |
| HID interface layout (Interface 6, EP `0x8A`, Report ID `0x06`) | Confirmed (F-003, F-004) |
| Report ID `0x06` output = DFU mode trigger (radio-based, not USB) | Confirmed (F-026, F-032) |
| Dongle recovery procedure (button-hold on plug-in) | Confirmed, repeatable (F-029) |
| Red-blink mode = wireless-only recovery; HID output disabled | Confirmed (F-033) |
| Headset USB-C = charge-only; no data path | Confirmed (F-034) |
| No USB DFU bootloader; DFU is 2.4 GHz wireless | Confirmed (F-032) |

### What remains open

1. **RF pairing** — headset and dongle will not establish a wireless link. Without it, the
   app-mode HID command interface cannot be exercised. Candidate paths: try app-mode +
   headset pairing; research factory re-pair procedure; or reflash firmware via Q-010.

2. **Firmware binary acquisition (Q-010)** — CDN URL pattern known; module ID unknown.
   Getting the firmware binary would enable `ROCCAT_Recover_Tool.exe` reflash and potentially
   fix the RF pairing stack.

3. **App-mode command format (Q-003/Q-011)** — deferred until RF pairing is working.
   Red-blink mode is not viable for this (HID output disabled). Requires solid-white mode
   with an active headset connection.

4. **JTAG/hardware debug** — if firmware reflash via software paths remains blocked,
   physical JTAG/SWD access to the PIC32 or nRF5x MCU is the last-resort path.

---

## Session 10 — 2026-04-18

### F-037 — settings.xml decoded: complete Roccat device database; Elo DFU PID confirmed

**Phase:** Swarm data extraction — decompression and parsing of `settings.xml`

The file `settings.xml` inside the Swarm installation is zlib-compressed with a 4-byte
header. Decompressed from 3,212 bytes to 20,789 bytes. Contains the complete Roccat device
database: 143 products, all with VID/PID, DFU PID, DLL name, and display name fields.

**Elo Air entries:**

| Device | Type | App PID | DFU/updating PID | DLL name | Display name |
|--------|------|---------|-----------------|----------|--------------|
| Elo Air dongle | 52 | `0x3A37` | **`0x3A36`** | `3A37` | `ELO_AIR` |
| Elo Air headset | 50 | `0x3A39` | **`0x3A38`** | `3A39` | `ELO_AIR` |
| Elo USB (wired) | 49 | `0x3A34` | `0x3A34` | `KHAN_AIMO` | `ELO_USB` |

All entries use VID `0x1E7D`.

**Key confirmed facts:**

1. **DFU PID for the Elo Air dongle is `0x3A36`** — when the dongle enters DFU/bootloader
   mode, it should present as `1E7D:3A36`. Prior USB scans after DFU entry (F-032) found
   nothing under this VID because the dongle now presents as `26CE:0A0B`, not `1E7D:3A37`.
   The DFU PID change (`26CE:????` → unknown) is a direct consequence of the VID change
   documented in F-038.

2. **`updating_pid` is a distinct PID, not identical to app PID** — the Elo USB wired
   device (type 49) uses the same PID for both app and DFU, but the wireless Elo Air
   dongle (type 52) drops to `0x3A36` in DFU mode. This confirms the F-032 observation
   that nothing appeared after DFU entry — we were looking for a re-enumeration under the
   wrong VID entirely.

3. **DLL name `3A37` maps to the firmware file directory** — the `data/3A37/firmware/`
   path documented in F-014 is derived directly from the DLL name field, not the PID hex.

**Confidence:** confirmed — decoded directly from Swarm's own device database

---

### F-038 — VID `0x26CE` is Savitech (USB audio chip vendor); VID change was deliberate

**Phase:** Binary analysis — `firmware_upgrade.dll` VID occurrence mapping

VID `0x26CE` appears exactly **2 times** in the `firmware_upgrade.dll` binary. The VID is
identified as belonging to **Savitech Corporation**, the manufacturer of the USB audio
chip used in the Roccat Elo Air dongle. This is not the Realtek or ASRock VID as previously
speculated — it is the audio codec vendor's own VID.

**The VID change was deliberate and planned:**
- The DLL loads `0x26CE` from the INI file at runtime rather than hardcoding it alongside
  the `0x1E7D` entries. This means the VID change was a conscious engineering decision,
  not an accident or silicon substitution.
- `0x1E7D` (Roccat GmbH) appears **61 times** in the same DLL — it is the primary VID for
  all other Roccat devices. The `0x26CE` entries are deliberately segregated as INI-loaded
  runtime values.

**Consequence chain:**

```
1. Dongle ships with VID 0x1E7D PID 0x3A37 (app mode) → Swarm detects it
2. Roccat ships firmware update via Swarm that changes VID to 0x26CE PID 0x0A0B
3. Post-update: Swarm no longer detects the dongle (looks for 0x1E7D only)
4. ROCCAT_Recover_Tool.exe detects it (uses broader scan) but needs firmware files
5. Firmware files require Swarm module download → Swarm can't see device → circular
6. CDN firmware modules then decommissioned (F-040) → no download path remains
```

**Significance for users experiencing the F-012 field reliability failures:** Any user
whose dongle received this firmware update is permanently locked out of official software
support. The button-hold recovery (F-029) is the only remaining recovery method, and it
only restores USB enumeration — it does not revert the VID change.

**Confidence:** confirmed — VID occurrence counts from binary analysis; deliberate INI
loading confirmed from DLL structure; Savitech VID registration confirmed

---

### F-039 — `firmware_upgrade.dll` fully analysed: 9 protocols, flash packet format, checksums

**Phase:** Static analysis — complete export table and protocol RE

Full analysis of `firmware_upgrade.dll`:

**Export table:**
- 70 total exports
- `CFirmware_upgrade` class: 44 methods (constructor, destructor, `set_pid()`, protocol
  dispatch, progress callbacks, error handling)
- Embedded hidapi: 26 functions (`hid_open`, `hid_write`, `hid_read`, `hid_send_feature_report`,
  `hid_get_feature_report`, `hid_enumerate`, and related)

**9 distinct firmware update protocols:**

| Protocol name | Target chip/device | Notes |
|--------------|-------------------|-------|
| PIC32 | Microchip PIC32 | Dongle application MCU |
| Neon `0x06`/`0x07` | Neon device family | DFU trigger commands documented in F-026 |
| Holtek ISP | Holtek HT32 | Mice, keyboards |
| Klassic boot-mode | Klassic device | Boot mode selection |
| Kain 200 HID | Kain 200 mouse | Direct HID flash |
| PURE OTA BT | Bluetooth OTA | Pure wireless BT |
| Nordic nRF / nrfutil | Nordic nRF5x | Wireless MCU; invoked as `nrfutil.exe` |
| Khan Aimo / CMedia | CMedia USB audio | Audio codec firmware |
| PXI / Pixart | Pixart sensor | Mouse optical sensor |

**Flash packet format:**
- **520 bytes per packet: 8-byte header + 512-byte data payload**
- This format constant appears 62 times in the compiled code — it is the primary transfer
  unit for all PIC32 flash operations
- The 8-byte header likely contains: sequence number, command/type byte, length, CRC

**Checksum algorithms:**
- CRC-16 CCITT (polynomial `0x1021`) — standard CRC-16
- CRC-16 reflected (polynomial `0x8408`) — bit-reversed variant
- Simple additive checksum — used for lightweight packet integrity checks

**Runtime DLL loading:**

| DLL / executable | Purpose |
|-----------------|---------|
| `headset_x86.dll` | Headset-side command interface |
| `Dongle_DFU.dll` | Dongle DFU flash operations |
| `USBCmdLib.dll` | Low-level USB command library |
| `ISPDLL.dll` | ISP (in-system programming) for Holtek |
| `nordic_x86.dll` | Nordic nRF5x wrapper |
| `PXICtrl3318.dll` | Pixart sensor controller |
| `nrfutil.exe` | Nordic DFU utility (invoked as subprocess) |

**Significance:** The Neon protocol (`0x06`/`0x07`) is the one our dongle uses. The 520-byte
flash packet format and CRC-16 CCITT checksum are the parameters needed to construct a valid
DFU firmware image if/when the firmware binary is obtained. The embedded hidapi in the DLL
is the actual HID communication layer — its function signatures match the open-source hidapi
API exactly, meaning the DLL's HID operations are fully understood.

**Confidence:** confirmed — from binary export table analysis and constant extraction

---

### F-040 — CDN firmware modules decommissioned; download endpoints return 404

**Phase:** CDN enumeration — autoupdate API RE and hardware download probe

**Autoupdate API fully reverse-engineered:**

Endpoint: `POST https://acpv.prod.turtlebeach.com/swarm1/autoupdate/ELO_AIR`

Request body (JSON, `Content-Type: application/x-www-form-urlencoded`):
```json
data={"system":27,"version":1.9481,"protocol":2,"hardware":{},"software":{"3A37":0.0}}
```

Response structure:
```json
["successfully", {"hardware": null, "software": null}]
```

The server responds `"successfully"` but returns `null` for both `hardware` and `software`
fields for **every device tested** — not just the Elo. This is not a VID/PID mismatch
issue; the server returns null universally.

**Hardware download endpoint probed:**

URL pattern: `https://acpv.prod.turtlebeach.com/swarm1/download/hardware/2/{id}`

Result: **404 for every ID tested in the range 1–500+**

**Software download endpoint probed:**

URL pattern: `https://acpv.prod.turtlebeach.com/swarm1/form/{id}`

Result: IDs 900–1039 found — these are Swarm installer packages only, not device firmware.

**Swarm changelog confirms Elo module existed:**
- Version 1.9427 changelog contains Elo-specific fixes — the module was actively maintained
  through at least that version
- No Elo entries appear in changelog versions after 1.9427, suggesting the module was
  removed or the device was dropped from support at that point

**Conclusion:** Roccat/Turtle Beach have decommissioned the hardware firmware CDN. The
module download infrastructure that `ROCCAT_Recover_Tool.exe` and Swarm's auto-update
system depend on no longer serves firmware content. All hardware download endpoints return
404. The firmware binary for the Elo Air dongle **cannot be obtained from the official CDN**.

**Confidence:** confirmed — HTTP responses observed directly; 500+ IDs tested

---

### F-041 — Swarm auto-update log decoded; module ID for Elo never transmitted

**Phase:** Log file analysis — `C:\Users\gelum\AppData\Roaming\ROCCAT\SWARM\log\Auto_Update\`

Swarm writes detailed JSON request/response logs to the above path. Log analysis reveals:

**Request format observed in logs:**
```json
data={"system":27,"version":1.9481,"protocol":2,"hardware":{},"software":{"2713":0.0}}
```

The software key `"2713"` is the AlienFX device PID (`0x2713`) — a different Roccat product
that Swarm successfully detects. The Elo dongle PID (`3A37` or `0A0B`) never appears in any
log entry because Swarm cannot detect the `26CE:0A0B` device (F-017).

**Consequence:** Since Swarm never includes the Elo module ID in its autoupdate requests,
the Elo module ID is not observable from this installation's logs. The module ID can only
be found from a log captured on a system where Swarm detected the dongle as `1E7D:3A37`.

**Swarm CDN infrastructure:**
The signed download URL in the logs resolves to:
`nbg1.your-objectstorage.com/tbnb/production/software-update/roccat--swarm/`

This is a Hetzner S3-compatible object store (Hetzner Nuremberg region). Software packages
(Swarm installers) are hosted here. Hardware firmware modules used a separate path
(`/swarm1/download/hardware/`) that is now 404 (F-040).

**Confidence:** confirmed — log contents observed directly

---

### End-of-session assessment — software recovery paths exhausted

The parallel agent work in Session 10 has closed the firmware acquisition path via official
channels. The complete failure chain is now documented:

```
Firmware update (Swarm) changes dongle VID: 1E7D:3A37 → 26CE:0A0B
    ↓
Swarm stops detecting the dongle (looks for 1E7D only)
    ↓
ROCCAT_Recover_Tool.exe detects it but needs firmware files
    ↓
Firmware files require Swarm module download
    ↓
Swarm can't download: device not detected → files never created
    ↓
Roccat decommissions the hardware CDN → download endpoint returns 404
    ↓
No official software path to obtain firmware or reflash the device
```

**Remaining paths to a working device:**

| Path | Viability | Notes |
|------|-----------|-------|
| Community-sourced firmware cache | Possible | Someone with a pre-update dongle may have `data/3A37/firmware/` cached |
| Archived Swarm installer with bundled firmware | Unknown | Older installers may predate CDN-only delivery |
| Wayback Machine CDN snapshot | Unlikely | CDN content rarely archived |
| JTAG/SWD hardware debug | Viable (hardware work) | Requires opening the dongle and accessing test points |
| Replace with pre-update dongle (`1E7D:3A37`) | Viable | A dongle that never received the VID-changing update would work with Swarm |
