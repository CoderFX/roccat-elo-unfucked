"""
DFU Mode Detection Script for Roccat Elo 7.1 Air Dongle

Hypothesis: When we send a HID output report (report ID 0x06) to the dongle,
it enters DFU/bootloader mode and re-enumerates with a different VID/PID.

This script:
1. Snapshots all USB devices BEFORE sending the command
2. Sends ONE HID command to the dongle
3. Waits and repeatedly scans for NEW USB devices
4. Reports any new device that appeared (the DFU bootloader)
"""

import sys
import time
import ctypes
from ctypes import wintypes

# Add Python313 to path for hid module
sys.path.insert(0, r"C:\Users\gelum\AppData\Local\Programs\Python\Python313\Lib\site-packages")
import hid

# Also try libusb for broader device scanning
try:
    import usb.core
    import usb.backend.libusb1 as be
    LIBUSB_BACKEND = be.get_backend(find_library=lambda x: r'C:\msys64\mingw64\bin\libusb-1.0.dll')
    HAS_LIBUSB = LIBUSB_BACKEND is not None
except ImportError:
    HAS_LIBUSB = False


def get_all_hid_devices():
    """Snapshot all HID devices as a set of (vid, pid, product, path) tuples."""
    devices = set()
    for d in hid.enumerate():
        devices.add((d['vendor_id'], d['product_id'], d['product_string']))
    return devices


def get_all_usb_devices():
    """Snapshot all USB devices via libusb."""
    if not HAS_LIBUSB:
        return set()
    devices = set()
    for d in usb.core.find(find_all=True, backend=LIBUSB_BACKEND):
        try:
            prod = d.product or "unknown"
        except Exception:
            prod = "unknown"
        devices.add((d.idVendor, d.idProduct, prod))
    return devices


def send_hid_command(report_id, cmd_byte):
    """Send a single HID output report to the Roccat dongle."""
    path = None
    for d in hid.enumerate(0x26CE, 0x0A0B):
        if d['usage_page'] == 0xFFC0:
            path = d['path']
            break

    if not path:
        return False, "Dongle not found in HID enumeration"

    # Use Windows WriteFile for clean write
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateFileW(
        path.decode(),
        0xC0000000,  # GENERIC_READ | GENERIC_WRITE
        3,           # FILE_SHARE_READ | FILE_SHARE_WRITE
        None, 3, 0, None
    )

    if handle == -1 or handle == 0xFFFFFFFFFFFFFFFF:
        return False, f"Failed to open device: error {ctypes.GetLastError()}"

    wbuf = ctypes.create_string_buffer(2)
    wbuf[0] = report_id
    wbuf[1] = cmd_byte
    written = wintypes.DWORD(0)
    ret = kernel32.WriteFile(handle, wbuf, 2, ctypes.byref(written), None)
    err = ctypes.GetLastError() if not ret else 0
    kernel32.CloseHandle(handle)

    return ret != 0, f"WriteFile ret={ret} written={written.value} err={err}"


def main():
    print("=" * 60)
    print("DFU MODE DETECTION SCRIPT")
    print("=" * 60)

    # Step 1: Snapshot before
    print("\n[1] Snapshotting all USB/HID devices BEFORE command...")
    hid_before = get_all_hid_devices()
    usb_before = get_all_usb_devices()
    print(f"    HID devices: {len(hid_before)}")
    print(f"    USB devices: {len(usb_before)}")

    # Verify dongle is present
    dongle_present = any(vid == 0x26CE and pid == 0x0A0B for vid, pid, _ in hid_before)
    if not dongle_present:
        print("\n[!] Dongle (26CE:0A0B) not found! Plug it in first.")
        return
    print("    Dongle (26CE:0A0B) confirmed present.")

    # Step 2: Send ONE command
    print(f"\n[2] Sending HID command: report_id=0x06, cmd=0x01...")
    success, msg = send_hid_command(0x06, 0x01)
    print(f"    Result: {msg}")

    # Step 3: Scan repeatedly for new devices
    print(f"\n[3] Scanning for NEW devices (20 seconds)...")
    print("    (Looking for DFU bootloader device)")

    start = time.time()
    found_new = False
    scan_count = 0

    while time.time() - start < 20:
        time.sleep(0.5)
        scan_count += 1

        hid_after = get_all_hid_devices()
        usb_after = get_all_usb_devices()

        # Find NEW devices (in after but not in before)
        new_hid = hid_after - hid_before
        new_usb = usb_after - usb_before

        # Also check if dongle disappeared
        dongle_gone = not any(vid == 0x26CE and pid == 0x0A0B for vid, pid, _ in hid_after)

        elapsed = time.time() - start

        if new_hid or new_usb:
            found_new = True
            print(f"\n    *** NEW DEVICE(S) FOUND at {elapsed:.1f}s! ***")
            for vid, pid, prod in new_hid:
                print(f"    [HID] VID=0x{vid:04X} PID=0x{pid:04X} \"{prod}\"")
            for vid, pid, prod in new_usb:
                if (vid, pid, prod) not in new_hid:  # avoid duplicates
                    print(f"    [USB] VID=0x{vid:04X} PID=0x{pid:04X} \"{prod}\"")

        if dongle_gone and scan_count <= 4:
            print(f"    [{elapsed:.1f}s] Dongle dropped off USB (expected for DFU mode entry)")

        if scan_count % 4 == 0 and not found_new:
            print(f"    [{elapsed:.1f}s] ...scanning ({len(hid_after)} HID, {len(usb_after)} USB)...")

    # Step 4: Summary
    print(f"\n{'=' * 60}")
    if found_new:
        print("RESULT: New device(s) appeared! This is likely the DFU bootloader.")
        print("The 'crashes' were DFU mode entries all along!")
    else:
        # Final check — dongle status
        final_hid = get_all_hid_devices()
        dongle_back = any(vid == 0x26CE and pid == 0x0A0B for vid, pid, _ in final_hid)
        if dongle_back:
            print("RESULT: Dongle still present, no new devices. Command had no effect.")
        else:
            print("RESULT: Dongle disappeared but no new device appeared.")
            print("Possible explanations:")
            print("  1. DFU device uses a driver that hides it from HID/libusb enumeration")
            print("  2. DFU re-enumeration takes longer than 20 seconds")
            print("  3. The dongle truly crashed (not DFU)")
            print("  4. DFU device needs WinUSB driver to be visible")
            print("\nTry: Check Device Manager for unknown/unrecognized devices!")
    print("=" * 60)


if __name__ == "__main__":
    main()
