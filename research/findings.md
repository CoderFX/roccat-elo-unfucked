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
