"""Tests for the HID module — keyboard and mouse injection logic.

These tests verify HID report construction and key mapping without
requiring actual /dev/hidg* device nodes.
"""

from __future__ import annotations

import struct
from unittest.mock import patch, MagicMock

import pytest

from thricegrip import hid


class TestKeyCodes:
    """Verify keycode lookup and coverage."""

    def test_all_lowercase_letters_mapped(self):
        for ch in "abcdefghijklmnopqrstuvwxyz":
            assert ch in hid._KEYCODES, f"Missing keycode for '{ch}'"

    def test_all_digits_mapped(self):
        for ch in "0123456789":
            assert ch in hid._KEYCODES, f"Missing keycode for '{ch}'"

    def test_common_keys_mapped(self):
        for key in ("enter", "esc", "backspace", "tab", "space", "up", "down", "left", "right"):
            assert key in hid._KEYCODES

    def test_function_keys_mapped(self):
        for i in range(1, 13):
            assert f"f{i}" in hid._KEYCODES

    def test_shift_chars_all_have_base_keys(self):
        for shifted, base in hid._SHIFT_CHARS.items():
            assert base in hid._KEYCODES, f"Shift char '{shifted}' maps to '{base}' which has no keycode"


class TestPressKey:
    """Verify keyboard report generation."""

    @patch("thricegrip.hid._release_keyboard")
    @patch("thricegrip.hid._write_keyboard_report")
    def test_press_key_calls_write_and_release(self, mock_write, mock_release):
        hid.press_key("a")
        mock_write.assert_called_once_with(0, 0x04)
        mock_release.assert_called_once()

    @patch("thricegrip.hid._release_keyboard")
    @patch("thricegrip.hid._write_keyboard_report")
    def test_press_key_with_ctrl(self, mock_write, mock_release):
        hid.press_key("a", ["ctrl"])
        mock_write.assert_called_once_with(0x01, 0x04)

    @patch("thricegrip.hid._release_keyboard")
    @patch("thricegrip.hid._write_keyboard_report")
    def test_press_key_with_multiple_modifiers(self, mock_write, mock_release):
        hid.press_key("a", ["ctrl", "shift"])
        mock_write.assert_called_once_with(0x03, 0x04)

    @patch("thricegrip.hid._release_keyboard")
    @patch("thricegrip.hid._write_keyboard_report")
    def test_unknown_key_raises(self, mock_write, mock_release):
        with pytest.raises(ValueError, match="Unknown key"):
            hid.press_key("nonexistent_key")


class TestWriteKeyboardReport:
    """Verify raw report byte format."""

    def test_report_format(self):
        """Keyboard report is 8 bytes: [mod, 0, keycode, 0, 0, 0, 0, 0]."""
        import io
        buf = io.BytesIO()
        mock_path = MagicMock()
        mock_path.open.return_value.__enter__ = lambda s: buf
        mock_path.open.return_value.__exit__ = lambda s, *a: None

        with patch.object(hid, "KEYBOARD_DEV", mock_path):
            hid._write_keyboard_report(0x01, 0x04)

        report = buf.getvalue()
        assert len(report) == 8
        assert report[0] == 0x01  # ctrl modifier
        assert report[1] == 0x00  # reserved
        assert report[2] == 0x04  # 'a' keycode

    def test_release_report_is_zeros(self):
        import io
        buf = io.BytesIO()
        mock_path = MagicMock()
        mock_path.open.return_value.__enter__ = lambda s: buf
        mock_path.open.return_value.__exit__ = lambda s, *a: None

        with patch.object(hid, "KEYBOARD_DEV", mock_path):
            hid._release_keyboard()

        assert buf.getvalue() == b"\x00" * 8


class TestTypeString:
    """Verify string typing translates characters correctly."""

    @patch("thricegrip.hid.press_key")
    def test_type_lowercase(self, mock_press):
        hid.type_string("ab")
        assert mock_press.call_count == 2
        mock_press.assert_any_call("a")
        mock_press.assert_any_call("b")

    @patch("thricegrip.hid.press_key")
    def test_type_uppercase_uses_shift(self, mock_press):
        hid.type_string("A")
        mock_press.assert_called_once_with("a", ["shift"])

    @patch("thricegrip.hid.press_key")
    def test_type_space(self, mock_press):
        hid.type_string(" ")
        mock_press.assert_called_once_with("space")

    @patch("thricegrip.hid.press_key")
    def test_type_newline(self, mock_press):
        hid.type_string("\n")
        mock_press.assert_called_once_with("enter")

    @patch("thricegrip.hid.press_key")
    def test_type_tab(self, mock_press):
        hid.type_string("\t")
        mock_press.assert_called_once_with("tab")

    @patch("thricegrip.hid.press_key")
    def test_type_shifted_symbol(self, mock_press):
        hid.type_string("!")
        mock_press.assert_called_once_with("1", ["shift"])

    @patch("thricegrip.hid.press_key")
    def test_type_mixed_string(self, mock_press):
        hid.type_string("Hi!")
        assert mock_press.call_count == 3


class TestHotkey:
    """Verify hotkey combinations."""

    @patch("thricegrip.hid.press_key")
    def test_ctrl_c(self, mock_press):
        hid.hotkey("ctrl", "c")
        mock_press.assert_called_once_with("c", ["ctrl"])

    @patch("thricegrip.hid.press_key")
    def test_ctrl_alt_delete(self, mock_press):
        hid.hotkey("ctrl", "alt", "delete")
        mock_press.assert_called_once_with("delete", ["ctrl", "alt"])

    @patch("thricegrip.hid.press_key")
    def test_empty_hotkey_is_noop(self, mock_press):
        hid.hotkey()
        mock_press.assert_not_called()


class TestMouse:
    """Verify mouse report generation."""

    @patch("thricegrip.hid._write_mouse_report")
    def test_click_left(self, mock_write):
        hid.click("left")
        assert mock_write.call_count == 2
        mock_write.assert_any_call(1, 0, 0)  # press
        mock_write.assert_any_call(0, 0, 0)  # release

    @patch("thricegrip.hid._write_mouse_report")
    def test_click_right(self, mock_write):
        hid.click("right")
        mock_write.assert_any_call(2, 0, 0)

    @patch("thricegrip.hid._write_mouse_report")
    def test_move_mouse_small(self, mock_write):
        hid.move_mouse(10, -5)
        mock_write.assert_called_once_with(0, 10, -5)

    @patch("thricegrip.hid._write_mouse_report")
    def test_move_mouse_large_chunked(self, mock_write):
        hid.move_mouse(200, 0)
        assert mock_write.call_count == 2
        calls = mock_write.call_args_list
        assert calls[0][0] == (0, 127, 0)
        assert calls[1][0] == (0, 73, 0)

    @patch("thricegrip.hid._write_mouse_report")
    def test_move_mouse_negative_large(self, mock_write):
        hid.move_mouse(-200, 0)
        assert mock_write.call_count == 2
        calls = mock_write.call_args_list
        assert calls[0][0] == (0, -127, 0)
        assert calls[1][0] == (0, -73, 0)

    def test_write_mouse_report_format(self):
        import io
        buf = io.BytesIO()
        mock_path = MagicMock()
        mock_path.open.return_value.__enter__ = lambda s: buf
        mock_path.open.return_value.__exit__ = lambda s, *a: None

        with patch.object(hid, "MOUSE_DEV", mock_path):
            hid._write_mouse_report(1, 10, -5, 0)

        report = buf.getvalue()
        vals = struct.unpack("4b", report)
        assert vals == (1, 10, -5, 0)

    def test_write_mouse_report_clamps_values(self):
        import io
        buf = io.BytesIO()
        mock_path = MagicMock()
        mock_path.open.return_value.__enter__ = lambda s: buf
        mock_path.open.return_value.__exit__ = lambda s, *a: None

        with patch.object(hid, "MOUSE_DEV", mock_path):
            hid._write_mouse_report(0, 200, -200, 0)

        vals = struct.unpack("4b", buf.getvalue())
        assert vals[1] == 127
        assert vals[2] == -127

    @patch("thricegrip.hid._write_mouse_report")
    def test_scroll(self, mock_write):
        hid.scroll(-3)
        mock_write.assert_called_once_with(0, 0, 0, -3)

    @patch("thricegrip.hid._write_mouse_report")
    def test_double_click(self, mock_write):
        hid.double_click("left")
        # 2 clicks = 4 reports (press+release each)
        assert mock_write.call_count == 4
