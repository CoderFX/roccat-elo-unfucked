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

**Status:** open — CRITICAL; second crash confirmed (F-022)
**Priority:** CRITICAL — blocks all protocol RE work
**Related findings:** F-005, F-012, F-013, F-014, F-018, F-022

**Detail:** The dongle has now crashed twice under HID command probing (F-013: 256-command
storm; F-022: ~8 commands at 500 ms spacing). Each time it drops off USB enumeration.
`ROCCAT_Recover_Tool.exe` can detect it but cannot proceed because the required firmware
files do not exist on disk — Swarm would normally download them, but Swarm cannot see this
device (F-017, F-018). The circular failure documented in F-018 applies here.

**Updated recovery steps (in order):**

1. **Extended power-off:** Unplug for 30+ seconds to allow capacitors to discharge; then
   try a different USB root hub/controller
2. **Manually supply firmware files to recovery tool:** Obtain `firmware_upgrade.ini` and
   the firmware binary (see Q-010) and place them in the `firmware/` subdirectory adjacent
   to `ROCCAT_Recover_Tool.exe`; relaunch the tool with the dongle connected
3. **Firmware reflash via DFU:** If the Realtek or PIC32 chip (F-019) exposes a DFU
   interface while in fault state, attempt direct reflash via libusb
4. **Replace dongle:** If all recovery attempts fail, acquire a replacement unit; capture a
   USB traffic baseline via USBPcap before any further probing on the replacement

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

**Status:** open
**Priority:** HIGH — needed for Q-008 dongle recovery and for binary analysis
**Related findings:** F-014, F-017, F-018, F-019

**Detail:** `ROCCAT_Recover_Tool.exe` can see the dongle (F-018) but stalls because
`firmware_upgrade.ini` and the firmware binary are absent. If we can obtain those files, the
recovery tool may be able to reflash the dongle.

**Candidate acquisition methods:**

1. **Swarm CDN direct download:** `firmware_upgrade.dll` contains strings referencing the
   CDN URL pattern for module downloads. Static analysis of this DLL may reveal the URL
   template (e.g., `https://update.roccat.com/firmware/<PID>/FW_V<ver>.bin`). If the
   pattern uses the original PID (`3A37`), the Elo module may be downloadable directly.

2. **Cached install on another machine:** Any system where Swarm successfully detected the
   dongle before the firmware update (when it still presented as `1E7D:3A37`) would have
   the firmware binary cached in `data/3A37/firmware/`. Acquiring these files from community
   sources (Roccat forums, Reddit) is a viable path.

3. **Wayback Machine / archived installers:** Older Swarm versions may have bundled the
   firmware or may have had the original PID in their device scanner, making them able to
   enumerate `26CE:0A0B` if that VID was introduced by an older Swarm version.

4. **Static analysis of `firmware_upgrade.dll`:** Strings in the DLL may reveal enough of
   the INI file format and firmware binary layout to construct `firmware_upgrade.ini`
   manually, even without the actual firmware blob.

**How to resolve:**
- Strings-dump `firmware_upgrade.dll` for URL patterns and INI schema
- Search Roccat community forums for cached `data/3A37/firmware/` directory contents
- Check if any archived Swarm installers bundle the firmware blob

---

## Q-011 — What does the dongle actually send back? (Raw response capture)

**Status:** open
**Priority:** HIGH — this is now the primary live-traffic RE path
**Related findings:** F-004, F-021, F-022

**Detail:** F-021 confirmed that the dongle sends a response on EP `0x8A` after every HID
command, but hidapi's `hid_read()` fails to parse it. The raw bytes contain information that
could reveal the protocol structure. We have never actually seen these bytes.

**The problem with hidapi:** hidapi's Windows backend uses `ReadFile()` internally but wraps
it in report-ID validation logic. When the response does not match the expected report format,
hidapi returns an error without surfacing the raw bytes to the caller.

**Two approaches to capture raw responses:**

**Option A — Windows `ReadFile()` directly:**
```python
import ctypes, ctypes.wintypes
# Open device with CreateFile (not via hidapi)
# Call ReadFile() on the handle
# Returns raw interrupt endpoint bytes without any HID parsing
```
This stays within the Windows HID driver stack but skips hidapi's validation layer.

**Option B — libusb `libusb_interrupt_transfer()` on EP `0x8A`:**
```python
import usb.core
dev = usb.core.find(idVendor=0x26CE, idProduct=0x0A0B)
dev.detach_kernel_driver(6)  # detach HidUsb
data = dev.read(0x8A, 64, timeout=1000)
```
This completely bypasses the Windows HID stack. Requires detaching `HidUsb` from Interface
6 first. Gives raw USB frame bytes.

**Operational constraint:** F-022 confirmed the dongle crashes after ~8 unrecognized
commands. Any raw capture session must be designed to stay well under that limit — ideally
1–2 commands per session until crash threshold is better characterized. Consider:
- Fully power-cycle the dongle between probe sessions
- Log the exact response bytes before any subsequent commands
- Prioritize the zeroed-query command `[0x06, 0x00]` as the first probe (least likely to
  trigger an error state)

---

## Resolved / Out-of-Scope Questions

| ID    | Question (short)                                         | Resolution date | Finding |
|-------|----------------------------------------------------------|-----------------|---------|
| Q-001 | Is `26CE:0A0B` the Roccat dongle?                        | 2026-04-17      | F-010   |
| Q-005 | What do `0xA0`–`0xAA` opcodes on `26CE:01A2` control?   | 2026-04-17 (OOS)| F-010   |

---

## Revision History

| Date       | Change                                                                                    |
|------------|-------------------------------------------------------------------------------------------|
| 2026-04-17 | Initial question list from session 1                                                      |
| 2026-04-17 | Added Q-007 (firmware version query); expanded Q-003 with libusb ctrl_transfer approach   |
| 2026-04-17 | Q-001 RESOLVED via unplug test (F-010); Q-005 marked out of scope; Q-003 elevated to CRITICAL; Q-006 elevated to Medium; Q-002 revised to reflect confirmed dongle identity |
| 2026-04-17 | Session 3: Q-008 added (CRITICAL — dongle recovery); Q-009 added (HIGH — Swarm protocol capture); Q-003 updated with F-016 context (must test with active headset connection); Q-004 downgraded to Low with revised beep hypothesis |
| 2026-04-17 | Session 4: Q-008 updated (second crash confirmed F-022; recovery steps revised for F-018 circular dependency); Q-009 CLOSED (Swarm cannot detect 26CE:0A0B per F-017); Q-010 added (firmware binary acquisition); Q-011 added (raw response capture via ReadFile/libusb) |
