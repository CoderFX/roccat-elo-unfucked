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

**Status:** open
**Priority:** CRITICAL — blocks ALL further protocol RE work
**Related findings:** F-005, F-012, F-013, F-014

**Detail:** After a 256-command write storm (all bytes `0x00`–`0xFF`, no inter-command delay),
the dongle entered a fault state and stopped enumerating. It is physically plugged in but
Windows reports `CM_PROB_PHANTOM` (device node cached but hardware not responding to USB
enumeration). It did not recover on replug to a different USB port.

This is consistent with the known population-level reliability defect (F-012) where the
Realtek firmware enters a bad state that survives brief power cycles.

**Recovery steps (in order):**

1. **Extended power-off:** Unplug for 30+ seconds to allow internal capacitors to fully
   discharge, forcing a true power-on reset of the Realtek chip firmware
2. **Try a different USB controller:** Use a USB port on a different root hub (e.g., rear
   motherboard ports vs. front panel, or a PCIe USB card) in case the issue is host-side
3. **Roccat Swarm recovery tool:** Install Roccat Swarm; use `ROCCAT_RECOVER_TOOL.exe`.
   Procedure: connect headset first, then plug dongle — tool should detect the pair and
   reflash firmware (see F-014)
4. **Firmware reflash via DFU (if supported):** If Realtek USB audio chips expose a DFU
   interface in fault mode, attempt reflash via libusb
5. **Declare loss:** If all recovery attempts fail, dongle is bricked and a replacement is
   required before investigation can continue

**Time sensitivity:** If the dongle is in a recoverable state, it may only remain recoverable
for a limited window before NVRAM or flash is corrupted.

---

## Q-009 — Should we install Roccat Swarm to capture the protocol via USB traffic sniffing?

**Status:** open
**Priority:** HIGH — most efficient path to protocol documentation
**Related findings:** F-011, F-014, F-016
**Blocked on:** Q-008 (need a working dongle)

**Detail:** Roccat Swarm companion software communicates with the dongle over the same HID
interface we are trying to reverse engineer. By installing Swarm and capturing its USB traffic
with USBPcap + Wireshark, we would get the complete command/response protocol with accurate
field values — potentially eliminating the need for blind brute-force probing.

**Advantages over blind RE:**
- Complete command sequences for known features (battery query, LED, inactive timeout)
- Correct initialization sequence — confirms or denies hypothesis from F-016 that Swarm
  performs a startup handshake before the HID interface becomes active
- Full protocol traffic for pairing events, headset state changes, button presses

**Concerns:**
- Requires a working dongle (Q-008 must be resolved first)
- Swarm may use encrypted or obfuscated HID payloads (unlikely for simple HID, but possible)
- Swarm may behave differently on `26CE:0A0B` vs. the `0x1E7D`/`0x3A37` it was originally
  designed for (see note in F-014 that Swarm's firmware path uses `3A37` PID)

**How to proceed:**
1. Recover dongle (Q-008)
2. Ensure headset pairs successfully with recovered dongle
3. Install Roccat Swarm (or Roccat NEON)
4. Install USBPcap filter on the dongle's USB port
5. Start Wireshark capture; launch Swarm; perform: initial launch, battery check, LED
   configuration, inactive timeout change
6. Export capture and analyze URB_BULK/URB_INTERRUPT frames on the HID interface

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
