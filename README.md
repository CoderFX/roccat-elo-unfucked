# roccat-elo-unfucked

**Community firmware fix and tools for the ROCCAT Elo 7.1 Air wireless dongle. Because Roccat won't.**

## The Problem

You bought a ROCCAT Elo 7.1 Air. It worked. Then Roccat Swarm pushed a firmware update. Now your dongle:

- Disconnects every hour
- Gets hot enough to fry an egg
- Refuses to pair after you turn the headset off and on
- Shows up in Device Manager one minute, vanishes the next
- Beeps at you like a smoke detector with a dying battery

And Roccat's response? Radio silence. For **four years** (2021-2025). Hundreds of users. Same bug. No fix.

So we fixed it ourselves.

## What This Repo Contains

### Phase 1: Fix It (Current)
- Full USB descriptor dump of the broken dongle firmware (`26CE:0A0B`)
- Protocol reverse engineering notes
- Firmware downgrade procedure back to the working original (`1E7D:3A37`)
- Recovery tools that don't require Roccat Swarm

### Phase 2: Custom Tools (Planned)
- Standalone battery monitor (no Swarm needed)
- LED control
- Sidetone adjustment
- Portable `.exe` that works on any PC without Swarm

### Phase 3: Full Hack (Planned)
- Complete firmware dump and analysis
- Custom firmware patches
- Documentation of the Realtek USB Audio 2.0 chip protocol

## The Dongle's Identity Crisis

The original Elo 7.1 Air dongle identified as:
- **VID `0x1E7D`** (ROCCAT GmbH), **PID `0x3A37`**
- Standard 64-byte HID protocol
- Worked fine

After Roccat's firmware update, it became:
- **VID `0x26CE`** (Savitech — the USB audio chip vendor), **PID `0x0A0B`**
- Completely different USB Audio 2.0 protocol
- Vendor HID with Report ID `0x06`, 2-byte output, 64-byte input
- Broken

Yes, Roccat's own firmware update changed the USB Vendor ID. The dongle no longer identifies as a Roccat device. You can't make this up.

## The Full Chain of Incompetence

We reverse-engineered Roccat's own tools. Here's what we found:

1. **Roccat pushed a firmware update** that changed the dongle's VID from their own (`0x1E7D`) to the chip vendor's (`0x26CE` — Savitech). This was **intentional** — the VID is loaded from config at runtime.

2. **Their own software can't detect the updated dongle.** Swarm looks for VID `0x1E7D`. The dongle now reports `0x26CE`. Swarm literally cannot see the device its own update created.

3. **The Recovery Tool is broken by design.** It shows "firmware update required" but the dropdown is frozen because it needs device module files that are only downloaded by Swarm — which can't detect the dongle. Circular failure.

4. **They decommissioned the firmware CDN.** We fully reverse-engineered their update API (`POST /swarm1/autoupdate/ELO_AIR`) — it responds `"successfully"` but returns `null` for all firmware and module downloads. The server is alive but empty. **Even if Swarm could detect your dongle, it can't download the fix.**

5. **The dongle's radio stack is broken too.** We tested every pairing combination (4 different LED modes). The dongle and headset can both enter pairing mode but can't find each other. The firmware corrupted the wireless protocol.

6. **The headset USB port is charge-only.** No data. Can't update firmware through the headset either.

**Result:** A $100 wireless headset turned into a wired paperweight by the company that made it, with every possible recovery path deliberately or negligently destroyed.

## Known Issues With Roccat's Firmware

Source: Community reports from Reddit, forums, and reviews (2021-2025)

| Issue | Frequency | Roccat's Fix |
|-------|-----------|-------------|
| Dongle stops being recognized after ~1 hour | Widespread | None |
| Dongle overheats | Common | None |
| Pairing fails after headset power cycle | Common | None |
| Firmware update bricks dongle | Multiple reports | Recovery tool (doesn't work) |
| Swarm fails to detect dongle | Common | Reinstall Swarm (doesn't help) |
| Firmware CDN decommissioned | Permanent | None — they deleted the fix |

## Hardware Details

Full technical documentation in [`research/`](research/):

- [`findings.md`](research/findings.md) - Chronological RE findings
- [`usb_descriptor.md`](research/usb_descriptor.md) - Complete USB descriptor dump
- [`protocol_notes.md`](research/protocol_notes.md) - HID protocol analysis
- [`open_questions.md`](research/open_questions.md) - What we're still figuring out

## Contributing

Got a ROCCAT Elo 7.1 Air that Roccat ruined? We want your data:

- USB descriptor dumps (`lsusb -v` on Linux, or use the Python scripts in `tools/`)
- Wireshark/USBPcap captures of Roccat Swarm communicating with the dongle
- Firmware binary dumps
- Your rage (channel it into PRs)

## License

MIT. Because unlike Roccat, we believe in giving people tools that actually work.

## Disclaimer

This project exists because a major gaming peripheral company shipped broken firmware, refused to fix it for four years, and left their customers with expensive paperweights. If Roccat ever decides to fix their dongle, this repo becomes a museum piece. We'd love nothing more.

Until then: **welcome to the unfuckening.**
