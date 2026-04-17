# Open Questions — Roccat Elo Wireless Headset

Questions numbered for cross-reference with findings.md. Status: **open** / **resolved** / **blocked**.

---

## Q-001 — Is `26CE:0A0B` the headset dongle or motherboard onboard audio?

**Status:** RESOLVED — 2026-04-17
**Priority:** ~~CRITICAL~~ (resolved)
**Related findings:** F-001, F-009, F-010

**Resolution:** Unplug test performed. `26CE:0A0B` disappeared when the Roccat dongle was
unplugged. `26CE:01A2` ("LED Controller") remained — it is a **separate, non-headset device**
(motherboard LED controller or similar peripheral).

**Confirmed facts:**
- `26CE:0A0B` = Roccat Elo wireless headset dongle
- `26CE:01A2` = unrelated motherboard/peripheral device; **out of scope for this investigation**
- The two `26CE` devices do NOT belong to the same product despite sharing a VID

**Impact:** All LED controller probe data (F-006, Q-005) is out of scope. The headset
dongle is confirmed as the sole target for protocol RE.

---

## Q-002 — What hardware revision / SKU is this headset, and why does it use VID `0x26CE`?

**Status:** open
**Priority:** Medium (was High; partially answered by F-010/F-011)
**Related findings:** F-001, F-007, F-010, F-011

**Detail:** The dongle is confirmed as Roccat Elo (`26CE:0A0B`), but VID `0x1E7D` (ROCCAT GmbH)
is absent. The most likely explanation is a hardware revision using Realtek USB audio silicon
where Realtek's VID (`26CE`) is used rather than Roccat's. This is consistent with the custom
driver `RtkUsbAD_2395` and the USB Audio Class 2.0 implementation.

Remaining sub-questions:
- Which specific Elo model is this? (Elo 7.1 Air gen 2? Elo X Stereo? Elo Air?)
- Was `0x26CE` adopted in a specific firmware/hardware revision, or is it a new product line?
- Is the HID protocol a vendor extension on top of UAC2, or completely proprietary?

**How to resolve:**
- Check model number printed on headset, dongle, or packaging
- Search HeadsetControl GitHub issues for `26CE:0A0B`
- Retrieve USB string descriptors: `device.product`, `device.manufacturer`, `device.serial_number`
  via pyusb — may identify model name or revision string
- Query firmware version (see Q-007)

---

## Q-003 — What is the correct command format for `26CE:0A0B`?

**Status:** open — secondary blocker (blocked on Q-008 dongle recovery first)
**Priority:** CRITICAL — primary blocker for protocol RE once dongle is recovered
**Related findings:** F-004, F-011, F-016

**Detail:** The HID output report for Interface 6 is only **2 bytes** total (1 report ID + 1 byte
payload). The reference `0x1E7D` protocol sends 64-byte command packets. Since the protocol must
be RE'd from scratch (F-011), the command mechanism is completely unknown. Options:

1. Commands are sent as **USB control transfers** (HID Set_Report, `bmRequestType=0x21`) at the
   USB layer, bypassing the Windows HID report-size restriction and allowing arbitrary payload
   sizes — this is the most promising avenue given the 2-byte output report constraint
2. The HID output report's single byte is a **trigger/selector** that causes the dongle to emit
   a specific pre-programmed response on the IN endpoint
3. Commands use a **different interface** entirely — possibly EP `0x89` on the Audio Control
   interface, sent as UAC2 control requests
4. The protocol uses only the **HID IN endpoint** passively (dongle pushes state) and settings
   are configured exclusively via USB control transfers out-of-band from the HID stack

**Updated context (2026-04-17, F-016):** The HID interface was likely inactive during prior
probing because no headset was actively paired/connected to the dongle. Future testing of the
command format MUST be done with a confirmed active headset connection — otherwise it is
impossible to distinguish "wrong command format" from "no headset connected." This changes
the approach: confirm headset pairing state before attempting any command probe.

**How to resolve (priority order):**
1. **Recover dongle first (Q-008)** — all command testing is blocked until dongle enumerates
2. USB traffic capture: Install Roccat Swarm (see Q-009) and capture ALL USB traffic via
   USBPcap/Wireshark during headset pairing, battery check, and LED configuration
3. With active headset connection confirmed: try `usb.ctrl_transfer(0x21, 0x09, 0x0306, 6,
   payload)` via libusb with 64-byte payloads mirroring the reference protocol trigger
   `[0x06, 0xFF, 0x01, 0x00, ...]`
4. Try `usb.ctrl_transfer(0x21, 0x09, 0x0306, 6, [0x06, 0x00, ...])` (all-zero query) and
   log any IN endpoint response

---

## Q-004 — What is causing the periodic beeping?

**Status:** open (revised interpretation — 2026-04-17)
**Priority:** Low (downgraded from Medium)
**Related findings:** F-008, F-015

**Detail:** Headset produced regular beep tones during the investigation session. Original
hypothesis was low battery. However, F-015 establishes that the headset was new and almost
unused, making critically low battery unlikely. Revised most-probable cause: the headset was
signaling a connection/pairing failure because the dongle's HID interface was in an inactive
state during probing (F-016) — the headset could not establish or maintain its wireless link
with the dongle and was beeping to alert the user.

**How to resolve:**
1. Confirm headset charges to full (charging confirmed at 5V, ~400–440 mA per F-015)
2. Attempt normal pairing with the dongle once dongle is recovered (Q-008)
3. If beeping stops after successful pairing, confirm connection-failure hypothesis

---

## Q-005 — What do opcodes `0xA0`–`0xAA` on `26CE:01A2` control?

**Status:** OUT OF SCOPE — 2026-04-17
**Priority:** N/A
**Related findings:** F-006, F-010

**Resolution:** `26CE:01A2` was confirmed by the unplug test (F-010) to be a separate device
unrelated to the Roccat Elo headset (it remained enumerated after the dongle was unplugged).
This device is a motherboard peripheral. Its protocol is outside the scope of this investigation.

Probe data from F-006 is retained for reference but requires no further action.

---

## Q-006 — Does Audio Control endpoint `0x89` carry headset state events?

**Status:** open
**Priority:** Medium (elevated from Low — now critical path for protocol RE given scope of F-011)
**Related findings:** F-003, F-011

**Detail:** EP `0x89` on Interface 0 (Audio Control) is an interrupt IN endpoint. In UAC2, this
carries status change notifications. May also carry headset-specific events (power, pairing,
connection state).

**How to resolve:**
- Listen on `0x89` via pyusb while performing physical actions (mute button press, volume
  wheel turn, headset power on/off, dongle unplug)
- Log any packets and compare against UAC2 status change notification format

---

## Q-007 — Does the 26CE:0A0B dongle support firmware version query?

**Status:** open
**Priority:** Low

**Detail:** Many USB HID peripherals expose a firmware version via a feature report or a specific
query command. If present on this device, the version string would help identify the hardware
revision and whether it is related to any known Roccat firmware lineage.

**How to resolve:**
- Try `HidD_GetProductString`, `HidD_GetSerialNumberString` via Windows HID API
- Try pyusb `device.serial_number` and `device.product`
- Send `[0x06, 0x00, ...]` (report ID 0x06, all zeros) and observe response — some devices
  return firmware version on a zeroed query

---

## Q-008 — Is the dongle permanently damaged, and how do we recover it?

**Status:** open — CRITICAL; new failure mode observed (F-027): USB stack not initializing
**Priority:** CRITICAL — blocks all further work
**Related findings:** F-005, F-012, F-013, F-014, F-018, F-022, F-026, F-027, F-028

**Detail:** The dongle has entered a new, deeper failure mode (F-027): the LED lights on
plug-in (MCU is running) but the device does not enumerate on USB at all — not as app mode,
not as DFU bootloader. Prior DFU timeout states still produced USB enumeration; this does
not. The application firmware appears corrupted to the point where USB initialization is
never reached.

**Current recovery attempt:** Physical button held during plug-in (F-028) — testing whether
the button triggers a hardware ROM-level boot mode select, which would bypass the corrupted
application firmware entirely and present a fresh DFU or UART recovery interface.

**Recovery steps in priority order:**

1. **Hardware button + plug-in (F-028, in progress):** Hold the dongle's physical button
   while plugging in. Watch for any new USB device appearing — including previously unseen
   VID:PIDs. If successful, enumerate the recovery device and proceed with firmware reflash.
2. **CDN firmware + recovery tool (Q-010):** If button method fails, obtain the Elo firmware
   binary via CDN enumeration or community sourcing. Supply to `ROCCAT_Recover_Tool.exe`
   manually. This requires USB enumeration to be working — step 1 may be prerequisite.
3. **Replace dongle:** Acquire a replacement unit. Before any HID probing on the replacement,
   capture a full USBPcap baseline with the headset paired and connected — this documents
   normal DFU entry and app-mode traffic before any probe commands are sent.

---

## Q-009 — Swarm USB traffic capture approach: CLOSED; what is the alternative?

**Status:** CLOSED as originally scoped — 2026-04-17
**Priority:** N/A (approach abandoned; see Q-011 for replacement approach)
**Related findings:** F-011, F-014, F-016, F-017

**Resolution:** Swarm v1.9481 does not detect `26CE:0A0B` (F-017). The USB traffic capture
approach via Swarm + USBPcap cannot be executed — Swarm will never open the HID device.

The approach of capturing Swarm's traffic is definitively blocked by the VID:PID mismatch.
Swarm looks for `1E7D:3A37`; the dongle presents as `26CE:0A0B` after firmware update. There
is no configuration change or override that makes Swarm enumerate the current hardware.

**Alternative approach (Q-011):** Read dongle responses directly via `ReadFile()` or
`libusb_interrupt_transfer()` on EP `0x8A`, bypassing hidapi's parsing layer. F-021
confirmed the dongle sends response bytes on every command — we just cannot see them through
hidapi. This is now the primary live-traffic RE path.

**Retained value from original Q-009 work:**
- `firmware_upgrade.dll` PIC32 flash protocol strings (F-019)
- `HIDDLL.dll` identified as the HID layer Swarm uses (could be reverse-engineered statically)
- Recovery tool circular dependency documented (F-018)

---

## Q-010 — Can we obtain the Elo firmware binary directly, bypassing Swarm's device detection?

**Status:** open — CDN URL pattern confirmed; module ID is the missing piece (F-024)
**Priority:** HIGH — needed for Q-008 dongle recovery and for binary analysis
**Related findings:** F-014, F-017, F-018, F-019, F-023, F-024

**Detail:** `ROCCAT_Recover_Tool.exe` can see the dongle (F-018) but stalls because
`firmware_upgrade.ini` and the firmware binary are absent. The CDN URL pattern is now known
(F-024): `https://acpv.prod.turtlebeach.com/swarm1/form/<module_id>`. The Elo module ID
must be resolved — it is an integer key from Swarm's `version.ini`, not the PID directly.

Swarm II is confirmed as a dead end (F-023) — it carries only Turtle Beach device modules.

**Candidate acquisition methods (updated):**

1. **Enumerate CDN module IDs:** The `version.ini` section numbers appear to be small
   integers. Iterating a plausible range (e.g., 1–200) against the CDN endpoint and
   inspecting responses for Elo-related content may locate the module without needing a
   `version.ini` that lists the Elo device.

2. **Extract module ID from a Swarm install that detected `1E7D:3A37`:** Any system where
   Swarm enumerated the dongle under its original VID:PID would have the Elo module ID in
   `version.ini` and the firmware binary cached in `data/3A37/firmware/`. Community sourcing
   (Roccat forums, Reddit) is viable.

3. **Static analysis of `firmware_upgrade.dll` for INI schema:** The DLL may contain enough
   format strings to reconstruct a valid `firmware_upgrade.ini` manually. Combined with the
   firmware binary from method 1 or 2, this would feed the recovery tool.

4. **Wayback Machine / archived Swarm installers:** Older installers may bundle firmware or
   carry a `version.ini` that includes the Elo module ID.

**How to resolve:**
- Attempt CDN enumeration: iterate `https://acpv.prod.turtlebeach.com/swarm1/form/N`
  for N in 1–200; inspect HTTP responses for firmware binary signatures
- Search Roccat community for `data/3A37/firmware/` cache contents
- Strings-dump `firmware_upgrade.dll` for INI format schema

---

## Q-011 — Identify the bootloader-mode VID:PID and enumerate the DFU device

**Status:** open — approach completely reframed by F-026
**Priority:** CRITICAL — this is the direct path to firmware access and protocol RE
**Related findings:** F-004, F-021, F-022, F-025, F-026

**Reframe (F-026):** OVERLAPPED I/O is no longer the goal. The dongle is not crashing —
it is entering DFU/bootloader mode in response to report ID `0x06` output reports
(confirmed from `firmware_upgrade.dll` strings). After the drop, it re-enumerates as a
**different USB device** in bootloader mode. We have never scanned for this device.

**What we need to do:**

1. Send one `WriteFile(report_id=0x06)` to trigger DFU mode entry
2. Immediately and repeatedly call `Get-PnpDevice` (or `usb.core.find()`) to detect any
   new VID:PID that appears on the bus
3. Log the bootloader device's full descriptor (VID, PID, bcdDevice, product string,
   interface layout)
4. Once identified, enumerate all HID interfaces on the bootloader device

**Candidate bootloader VID:PIDs to watch for:**

| Candidate | Rationale |
|-----------|-----------|
| `04D8:xxxx` | Microchip VID — PIC32 USB bootloader uses this |
| `26CE:0A0B` | Same VID:PID but different bcdDevice revision or interface count |
| `26CE:xxxx` | Different PID under same Realtek/ASRock VID |
| Realtek DFU VID | If Realtek chip handles USB in bootloader mode |

**Scan procedure:**

```python
import usb.core, time

# Baseline — enumerate all devices before trigger
before = {(d.idVendor, d.idProduct) for d in usb.core.find(find_all=True)}

# Trigger DFU entry (via WriteFile or hidapi write)
# ... send report ID 0x06 ...

# Poll for new device
deadline = time.time() + 10.0  # 10-second window
while time.time() < deadline:
    after = {(d.idVendor, d.idProduct) for d in usb.core.find(find_all=True)}
    new_devices = after - before
    if new_devices:
        print("Bootloader device appeared:", new_devices)
        break
    time.sleep(0.1)
```

**What a successful result unlocks:**
- Full DFU flashing path via `Dongle_DFU.dll` protocol (once identified)
- Firmware binary read-back (if DFU implementation supports readback)
- Firmware recovery without needing Swarm (unblocks Q-008 cleanly)
- Potential access to app-mode command protocol via DFU memory readback

**PowerShell alternative for scanning (no Python required):**
```powershell
$before = Get-PnpDevice -PresentOnly | Select-Object InstanceId
# ... trigger DFU ...
Start-Sleep -Seconds 2
$after = Get-PnpDevice -PresentOnly | Select-Object InstanceId
Compare-Object $before $after
```

---

## Resolved / Out-of-Scope Questions

| ID    | Question (short)                                         | Resolution date | Finding |
|-------|----------------------------------------------------------|-----------------|---------|
| Q-001 | Is `26CE:0A0B` the Roccat dongle?                        | 2026-04-17      | F-010   |
| Q-005 | What do `0xA0`–`0xAA` opcodes on `26CE:01A2` control?   | 2026-04-17 (OOS)| F-010   |
| Q-009 | Swarm USB traffic capture — viable approach?             | 2026-04-17 (CLOSED) | F-017 |

---

## Revision History

| Date       | Change                                                                                    |
|------------|-------------------------------------------------------------------------------------------|
| 2026-04-17 | Initial question list from session 1                                                      |
| 2026-04-17 | Added Q-007 (firmware version query); expanded Q-003 with libusb ctrl_transfer approach   |
| 2026-04-17 | Q-001 RESOLVED via unplug test (F-010); Q-005 marked out of scope; Q-003 elevated to CRITICAL; Q-006 elevated to Medium; Q-002 revised to reflect confirmed dongle identity |
| 2026-04-17 | Session 3: Q-008 added (CRITICAL — dongle recovery); Q-009 added (HIGH — Swarm protocol capture); Q-003 updated with F-016 context (must test with active headset connection); Q-004 downgraded to Low with revised beep hypothesis |
| 2026-04-17 | Session 4: Q-008 updated (second crash confirmed F-022; recovery steps revised for F-018 circular dependency); Q-009 CLOSED (Swarm cannot detect 26CE:0A0B per F-017); Q-010 added (firmware binary acquisition); Q-011 added (raw response capture via ReadFile/libusb) |
| 2026-04-17 | Session 5: Q-010 updated with confirmed CDN URL pattern (F-024) and Swarm II dead-end (F-023); Q-011 updated with OVERLAPPED I/O approach and revised crash model (F-025: single output report crashes firmware); Q-009 added to resolved table |
| 2026-04-17 | Session 6: Q-011 completely reframed — OVERLAPPED I/O abandoned; goal is now bootloader VID:PID identification after DFU mode entry (F-026); DFU scan procedure documented |
| 2026-04-17 | Session 7: Q-008 updated — new failure mode (F-027: USB stack not initializing); hardware button recovery attempt (F-028) added as priority 1 step |
