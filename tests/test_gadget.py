"""Tests for USB gadget configuration logic."""

from thricegrip.gadget import (
    KEYBOARD_REPORT_DESC,
    MOUSE_REPORT_DESC,
    VENDOR_ID,
    PRODUCT_ID,
)


class TestReportDescriptors:
    """Verify HID report descriptors are well-formed."""

    def test_keyboard_descriptor_starts_with_usage_page(self):
        assert KEYBOARD_REPORT_DESC[:2] == b"\x05\x01"  # Usage Page (Generic Desktop)

    def test_keyboard_descriptor_has_keyboard_usage(self):
        assert b"\x09\x06" in KEYBOARD_REPORT_DESC  # Usage (Keyboard)

    def test_keyboard_descriptor_ends_with_end_collection(self):
        assert KEYBOARD_REPORT_DESC[-1:] == b"\xc0"

    def test_mouse_descriptor_starts_with_usage_page(self):
        assert MOUSE_REPORT_DESC[:2] == b"\x05\x01"

    def test_mouse_descriptor_has_mouse_usage(self):
        assert b"\x09\x02" in MOUSE_REPORT_DESC  # Usage (Mouse)

    def test_mouse_descriptor_ends_with_end_collection(self):
        assert MOUSE_REPORT_DESC[-1:] == b"\xc0"

    def test_descriptors_are_bytes(self):
        assert isinstance(KEYBOARD_REPORT_DESC, bytes)
        assert isinstance(MOUSE_REPORT_DESC, bytes)


class TestDeviceDescriptors:
    """Verify USB device descriptor constants."""

    def test_vendor_id_is_linux_foundation(self):
        assert VENDOR_ID == "0x1d6b"

    def test_product_id_is_composite_gadget(self):
        assert PRODUCT_ID == "0x0104"
