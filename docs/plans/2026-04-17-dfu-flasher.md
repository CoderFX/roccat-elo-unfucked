# Roccat Elo Air DFU Flasher — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Python tool that enters the dongle's DFU bootloader, discovers the bootloader device, dumps the current firmware, and can flash new firmware — all without Roccat Swarm.

**Architecture:** The tool has three phases executed sequentially: (1) DFU entry — send HID command to trigger bootloader mode, (2) Bootloader discovery — scan for the re-enumerated device and probe its capabilities, (3) Flash operations — read/write firmware via the bootloader's protocol. Each phase is a separate module. The dongle crashes on ANY HID write, so every interaction is single-shot with automatic recovery via button-hold replug.

**Tech Stack:** Python 3.13, hidapi, pyusb+libusb, ctypes (Windows HID API)

**Known constraints:**
- Dongle drops off USB after ONE HID output report (report ID 0x06)
- Recovery requires physical unplug → button-hold → replug
- DFU protocol uses commands 0x06 (enter DFU) and 0x07 (status/reboot)
- Bootloader device VID:PID is unknown — must be discovered
- Firmware binary is not available — must be dumped from device or obtained separately
- `Dongle_DFU.dll` handles flashing but is part of the missing Swarm module

**Dongle interaction budget per power cycle: ONE command.** Plan accordingly.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `tools/elo_dfu.py` | Main CLI entry point — orchestrates phases |
| `tools/elo_hid.py` | Low-level HID communication (WriteFile, ReadFile, device open/close) |
| `tools/elo_scan.py` | USB/HID device enumeration and diffing |
| `tools/elo_bootloader.py` | Bootloader device interaction (probe, read, write) |
| `tools/dfu_probe.py` | Already exists — Phase 1 standalone script |
| `tests/test_elo_scan.py` | Tests for device scanning logic |

---

### Task 1: Confirm DFU Bootloader Device Appears

**This is the critical gate. Everything else depends on this.**

**Files:**
- Use: `tools/dfu_probe.py` (already written)

**Prerequisite:** Dongle must be plugged in and enumerated (use button-hold reset if needed).

- [ ] **Step 1: Plug in dongle with button-hold reset**

Physical action: unplug dongle, hold button, plug in, wait for red blinking LED. Verify enumeration:

```bash
"C:/Users/gelum/AppData/Local/Programs/Python/Python313/python.exe" -c "
import hid
devs = list(hid.enumerate(0x26CE, 0x0A0B))
print(f'Found: {len(devs)} interfaces')
"
```

Expected: `Found: 1 interfaces`

- [ ] **Step 2: Run DFU probe**

```bash
"C:/Users/gelum/AppData/Local/Programs/Python/Python313/python.exe" tools/dfu_probe.py
```

Expected outcomes (one of):
- **Best case:** New device appears with different VID:PID → bootloader found, proceed to Task 2
- **Likely case:** Dongle disappears, no new device in HID/libusb → check Device Manager for unknown devices
- **Worst case:** Dongle disappears, nothing anywhere → need alternative approach (Task 1B)

- [ ] **Step 3: Check Device Manager regardless of script output**

```powershell
# Run in PowerShell — check for ANY new/unknown/error USB devices
powershell.exe -Command "Get-PnpDevice | Where-Object { $_.Status -ne 'OK' -and $_.InstanceId -match 'USB' -and $_.Problem -ne 'CM_PROB_PHANTOM' } | Select-Object InstanceId, FriendlyName, Status | Format-Table"
```

Also visually check Device Manager > Universal Serial Bus devices and "Other devices" for anything with a yellow triangle.

- [ ] **Step 4: Document result**

Record the bootloader VID:PID (or lack thereof) in `research/findings.md` as F-032. Update scribe agent.

- [ ] **Step 5: Commit**

```bash
git add tools/ research/ && git commit -m "DFU probe: bootloader device discovery result"
git push
```

---

### Task 1B: Alternative Bootloader Discovery (if Task 1 finds nothing)

**Only execute if Task 1 Step 2 shows no new device.**

**Files:**
- Create: `tools/elo_usb_monitor.py`

- [ ] **Step 1: Install USBPcap or use PowerShell WMI event watcher**

```bash
# WMI event watcher — catches device arrival at the OS level
"C:/Users/gelum/AppData/Local/Programs/Python/Python313/python.exe" -c "
import subprocess, time, sys

# Start WMI watcher in background
proc = subprocess.Popen([
    'powershell.exe', '-Command',
    '''Register-WmiEvent -Query \"SELECT * FROM __InstanceCreationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_PnPEntity' AND TargetInstance.DeviceID LIKE 'USB%'\" -Action { Write-Host \"NEW: \$(\$Event.SourceEventArgs.NewEvent.TargetInstance.DeviceID) - \$(\$Event.SourceEventArgs.NewEvent.TargetInstance.Name)\" } ; Start-Sleep 60'''
], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

print('WMI USB watcher running for 60s...')
print('Plug in the dongle NOW (button-hold reset)')
time.sleep(60)
out, _ = proc.communicate(timeout=5)
print(out)
"
```

This catches ANY USB device arrival at the Windows level, including devices without drivers.

- [ ] **Step 2: Try different command bytes**

The DFU entry might not be byte 0x01. Try other candidates one per power cycle:
- `0x00` — null command
- `0x06` — DFU start (matching the report ID)
- `0xFF` — max value
- `0x02` — alternate mode

Each attempt: button-hold replug → send ONE command → monitor 30s → document result.

- [ ] **Step 3: Try sending via feature report instead of output report**

Some devices use `hid_send_feature_report` for DFU instead of `hid_write`:

```python
dev = hid.device()
dev.open_path(path)
dev.send_feature_report(bytes([0x06, 0x01]))  # feature report approach
```

- [ ] **Step 4: Commit findings**

```bash
git add tools/ research/ && git commit -m "Alternative bootloader discovery attempts"
git push
```

---

### Task 2: Probe Bootloader Device

**Only execute after Task 1 identifies the bootloader VID:PID.**

**Files:**
- Create: `tools/elo_bootloader.py`

- [ ] **Step 1: Enumerate bootloader HID descriptors**

```python
# After DFU entry, open the bootloader device and dump everything
import hid

BOOT_VID = 0x____  # fill from Task 1
BOOT_PID = 0x____  # fill from Task 1

for d in hid.enumerate(BOOT_VID, BOOT_PID):
    print(f"  iface={d['interface_number']} usage=0x{d['usage_page']:04X}:0x{d['usage']:04X}")

# Get HID caps via Windows API (InputReportSize, OutputReportSize, FeatureReportSize)
# This tells us the bootloader's packet format
```

- [ ] **Step 2: Try reading firmware version**

From DLL strings: `"Get FW version"`, `"Get flash size"`, `"Get page size"`, `"Get start address"`, `"Get AP version address"`, `"Get AP version length"`

Try sending known DFU query commands and reading responses. Each command = one power cycle if it crashes.

- [ ] **Step 3: Try reading flash memory**

From DLL strings: `"PIC32 Read Flash Write Failed"` — there IS a read capability.

```python
# PIC32 flash read: send read command, receive flash data
# Exact packet format TBD from bootloader HID descriptor
```

- [ ] **Step 4: Document bootloader protocol**

Record all discovered commands, packet formats, and responses in `research/protocol_notes.md`.

- [ ] **Step 5: Commit**

```bash
git add tools/ research/ && git commit -m "Bootloader protocol discovery"
git push
```

---

### Task 3: Firmware Dump

**Only execute after Task 2 establishes read capability.**

**Files:**
- Create: `tools/elo_dump.py`
- Output: `firmware/current_dump.bin`

- [ ] **Step 1: Implement flash reader**

```python
# Read firmware in pages/blocks
# PIC32 typical page size: 4096 bytes
# Total flash: varies (256KB-2MB typical for PIC32)

def dump_firmware(bootloader_dev, output_path):
    """Read entire flash and save to binary file."""
    flash_size = query_flash_size(bootloader_dev)
    page_size = query_page_size(bootloader_dev)

    with open(output_path, 'wb') as f:
        for addr in range(0, flash_size, page_size):
            page = read_flash_page(bootloader_dev, addr, page_size)
            f.write(page)
            print(f"  {addr:#x}/{flash_size:#x} ({addr*100//flash_size}%)")

    print(f"Dumped {flash_size} bytes to {output_path}")
```

- [ ] **Step 2: Run firmware dump**

```bash
# Requires dongle in bootloader mode (from Task 1)
"C:/Users/gelum/AppData/Local/Programs/Python/Python313/python.exe" tools/elo_dump.py
```

- [ ] **Step 3: Verify dump integrity**

```bash
sha256sum firmware/current_dump.bin
"C:/Users/gelum/AppData/Local/Programs/Python/Python313/python.exe" -c "
with open('firmware/current_dump.bin', 'rb') as f:
    data = f.read()
print(f'Size: {len(data)} bytes')
print(f'First 32: {data[:32].hex(\" \")}')
print(f'Last 32: {data[-32:].hex(\" \")}')
print(f'All FF: {sum(1 for b in data if b == 0xFF)} bytes')
print(f'All 00: {sum(1 for b in data if b == 0x00)} bytes')
"
```

- [ ] **Step 4: Commit firmware dump**

```bash
mkdir -p firmware
git add firmware/current_dump.bin tools/elo_dump.py
git commit -m "Firmware dump from bricked dongle"
git push
```

---

### Task 4: Analyze Firmware Dump & Patch VID/PID

**Files:**
- Create: `tools/elo_patch.py`
- Input: `firmware/current_dump.bin`
- Output: `firmware/patched.bin`

- [ ] **Step 1: Find USB descriptors in firmware dump**

```python
# USB Device Descriptor starts with: 12 01 (bLength=18, bDescriptorType=DEVICE)
# Search for VID 26CE (CE 26 in little-endian) and PID 0A0B (0B 0A)
import struct

with open('firmware/current_dump.bin', 'rb') as f:
    data = f.read()

# Find USB device descriptor
for i in range(len(data) - 18):
    if data[i] == 0x12 and data[i+1] == 0x01:  # device descriptor
        vid = struct.unpack_from('<H', data, i+8)[0]
        pid = struct.unpack_from('<H', data, i+10)[0]
        if vid == 0x26CE or vid == 0x1E7D:
            print(f"  USB descriptor at offset 0x{i:06X}: VID=0x{vid:04X} PID=0x{pid:04X}")

# Also search for raw VID/PID bytes
for pattern, label in [
    (b'\xCE\x26', '26CE (current VID)'),
    (b'\x0B\x0A', '0A0B (current PID)'),
    (b'\x7D\x1E', '1E7D (original VID)'),
    (b'\x37\x3A', '3A37 (original PID)'),
]:
    offsets = []
    pos = 0
    while True:
        pos = data.find(pattern, pos)
        if pos == -1: break
        offsets.append(pos)
        pos += 1
    print(f"  {label}: found at {len(offsets)} offsets: {[f'0x{o:06X}' for o in offsets[:10]]}")
```

- [ ] **Step 2: Patch VID/PID back to original**

```python
# Replace 26CE:0A0B with 1E7D:3A37 at the USB descriptor location(s)
patched = bytearray(data)

for offset in vid_offsets:
    print(f"  Patching VID at 0x{offset:06X}: 26CE -> 1E7D")
    struct.pack_into('<H', patched, offset, 0x1E7D)

for offset in pid_offsets:
    print(f"  Patching PID at 0x{offset:06X}: 0A0B -> 3A37")
    struct.pack_into('<H', patched, offset, 0x3A37)

# Recalculate any checksums if present
# ... (depends on firmware format)

with open('firmware/patched.bin', 'wb') as f:
    f.write(patched)
```

- [ ] **Step 3: Verify patch**

```python
# Re-run descriptor search on patched firmware
# Should show VID=0x1E7D PID=0x3A37
```

- [ ] **Step 4: Commit**

```bash
git add firmware/patched.bin tools/elo_patch.py
git commit -m "Patched firmware: VID/PID restored to 1E7D:3A37"
git push
```

---

### Task 5: Flash Patched Firmware

**Files:**
- Create: `tools/elo_flash.py`
- Input: `firmware/patched.bin`

- [ ] **Step 1: Implement flash writer**

Based on DFU protocol from firmware_upgrade.dll:

```python
def flash_firmware(bootloader_dev, firmware_path):
    """Write firmware image to dongle flash."""
    with open(firmware_path, 'rb') as f:
        firmware = f.read()

    checksum = sum(firmware) & 0xFFFFFFFF

    # Step 1: Send erase command
    send_erase(bootloader_dev)

    # Step 2: Send file size
    send_file_size(bootloader_dev, len(firmware))

    # Step 3: Write data in blocks
    for offset in range(0, len(firmware), BLOCK_SIZE):
        block = firmware[offset:offset+BLOCK_SIZE]
        send_program_data(bootloader_dev, offset, block)
        print(f"  {offset:#x}/{len(firmware):#x}")

    # Step 4: Send finished
    send_program_finished(bootloader_dev)

    # Step 5: Verify checksum
    verify_checksum(bootloader_dev, checksum)

    # Step 6: Reboot to app mode (command 0x07)
    send_reboot(bootloader_dev)
```

- [ ] **Step 2: Flash the patched firmware**

```bash
# DANGER: This writes to the dongle. Have the dump as backup.
"C:/Users/gelum/AppData/Local/Programs/Python/Python313/python.exe" tools/elo_flash.py firmware/patched.bin
```

- [ ] **Step 3: Verify — check if dongle now identifies as 1E7D:3A37**

```bash
# Unplug and replug (normal, no button hold)
"C:/Users/gelum/AppData/Local/Programs/Python/Python313/python.exe" -c "
import hid
for d in hid.enumerate():
    if d['vendor_id'] in [0x1E7D, 0x26CE]:
        print(f'VID=0x{d[\"vendor_id\"]:04X} PID=0x{d[\"product_id\"]:04X} \"{d[\"product_string\"]}\"')
"
```

Expected: VID=0x1E7D PID=0x3A37

- [ ] **Step 4: Test Swarm detection**

Launch Swarm. It should now detect the Elo Air and offer to download the module + update firmware properly.

- [ ] **Step 5: Test headset pairing**

Turn on headset near dongle. They should pair (both devices now speaking the same protocol).

- [ ] **Step 6: Commit**

```bash
git add tools/elo_flash.py
git commit -m "DFU flasher: patched firmware restores original VID/PID"
git push
```

---

## Dependency Graph

```
Task 1: Confirm bootloader device appears
  |
  ├─ [found] ──→ Task 2: Probe bootloader
  │                 |
  │                 └──→ Task 3: Dump firmware
  │                        |
  │                        └──→ Task 4: Patch VID/PID
  │                               |
  │                               └──→ Task 5: Flash patched firmware
  │
  └─ [not found] ──→ Task 1B: Alternative discovery
                        |
                        └──→ Task 1 (retry with new info)
```

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Bootloader device doesn't appear | Blocks everything | Task 1B alternatives; may need JTAG/SWD hardware debugger |
| Bootloader has no read capability | Can't dump firmware | Obtain firmware from Swarm CDN or community; flash blind |
| Firmware has checksums we can't recalculate | Patched firmware rejected | Analyze checksum algorithm from firmware_upgrade.dll |
| Flash write bricks dongle permanently | Hardware loss | Always keep dump backup; test with read-only operations first |
| Bootloader protocol is different from what strings suggest | Wrong commands | Probe carefully, one command per power cycle |
