# ROCCAT Swarm firmware_upgrade.dll Analysis

**File:** `C:\Program Files (x86)\ROCCAT\ROCCAT SWARM\firmware_upgrade.dll`
**Size:** 868,816 bytes (848.5 KB)
**Format:** PE32 executable (DLL), Intel i386, stripped, 11 sections
**Build:** MinGW/GCC (libgcc_s_dw2-1.dll, libstdc++-6.dll), Qt 5, Windows GUI subsystem
**Timestamp:** Mon May 12 12:06:57 2025
**ImageBase:** 0x6AA80000

---

## 1. Export Table (70 exports)

### CFirmware_upgrade Class Methods (C++ mangled)

| Export | Demangled | Notes |
|--------|-----------|-------|
| `create` | factory function | Returns CFirmware_upgrade widget |
| `_ZN17CFirmware_upgradeC1EP7QWidget` | `CFirmware_upgrade(QWidget*)` | Constructor |
| `_ZN17CFirmware_upgradeD0Ev` / `D1` / `D2` | Destructors | Virtual + base |
| `connect_vid_pid` | `connect_vid_pid(QVector<ushort>&, QVector<ushort>&)` | Connect VID/PID lists |
| `set_pid` | `set_pid(ushort, ushort, ushort, bool)` | Set VID, PID, type, flag |
| `set_mode` / `get_mode` | `set_mode(uchar)` / `get_mode()` | Operating mode |
| `start_firmware_upgrade` | `start_firmware_upgrade()` | Begin update process |
| `finish_firmware_upgrade` | `finish_firmware_upgrade()` | Complete update |
| `hide_firmware_upgrade` | `hide_firmware_upgrade()` | Hide UI |
| `set_number` / `get_number` | Number (QString) | Device identifier |
| `set_material` / `get_material` | Material (QString) | Device material |
| `set_factory` / `get_factory` | Factory (bool) | Factory mode flag |
| `set_language` / `get_language` | Language (language_type_e) | UI language |
| `set_font` | `set_font()` | Font setup |
| `get_caller` | `get_caller()` | Parent caller |
| `get_widget` | `get_widget()` | Main widget |
| `get_progress_bar` | `get_progress_bar()` | Progress bar widget |
| `init_language` | `init_language()` | Language initialization |
| `retranslate_ui` | `retranslate_ui()` | UI retranslation |
| `load_resource_dll` | `load_resource_dll()` | Load resource DLL |
| `language_translator` | `language_translator()` | Translation object |
| `staticMetaObject` / `metaObject` | Qt MOC metadata | |
| `qt_metacall` / `qt_metacast` / `qt_static_metacall` | Qt meta-object system | |
| `_ZTI17CFirmware_upgrade` | typeinfo | RTTI |
| `_ZTV17CFirmware_upgrade` | vtable | Virtual table |

### HID API Exports (C-style, hidapi-compatible)

| Export | Purpose |
|--------|---------|
| `hid_init` | Initialize HID library |
| `hid_exit` | Cleanup HID library |
| `hid_enumerate` | Enumerate HID devices (standard) |
| `hid_enumerate2` | Enumerate variant 2 |
| `hid_enumerate3` | Enumerate variant 3 |
| `hid_enumerate_com_device` | Enumerate COM port devices |
| `hid_open` | Open device by VID/PID |
| `hid_open_path` | Open device by path |
| `hid_close` | Close device |
| `hid_write` | Write output report (WriteFile) |
| `hid_read` | Read input report (ReadFile) |
| `hid_read_timeout` | Read with timeout |
| `hid_send_feature_report` | Send feature report (HidD_SetFeature) |
| `hid_get_feature_report` | Get feature report (HidD_GetFeature) |
| `hid_set_output_report` | Set output report (HidD_SetOutputReport) |
| `hid_get_input_report` | Get input report (HidD_GetInputReport) |
| `hid_get_manufacturer_string` | Get manufacturer string |
| `hid_get_product_string` | Get product string |
| `hid_get_serial_number_string` | Get serial number |
| `hid_get_indexed_string` | Get indexed string |
| `hid_get_physical_descriptor` | Get physical descriptor |
| `hid_set_nonblocking` | Set non-blocking mode |
| `hid_error` | Get error string |
| `hid_free_enumeration` | Free enumeration list |
| `hid_CheckComPort` | Check COM port availability |
| `hid_Enum_ComPortName` | Enumerate COM port names |

---

## 2. Import Table

### Imported DLLs

| DLL | Category | Key Imports |
|-----|----------|-------------|
| **Qt5Core.dll** | Framework | QSettings, QFile, QProcess, QThread, QSharedMemory, QXmlStreamReader, QDataStream, QTimer, QThreadPool, QLibrary, QFutureInterface |
| **Qt5Gui.dll** | UI | QImage, QPixmap, QPainter, QFont, QColor, QBrush |
| **Qt5Widgets.dll** | UI | QDialog, QWidget, QLabel, QPushButton, QComboBox, QLayout, QGraphicsDropShadowEffect |
| **KERNEL32.dll** | OS | CreateFileA, ReadFile, WriteFile, CloseHandle, CancelIo, CreateEventW, WaitForSingleObject, GetOverlappedResult, CreateProcessW, CreatePipe, GetLastError, Sleep, CreateToolhelp32Snapshot, Process32FirstW/NextW, LoadLibraryA, GetProcAddress |
| **SETUPAPI.dll** | Device enum | SetupDiGetClassDevsA/W, SetupDiEnumDeviceInterfaces, SetupDiGetDeviceInterfaceDetailA/W, SetupDiGetDeviceInstanceIdW, SetupDiOpenDevRegKey, SetupDiDestroyDeviceInfoList |
| **hid.dll** | HID API | HidD_GetHidGuid (via GetProcAddress), HidD_SetFeature, HidD_GetFeature, HidD_SetOutputReport, HidD_GetInputReport, HidD_GetAttributes, HidD_GetPreparsedData, HidD_FreePreparsedData, HidP_GetCaps, HidD_GetSerialNumberString, HidD_GetManufacturerString, HidD_GetProductString, HidD_GetIndexedString, HidD_GetPhysicalDescriptor |
| **ADVAPI32.dll** | Security | GetTokenInformation, OpenProcessToken, RegCloseKey, RegQueryValueExA |
| **USER32.dll** | Window | RegisterDeviceNotificationW, GetClassLongW, SetClassLongW, GetKeyNameTextW |
| **WINMM.dll** | Timing | timeBeginPeriod, timeEndPeriod |
| **msvcrt.dll** | C runtime | Standard C library functions |
| **libgcc_s_dw2-1.dll** | GCC runtime | Exception handling, division |
| **libstdc++-6.dll** | C++ runtime | STL, streams, locale |

### Runtime-loaded DLLs (via QLibrary)

| DLL | Purpose |
|-----|---------|
| `hid.dll` | Windows HID API (loaded dynamically for HidD_* functions) |
| `headset_x86.dll` | Headset-specific firmware update logic (Syn Pro/Max Air) |
| `USBCmdLib.dll` | Holtek ISP USB command library |
| `ISPDLL.dll` | Holtek ISP DLL (Suora keyboard ISP) |
| `Dongle_DFU.dll` | Dongle DFU library (Kain 200 dongle) |
| `PXICtrl3318.dll` | Pixart/PXI controller (PURE SEL) |
| `nordic_x86.dll` | Nordic nRF DFU library |
| `tiLoader.dll` | TI loader (Kain 200 dongle via tiCom) |
| `tiCom.dll` | TI communication library |
| `jFWUpdater.dll` | Firmware updater helper |
| `ConfDLL.dll` / `ConfDLL_x64.dll` | Configuration DLL (Khan Aimo) |
| `AfxDLL.dll` | Application framework helper |

---

## 3. DFU Protocol Analysis

The DLL implements **6 distinct firmware update protocols**, each used by different device families:

### Protocol A: PIC32-based DFU (Syn Pro Air, Syn Max Air headsets)

Used for headsets with PIC32 microcontroller + ATTiny + EXTFLASH + Bluetooth.

**HID Communication:** Feature reports via `hid_send_feature_report` / `hid_get_feature_report`

**Command Sequence:**
1. **Query Device** (Write + Read) - Get device info, Flash ID
2. **Erase Device** (Write + Read) - Erase flash memory
3. **Write Flash** (Write + Read) - Program firmware data
4. **Read Flash** (Write + Read) - Verify written data
5. **Sign Flash** (Write + Read + Verify) - Finalize firmware
6. **DIAGEX power up** - Final activation step

**Multi-target flash regions:**
- Main MCU (PIC32) - primary firmware binary
- EXTFLASH - external flash (sound data, profiles)
- ATTiny - secondary MCU (power management, LED control)
- BT Mini Driver - Bluetooth firmware layer
- BT App Layer - Bluetooth application code
- BT Voice Prompts - Bluetooth voice prompt data

**Mode transitions:**
- App mode -> Bootloader mode: `"Headset in app mode, change to bootloader mode"`
- Bootloader mode -> App mode: after firmware complete
- Timeout detection: `"Reset to DFU mode time out"`

### Protocol B: Neon Device DFU (0x06/0x07 command protocol)

**Command bytes:**
- **0x06**: Start DFU mode command (enter DFU via feature report)
- **0x07**: Check DFU status / Wait for state change / Reboot firmware

**State machine:**
```
App Mode --[0x06]--> DFU Pending --[poll 0x07]--> DFU Ready
DFU Ready --[write buffer]--> Writing --[0x07]--> Verify
Verify --[0x07]--> Reboot --> App Mode
```

**Error handling:**
- `"Check DFU status 0x07 command failed!"` - Status check failure
- `"FW always return pending"` - Device stuck in pending state
- `"FW return DFU state = %1"` - Unexpected state
- `"Writing buffer failed, at %1, try to re-write, retry time: %2"` - Write retry logic
- Retrieves Flash ID for firmware compatibility check

### Protocol C: Holtek ISP (Suora/Suora FX keyboards, generic keyboards)

Uses external `USBCmdLib.dll` or `ISPDLL.dll` for ISP programming.

**ISP Functions (imported from DLL):**
- `ISP_IsConnectedToDevice` - Check connection
- `ISP_ResetToIAP` - Reset to IAP mode
- `ISP_SendAuthentication` - Authenticate
- `ISP_GetInformation` - Get MCU info (Size, PageSize, MaxProgramPage, MaxLockPage, BootloaderSize, MCU NAME)
- `ISP_ReadData` - Read flash
- `ISP_ErasePage` - Erase by page
- `ISP_EraseMass` - Mass erase
- `ISP_WriteProgramB` - Write program (with verify)
- `ISP_GetTransProgress` - Progress polling
- `ISP_CRCCheck` - CRC verification
- `ISP_Reset` - Reset device
- `ISP_Execute` - Execute program
- `ISP_CloseSerialPortConnect` - Close connection

**Additional crypto functions:**
- `CRYPT_SetCommandKey` - Set encryption key
- `CRYPT_EnableCommandKey` - Enable encryption

**Key file:** `//firmware//Command_Key.bin` (encryption key)

**Firmware info keys:**
- `Get flash size`
- `Get page size`
- `Get start address`
- `Get AP version address`
- `Get AP version length`

### Protocol D: Klassic Updater (Kone XP Air, etc.)

Boot mode packet-based protocol:

1. Enter PVT boot mode
2. Open boot mode handle
3. Set Upgrade command + verify response
4. Set packet size + verify response
5. Send file packets + verify response
6. Transmission Completed

**Error strings indicate packet-level protocol:**
- `"Set Upgrade fial"` / `"Set Upgrade Response fial"`
- `"Set packet size fial"` / `"Set packet size Response fial"`
- `"Send file packets fial"` / `"Send file packets Response fial"`

### Protocol E: Kain 200 / Legacy DFU

**Direct HID protocol with checksum verification:**

1. Reset AP mode -> ISP mode
2. Open ISP handle
3. Send firmware start command
4. Write firmware image data sequentially
5. Verify checksum: `"Kain 200 firmware image size = %1, Checksum = %2"`
6. Check sum comparison: `"Check sum not equal, Swarm check sum = %1, firmware check sum = %2, try to re-update!"`
7. Reset to AP mode

**Dongle update:** Uses `Dongle_DFU.dll` with:
- `DFU_Start` - Start DFU process
- `DFU_GetProcessCount` - Get progress count

### Protocol F: PURE/OTA (Bluetooth OTA update)

Used for PURE Air headsets, uses feature reports with start/data packet structure:

**OTA Flow:**
1. `OTAInitial` - Initialize OTA
2. `OTAGetFWInfo` - Get current firmware info
3. Firmware Version Check
4. `OTACheckCrc` - Verify firmware CRC
5. `getFWContent` - Get firmware content (reports length + checksum)
6. `OTACreateObj` - Create firmware object (by index)
7. `OTAFWWrite` - Write firmware data (by index)
8. `OTAFWUpgrade` - Trigger upgrade
9. `OTAReset` - Reset device

**Packet structure (from strings):**
- **Start packet:** Set feature -> Get feature -> verify response
- **Data packet:** Set feature -> Get feature -> verify response
- Error: `"start packet return not meet"` / `"data packet return not meet"` (response validation)

### Protocol G: Nordic nRF DFU (Vulcan2 Mini Air)

Uses external `nrfutil.exe` CLI tool via COM port:

```
nrfutil dfu usb-serial --package <firmware.zip> ...
```

**Flow:**
1. Open HID handle to device
2. Send bootloader mode command via `hid_write`
3. Check COM port for bootloader device
4. Launch `nrfutil.exe` via `CreateProcessW` + `CreatePipe`
5. Monitor stdout for "Device programmed" success
6. Report result

### Protocol H: Khan Aimo (CMedia USB Audio)

Uses external `khan_aimo_fw_update.exe` / `khan_aimo_fw_update64.exe` (or V2 variants).
Also loads CMedia firmware driver: `firmware_driver/isousb.inf`
CMedia flash tool handles register-level access: reads/writes 0xC2-0xC5 and 0xE8 registers.

### Protocol I: PXI/Pixart (PURE SEL)

Uses `PXICtrl3318.dll`:
- `PXI_HidOpen` / `PXI_HidClose` - Device open/close
- `PXI_HidOpenIntf` / `PXI_HidCloseIntf` - Interface open/close
- `PXI_EraseRtData3318` - Erase runtime data
- `PXI_EraseShadowPara3318` - Erase shadow parameters
- `PXI_HidWriteBlockLong` - Write block data
- `PXI_WriteFwBin3318` - Write firmware binary

---

## 4. firmware_upgrade.ini Format

Parsed via `QSettings` (INI format). Loaded from: `firmware//firmware_upgrade.ini` or `firmware_upgrade.ini` relative to firmware path.

### Section Structure

Each device/component has its own INI section with the device name in brackets:

```ini
[Elo Air]                    ; Section = device name
vid = 0x1E7D                 ; USB Vendor ID (hex or decimal)
pid = 0x3A37                 ; USB Product ID (hex or decimal)
dll_path = headset_x86.dll   ; Update helper DLL path
fw_path = firmware/          ; Firmware binary directory
bin_file = firmware.bin       ; Firmware binary filename
headset_version = 0          ; Current headset version (placeholder)
dongle_version = 0           ; Current dongle version (placeholder)
auto_reset = 1               ; Auto-reset after update (bool)
auto_reset_version = 0       ; Version to auto-reset to
1_Version = 0                ; Firmware component 1 version
2_Version = 0                ; Firmware component 2 version
type = 3                     ; Device type enum
device_type = headset        ; Device type string
```

### Known INI Keys

| Key | Type | Purpose |
|-----|------|---------|
| `vid` | int (hex/dec) | USB Vendor ID |
| `pid` | int (hex/dec) | USB Product ID |
| `dll_path` | string | Path to helper DLL |
| `fw_path` | string | Firmware binary directory |
| `bin_file` | string | Firmware binary filename |
| `headset_version` | int | Headset firmware version |
| `dongle_version` | int | Dongle firmware version |
| `auto_reset` | int (bool) | Auto-reset after update |
| `auto_reset_version` | int | Version for auto-reset |
| `1_Version` | int | Component 1 firmware version |
| `2_Version` | int | Component 2 firmware version |
| `version` | int | Generic version field |
| `type` | int | Device type enumeration |
| `device_type` | string | Device type name ("headset", "keyboard", etc.) |
| `EXTFLASH` | section/key | External flash firmware info |
| `disp_name` | string | Display name for UI |
| `driver_path` | string | Driver path (CMedia) |
| `updating_pid` | int | PID while in update/bootloader mode |

### Additional INI/Config Files

| File | Purpose |
|------|---------|
| `firmware_upgrade.ini` | Main firmware config |
| `version.txt` | Version verification file |
| `version.ini` | Version tracking |
| `SWARM.ini` | SWARM application settings |
| `RoccatTalk.ini` | Roccat Talk integration |
| `AlienFx.ini` | Alienware lighting integration |
| `settings.xml` | XML settings (keyboards) |
| `test_value.ini` | Test configuration |
| `info.ini` | Device info (PURE) |

### QSettings Usage Pattern

The DLL uses both `QSettings(filename, IniFormat)` constructor and `QSettings(Format, Scope, org, app)`:
- `beginGroup(section_name)` / `endGroup()` for section navigation
- `value(key, default)` for reading
- `setValue(key, value)` for writing
- `contains(key)` for existence check
- `sync()` for flushing to disk
- `clear()` / `remove(key)` for cleanup

---

## 5. HID Communication Flow

### HID API Wrapper Architecture

The DLL embeds a modified **hidapi** library (Windows backend) with these additions:
- `hid_enumerate2` / `hid_enumerate3` - Extended enumeration
- `hid_enumerate_com_device` - COM port device enumeration
- `hid_CheckComPort` - COM port validation
- `hid_Enum_ComPortName` - COM port name lookup

### Report Types Used

| API Function | Windows API | Direction | Usage |
|--------------|-------------|-----------|-------|
| `hid_send_feature_report` | `HidD_SetFeature` | Host -> Device | DFU commands, configuration writes |
| `hid_get_feature_report` | `HidD_GetFeature` | Device -> Host | Status reads, version queries |
| `hid_set_output_report` | `HidD_SetOutputReport` | Host -> Device | Data transfer |
| `hid_get_input_report` | `HidD_GetInputReport` | Device -> Host | Data reads |
| `hid_write` | `WriteFile` | Host -> Device | Output reports (interrupt transfer) |
| `hid_read` / `hid_read_timeout` | `ReadFile` | Device -> Host | Input reports (interrupt transfer) |

### Report Buffer Sizes

From binary analysis, the most frequently used buffer sizes in the .text section:

| Size (bytes) | Hex | Frequency | Likely Usage |
|--------------|-----|-----------|--------------|
| 8 | 0x08 | Very high | Short command/status reports |
| 20 | 0x14 | High | Medium-length feature reports |
| 32 | 0x20 | High | Standard feature reports |
| 64 | 0x40 | High | Standard HID report size |
| 65 | 0x41 | Medium | 64-byte report + report ID |
| 264 | 0x108 | High | Extended reports (8 header + 256 data) |
| **520** | **0x208** | **62 in .text** | **512-byte data payload + 8-byte header** |

The 520-byte (0x208) buffer is particularly significant -- it appears 62 times in code and represents the primary firmware data transfer packet format: 8 bytes of header/command + 512 bytes of firmware data payload.

### HID Communication Patterns

**Feature Report Pattern (DFU commands):**
```
1. Allocate buffer (e.g., 520 bytes)
2. Set buffer[0] = report_id
3. Set buffer[1..n] = command/data
4. hid_send_feature_report(handle, buffer, size)
5. hid_get_feature_report(handle, response, size)
6. Validate response bytes
```

**Logging on failure:**
- `"hid_send_feature_report fail"` - Write failed
- `"hid_get_feature_report fail, buffer[0] = %1"` - Read failed, logs report ID
- `"hid_get_input_report fail, buffer[0] = %1"` - Input report failed

### DFU-Specific Command Bytes

| Byte | Command | Protocol |
|------|---------|----------|
| 0x06 | Start DFU mode | Neon device DFU |
| 0x07 | Check DFU status / Reboot | Neon device DFU |

---

## 6. Checksum Mechanisms

### CRC-16 CCITT (polynomial 0x1021)

- **Found at:** file offset 0x083D40
- **Used by:** ISP/Holtek updater protocol for firmware verification
- **Context:** Part of `ISP_CRCCheck` flow for Suora/keyboard updates

### CRC-16 Reflected (polynomial 0x8408)

- **Found at:** file offset 0x0072E6
- **Used by:** Kain 200 / legacy firmware protocol
- **Note:** 0x8408 is the bit-reversed form of CRC-16 CCITT (0x1021)

### Simple Additive Checksum (Kain 200)

- After writing the complete firmware image, the host computes a checksum
- Device independently computes its own checksum of the received data
- Comparison: `"Check sum not equal, Swarm check sum = %1, firmware check sum = %2, try to re-update!"`
- On match: `"Check sum correct!"`

### OTA CRC (PURE protocol)

- `OTACheckCrc` function validates firmware CRC before OTA transfer
- Error: `"OTACheckCrc failed with crc: %1"`
- Firmware content validation: `"getFWContent length: %1, checksum: %2"`

### ISP CRC (Holtek)

- External `ISP_CRCCheck` function from `USBCmdLib.dll` / `ISPDLL.dll`
- Verifies programmed flash content against expected CRC

### No CRC-32

Standard CRC-32 polynomials (0xEDB88320 normal, 0x04C11DB7 reversed) were **not found** in the binary. All checksum mechanisms use CRC-16 or simple additive checksums.

---

## 7. Hardcoded VID/PID Values

### Primary: ROCCAT VID 0x1E7D

61 occurrences of 0x1E7D in the binary (as 16-bit LE: `7D 1E`).

**Confirmed VID+PID pairs loaded as x86 immediate values:**

| VID | PID | Hex PID | Product | Evidence |
|-----|-----|---------|---------|----------|
| 0x1E7D | 0x3A39 | 14905 | ROCCAT Elo 7.1 Air (headset) | `mov [esp+4], 0x3A39; mov [esp], 0x1E7D` at 0x00BFD5 |
| 0x1E7D | 0x3A37 | 14903 | ROCCAT Elo 7.1 Air (alt/dongle) | `mov [esp+4], 0x3A37; mov [esp], 0x1E7D` at 0x00C2D3 |
| 0x1E7D | 0x3A38 | 14904 | ROCCAT Elo 7.1 USB | `mov [esp+4], 0x3A38; mov [esp], 0x1E7D` at 0x00C457 |
| 0x1E7D | 0x3A36 | 14902 | ROCCAT Elo 7.1 (variant) | `mov [esp+4], 0x3A36; mov [esp], 0x1E7D` at 0x00C488 |

### Secondary: Holtek VID 0x04D9

8 occurrences in the binary. Used for keyboard ISP mode (Holtek MCU).

**16-bit comparison at 0x00694E:** `cmp word [ebp-0x14], 0x04D9` -- VID check for Holtek devices.
**16-bit comparison at 0x0120D6:** `cmp word [ebp-0x5C], 0x04D9` -- Another Holtek VID check.

### Tertiary: CMedia VID 0x0D8C

9 occurrences. Used for CMedia USB Audio chip (Khan Aimo headset).

| VID | PID | Product | Evidence |
|-----|-----|---------|----------|
| 0x0D8C | 0x0018 | CMedia USB Audio (Khan Aimo) | `cmp edx, 0x00180D8C` at 0x010C5E (combined 32-bit VID:PID check) |

**String confirmation:** `"USB\VID_0D8C&PID_0018"` found in string table.

### Quaternary: Savitech VID 0x26CE

2 occurrences as 16-bit value. Used for Savitech USB audio dongles.
Referenced in v2 INI: `vid = 0x26CE, pid = 0x0A0B`

**PID 0x0A0B** was NOT found as a 32-bit immediate -- it is read from the INI file at runtime rather than hardcoded in code.

### ROCCAT PID Range Values in Code

Additional PIDs found as MOV immediates in the 0x2000-0x4000 range:

| PID | Decimal | Occurrences | Notes |
|-----|---------|-------------|-------|
| 0x3A36 | 14902 | 1 | Elo variant |
| 0x3A37 | 14903 | 1 | Elo Air (matches v3 INI) |
| 0x3A38 | 14904 | 1 | Elo USB |
| 0x3A39 | 14905 | 1 | Elo Air (primary) |
| 0x2710 | 10000 | 7 | Timeout constant (10000ms), not a PID |
| 0x3A98 | 15000 | 3 | Timeout or timer constant (15s) |

### VID/PID Comparison Instructions

| Offset | Instruction | Value | Context |
|--------|-------------|-------|---------|
| 0x013945 | `cmp word [esi+0x10], 0x1E7D` | ROCCAT VID | Device enumeration filter |
| 0x025745 | `cmp si, 0x1E7D` | ROCCAT VID | VID register comparison |
| 0x006415 | `cmp word [ebp-0x2C], 0x0D8C` | CMedia VID | CMedia device detection |
| 0x00694E | `cmp word [ebp-0x14], 0x04D9` | Holtek VID | Keyboard ISP detection |
| 0x0120D6 | `cmp word [ebp-0x5C], 0x04D9` | Holtek VID | Keyboard ISP detection |
| 0x0120E8 | `cmp word [ebp-0x5C], 0x0D8C` | CMedia VID | CMedia detection |

---

## 8. Internal Updater Classes (RTTI)

The DLL contains 13 distinct updater implementations:

| Class | Target Devices |
|-------|---------------|
| `firmware_updater_c` | Base/generic firmware updater |
| `khan_aimo_updater_c` | Khan Aimo headset (CMedia audio) |
| `syn_pro_air_updater_c` | Syn Pro Air headset (PIC32) |
| `syn_max_air_updater_c` | Syn Max Air headset (PIC32) |
| `kone_pro_updater_c` | Kone Pro mouse |
| `kone_xp_air_updater_c` | Kone XP Air mouse |
| `klassic_updater_c` | Klassic-series devices |
| `holtek_updater_c` | Holtek MCU devices (keyboards) |
| `neon_device_updater_c` | Neon devices (0x06/0x07 DFU) |
| `nordic_dongle_updater_c` | Nordic nRF dongles |
| `nordic_mouse_updater_c` | Nordic nRF mice |
| `vulcan2_mini_air_updater_c` | Vulcan II Mini Air keyboard |
| `pure_sel_updater_c` | PURE SEL headset (Pixart) |
| `cmedia_flash_tool_c` | CMedia audio chip flash tool |

---

## 9. Device Names Referenced

| Device | References | Update Protocol |
|--------|------------|-----------------|
| Khan Aimo | 3 | External exe + CMedia driver |
| Kain 200 | 13 | Direct HID DFU + Dongle_DFU.dll |
| Kone Pro Wireless | 2 | kone_pro_updater (via headset_x86.dll) |
| Kone Xp Air | 3 | klassic_updater (boot mode packets) |
| Leadr | 5 | ISP-based (legacy, USB cable required) |
| Suora / Suora FX | 14 | Holtek ISP (USBCmdLib.dll / ISPDLL.dll) |
| Syn Pro Air | 3 | PIC32 DFU (headset_x86.dll) |
| Syn Max Air | 3 | PIC32 DFU (headset_x86.dll) |
| Elo Air | 1 | PIC32 DFU / Neon DFU |
| Vulcan2 Mini Air | 26 | Nordic nRF DFU (nrfutil.exe via COM port) |
| PURE / PURE Air | 32 | OTA Bluetooth update |
| CA300 | 8 | PIC32 DFU |
| TORCH | 2 | Feature report protocol |

---

## 10. Key Paths and File Locations

| Path | Usage |
|------|-------|
| `/Public/Documents/ROCCAT/SWARM/` | Shared firmware storage |
| `firmware//firmware_upgrade.ini` | Firmware configuration |
| `firmware//` | Firmware binary directory |
| `//firmware//Command_Key.bin` | Encryption key for Holtek ISP |
| `/firmware/headset_x86.dll` | Headset update helper |
| `data//firmware//USBCmdLib.dll` | Holtek ISP library |
| `data//suora_fx//USBCmdLib.dll` | Suora FX ISP library |
| `data/PURE_SEL/firmware/PXICtrl3318.dll` | Pixart controller |
| `firmware/ConfDLL/` | Khan Aimo configuration DLLs |
| `firmware_driver/isousb.inf` | CMedia firmware driver INF |
| `\sysnative\pnputil.exe` | PnP utility for driver install |
| `/KoneXpAir/` | Kone XP Air firmware files |

---

## 11. Security / Obfuscation Notes

- Binary is **stripped** (symbols removed, external PDB)
- Uses **CRYPT_SetCommandKey** / **CRYPT_EnableCommandKey** for Holtek ISP firmware encryption
- CMedia update uses dedicated firmware driver (`isousb.inf`)
- **Administrator elevation** check: `"try to reopen app in admin rights"` -- some updates require admin
- Uses `OpenProcessToken` + `GetTokenInformation` for privilege checking
- Uses `QSharedMemory` for single-instance enforcement
- `RegisterDeviceNotificationW` for device plug/unplug detection
