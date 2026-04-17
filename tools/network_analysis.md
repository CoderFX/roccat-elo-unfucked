# ROCCAT Swarm Network Analysis

Date: 2026-04-18

## Summary

Captured the complete Swarm auto-update API protocol by analyzing local logs, probing CDN
endpoints, and resolving signed download URLs. Firmware (hardware) updates are served
through the same API but the server currently returns `null` for all hardware queries,
suggesting either no firmware updates are available or a device-presence check is required.

---

## 1. Auto-Update API Protocol (Fully Captured)

### Endpoint

```
POST https://acpv.prod.turtlebeach.com/swarm1/autoupdate/form
Content-Type: application/x-www-form-urlencoded
```

Alternative working endpoint: `POST .../swarm1/autoupdate/autoupdate`

### Request Format

```
data=<JSON payload>
```

JSON payload structure:

```json
{
  "system": 27,
  "version": 1.9481,
  "protocol": 2,
  "hardware": { "<product_id>": <fw_version_float> },
  "software": { "<product_id>": <sw_version_float> }
}
```

- `system`: 27 = Windows (likely an OS enum)
- `version`: Current Swarm version as float (e.g. 1.9481)
- `protocol`: 2 (API protocol version)
- `hardware`: Dict mapping product IDs to current firmware versions (0.0 = unknown/none)
- `software`: Dict mapping product IDs to current module versions (0.0 = unknown/none)

### Response Format

```json
["successfully", {
  "swarm": {
    "version": "1.9481",
    "release": 1764086400,
    "size": 78413138,
    "file": "https://acpv.prod.turtlebeach.com/swarm1/download/software/2/1035",
    "changelog": { ... }
  },
  "hardware": null,
  "software": null
}]
```

- `swarm.file`: URL to download latest Swarm. Fetching this URL returns a signed S3 URL.
- `hardware`: Would contain firmware download info when updates are available (always null in testing).
- `software`: Would contain module download info when updates are available (always null in testing).

### Observed API Calls from Logs

1. **Boot (no devices):**
   ```
   data={"system":27,"version":1.9481,"protocol":2,"hardware":{},"software":{}}
   ```

2. **With Elo Air connected:**
   ```
   data={"system":27,"version":1.9481,"protocol":2,"hardware":{},"software":{"2713":0.0}}
   ```

3. **Manual refresh (no devices):**
   ```
   data={"system":27,"version":1.9481,"protocol":2,"hardware":{},"software":{}}
   ```

Key observation: Even with the Elo Air connected (VID:9934/PID:2571), the software ID
"2713" was sent in the `software` dict, not `hardware`. The server returned `null` for both
hardware and software in all observed cases.

---

## 2. CDN Download URL Resolution

### Primary Download Endpoint

```
GET https://acpv.prod.turtlebeach.com/swarm1/download/{type}/{system_id}/{package_id}
```

- `{type}`: `software` or `hardware`
- `{system_id}`: `2` (appears constant for all queries)
- `{package_id}`: numeric ID assigned server-side

### Two Backend CDN Systems

The download endpoint returns a redirect URL (HTTP 200, body contains URL text):

**1. Hetzner Object Storage (ROCCAT Swarm legacy)**
```
https://nbg1.your-objectstorage.com/tbnb/production/software-update/roccat--swarm/
  roccat--swarm_main-76-1.9481-1016-v1.7z?X-Amz-...&X-Amz-Expires=259200&X-Amz-Signature=...
```
- Signed S3 URLs with 3-day expiry (259200 seconds)
- Used for ROCCAT Swarm installer packages
- Filename format: `roccat--swarm_main-{product_code}-{version}-{build}-v{rev}.7z`

**2. Turtle Beach CDN (Swarm II / newer)**
```
https://cdn.turtlebeach.com/device/software-update/swarm-ii/
  swarm-ii_main-319-1.0.0.38-8448-v1.7z
```
- Direct CDN URLs (no signature)
- Used for Swarm II packages
- Filename format: `swarm-ii_main-{product_code}-{version}-{build}-v{rev}.7z`

### Discovered Software Package IDs

Scanned range 900-1039. All return HTTP 200:

| ID Range | Content |
|----------|---------|
| 900-901 | ROCCAT Swarm 1.9416-1.9417 |
| 902 | Swarm Waves Driver 1.0005 |
| 905-936 | ROCCAT Swarm 1.9418-1.9444 (mixed with Neon Beta) |
| 930 | ROCCAT Neon Beta 0.99.10 |
| 941 | ROCCAT Swarm 2 (early) 0.0.0.1 |
| 946-966 | ROCCAT Swarm 1.9451-1.9466 |
| 967-1011 | Swarm II releases 0.0.0.x through 1.0.0.x |
| 1015-1039 | Mixed Swarm (1.9478-1.9481) and Swarm II (1.0.0.21-1.0.0.38) |

**Notable: ID 1035 = Current Swarm 1.9481** (the version pointed to by auto-update API).

### Hardware Download Endpoint

```
GET https://acpv.prod.turtlebeach.com/swarm1/download/hardware/2/{id}
```

Scanned IDs 1-500 (500-2000 scan running in background). **No hits found.** This strongly
suggests firmware packages are either:
- Delivered through a different endpoint
- Bundled inside software module packages
- Hosted on a separate CDN not yet discovered

---

## 3. Other API Endpoints

### FAQ Endpoint
```
GET https://acpv.prod.turtlebeach.com/swarm1/faq/{lang}/{product_id}
```
- `{lang}`: Language code (e.g. `en`)
- `{product_id}`: Numeric ID (e.g. `0000` for generic, `2713` returns same as `2711`)
- Returns generic Swarm FAQ JSON regardless of product ID

### Form Endpoints (from Swarm.exe binary strings)
```
POST https://acpv.prod.turtlebeach.com/swarm1/form/check  -> returns "4"
POST https://acpv.prod.turtlebeach.com/swarm1/form/update  -> returns "4"
```
These appear to be support form endpoints, not useful for firmware download.

### Dev Endpoint (from binary strings)
```
https://acpv.dev.turtlebeach.com/swarm1/autoupdate/%1
```
A development/staging version of the auto-update endpoint exists.

---

## 4. Local Storage Analysis

### AppData/Roaming/ROCCAT/SWARM/

| Path | Content |
|------|---------|
| `update/update.ini` | `[SWARM] lasted_version=19481 CDN=1` |
| `setting/SWARM` | Qt binary settings: language, product_order, last_check_time_for_update |
| `setting/monitor.ini` | Local IPC socket names |
| `setting/AlienFx.ini` | `[Setting] USED=0` |
| `log/Auto_Update/` | **Critical: Full API requests and responses logged** |
| `log/monitor/` | Device connect/disconnect events with VID/PID |
| `log/firmware_upgrade/` | Empty (no firmware upgrade was performed) |
| `log/recover_tool/` | Minimal init log |
| `change_log/SWARM/english.txt` | Swarm changelog (local cache) |

### Program Files Installation

| Path | Content |
|------|---------|
| `firmware/firmware_upgrade.ini` | Elo Air config: VID=9934, PID=2571, headset_x86.dll |
| `firmware_upgrade.dll` | Firmware update logic (loads firmware_upgrade.ini) |
| `headset_x86.dll` / `ISPDLL.dll` | ISP programming DLLs (Holtek MCU programmer) |
| `EFORMAT.INI` | Holtek MCU ISP format definitions (HT66FB/HT68FB families) |
| `data/Swarm/version.ini` | Product compatibility matrix (sections 4-84) |
| `settings.xml` | Encrypted/binary blob |

### Registry

No ROCCAT keys found under HKLM, HKCU, or WOW6432Node.

---

## 5. Device Identification

### Elo Air (Connected Device)

| Field | Value |
|-------|-------|
| VID | 9934 (0x26CE) |
| PID | 2571 (0x0A0B) |
| Swarm Product ID | 2713 (used in auto-update API) |
| Swarm FAQ ID | 2711 (generic, not device-specific) |
| firmware_upgrade.ini | Section `[Elo Air]`, uses `headset_x86.dll` |

### Other Detected USB Devices
- VID:1241/PID:41118 (0x04D9/0xA09E) - A generic HID keyboard, not a ROCCAT device
- VID:3725/PID:1815 - Unknown device briefly connected

---

## 6. Firmware Update Mechanism

### How It Works

1. **Monitor detects device** via VID/PID on HID interface
2. **Auto-update API** is called with product ID in `hardware` or `software` dict
3. If server returns non-null `hardware` response, firmware download URL is provided
4. Download URL resolves to a `.7z` package on Hetzner Object Storage or Turtle Beach CDN
5. Package is extracted locally
6. `firmware_upgrade.dll` reads `firmware_upgrade.ini` to find:
   - `dll_path` (updater DLL, e.g. `headset_x86.dll`)
   - `fw_path` (firmware directory)
   - `bin_file` (firmware binary filename)
   - `headset_version` / `dongle_version` (expected versions)
7. The appropriate DLL flashes the firmware via USB HID

### Why Firmware URLs Are Not Currently Available

The auto-update API consistently returns `hardware: null` and `software: null` for all
tested product IDs and version combinations. Possible explanations:

1. **No firmware updates pending**: The server may only return download URLs when a newer
   firmware exists than what was reported.
2. **Device must be connected**: Swarm may send additional device metadata (serial, actual
   FW version read from device) that we did not replicate.
3. **Firmware bundled in modules**: Firmware may be packaged inside the device-specific
   Swarm module (software) packages rather than served separately.

### Holtek ISP Connection

The `EFORMAT.INI` and `ISPDLL.dll` files reveal the firmware update uses Holtek
Semiconductor's In-System Programming (ISP) protocol for HT66FB/HT68FB Flash MCU families.
This is the MCU inside the headset/dongle that gets reprogrammed during firmware updates.

---

## 7. API Key Findings for Future Interception

### To capture actual firmware download URLs, try:

1. **Enable Swarm debug logging** and connect Elo Air with outdated firmware
2. **Use netsh trace** (requires admin):
   ```
   netsh trace start capture=yes tracefile=C:\Users\gelum\swarm_trace.etl
   # ... trigger firmware update in Swarm ...
   netsh trace stop
   ```
3. **Install mitmproxy** and configure system proxy:
   ```
   pip install mitmproxy
   mitmproxy --mode regular --set block_global=false
   ```
   Then set Windows proxy to localhost:8080.

4. **Replay API with actual device firmware version**: If the device reports its actual
   firmware version to Swarm, that version number would be sent in the `hardware` dict.
   The server would then return download URLs only if a newer version exists.

### Working API replay command:

```bash
curl -s -X POST "https://acpv.prod.turtlebeach.com/swarm1/autoupdate/form" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'data={"system":27,"version":1.9481,"protocol":2,"hardware":{"2713":0.0},"software":{"2713":0.0}}'
```

---

## 8. CDN URL Pattern Summary

| Endpoint | Pattern | Status |
|----------|---------|--------|
| Auto-update API | `POST /swarm1/autoupdate/form` | Working |
| Software download | `GET /swarm1/download/software/2/{id}` | Working (IDs 900-1039) |
| Hardware download | `GET /swarm1/download/hardware/2/{id}` | No hits found (1-500+) |
| FAQ | `GET /swarm1/faq/{lang}/{product_id}` | Working |
| Swarm S3 storage | `https://nbg1.your-objectstorage.com/tbnb/production/software-update/` | Signed URLs |
| Swarm II CDN | `https://cdn.turtlebeach.com/device/software-update/swarm-ii/` | Direct URLs |
| Dev endpoint | `https://acpv.dev.turtlebeach.com/swarm1/autoupdate/%1` | Exists (untested) |

---

## 9. Product ID Mapping (Partial)

From version.ini sections and API observations:

| Section | Compatibility | Likely Product |
|---------|--------------|----------------|
| 4 | 1 | (legacy product) |
| 6-7 | (FAQ/Swarm) | Elo Air related |
| 27 | (used as FAQ ID) | Swarm generic |
| 28 | 2 | (product module) |
| ... | ... | ... |
| 84 | 0 | (newest product) |

Product code 76 = ROCCAT Swarm main application (seen in download filenames).
Product code 319 = Swarm II main application.
Product code 250 = Swarm Waves audio driver.
Product code 241 = ROCCAT Neon Beta.

Product ID 2713 = Elo Air (used in auto-update API for software module).

---

## 10. Files Referenced

- `C:\Users\gelum\AppData\Roaming\ROCCAT\SWARM\log\Auto_Update\2026_04_17_21_19_01.txt` - API traffic log
- `C:\Users\gelum\AppData\Roaming\ROCCAT\SWARM\log\monitor\2026_04_17_21_19_01.txt` - Device detection log
- `C:\Users\gelum\AppData\Roaming\ROCCAT\SWARM\update\update.ini` - Update state
- `C:\Program Files (x86)\ROCCAT\ROCCAT SWARM\firmware\firmware_upgrade.ini` - Device firmware config
- `C:\Program Files (x86)\ROCCAT\ROCCAT SWARM\data\Swarm\version.ini` - Product compatibility
- `C:\Program Files (x86)\ROCCAT\ROCCAT SWARM\EFORMAT.INI` - Holtek ISP format definitions
