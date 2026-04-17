# Roccat Swarm `settings_decoded.xml` Analysis

Date: 2026-04-18
Source: `swarm_extracted/settings_decoded.xml` (decoded from `v1.9481_unpacked/settings.xml`)

## 1. Complete Device Database (PRODUCTS section)

The XML contains 84 `<PRODUCT>` entries. Each has: `dll_name`, `type` (module ID), `pid` (USB PID), `alias_name`, `disp_name`, and optionally `updating_pid`, `device_type`, `macro`, `release`, `swarm2`.

**VID is implicit: all products use VID `0x1E7D` (ROCCAT GmbH).** The VID is not stored in the XML because Swarm only scans for `0x1E7D` devices.

### Elo / Headset Products (device_type="2")

| Type | PID | Updating PID | DLL | Alias | Display Name | Notes |
|------|-----|-------------|-----|-------|-------------|-------|
| **30** | `0x39D0` | `0x39D1` | KHAN_AIMO | KHAN_AIMO | KHAN_AIMO | Original Khan AIMO headset |
| **49** | `0x3A34` | `0x3A34` | KHAN_AIMO | 3A34 | **ELO_USB** | Elo 7.1 USB (wired) -- reuses Khan DLL |
| **50** | `0x3A39` | `0x3A38` | 3A39 | 3A39 | **ELO_AIR** | Elo 7.1 Air **wireless headset** (PID 3A39) |
| **52** | `0x3A37` | `0x3A36` | 3A37 | 3A37 | **ELO_AIR** | Elo 7.1 Air **wireless dongle** (PID 3A37) |
| 66 | `0x3A41` | `0x3A40` | SYN_SERIES | SYN_MAX_AIR | SYN_MAX_AIR | release=0 |
| 67 | `0x3A3F` | `0x3A3E` | SYN_SERIES | SYN_MAX_AIR_DOCK | SYN_MAX_AIR | release=0 |
| 74 | `0x3A3D` | `0x3A3C` | SYN_SERIES | SYN_PRO_AIR | SYN_PRO_AIR | release=0 |
| 75 | `0x3A3B` | `0x3A3A` | SYN_SERIES | SYN_PRO_AIR_DONGLE | SYN_PRO_AIR | release=0 |
| 79 | `0x3A56` | `0x0000` | TORCH | TORCH | TORCH | USB mic; updating_pid=0 |

### Critical Elo 7.1 Air Entries

**Type 52 -- Elo 7.1 Air Dongle (our device):**
```xml
<PRODUCT dll_name="3A37" type="52" pid="0x3A37" updating_pid="0x3A36"
         alias_name="3A37" disp_name="ELO_AIR" release="1"
         device_type="2" macro="0x0" auto_unplug_plugin="1"/>
```

- **Normal PID:** `0x3A37` -- this is VID `1E7D`, PID `3A37` (the original identity before firmware update)
- **Updating PID:** `0x3A36` -- the PID the dongle presents when in DFU/update mode
- **Module type:** `52` -- this is the module ID for CDN downloads
- **DLL name:** `3A37` -- Swarm loads `3A37.dll` for device management
- **auto_unplug_plugin=1:** device disconnects during firmware update (consistent with DFU observation)

**Type 50 -- Elo 7.1 Air Headset:**
```xml
<PRODUCT dll_name="3A39" type="50" pid="0x3A39" updating_pid="0x3A38"
         alias_name="3A39" disp_name="ELO_AIR" release="1"
         device_type="2" macro="0x0" auto_unplug_plugin="1"/>
```

- **Normal PID:** `0x3A39` (headset in normal mode)
- **Updating PID:** `0x3A38` (headset in DFU/update mode)
- **Module type:** `50`

## 2. Module IDs (type field) -- Complete Mapping

The `type` field serves as the **module ID** used throughout Swarm for CDN downloads, version tracking, and firmware management. The `version.ini` sections use these same numbers.

### Module IDs for Elo-relevant devices

| Module ID (type) | Product | PID | Updating PID |
|-----------------|---------|-----|-------------|
| 50 | Elo 7.1 Air (headset) | 0x3A39 | 0x3A38 |
| **52** | **Elo 7.1 Air (dongle)** | **0x3A37** | **0x3A36** |
| 49 | Elo USB (wired) | 0x3A34 | 0x3A34 |
| 30 | Khan AIMO | 0x39D0 | 0x39D1 |

### version.ini confirmation

From `v1.9481_unpacked/data/Swarm/version.ini`:
```ini
[52]
compatibility=2

[50]
compatibility=2

[49]
compatibility=2
```

All three Elo entries exist in version.ini with `compatibility=2`, confirming they are active modules.

## 3. CDN / Download URLs

### Known URL patterns (from binary string extraction)

| Source binary | URL pattern | Purpose |
|---------------|-------------|---------|
| `ROCCAT_Swarm.exe` | `https://acpv.prod.turtlebeach.com/swarm1/form/%1` | Support form (not firmware) |
| `ROCCAT_Swarm_Monitor.exe` | `https://acpv.prod.turtlebeach.com/swarm1/autoupdate/%1` | Auto-update endpoint |
| `ROCCAT_Swarm_Monitor.exe` | `https://acpv.dev.turtlebeach.com/swarm1/autoupdate/%1` | Dev/staging auto-update |

### CDN probe status

Both `/swarm1/form/<N>` and `/swarm1/autoupdate/<N>` returned 404 for bare numeric IDs 1-84. The `%1` parameter is likely NOT the raw module ID number -- it may be a product slug, package name, or composite token.

**Untested candidates for `%1`:**
- Alias name: e.g. `3A37`, `3A39`, `KHAN_AIMO`
- DLL name: e.g. `3A37`, `3A39`
- Display name: e.g. `ELO_AIR`
- Combined format: e.g. `3A37/firmware_upgrade.ini`, `3A37.zip`
- Version-qualified: e.g. `3A37/19481`

## 4. Firmware File Paths

### Within Swarm installation (runtime-created, not bundled)

```
data/<PID_hex>/firmware/          -- per-device firmware directory
data/<PID_hex>/firmware/*.bin     -- firmware binary files (e.g., FW_V1.23.bin)
data/<PID_hex>/firmware_upgrade.ini  -- update configuration
```

For Elo 7.1 Air dongle, the expected path would be:
```
data/3A37/firmware/firmware.bin
data/3A37/firmware_upgrade.ini
```

### firmware_upgrade.ini format (from DLL string extraction + existing samples)

**Best current format (v3, from `tools/firmware_upgrade_v3.ini`):**
```ini
[Elo Air]
vid = 0x1E7D
pid = 0x3A37
dll_path = headset_x86.dll
fw_path = firmware/
bin_file = firmware.bin
headset_version = 0
dongle_version = 0
auto_reset = 1
1_Version = 0
2_Version = 0

[Elo Air Dongle]
vid = 0x26CE
pid = 0x0A0B
dll_path = headset_x86.dll
fw_path = firmware/
bin_file = firmware.bin
headset_version = 0
dongle_version = 0
auto_reset = 1
1_Version = 0
2_Version = 0
```

### DLLs involved in firmware update

| DLL | Purpose |
|-----|---------|
| `firmware_upgrade.dll` | Orchestrator -- reads INI, coordinates update |
| `Dongle_DFU.dll` | Dongle-specific DFU protocol handler |
| `headset_x86.dll` | Headset device communication (referenced in INI) |
| `HIDDLL.dll` | Low-level HID I/O |
| `ConfDLL.dll` | Configuration DLL |

## 5. Device Type Mappings

From the XML comment at line 114:
```xml
<!--device_type: 0 = mouse, 1 = keyboard, 2 = headset, 3 = mousepad -->
```

| device_type | Category | Examples |
|-------------|----------|---------|
| 0 | Mouse | Kone, Kain, Burst, Leadr, Nyth, Kova |
| 1 | Keyboard | Vulcan, Suora, Ryos, Horde, Magma, Pyro |
| 2 | Headset | Khan AIMO, Elo USB, Elo Air, Syn series, Torch |
| 3 | Mousepad/Dock | AIMO Pad, Kone XP Air Dock |

## 6. PID Relationships -- Elo 7.1 Air Identity Chain

```
ORIGINAL (Swarm-visible):
  VID: 0x1E7D (ROCCAT GmbH)
  Dongle normal PID: 0x3A37
  Dongle DFU PID:    0x3A36
  Headset normal PID: 0x3A39
  Headset DFU PID:    0x3A38

CURRENT (post-firmware-update, Swarm-invisible):
  VID: 0x26CE (Realtek/generic)
  Dongle PID: 0x0A0B
  LED controller PID: 0x01A2 (UNRELATED -- motherboard device)
```

The firmware update changed the dongle's USB identity from `1E7D:3A37` to `26CE:0A0B`, permanently orphaning it from Swarm's device scanner.

## 7. Additional Structural Observations

### Non-device PRODUCT entries (types 0-7, 27, 73)
These are Swarm infrastructure modules, not physical devices:

| Type | Name | Purpose |
|------|------|---------|
| 0 | MONITOR | Swarm background monitor |
| 1 | SWARM | Main Swarm application |
| 2 | KILL_PROCESS | Process termination utility |
| 3 | FIRMWARE_UPDATE | Firmware update subsystem |
| 4 | SWARM_CONNECT | Swarm Connect (cloud sync?) |
| 5 | UPGRADE_INSTALL | Upgrade installer |
| 6 | TALK_FX | Roccat Talk FX (inter-device lighting) |
| 7 | ALIEN_FX | AlienFX integration |
| 27 | AIMO | AIMO lighting ecosystem |
| 73 | WAVES_DRIVER | Waves audio DSP driver |

### Wireless device pattern
All wireless devices have TWO entries: one for the main device and one for the dongle. They share the same `dll_name` and `disp_name` but have different `type` (module ID), `pid`, and `updating_pid`. Examples:

| Product | Device type | Module ID | Main PID | Dongle type | Dongle Module ID | Dongle PID |
|---------|------------|-----------|----------|-------------|-----------------|------------|
| Elo Air | 50 (headset) | 50 | 0x3A39 | 52 (dongle) | 52 | 0x3A37 |
| Kain 200 | 43 (mouse) | 43 | 0x2D5F | 48 (dongle) | 48 | 0x2D60 |
| Burst Pro Air | 62 (mouse) | 62 | 0x2CAB | 63 (dongle) | 63 | 0x2CA6 |
| Kone XP Air | 69 (mouse) | 69 | 0x2CB2 | 70 (dongle) | 70 | 0x2CB6 |

### AIMO-compatible products
Types 26-84 (excluding gaps) are listed in the `<AMIO_PRODUCT>` section, including Elo types 49, 50, 52. This means Elo devices participate in the AIMO lighting ecosystem.

## 8. Actionable Next Steps for Dongle Recovery

### Priority 1: Try CDN download with product slug (not bare module ID)

The bare numeric IDs failed. Try these URL patterns:
```
https://acpv.prod.turtlebeach.com/swarm1/autoupdate/3A37
https://acpv.prod.turtlebeach.com/swarm1/autoupdate/ELO_AIR
https://acpv.prod.turtlebeach.com/swarm1/autoupdate/3A37.zip
https://acpv.prod.turtlebeach.com/swarm1/form/3A37
https://acpv.prod.turtlebeach.com/swarm1/form/ELO_AIR
```

Also try the Swarm II endpoint pattern:
```
https://acpv.prod.turtlebeach.com/support/generated/software/0-319/...
```

### Priority 2: Populate firmware_upgrade.ini with confirmed values

Now that we know from settings_decoded.xml:
- **Module type 52** = Elo Air dongle
- **PID 0x3A37** = normal mode
- **Updating PID 0x3A36** = DFU mode
- **VID 0x1E7D** = original ROCCAT VID

The `firmware_upgrade.ini` should include:
```ini
[Elo Air]
vid = 0x1E7D
pid = 0x3A37
updating_pid = 0x3A36
type = 52
device_type = 2
dll_path = headset_x86.dll
fw_path = firmware/
bin_file = firmware.bin
headset_version = 0
dongle_version = 0
auto_reset = 1
```

### Priority 3: Locate Dongle_DFU.dll

The key DLL for the dongle's DFU protocol is `Dongle_DFU.dll`, referenced in `firmware_upgrade.dll` strings. This DLL is not in the base Swarm installer -- it is downloaded as part of the Elo device module. It must be obtained from:
- A system where Swarm successfully detected an `1E7D:3A37` dongle and downloaded its module
- The CDN directly (once the correct URL is discovered)
- Community sharing

### Priority 4: Use updating_pid 0x3A36 for DFU device detection

After sending the DFU trigger command (report ID `0x06`), scan for a device with PID `0x3A36` (not just any new device). The settings_decoded.xml explicitly declares this as the updating PID. It may re-enumerate with VID `0x1E7D` or VID `0x26CE`.
