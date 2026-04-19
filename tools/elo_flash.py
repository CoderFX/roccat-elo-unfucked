"""
Elo Air Firmware Flasher — uses Roccat's own firmware_upgrade.dll HID functions

Bypasses the Recovery Tool's VID check by calling the DLL's exported hidapi
directly with our dongle's VID:PID (0x26CE:0x0A0B).

This is the same HID implementation Roccat uses internally.
"""

import ctypes
from ctypes import c_int, c_ushort, c_char_p, c_wchar_p, c_void_p, POINTER, Structure, c_size_t
import os
import sys
import time

# Path to Roccat's DLL
DLL_PATH = r"C:\Program Files (x86)\ROCCAT\ROCCAT SWARM\firmware_upgrade.dll"

# Our dongle
DONGLE_VID = 0x26CE
DONGLE_PID = 0x0A0B

# Original dongle IDs (for reference)
ORIG_VID = 0x1E7D
ORIG_PID = 0x3A37

# Firmware file
FW_PATH = r"C:\Program Files (x86)\ROCCAT\ROCCAT SWARM\data\3A37\firmware\FW_V1.26.bin"


class hid_device_info(Structure):
    pass

hid_device_info._fields_ = [
    ("path", c_char_p),
    ("vendor_id", c_ushort),
    ("product_id", c_ushort),
    ("serial_number", c_wchar_p),
    ("release_number", c_ushort),
    ("manufacturer_string", c_wchar_p),
    ("product_string", c_wchar_p),
    ("usage_page", c_ushort),
    ("usage", c_ushort),
    ("interface_number", c_int),
    ("next", POINTER(hid_device_info)),
]


def main():
    print("=" * 60)
    print("ROCCAT ELO AIR FIRMWARE FLASHER")
    print("Using Roccat's own firmware_upgrade.dll HID functions")
    print("=" * 60)

    # Load the DLL
    print(f"\n[1] Loading {DLL_PATH}...")
    try:
        dll = ctypes.CDLL(DLL_PATH)
    except Exception as e:
        print(f"    Failed: {e}")
        print("    Make sure you're running from the Swarm directory or DLL dependencies are available")
        return

    # Set up function signatures
    dll.hid_init.restype = c_int
    dll.hid_enumerate.restype = POINTER(hid_device_info)
    dll.hid_enumerate.argtypes = [c_ushort, c_ushort]
    dll.hid_free_enumeration.argtypes = [POINTER(hid_device_info)]
    dll.hid_open.restype = c_void_p
    dll.hid_open.argtypes = [c_ushort, c_ushort, c_wchar_p]
    dll.hid_open_path.restype = c_void_p
    dll.hid_open_path.argtypes = [c_char_p]
    dll.hid_write.restype = c_int
    dll.hid_write.argtypes = [c_void_p, c_char_p, c_size_t]
    dll.hid_read.restype = c_int
    dll.hid_read.argtypes = [c_void_p, c_char_p, c_size_t]
    dll.hid_read_timeout.restype = c_int
    dll.hid_read_timeout.argtypes = [c_void_p, c_char_p, c_size_t, c_int]
    dll.hid_set_nonblocking.restype = c_int
    dll.hid_set_nonblocking.argtypes = [c_void_p, c_int]
    dll.hid_close.argtypes = [c_void_p]
    dll.hid_get_feature_report.restype = c_int
    dll.hid_get_feature_report.argtypes = [c_void_p, c_char_p, c_size_t]
    dll.hid_send_feature_report.restype = c_int
    dll.hid_send_feature_report.argtypes = [c_void_p, c_char_p, c_size_t]
    dll.hid_error.restype = c_wchar_p
    dll.hid_error.argtypes = [c_void_p]

    # Initialize HID
    print("[2] Initializing HID...")
    ret = dll.hid_init()
    print(f"    hid_init() = {ret}")

    # Enumerate our dongle
    print(f"\n[3] Enumerating 0x{DONGLE_VID:04X}:0x{DONGLE_PID:04X}...")
    devs = dll.hid_enumerate(DONGLE_VID, DONGLE_PID)
    if not devs:
        print("    Dongle not found!")
        dll.hid_exit()
        return

    dev_info = devs.contents
    found_path = None
    while True:
        print(f"    Found: VID=0x{dev_info.vendor_id:04X} PID=0x{dev_info.product_id:04X} "
              f"usage_page=0x{dev_info.usage_page:04X} iface={dev_info.interface_number} "
              f"path={dev_info.path}")
        if dev_info.usage_page == 0xFFC0:
            found_path = dev_info.path
        if dev_info.next:
            dev_info = dev_info.next.contents
        else:
            break

    dll.hid_free_enumeration(devs)

    if not found_path:
        print("    Vendor HID interface not found!")
        dll.hid_exit()
        return

    # Open the device
    print(f"\n[4] Opening device via Roccat's hidapi...")
    handle = dll.hid_open_path(found_path)
    if not handle:
        err = dll.hid_error(None)
        print(f"    Open failed: {err}")
        dll.hid_exit()
        return
    print(f"    Handle: {handle}")

    # Try reading first (non-blocking) to see device state
    print("\n[5] Reading device state...")
    dll.hid_set_nonblocking(handle, 1)
    buf = ctypes.create_string_buffer(64)
    ret = dll.hid_read(handle, buf, 64)
    if ret > 0:
        data = bytes(buf.raw[:ret])
        print(f"    State data: {' '.join(f'{b:02x}' for b in data)}")
    else:
        print(f"    No data (ret={ret})")

    # Try sending a version query or status check
    # Using the DLL's own write function — this is how Swarm talks to devices
    print("\n[6] Sending status query via Roccat hidapi...")
    cmd = ctypes.create_string_buffer(bytes([0x06, 0x07]))  # report ID + DFU status command
    ret = dll.hid_write(handle, cmd, 2)
    print(f"    hid_write([06 07]) = {ret}")

    if ret > 0:
        print("    Write succeeded! Reading response...")
        resp = ctypes.create_string_buffer(64)
        ret = dll.hid_read_timeout(handle, resp, 64, 2000)
        if ret > 0:
            data = bytes(resp.raw[:ret])
            print(f"    RESPONSE: {' '.join(f'{b:02x}' for b in data)}")
        else:
            err = dll.hid_error(handle)
            print(f"    Read: ret={ret}, error={err}")
    else:
        err = dll.hid_error(handle)
        print(f"    Write failed: ret={ret}, error={err}")

    # Check if dongle is still alive
    print("\n[7] Checking dongle alive...")
    time.sleep(1)
    devs2 = dll.hid_enumerate(DONGLE_VID, DONGLE_PID)
    if devs2:
        print("    Dongle still on USB!")
        dll.hid_free_enumeration(devs2)
    else:
        print("    Dongle dropped off USB (possible DFU mode entry)")
        print("    Scanning for DFU device (0x1E7D:0x3A36)...")
        time.sleep(3)
        dfu_devs = dll.hid_enumerate(ORIG_VID, 0x3A36)
        if dfu_devs:
            print("    *** DFU BOOTLOADER FOUND! ***")
            dfu_info = dfu_devs.contents
            print(f"    VID=0x{dfu_info.vendor_id:04X} PID=0x{dfu_info.product_id:04X}")
            dll.hid_free_enumeration(dfu_devs)
        else:
            print("    No DFU device found. Trying all VIDs with PID 3A36...")
            all_devs = dll.hid_enumerate(0, 0)
            if all_devs:
                dev = all_devs.contents
                while True:
                    if dev.vendor_id not in [0x046D, 0x04D9, 0x0D8C, 0x0E8D, 0x1532, 0x26CE, 0x05E3]:
                        print(f"    Unknown: VID=0x{dev.vendor_id:04X} PID=0x{dev.product_id:04X} "
                              f"\"{dev.product_string}\"")
                    if dev.next:
                        dev = dev.next.contents
                    else:
                        break
                dll.hid_free_enumeration(all_devs)

    dll.hid_close(handle)
    dll.hid_exit()
    print("\nDone.")


if __name__ == "__main__":
    main()
