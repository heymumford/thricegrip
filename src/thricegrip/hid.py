"""Keyboard and mouse injection via USB HID gadget.

Writes HID reports to /dev/hidg0 (keyboard) and /dev/hidg1 (mouse).
These device nodes are created by the USB composite gadget setup script.
"""

from __future__ import annotations

import struct
import time
from pathlib import Path

KEYBOARD_DEV = Path("/dev/hidg0")
MOUSE_DEV = Path("/dev/hidg1")

# Inter-keystroke delay (seconds). Prevents dropped keys on slow targets.
KEY_DELAY = 0.02

# USB HID keycodes for printable characters and common keys.
_KEYCODES: dict[str, int] = {
    "a": 0x04, "b": 0x05, "c": 0x06, "d": 0x07, "e": 0x08, "f": 0x09,
    "g": 0x0A, "h": 0x0B, "i": 0x0C, "j": 0x0D, "k": 0x0E, "l": 0x0F,
    "m": 0x10, "n": 0x11, "o": 0x12, "p": 0x13, "q": 0x14, "r": 0x15,
    "s": 0x16, "t": 0x17, "u": 0x18, "v": 0x19, "w": 0x1A, "x": 0x1B,
    "y": 0x1C, "z": 0x1D,
    "1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    "enter": 0x28, "esc": 0x29, "backspace": 0x2A, "tab": 0x2B,
    "space": 0x2C, "-": 0x2D, "=": 0x2E, "[": 0x2F, "]": 0x30,
    "\\": 0x31, ";": 0x33, "'": 0x34, "`": 0x35, ",": 0x36,
    ".": 0x37, "/": 0x38,
    "capslock": 0x39, "f1": 0x3A, "f2": 0x3B, "f3": 0x3C, "f4": 0x3D,
    "f5": 0x3E, "f6": 0x3F, "f7": 0x40, "f8": 0x41, "f9": 0x42,
    "f10": 0x43, "f11": 0x44, "f12": 0x45,
    "printscreen": 0x46, "scrolllock": 0x47, "pause": 0x48,
    "insert": 0x49, "home": 0x4A, "pageup": 0x4B, "delete": 0x4C,
    "end": 0x4D, "pagedown": 0x4E,
    "right": 0x4F, "left": 0x50, "down": 0x51, "up": 0x52,
}

# Characters that require shift to type.
_SHIFT_CHARS: dict[str, str] = {
    "!": "1", "@": "2", "#": "3", "$": "4", "%": "5",
    "^": "6", "&": "7", "*": "8", "(": "9", ")": "0",
    "_": "-", "+": "=", "{": "[", "}": "]", "|": "\\",
    ":": ";", '"': "'", "~": "`", "<": ",", ">": ".", "?": "/",
}

# Modifier bitmask values.
MODS = {
    "ctrl": 0x01, "shift": 0x02, "alt": 0x04, "super": 0x08,
    "rctrl": 0x10, "rshift": 0x20, "ralt": 0x40, "rsuper": 0x80,
}


def _write_keyboard_report(mod: int, keycode: int) -> None:
    """Write an 8-byte HID keyboard report."""
    report = struct.pack("8B", mod, 0, keycode, 0, 0, 0, 0, 0)
    with KEYBOARD_DEV.open("wb") as f:
        f.write(report)


def _release_keyboard() -> None:
    """Send an all-zeros report to release all keys."""
    _write_keyboard_report(0, 0)


def press_key(key: str, modifiers: list[str] | None = None) -> None:
    """Press and release a single key with optional modifiers.

    Args:
        key: Key name (e.g. "a", "enter", "f5", "up").
        modifiers: Optional list of modifier names ("ctrl", "shift", "alt", "super").
    """
    mod_byte = 0
    for m in (modifiers or []):
        mod_byte |= MODS.get(m, 0)

    keycode = _KEYCODES.get(key.lower(), 0)
    if keycode == 0 and key.lower() not in _KEYCODES:
        raise ValueError(f"Unknown key: {key!r}")

    _write_keyboard_report(mod_byte, keycode)
    time.sleep(KEY_DELAY)
    _release_keyboard()
    time.sleep(KEY_DELAY)


def type_string(text: str) -> None:
    """Type a string character by character.

    Handles uppercase, shifted symbols, spaces, and newlines.
    """
    for ch in text:
        if ch == " ":
            press_key("space")
        elif ch == "\n":
            press_key("enter")
        elif ch == "\t":
            press_key("tab")
        elif ch in _SHIFT_CHARS:
            press_key(_SHIFT_CHARS[ch], ["shift"])
        elif ch.isupper():
            press_key(ch.lower(), ["shift"])
        elif ch.lower() in _KEYCODES:
            press_key(ch.lower())
        else:
            pass  # Skip unsupported characters silently


def hotkey(*keys: str) -> None:
    """Press a key combination (e.g. hotkey("ctrl", "alt", "delete")).

    The last key in the sequence is the primary key; all preceding keys
    are treated as modifiers.
    """
    if not keys:
        return
    *mods, primary = keys
    press_key(primary, list(mods))


# --- Mouse ---

def _write_mouse_report(buttons: int, dx: int, dy: int, wheel: int = 0) -> None:
    """Write a 4-byte HID mouse report."""
    dx = max(-127, min(127, dx))
    dy = max(-127, min(127, dy))
    wheel = max(-127, min(127, wheel))
    report = struct.pack("4b", buttons, dx, dy, wheel)
    with MOUSE_DEV.open("wb") as f:
        f.write(report)


def move_mouse(dx: int, dy: int) -> None:
    """Move mouse by relative dx, dy pixels."""
    # Break large moves into 127-step chunks
    while dx != 0 or dy != 0:
        step_x = max(-127, min(127, dx))
        step_y = max(-127, min(127, dy))
        _write_mouse_report(0, step_x, step_y)
        dx -= step_x
        dy -= step_y
        time.sleep(0.001)


def click(button: str = "left") -> None:
    """Click a mouse button ("left", "right", or "middle")."""
    btn = {"left": 1, "right": 2, "middle": 4}.get(button, 1)
    _write_mouse_report(btn, 0, 0)
    time.sleep(KEY_DELAY)
    _write_mouse_report(0, 0, 0)  # release
    time.sleep(KEY_DELAY)


def double_click(button: str = "left") -> None:
    """Double-click a mouse button."""
    click(button)
    time.sleep(0.05)
    click(button)


def scroll(amount: int) -> None:
    """Scroll the mouse wheel. Positive = up, negative = down."""
    _write_mouse_report(0, 0, 0, amount)
