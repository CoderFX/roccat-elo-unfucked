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

**Status:** RESOLVED — 2026-04-17
**Priority:** ~~CRITICAL~~ (resolved)
**Related findings:** F-005, F-012, F-013, F-014, F-018, F-022, F-026, F-027, F-028, F-029

**Resolution:** Button-hold on plug-in reliably recovers the dongle from any observed crash
state, including the deep F-027 failure where USB would not enumerate at all (F-029).

**Recovery procedure (confirmed, repeatable):**
1. Unplug the dongle
2. Hold the physical button on the dongle body
3. Plug in USB while still holding the button
4. LED changes to blinking red — device is fully enumerated as `26CE:0A0B`

This procedure works from all observed failure states. Extended power-off is no longer
required. The button recovery is the definitive, hardware-level recovery method.

**Remaining open question:** Whether the button puts the dongle into a true ROM bootloader
(bypassing application flash) or simply forces a clean MCU reset. This is not critical for
recovery purposes but is relevant to Q-010 (firmware binary acquisition via readback).
See Q-012 for the next blocker: establishing a working RF link.

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

**Status:** CLOSED (official CDN paths) — 2026-04-18; community sourcing still possible
**Priority:** HIGH for community/hardware paths; official CDN path is dead
**Related findings:** F-014, F-017, F-018, F-019, F-023, F-024, F-037, F-040, F-041

**Official CDN result (F-040):** The hardware firmware CDN is decommissioned. The endpoint
`/swarm1/download/hardware/2/{id}` returns 404 for all IDs 1–500+. The autoupdate API
returns `{"hardware": null, "software": null}` for every device. The Elo module ID is never
transmitted in Swarm logs on this system because Swarm never detects `26CE:0A0B` (F-041).
The DFU PID is now known (`1E7D:3A36` per F-037) but irrelevant — the dongle no longer
presents under VID `0x1E7D` at all.

**Remaining acquisition paths (non-CDN):**

1. **Community-sourced firmware cache:** Any user whose dongle received the VID-changing
   firmware update while running Swarm would have `data/3A37/firmware/` cached locally
   before the update completed. Sourcing from Roccat forums, Reddit, or Discord is viable.
   The firmware binary and `firmware_upgrade.ini` are the target files.

2. **Archived Swarm installer:** Swarm versions prior to the CDN-only delivery model may
   have bundled device firmware in the NSIS installer. The Swarm changelog notes Elo fixes
   through v1.9427 — installers from that era are worth examining.

3. **JTAG/SWD firmware readback:** If the dongle is opened and debug pins are accessible,
   a PIC32 debugger (PICkit, or SWD if nRF handles USB) can read back the flash contents.
   This bypasses all software paths entirely and yields the binary directly.

4. **Replace with pre-update dongle:** Acquiring a second-hand dongle that never received
   the VID-changing update (still presents as `1E7D:3A37`) would allow Swarm to detect and
   update it normally.

---

## Q-011 — Identify the bootloader-mode VID:PID and enumerate the DFU device

**Status:** CLOSED — 2026-04-17; DFU is radio-based, no USB bootloader exists
**Priority:** N/A
**Related findings:** F-004, F-021, F-022, F-025, F-026, F-032

**Resolution:** F-032 (dfu_probe.py) confirmed that no USB device appears after a DFU
trigger command, even after a 30-second scan with HID enumeration, libusb, Device Manager,
and `devcon rescan`. There is no USB bootloader. The DFU firmware update path operates
entirely over the 2.4 GHz radio link — the `firmware_upgrade.dll` strings about "Enum
bootloader mode device" refer to wireless re-enumeration, not USB.

The USB DFU scan approach is closed. The DFU mechanism is not accessible from the host PC
over USB. Firmware updates require an active wireless link between dongle and headset with
Swarm acting as the bridge.

---

## Q-012 — Why is RF pairing failing, and how do we establish a headset connection?

**Status:** open — reduced priority; vendor control transfer channel established (F-045/F-046)
**Priority:** MEDIUM — no longer the primary blocker; flash write protocol RE (Q-013) is now the critical path
**Related findings:** F-016, F-020, F-029, F-030, F-031, F-033, F-034, F-036, F-045, F-046, F-047

**Update (Session 11 — 2026-04-19):** The WinUSB breakthrough (F-045) and working vendor
control transfer channel (F-046) have fundamentally changed the investigation's dependency
on RF pairing. The host can now communicate bidirectionally with the dongle's Realtek 8051
MCU without a wireless link. Flash content is readable via `bReq=0x26` (confirmed producing
8051 opcodes, F-047). RF pairing is still desirable for HID command format RE (Q-003) and
operational protocol documentation, but it is no longer the gate for firmware analysis.

**Remaining detail:** The headset and dongle will not pair in any tested configuration.
F-033 confirms red-blink mode intentionally disables the HID output endpoint. HID Interface 6
is silent without an established RF link.

Additional constraints confirmed in Session 9:
- Headset USB-C is charge-only — no data path, no headset-side firmware update possible
  over USB (F-034)
- Headset has no button-hold recovery equivalent — no independent headset recovery method
  exists (F-036)
- DFU is radio-based — there is no USB DFU path to reflash the dongle RF stack (F-032,
  Q-011 closed)

**Candidate causes:**

1. **Wrong pairing mode on dongle:** Red-blink mode may be a firmware recovery/wireless
   scan state rather than the standard user-facing pairing mode. The solid-white app mode
   with a brief button press (pink/magenta state, F-030) may be the correct entry point for
   normal pairing.

2. **Lost pairing bond:** Factory-paired devices store the bond in flash. DFU mode cycling
   or firmware corruption may have cleared the dongle's pairing table. The headset still
   has the old bond and the dongle does not recognise the headset's address.

3. **Broken nRF radio stack in current firmware:** The firmware version running on the
   dongle may have a broken RF subsystem — the same corruption that caused the F-027 USB
   non-init state could affect the nRF5x radio initialisation.

4. **Headset auto-shutdown too fast:** Headset powered off before the pairing handshake
   completed. Keep headset on charge during pairing attempts to prevent shutdown.

**How to resolve (priority order):**

1. **Try app mode + button press:** Plug dongle normally (solid white LED), immediately
   put headset into pairing mode, then short-press the dongle button to enter pink/magenta
   state. This is the most likely correct pairing flow.
2. **Keep headset charged during test:** Use USB power during pairing attempts to prevent
   auto-shutdown cutting the window short.
3. **Research factory re-pair procedure:** Search for Roccat Elo Air pairing reset — some
   devices support holding headset power button for 10+ seconds to clear bond and
   re-advertise to any dongle.
4. **Firmware reflash:** With the vendor write protocol mapped (Q-013), reflashing the
   dongle RF stack directly via the USB control pipe is now a viable path — no longer
   dependent on Swarm or CDN.

---

---

## Q-013 — What are the vendor OUT request opcodes for flash erase, write-page, and verify?

**Status:** open
**Priority:** CRITICAL — primary blocker for firmware reflash and HID protocol RE
**Related findings:** F-039, F-045, F-046, F-047

**Detail:** The vendor control transfer channel is fully established (F-046). Flash read
is confirmed working via `bReq=0x26` (and likely `0x2E`). The readback produces valid 8051
opcodes (F-047). What remains unknown is the write side of the flash protocol: which
`bReq` values trigger flash erase, write-page, and verify operations on the Realtek 8051.

**Known read opcodes (confirmed):**

| bReq  | Direction | Purpose                                  | Confidence    |
|-------|-----------|------------------------------------------|---------------|
| `0x07`| IN        | Descriptor string query (wVal=2→date, wVal=3→"REALSIL\0") | confirmed |
| `0x26`| IN        | Flash content readback — produces 8051 opcodes | confirmed |
| `0x2E`| IN        | Likely flash read (adjacent to `0x26`)   | likely        |
| `0x01`| IN        | DFU UPLOAD equivalent — response observed| likely        |

**Write opcode candidates:**

1. **Adjacent opcodes (`0x27`, `0x2F`, `0x28`):** Realtek typically pairs read/write at
   adjacent opcode numbers. `0x27` (next after `0x26`) and `0x2F` (next after `0x2E`) are
   the highest-priority candidates for write-page.
2. **USB DFU DNLOAD (`bReq=4`):** Standard USB DFU uses request 4 (DNLOAD) for write and
   request 1 (UPLOAD) for read. If the vendor layer wraps the standard DFU protocol on the
   control pipe, `bReq=4` with `bmRequestType=0x41` (OUT|VENDOR|INTERFACE) may be the
   write trigger.
3. **Erase opcode:** Flash block erase is typically a separate command. Candidates:
   `0x24`, `0x28`, or a wValue-parameterized variant of the read opcode.

**flash packet format (from F-039, `firmware_upgrade.dll`):**
```
520 bytes total:
  Bytes 0–7:   Header (address, length, sequence, flags — exact layout TBD)
  Bytes 8–519: 512-byte data payload
CRC-16 CCITT poly 0x1021 (standard) and 0x8408 (reflected) both present in DLL
```

**How to resolve:**

1. **Enumerate vendor OUT requests systematically:** Send `bmRequestType=0x41` (OUT|VENDOR|
   INTERFACE), `wIndex=6`, `bReq` = `0x24`–`0x30` with a 520-byte zero-filled buffer.
   Observe whether dongle stays alive (safe opcode), produces an IN response, or drops (active write triggered). Start with power-of-two padding to avoid accidental flash corruption.
2. **Differential flash reads:** After each candidate OUT request, immediately read back
   flash via `bReq=0x26` at the same address. Any change in returned bytes confirms a
   write opcode.
3. **Static analysis of `firmware_upgrade.dll`:** The `Neon` protocol handler (report ID
   `0x06`/`0x07` path) and the PIC32 handler both use the 520-byte packet format. Disassemble
   the DLL's flash write path to extract the exact `bReq` values it sends. This is the
   ground truth — the DLL was writing to this hardware successfully before the CDN closed.
4. **Test `bReq=4` (USB DFU DNLOAD):** If the device responds to `bReq=1` as UPLOAD, it
   may implement the full USB DFU class on the vendor control pipe. Standard DFU DNLOAD is
   `bReq=4`, `bmRequestType=0x21` (OUT|CLASS|INTERFACE).

---

## Resolved / Out-of-Scope Questions

| ID    | Question (short)                                         | Resolution date | Finding |
|-------|----------------------------------------------------------|-----------------|---------|
| Q-001 | Is `26CE:0A0B` the Roccat dongle?                        | 2026-04-17      | F-010   |
| Q-005 | What do `0xA0`–`0xAA` opcodes on `26CE:01A2` control?   | 2026-04-17 (OOS)| F-010   |
| Q-008 | Is the dongle permanently damaged / how to recover?      | 2026-04-17      | F-029   |
| Q-009 | Swarm USB traffic capture — viable approach?             | 2026-04-17 (CLOSED) | F-017 |
| Q-010 | Obtain Elo firmware binary via CDN                       | 2026-04-18 (CDN dead); F-042 community binary obtained | F-040, F-042 |
| Q-011 | Identify bootloader-mode VID:PID / enumerate DFU device  | 2026-04-17 (CLOSED) | F-032 |

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
| 2026-04-17 | Session 8: Q-008 RESOLVED — button-hold recovery confirmed (F-029); Q-012 added (RF pairing failure, new blocker for HID RE) |
| 2026-04-17 | Session 9: Q-011 CLOSED — no USB bootloader exists; DFU is radio-based (F-032); Q-012 updated with F-033/F-034/F-036 constraints; resolution steps revised |
| 2026-04-18 | Session 10: Q-010 official CDN path CLOSED — hardware download endpoint 404 (F-040); DFU PID 0x3A36 confirmed from settings.xml (F-037); community/JTAG paths remain open |
| 2026-04-19 | Session 11: MAJOR BREAKTHROUGH — Q-012 priority downgraded; vendor control transfer channel established (F-045/F-046) means investigation is no longer gated on RF pairing; Q-013 added (flash write protocol RE — new critical blocker); Q-010 resolved table note updated — community firmware obtained (F-042); chip confirmed Realtek 8051, not PIC32 (F-047) |
