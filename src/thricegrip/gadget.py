"""USB composite gadget setup and teardown.

Configures the Raspberry Pi's USB-C port as a composite HID device
presenting a keyboard and mouse to the target computer.

Must run as root. Typically called once at boot via systemd.
"""

from __future__ import annotations

import os
from pathlib import Path

GADGET_BASE = Path("/sys/kernel/config/usb_gadget")
GADGET_NAME = "thricegrip"
GADGET_DIR = GADGET_BASE / GADGET_NAME

# Device descriptors — appear as a generic Linux composite gadget.
VENDOR_ID = "0x1d6b"   # Linux Foundation
PRODUCT_ID = "0x0104"  # Multifunction Composite Gadget
BCD_DEVICE = "0x0100"  # v1.0.0
BCD_USB = "0x0200"     # USB 2.0

SERIAL = "thricegrip-001"
MANUFACTURER = "ThricoGrip"
PRODUCT = "ThricoGrip KVM HID Device"

# Standard HID report descriptor for a boot-protocol keyboard (8 bytes).
KEYBOARD_REPORT_DESC = (
    b"\x05\x01"        # Usage Page (Generic Desktop)
    b"\x09\x06"        # Usage (Keyboard)
    b"\xa1\x01"        # Collection (Application)
    b"\x05\x07"        #   Usage Page (Key Codes)
    b"\x19\xe0"        #   Usage Minimum (224) — Left Control
    b"\x29\xe7"        #   Usage Maximum (231) — Right Super
    b"\x15\x00"        #   Logical Minimum (0)
    b"\x25\x01"        #   Logical Maximum (1)
    b"\x75\x01"        #   Report Size (1)
    b"\x95\x08"        #   Report Count (8)
    b"\x81\x02"        #   Input (Data, Variable, Absolute) — Modifier byte
    b"\x95\x01"        #   Report Count (1)
    b"\x75\x08"        #   Report Size (8)
    b"\x81\x03"        #   Input (Constant) — Reserved byte
    b"\x95\x05"        #   Report Count (5)
    b"\x75\x01"        #   Report Size (1)
    b"\x05\x08"        #   Usage Page (LEDs)
    b"\x19\x01"        #   Usage Minimum (1) — Num Lock
    b"\x29\x05"        #   Usage Maximum (5) — Kana
    b"\x91\x02"        #   Output (Data, Variable, Absolute) — LED report
    b"\x95\x01"        #   Report Count (1)
    b"\x75\x03"        #   Report Size (3)
    b"\x91\x03"        #   Output (Constant) — LED padding
    b"\x95\x06"        #   Report Count (6)
    b"\x75\x08"        #   Report Size (8)
    b"\x15\x00"        #   Logical Minimum (0)
    b"\x25\x65"        #   Logical Maximum (101)
    b"\x05\x07"        #   Usage Page (Key Codes)
    b"\x19\x00"        #   Usage Minimum (0)
    b"\x29\x65"        #   Usage Maximum (101)
    b"\x81\x00"        #   Input (Data, Array) — Key array (6 keys)
    b"\xc0"            # End Collection
)

# Standard HID report descriptor for a 3-button relative mouse (4 bytes).
MOUSE_REPORT_DESC = (
    b"\x05\x01"        # Usage Page (Generic Desktop)
    b"\x09\x02"        # Usage (Mouse)
    b"\xa1\x01"        # Collection (Application)
    b"\x09\x01"        #   Usage (Pointer)
    b"\xa1\x00"        #   Collection (Physical)
    b"\x05\x09"        #     Usage Page (Buttons)
    b"\x19\x01"        #     Usage Minimum (1)
    b"\x29\x03"        #     Usage Maximum (3)
    b"\x15\x00"        #     Logical Minimum (0)
    b"\x25\x01"        #     Logical Maximum (1)
    b"\x75\x01"        #     Report Size (1)
    b"\x95\x03"        #     Report Count (3)
    b"\x81\x02"        #     Input (Data, Variable, Absolute) — 3 buttons
    b"\x95\x01"        #     Report Count (1)
    b"\x75\x05"        #     Report Size (5)
    b"\x81\x03"        #     Input (Constant) — Button padding
    b"\x05\x01"        #     Usage Page (Generic Desktop)
    b"\x09\x30"        #     Usage (X)
    b"\x09\x31"        #     Usage (Y)
    b"\x15\x81"        #     Logical Minimum (-127)
    b"\x25\x7f"        #     Logical Maximum (127)
    b"\x75\x08"        #     Report Size (8)
    b"\x95\x02"        #     Report Count (2)
    b"\x81\x06"        #     Input (Data, Variable, Relative) — X, Y
    b"\xc0"            #   End Collection
    b"\xc0"            # End Collection
)


def _write(path: Path, data: str | bytes) -> None:
    """Write string or bytes to a sysfs path."""
    if isinstance(data, str):
        path.write_text(data)
    else:
        path.write_bytes(data)


def setup() -> None:
    """Create the USB composite gadget with keyboard + mouse HID functions.

    Creates /dev/hidg0 (keyboard) and /dev/hidg1 (mouse).
    Requires root privileges.
    """
    if os.geteuid() != 0:
        raise PermissionError("USB gadget setup requires root")

    if GADGET_DIR.exists():
        teardown()

    # Create gadget directory
    GADGET_DIR.mkdir(parents=True, exist_ok=True)

    # Device descriptors
    _write(GADGET_DIR / "idVendor", VENDOR_ID)
    _write(GADGET_DIR / "idProduct", PRODUCT_ID)
    _write(GADGET_DIR / "bcdDevice", BCD_DEVICE)
    _write(GADGET_DIR / "bcdUSB", BCD_USB)

    # Strings
    strings_dir = GADGET_DIR / "strings" / "0x409"
    strings_dir.mkdir(parents=True, exist_ok=True)
    _write(strings_dir / "serialnumber", SERIAL)
    _write(strings_dir / "manufacturer", MANUFACTURER)
    _write(strings_dir / "product", PRODUCT)

    # Configuration
    config_dir = GADGET_DIR / "configs" / "c.1"
    config_strings = config_dir / "strings" / "0x409"
    config_strings.mkdir(parents=True, exist_ok=True)
    _write(config_strings / "configuration", "Keyboard + Mouse")
    _write(config_dir / "MaxPower", "250")

    # Keyboard HID function
    kbd_dir = GADGET_DIR / "functions" / "hid.keyboard"
    kbd_dir.mkdir(parents=True, exist_ok=True)
    _write(kbd_dir / "protocol", "1")     # 1 = keyboard
    _write(kbd_dir / "subclass", "1")     # 1 = boot interface
    _write(kbd_dir / "report_length", "8")
    _write(kbd_dir / "report_desc", KEYBOARD_REPORT_DESC)

    # Mouse HID function
    mouse_dir = GADGET_DIR / "functions" / "hid.mouse"
    mouse_dir.mkdir(parents=True, exist_ok=True)
    _write(mouse_dir / "protocol", "2")   # 2 = mouse
    _write(mouse_dir / "subclass", "1")
    _write(mouse_dir / "report_length", "4")
    _write(mouse_dir / "report_desc", MOUSE_REPORT_DESC)

    # Link functions to configuration
    (config_dir / "hid.keyboard").symlink_to(kbd_dir)
    (config_dir / "hid.mouse").symlink_to(mouse_dir)

    # Activate gadget — bind to the UDC (USB Device Controller)
    udc = next(Path("/sys/class/udc").iterdir()).name
    _write(GADGET_DIR / "UDC", udc)


def teardown() -> None:
    """Remove the USB composite gadget and release device nodes."""
    if not GADGET_DIR.exists():
        return

    # Deactivate
    udc_path = GADGET_DIR / "UDC"
    if udc_path.exists():
        _write(udc_path, "")

    # Unlink functions from config
    config_dir = GADGET_DIR / "configs" / "c.1"
    for link in config_dir.iterdir():
        if link.is_symlink():
            link.unlink()

    # Remove in reverse order
    for func_dir in (GADGET_DIR / "functions").iterdir():
        func_dir.rmdir()
    (config_dir / "strings" / "0x409").rmdir()
    config_dir.rmdir()
    (GADGET_DIR / "strings" / "0x409").rmdir()
    GADGET_DIR.rmdir()


def is_active() -> bool:
    """Check if the gadget is currently active."""
    udc_path = GADGET_DIR / "UDC"
    if not udc_path.exists():
        return False
    return udc_path.read_text().strip() != ""
