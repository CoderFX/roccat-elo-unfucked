"""
DFU Probe Tool for Roccat Elo 7.1 Air Dongle

Phase 1: Discover the bootloader device
- Snapshot all USB/HID devices
- Send DFU mode entry command (report ID 0x06)
- Monitor for new device appearing (the bootloader)
- If found, dump its HID descriptor and capabilities

Phase 2 (if bootloader found): Attempt firmware dump
- Open HID to bootloader device
- Try reading flash memory
- Try querying device info

Usage: Run with dongle plugged in. Will send ONE command.
"""

import sys
import os
import time
import ctypes
from ctypes import wintypes
import threading

sys.path.insert(0, r"C:\Users\gelum\AppData\Local\Programs\Python\Python313\Lib\site-packages")
import hid

try:
    import usb.core
    import usb.backend.libusb1 as be
    LIBUSB_BACKEND = be.get_backend(find_library=lambda x: r'C:\msys64\mingw64\bin\libusb-1.0.dll')
    HAS_LIBUSB = LIBUSB_BACKEND is not None
except ImportError:
    HAS_LIBUSB = False


def snapshot_hid():
    """Return set of (vid, pid, product, usage_page, usage, iface, path)."""
    devices = set()
    for d in hid.enumerate():
        devices.add((
            d['vendor_id'], d['product_id'], d['product_string'],
            d['usage_page'], d['usage'], d['interface_number'],
            d['path']
        ))
    return devices


def snapshot_usb():
    """Return set of (vid, pid, product) via libusb."""
    if not HAS_LIBUSB:
        return set()
    devices = set()
    for d in usb.core.find(find_all=True, backend=LIBUSB_BACKEND):
        try:
            prod = d.product or "?"
        except:
            prod = "?"
        devices.add((d.idVendor, d.idProduct, prod))
    return devices


def send_dfu_command():
    """Send DFU mode entry command to dongle. Returns (success, message)."""
    path = None
    for d in hid.enumerate(0x26CE, 0x0A0B):
        if d['usage_page'] == 0xFFC0:
            path = d['path']
            break

    if not path:
        return False, "Dongle HID not found"

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateFileW(
        path.decode(), 0xC0000000, 3, None, 3, 0, None
    )
    if handle == -1 or handle == 0xFFFFFFFFFFFFFFFF:
        return False, f"Open failed: {ctypes.GetLastError()}"

    # Send report ID 0x06 with command byte 0x01
    # This should trigger DFU mode entry based on firmware_upgrade.dll analysis
    wbuf = ctypes.create_string_buffer(2)
    wbuf[0] = 0x06  # report ID
    wbuf[1] = 0x01  # command byte
    written = wintypes.DWORD(0)
    ret = kernel32.WriteFile(handle, wbuf, 2, ctypes.byref(written), None)
    err = ctypes.GetLastError() if not ret else 0
    kernel32.CloseHandle(handle)

    return ret != 0, f"WriteFile ret={ret} written={written.value} err={err}"


def probe_new_device(vid, pid, product, usage_page, usage, iface, path):
    """Try to probe a newly discovered HID device."""
    print(f"\n{'='*60}")
    print(f"PROBING NEW DEVICE: VID=0x{vid:04X} PID=0x{pid:04X}")
    print(f"  Product: {product}")
    print(f"  UsagePage: 0x{usage_page:04X} Usage: 0x{usage:04X} Interface: {iface}")
    print(f"{'='*60}")

    try:
        dev = hid.device()
        dev.open_path(path)
        print(f"  Opened successfully!")

        # Try reading (non-blocking)
        dev.set_nonblocking(True)
        for _ in range(10):
            data = dev.read(64)
            if data:
                print(f"  Unsolicited data: {' '.join(f'{b:02x}' for b in data)}")
            time.sleep(0.1)

        # Try get_feature_report for various report IDs
        print("  Feature reports:")
        for rid in range(0, 16):
            try:
                data = dev.get_feature_report(rid, 64)
                if data and any(b != 0 for b in data[1:]):
                    print(f"    Report 0x{rid:02X}: {' '.join(f'{b:02x}' for b in data[:20])}")
            except:
                pass

        dev.close()
    except Exception as e:
        print(f"  Failed to open: {e}")

    # Also get Windows HID caps
    try:
        kernel32 = ctypes.windll.kernel32
        hid_dll = ctypes.windll.hid

        handle = kernel32.CreateFileW(
            path.decode() if isinstance(path, bytes) else path,
            0x80000000, 3, None, 3, 0, None  # GENERIC_READ
        )
        if handle and handle != 0xFFFFFFFFFFFFFFFF:
            ppd = ctypes.c_void_p()
            if hid_dll.HidD_GetPreparsedData(handle, ctypes.byref(ppd)):
                class HIDP_CAPS(ctypes.Structure):
                    _fields_ = [
                        ('Usage', ctypes.c_ushort), ('UsagePage', ctypes.c_ushort),
                        ('InputReportByteLength', ctypes.c_ushort),
                        ('OutputReportByteLength', ctypes.c_ushort),
                        ('FeatureReportByteLength', ctypes.c_ushort),
                        ('Reserved', ctypes.c_ushort * 17),
                        ('NumberLinkCollectionNodes', ctypes.c_ushort),
                        ('NumberInputButtonCaps', ctypes.c_ushort),
                        ('NumberInputValueCaps', ctypes.c_ushort),
                        ('NumberInputDataIndices', ctypes.c_ushort),
                        ('NumberOutputButtonCaps', ctypes.c_ushort),
                        ('NumberOutputValueCaps', ctypes.c_ushort),
                        ('NumberOutputDataIndices', ctypes.c_ushort),
                        ('NumberFeatureButtonCaps', ctypes.c_ushort),
                        ('NumberFeatureValueCaps', ctypes.c_ushort),
                        ('NumberFeatureDataIndices', ctypes.c_ushort),
                    ]
                caps = HIDP_CAPS()
                hid_dll.HidP_GetCaps(ppd, ctypes.byref(caps))
                print(f"  HID Caps: In={caps.InputReportByteLength}B Out={caps.OutputReportByteLength}B Feat={caps.FeatureReportByteLength}B")
                print(f"  Usage=0x{caps.Usage:04X} UsagePage=0x{caps.UsagePage:04X}")
                hid_dll.HidD_FreePreparsedData(ppd)
            kernel32.CloseHandle(handle)
    except Exception as e:
        print(f"  HID Caps failed: {e}")


def main():
    print("=" * 60)
    print("ROCCAT ELO AIR DFU PROBE TOOL")
    print("=" * 60)

    # Step 1: Verify dongle present
    dongle = [d for d in hid.enumerate(0x26CE, 0x0A0B) if d['usage_page'] == 0xFFC0]
    if not dongle:
        print("\n[!] Dongle (26CE:0A0B) not found!")
        print("    Plug it in (use button-hold reset if needed)")
        return
    print(f"\n[OK] Dongle found: {dongle[0]['product_string']}")

    # Step 2: Snapshot BEFORE
    print("\n[1] Snapshotting all devices BEFORE DFU command...")
    hid_before = snapshot_hid()
    usb_before = snapshot_usb()

    # Also snapshot via PowerShell for devices hidapi can't see
    print(f"    {len(hid_before)} HID devices, {len(usb_before)} USB devices")

    # Step 3: Send DFU command
    print("\n[2] Sending DFU mode entry command (report 0x06, cmd 0x01)...")
    success, msg = send_dfu_command()
    print(f"    {msg}")

    if not success:
        print("    Write failed! Aborting.")
        return

    # Step 4: Monitor for new devices
    print("\n[3] Monitoring for new devices (30 seconds)...")
    print("    Looking for bootloader device after DFU entry...")
    sys.stdout.flush()

    start = time.time()
    found_new_hid = set()
    found_new_usb = set()
    dongle_gone_at = None

    while time.time() - start < 30:
        time.sleep(0.5)
        elapsed = time.time() - start

        hid_now = snapshot_hid()
        usb_now = snapshot_usb()

        # Check if dongle disappeared
        dongle_still = any(
            vid == 0x26CE and pid == 0x0A0B
            for vid, pid, _, _, _, _, _ in hid_now
        )
        if not dongle_still and dongle_gone_at is None:
            dongle_gone_at = elapsed
            print(f"    [{elapsed:.1f}s] Dongle dropped off USB (DFU entry!)")
            sys.stdout.flush()

        # Check for NEW HID devices
        new_hid = hid_now - hid_before
        for dev_tuple in new_hid:
            if dev_tuple not in found_new_hid:
                found_new_hid.add(dev_tuple)
                vid, pid, prod, up, u, iface, path = dev_tuple
                print(f"    [{elapsed:.1f}s] *** NEW HID: VID=0x{vid:04X} PID=0x{pid:04X} \"{prod}\" UP=0x{up:04X}")
                sys.stdout.flush()

        # Check for NEW USB devices (libusb)
        new_usb = usb_now - usb_before
        for dev_tuple in new_usb:
            if dev_tuple not in found_new_usb:
                found_new_usb.add(dev_tuple)
                vid, pid, prod = dev_tuple
                print(f"    [{elapsed:.1f}s] *** NEW USB: VID=0x{vid:04X} PID=0x{pid:04X} \"{prod}\"")
                sys.stdout.flush()

        # Progress indicator
        if int(elapsed) % 5 == 0 and int(elapsed * 2) % 2 == 0:
            print(f"    [{elapsed:.0f}s] scanning... ({len(hid_now)} HID, {len(usb_now)} USB)")
            sys.stdout.flush()

    # Step 5: Results
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")

    if dongle_gone_at:
        print(f"  Dongle dropped off USB at {dongle_gone_at:.1f}s")
    else:
        print("  Dongle STILL present (command may not have triggered DFU)")

    if found_new_hid or found_new_usb:
        print(f"\n  *** BOOTLOADER DEVICE(S) FOUND! ***")
        for vid, pid, prod, up, u, iface, path in found_new_hid:
            print(f"  [HID] VID=0x{vid:04X} PID=0x{pid:04X} \"{prod}\"")
            probe_new_device(vid, pid, prod, up, u, iface, path)
        for vid, pid, prod in found_new_usb:
            print(f"  [USB] VID=0x{vid:04X} PID=0x{pid:04X} \"{prod}\"")
    else:
        print("\n  No new devices appeared.")
        print("  Possible reasons:")
        print("    1. Bootloader uses a WinUSB/vendor driver (invisible to HID/libusb)")
        print("    2. Bootloader re-enumeration takes >30 seconds")
        print("    3. Device truly crashed (not DFU)")
        print("    4. Bootloader enumerates on a different USB port/hub")
        print("\n  CHECK DEVICE MANAGER for unknown/unrecognized devices!")

    print(f"\n{'='*60}")


if __name__ == "__main__":
    main()
