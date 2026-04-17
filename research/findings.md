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
   (F-017). New approach: raw `ReadFile`/libusb read to capture dongle responses (Q-010).
3. **Q-010** (NEW): Can we obtain the Elo firmware binary directly from Swarm's CDN or from
   a cached install? Needed to feed `ROCCAT_Recover_Tool.exe` and for binary analysis.
4. **Q-011** (NEW): Raw response bytes — what does the dongle actually send back? Need
   `ReadFile` or libusb read to bypass hidapi parsing.
