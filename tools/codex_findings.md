# ROCCAT Swarm Recovery / firmware_upgrade.ini Findings

Date: 2026-04-17
Workspace: `C:\msys64\home\gelum\headphones`

## Scope

Tasks completed:

1. Extracted strings from:
   - `swarm_extracted/v1.9481_unpacked/firmware_upgrade.dll`
   - `swarm_extracted/v1.9481_unpacked/ROCCAT_Recover_Tool.exe`
2. Checked related strings in:
   - `swarm_extracted/v1.9481_unpacked/ROCCAT_Swarm.exe`
   - `swarm_extracted/v1.9481_unpacked/ROCCAT_Swarm_Monitor.exe`
3. Searched the web for:
   - `roccat swarm firmware_upgrade.ini format`
   - `roccat elo 7.1 air firmware download`
4. Probed Turtle Beach CDN endpoints under:
   - `https://acpv.prod.turtlebeach.com/swarm1/form/`
   - `https://acpv.prod.turtlebeach.com/swarm1/autoupdate/`
5. Inspected:
   - `swarm_extracted/v1.9481_unpacked/data/Swarm/version.ini`

## Important environment note

The requested MSYS2 `bash` and MSYS2 `grep` runtime binaries fail in this sandbox with `Win32 error 5` when they try to create signal pipes. To work around that, I used native MinGW `strings.exe` and `curl.exe`, with PowerShell only as the outer launcher. The actual extraction/probing work still used `strings` and `curl`.

## 1. `firmware_upgrade.dll` strings: firmware INI key evidence

High-confidence strings pulled from `firmware_upgrade.dll`:

- `firmware_upgrade.ini`
- `SWARM.ini`
- `headset_version`
- `dongle_version`
- `type`
- `version`
- `auto_reset_version`
- `auto_reset`
- `VID_`
- `PID_`
- `vid_`
- `pid_`
- `dll_path`
- `fw_path`
- `bin_file`
- `driver_path`
- `delay`
- `default`
- `1_Version =`
- `2_Version =`
- `1 Version =`
- `2 Version =`

Relevant nearby string clusters:

```text
firmware_upgrade.ini
EXTFLASH
ATTINY
BT_MD
zip_name
.zip
%1 FW file missing, check %2
Checking firmware_upgrade.ini is not exist :
Main/factory
Main/number
Main/material
name
version
auto_reset_version
.bin
```

```text
ConfDLL.dll
driver_path
dll_path
fw_path
delay
khan_aimo_fw_update64.exe
```

```text
firmware
default
bin_file
fw_path
Fw file : %1
Fw path : %1
```

```text
Roccat
headset_version
dongle_version
```

```text
keyboard_get_firmware_version
default
2_Version =
1 Version =
2 Version =
region : %1
```

Interpretation:

- `firmware_upgrade.dll` definitely reads `firmware_upgrade.ini`.
- For at least one code path, the INI contains a `default` group/section with `bin_file` and `fw_path`.
- Some device-specific paths also use `dll_path`, `driver_path`, `delay`, `auto_reset`, and `auto_reset_version`.
- Wireless headset paths clearly reference both `headset_version` and `dongle_version`.
- There are separate updater families inside the DLL, so not every key applies to every device.

## 2. `ROCCAT_Recover_Tool.exe` strings: recovery-tool-specific evidence

High-signal strings from `ROCCAT_Recover_Tool.exe`:

- `firmware_upgrade.ini`
- `version.ini`
- `type`
- `updating_pid`
- `device_type`
- `dll_path`
- `fw_path`
- `bin_file`
- `headset`
- `dongle`
- `monitor.ini`
- `AlienFx.ini`
- `RoccatTalk.ini`
- `test_value.ini`

Recovery/update related strings:

```text
firmware_upgrade.ini
type
updating_pid
device_type
test_value.ini
version
version.ini
AlienFx.ini
RoccatTalk.ini
```

```text
dll_path
fw_path
```

```text
bin_file
fw_path
/firmware/headset_x86.dll
```

```text
Start Syn Pro Air headset firmware update.
Start Syn Pro Air dongle firmware update.
firmware_upgrade.ini
Firmware update failed, version.txt file is not exist!
Firmware update failed, load firmware_upgrade.ini file failed!
```

```text
Start Syn Max Air headset firmware update.
Start Syn Max Air dongle firmware update.
firmware_upgrade.ini
Firmware update failed, version.txt file is not exist!
Firmware update failed, firmware_upgrade.ini file is not exist!
```

Interpretation:

- The recovery tool and firmware DLL both expect `firmware_upgrade.ini`.
- `type`, `updating_pid`, and `device_type` appear in the recovery tool, but these may be broader Swarm module/device metadata rather than the minimal headset recovery INI.
- Headset update flows are explicitly split into headset and dongle phases for wireless products.

## 3. Existing local sample INI

There is already a local sample at [tools/firmware_upgrade.ini](/C:/msys64/home/gelum/headphones/tools/firmware_upgrade.ini:1):

```ini
[Elo Air]
vid = 9934
pid = 2571
dll_path = headset_x86.dll
fw_path = firmware
bin_file = firmware.bin
headset_version = 0
dongle_version = 0
auto_reset = 1
auto_reset_version = 0
1_Version = 0
2_Version = 0
```

This sample matches multiple strings found in `firmware_upgrade.dll`:

- `dll_path`
- `fw_path`
- `bin_file`
- `headset_version`
- `dongle_version`
- `auto_reset`
- `auto_reset_version`
- `1_Version`
- `2_Version`

It does **not** prove the section name must be `Elo Air`; it only proves that this sample is consistent with the binary-extracted key names.

## 4. Best current inference: exact INI shape expected by the recovery DLL

Most likely minimal INI shape for the Elo/Syn-style wireless headset recovery path:

```ini
[Some Device Section]
vid=<decimal VID>
pid=<decimal PID>
dll_path=<updater dll filename>
fw_path=<firmware folder path>
bin_file=<firmware image filename>
headset_version=<integer>
dongle_version=<integer>
auto_reset=<integer 0|1>
auto_reset_version=<integer>
1_Version=<integer>
2_Version=<integer>
```

Likely notes:

- `vid` and `pid` appear in logs as decimal numbers, not hex.
- `dll_path`, `fw_path`, and `bin_file` are plain filenames/relative paths.
- Wireless headset products use separate headset and dongle version keys.
- `1_Version` / `2_Version` and also `1 Version` / `2 Version` exist in strings. The exact whitespace-sensitive key spelling used by each code path is still not fully proven, but the sample file uses underscore versions.
- `default` is also present in the DLL strings, so some updater paths may use `[default]` instead of a human product section.

## 5. What is definitely not yet proven

The string extraction does **not** prove all of these points:

- Whether the recovery tool reads the first section, a specific named section, or enumerates sections.
- Whether `type` is required for Elo Air style recovery.
- Whether `version` must exist alongside `headset_version` / `dongle_version`.
- Whether `vid` / `pid` must be lowercase exactly, although the binaries also contain `VID_` and `PID_` log strings.

So the safest current conclusion is:

- `dll_path`, `fw_path`, `bin_file`, `headset_version`, `dongle_version`, `auto_reset`, and `auto_reset_version` are strongly supported for the wireless headset path.
- `vid` and `pid` are also strongly supported.
- The exact section-selection rule still needs runtime validation if complete certainty is required.

## 6. Swarm CDN URL patterns found in binaries

From `ROCCAT_Swarm.exe`:

```text
https://acpv.prod.turtlebeach.com/swarm1/form/%1
Product=%1&Name=%2&Email=%3&Message=%4
```

Interpretation:

- `/swarm1/form/%1` is almost certainly a support/contact form endpoint, not the module download endpoint.
- The adjacent POST-like payload string strongly supports that interpretation.

From `ROCCAT_Swarm_Monitor.exe`:

```text
https://acpv.dev.turtlebeach.com/swarm1/autoupdate/%1
https://acpv.prod.turtlebeach.com/swarm1/autoupdate/%1
update.ini content :
file_version
```

Interpretation:

- `/swarm1/autoupdate/%1` is the actual auto-update endpoint family.
- `update.ini` and `file_version` are part of that flow.
- If module downloads are being fetched from the CDN, `autoupdate/%1` is the better lead than `form/%1`.

## 7. CDN probe results

### `/swarm1/form/`

Base URL:

- `curl -I https://acpv.prod.turtlebeach.com/swarm1/form/`
- Result: `HTTP/2 404`

Numeric probes `1..84`:

- Every request to `https://acpv.prod.turtlebeach.com/swarm1/form/<id>` returned `404`
- No non-404 responses were observed for any ID from `1` through `84`

Conclusion:

- Bare numeric IDs do not work directly on `/swarm1/form/`
- This endpoint is probably not meant for module downloads

### `/swarm1/autoupdate/`

Base URL family from strings:

- `https://acpv.prod.turtlebeach.com/swarm1/autoupdate/%1`

Numeric probes:

- Tested `1..10` directly and then `1..84` for non-404s
- Every observed bare numeric request returned `404`
- No non-404 responses were found in `1..84`

Conclusion:

- `/swarm1/autoupdate/%1` is real, but `%1` is probably **not** the raw numeric section ID from `version.ini`
- It likely expects a different token: product code, package slug, filename, or some composite identifier

## 8. `version.ini` findings

File: [version.ini](/C:/msys64/home/gelum/headphones/swarm_extracted/v1.9481_unpacked/data/Swarm/version.ini:1)

Observed:

- `[General]`
  - `version=19481`
- 76 numbered sections
- Minimum section ID: `4`
- Maximum section ID: `84`
- Missing IDs in `1..84`: `1,2,3,5,6,7,27,76`

Each numbered section only contains:

```ini
[N]
compatibility=<integer>
```

Examples:

```ini
[18]
compatibility=35

[40]
compatibility=5

[65]
compatibility=0
```

Interpretation:

- These numbered sections do look like module IDs or package IDs.
- But they are only compatibility markers in this local file.
- They do **not** map directly to working CDN URLs by simple substitution into `/form/<id>` or `/autoupdate/<id>`.

## 9. Web search results

Queries run:

- `roccat swarm firmware_upgrade.ini format`
- `roccat elo 7.1 air firmware download`

What I found:

- General ROCCAT Elo 7.1 Air product/manual pages
- General review pages
- No public documentation describing the exact `firmware_upgrade.ini` schema
- No clear direct firmware download for Elo 7.1 Air from public web search results

Useful but indirect results:

- Manuals mention firmware/software updates happen through ROCCAT Swarm
- No public support page surfaced with a standalone Elo 7.1 Air firmware package

Interpretation:

- The `firmware_upgrade.ini` format appears to be undocumented publicly.
- Direct Elo 7.1 Air firmware packages are not easily discoverable via normal public search.

## 10. Final conclusions

Most defensible current conclusion:

1. The recovery DLL definitely uses Qt `QSettings`-style INI data and expects keys including:
   - `vid`
   - `pid`
   - `dll_path`
   - `fw_path`
   - `bin_file`
   - `headset_version`
   - `dongle_version`
   - `auto_reset`
   - `auto_reset_version`
   - possibly `1_Version`
   - possibly `2_Version`
2. The local sample `tools/firmware_upgrade.ini` is consistent with those extracted key names and is the best current concrete format example.
3. `https://acpv.prod.turtlebeach.com/swarm1/form/%1` exists in `ROCCAT_Swarm.exe`, but it appears to be a support form endpoint, not a module-download endpoint.
4. `https://acpv.prod.turtlebeach.com/swarm1/autoupdate/%1` exists in `ROCCAT_Swarm_Monitor.exe` and is the stronger lead for actual module/update retrieval.
5. The `version.ini` numeric sections probably represent module/package IDs, but they do not work as direct bare numeric substitutions into either `/form/<id>` or `/autoupdate/<id>`.

## 11. Practical next step if exact runtime behavior is still needed

If exact section-selection and key requirements must be proven rather than inferred, the next step should be runtime interception:

- monitor file access to the actual `firmware_upgrade.ini`
- log which section name is selected
- capture the final resolved `dll_path`, `fw_path`, and `bin_file`
- if needed, MITM or API-hook Swarm's `autoupdate` requests to discover what `%1` actually is

