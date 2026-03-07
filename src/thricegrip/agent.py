"""LLM agent integration for AI-driven computer control.

Provides the capture-reason-act loop that connects an LLM with vision
to the target computer's display and input devices.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from thricegrip import capture, hid


@dataclass(frozen=True)
class AgentAction:
    """A single action to perform on the target computer."""

    action: str  # "key", "type", "hotkey", "click", "double_click", "move", "scroll"
    params: dict[str, Any] = field(default_factory=dict)


def execute_action(action: AgentAction) -> None:
    """Execute a single agent action on the target."""
    match action.action:
        case "key":
            hid.press_key(action.params["key"], action.params.get("modifiers"))
        case "type":
            hid.type_string(action.params["text"])
        case "hotkey":
            hid.hotkey(*action.params["keys"])
        case "click":
            hid.click(action.params.get("button", "left"))
        case "double_click":
            hid.double_click(action.params.get("button", "left"))
        case "move":
            hid.move_mouse(action.params["dx"], action.params["dy"])
        case "scroll":
            hid.scroll(action.params["amount"])
        case _:
            raise ValueError(f"Unknown action: {action.action}")


def execute_actions(actions: list[AgentAction]) -> None:
    """Execute a sequence of agent actions."""
    for action in actions:
        execute_action(action)


def capture_for_llm(
    device: str = capture.DEFAULT_DEVICE,
    width: int = capture.DEFAULT_WIDTH,
    height: int = capture.DEFAULT_HEIGHT,
) -> dict[str, Any]:
    """Capture a frame and format it for LLM vision API input.

    Returns a dict suitable for use as a content block in the
    Anthropic Messages API.
    """
    b64 = capture.screenshot_base64(device=device, width=width, height=height)
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/jpeg",
            "data": b64,
        },
    }
