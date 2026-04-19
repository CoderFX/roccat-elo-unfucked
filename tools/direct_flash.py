"""
Direct Flash Tool — bypasses hid_open VID/PID matching by using hid_open_path

Uses Roccat's own 32-bit firmware_upgrade.dll with hid_open_path() to open
our dongle's HID device directly by path, avoiding the VID/PID filter.
"""

import ctypes
from ctypes import c_int, c_ushort, c_char_p, c_wchar_p, c_void_p, POINTER, Structure, c_size_t
import os
import sys
import time

DLL_DIR = r"C:\Program Files (x86)\ROCCAT\ROCCAT SWARM"
DLL_PATH = os.path.join(DLL_DIR, "firmware_upgrade.dll")

# Our dongle's HID path (from hidapi enumeration)
DEVICE_PATH = rb"\\?\HID#VID_26CE&PID_0A0B&MI_06#a&2cc00ac0&0&0000#{4d1e55b2-f16f-11cf-88cb-001111000030}"


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
    print("DIRECT FLASH — hid_open_path bypass")
    print("=" * 60)

    # Change to DLL directory so it finds dependencies
    os.chdir(DLL_DIR)

    print("\n[1] Loading firmware_upgrade.dll (32-bit)...")
    try:
        dll = ctypes.CDLL(DLL_PATH)
        print("    Loaded OK")
    except Exception as e:
        print("    FAILED: %s" % e)
        return

    # Set up function signatures
    dll.hid_init.restype = c_int
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
    dll.hid_send_feature_report.restype = c_int
    dll.hid_send_feature_report.argtypes = [c_void_p, c_char_p, c_size_t]
    dll.hid_get_feature_report.restype = c_int
    dll.hid_get_feature_report.argtypes = [c_void_p, c_char_p, c_size_t]
    dll.hid_error.restype = c_wchar_p
    dll.hid_error.argtypes = [c_void_p]
    dll.hid_enumerate.restype = POINTER(hid_device_info)
    dll.hid_enumerate.argtypes = [c_ushort, c_ushort]
    dll.hid_free_enumeration.argtypes = [POINTER(hid_device_info)]

    # Initialize
    print("[2] hid_init()...")
    ret = dll.hid_init()
    print("    ret = %d" % ret)

    # First verify we can enumerate the device
    print("\n[3] Enumerating 0x26CE:0x0A0B...")
    devs = dll.hid_enumerate(0x26CE, 0x0A0B)
    if devs:
        dev = devs.contents
        found_path = None
        while True:
            path_str = dev.path.decode('ascii') if dev.path else "None"
            print("    VID=0x%04X PID=0x%04X iface=%d usage=0x%04X path=%s" % (
                dev.vendor_id, dev.product_id, dev.interface_number,
                dev.usage_page, path_str[:80]))
            if dev.usage_page == 0xFFC0:
                found_path = dev.path
            if dev.next:
                dev = dev.next.contents
            else:
                break
        dll.hid_free_enumeration(devs)
    else:
        print("    NOT FOUND via enumerate")
        found_path = DEVICE_PATH

    # Try hid_open_path with the actual device path
    path_to_use = found_path if found_path else DEVICE_PATH
    print("\n[4] hid_open_path(%s)..." % path_to_use[:60])
    handle = dll.hid_open_path(path_to_use)

    if not handle:
        err = dll.hid_error(None)
        print("    FAILED: %s" % err)

        # Try with hardcoded path
        print("\n[4b] Trying hardcoded path...")
        handle = dll.hid_open_path(DEVICE_PATH)
        if not handle:
            err = dll.hid_error(None)
            print("    ALSO FAILED: %s" % err)
            dll.hid_exit()
            return

    print("    SUCCESS! Handle = 0x%X" % handle)

    # Try reading device state
    print("\n[5] Reading device state (non-blocking)...")
    dll.hid_set_nonblocking(handle, 1)
    buf = ctypes.create_string_buffer(64)
    ret = dll.hid_read(handle, buf, 64)
    if ret > 0:
        data = bytes(buf.raw[:ret])
        print("    DATA: %s" % ' '.join('%02x' % b for b in data))
    else:
        print("    No data (ret=%d)" % ret)

    # Try feature report read
    print("\n[6] Feature reports...")
    for rid in range(0, 8):
        fbuf = ctypes.create_string_buffer(64)
        fbuf[0] = rid
        ret = dll.hid_get_feature_report(handle, fbuf, 64)
        if ret > 0:
            data = bytes(fbuf.raw[:ret])
            print("    Report 0x%02X: %s" % (rid, ' '.join('%02x' % b for b in data[:20])))

    # If we got here, the DLL CAN open the device!
    # Now try a safe write (DFU status query 0x07)
    print("\n[7] Writing DFU status query [06 07]...")
    cmd = ctypes.create_string_buffer(b"\x06\x07")
    ret = dll.hid_write(handle, cmd, 2)
    print("    hid_write ret = %d" % ret)

    if ret >= 0:
        err = dll.hid_error(handle)
        print("    Error: %s" % err)

        # Try to read response
        resp = ctypes.create_string_buffer(64)
        ret = dll.hid_read_timeout(handle, resp, 64, 2000)
        if ret > 0:
            data = bytes(resp.raw[:ret])
            print("    RESPONSE: %s" % ' '.join('%02x' % b for b in data))
        else:
            print("    Read ret = %d" % ret)

    dll.hid_close(handle)
    dll.hid_exit()
    print("\nDone.")


if __name__ == "__main__":
    main()
