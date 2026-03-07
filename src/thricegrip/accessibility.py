"""Accessibility mode — voice-driven AI agent loop.

Transforms ThricoGrip from a remote KVM into a hands-free computer
assistant for blind users and users with physical disabilities.

The loop:
  1. Listen for wake word ("Hey Grip")
  2. Record user's spoken command
  3. Capture target screen
  4. Send command + screenshot to LLM
  5. Execute LLM's actions (click, type, scroll)
  6. Narrate the result back to the user via TTS

All voice processing runs locally on the Pi.
LLM calls require network (Anthropic API).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from thricegrip import capture, hid
from thricegrip.agent import AgentAction, execute_action
from thricegrip.voice import (
    ListenState,
    PiperTTS,
    SpeechToText,
    TextToSpeech,
    VoiceConfig,
    VoskSTT,
)

logger = logging.getLogger(__name__)


class SafetyLevel(Enum):
    """How cautiously the agent should act."""

    CAUTIOUS = "cautious"      # Confirm before every action
    STANDARD = "standard"      # Confirm destructive actions only
    AUTONOMOUS = "autonomous"  # Confirm financial/legal actions only


@dataclass
class AccessibilityConfig:
    """Configuration for accessibility mode."""

    voice: VoiceConfig = field(default_factory=VoiceConfig)
    safety: SafetyLevel = SafetyLevel.STANDARD

    # Narration verbosity
    narrate_actions: bool = True       # "I'm clicking the Submit button"
    narrate_screen: bool = True        # "I see a login form with username and password fields"
    narrate_confirmations: bool = True  # "The form was submitted successfully"

    # Screen description on demand
    describe_on_wake: bool = False     # Auto-describe screen when activated

    # Agent model
    model: str = "claude-sonnet-4-20250514"  # Balanced cost/quality for real-time use


@dataclass(frozen=True)
class AgentResponse:
    """Structured response from the LLM agent."""

    narration: str                          # What to tell the user
    actions: list[AgentAction]              # What to do on the target
    needs_confirmation: bool = False        # Ask user before executing
    confirmation_prompt: str = ""           # What to ask
    follow_up_question: str = ""            # Clarifying question for the user


def requires_confirmation(
    response: AgentResponse,
    config: AccessibilityConfig,
) -> bool:
    """Determine if the user should confirm before execution."""
    if config.safety == SafetyLevel.CAUTIOUS:
        return True
    if response.needs_confirmation:
        return True
    if config.safety == SafetyLevel.STANDARD:
        # Check if any action involves typing sensitive keywords
        for action in response.actions:
            if action.action == "type":
                text = action.params.get("text", "").lower()
                for keyword in config.voice.confirmation_required:
                    if keyword in text:
                        return True
    return False


def build_system_prompt(config: AccessibilityConfig) -> str:
    """Build the system prompt for the accessibility agent."""
    return """You are ThricoGrip, an accessibility assistant that helps users interact with \
their computer through voice commands. You can see the user's screen and control their \
keyboard and mouse.

IMPORTANT RULES:
1. Always narrate what you see and what you're about to do.
2. Be concise but clear. Users are listening, not reading.
3. For destructive actions (delete, send, submit, pay), set needs_confirmation=true.
4. If you're unsure what the user wants, ask a clarifying question instead of guessing.
5. Describe UI elements by their visible label or position, not technical attributes.
6. When reading text from the screen, read it naturally — don't spell out URLs character by character unless asked.
7. If you encounter a CAPTCHA, describe it and ask the user for help.

RESPONSE FORMAT (JSON):
{
    "narration": "What to tell the user about what you see or did",
    "actions": [
        {"action": "click", "params": {"button": "left"}},
        {"action": "type", "params": {"text": "hello"}},
        {"action": "key", "params": {"key": "enter"}},
        {"action": "move", "params": {"dx": 100, "dy": 50}},
        {"action": "scroll", "params": {"amount": -3}},
        {"action": "hotkey", "params": {"keys": ["ctrl", "a"]}}
    ],
    "needs_confirmation": false,
    "confirmation_prompt": "",
    "follow_up_question": ""
}

If the user says "describe" or "what do you see", just describe the screen with no actions.
If the user says "read that" or "read this", read the main text content on screen.
If the user says "where am I", describe which application and page/section is active."""


def parse_agent_response(raw: dict[str, Any]) -> AgentResponse:
    """Parse the LLM's JSON response into a structured AgentResponse."""
    actions = []
    for a in raw.get("actions", []):
        actions.append(AgentAction(
            action=a["action"],
            params=a.get("params", {}),
        ))

    return AgentResponse(
        narration=raw.get("narration", ""),
        actions=actions,
        needs_confirmation=raw.get("needs_confirmation", False),
        confirmation_prompt=raw.get("confirmation_prompt", ""),
        follow_up_question=raw.get("follow_up_question", ""),
    )


class AccessibilityAgent:
    """Voice-driven accessibility agent loop.

    This is the main orchestrator that ties together:
    - Voice input (wake word + speech-to-text)
    - Screen capture (video grip)
    - LLM reasoning (Claude vision)
    - HID output (keyboard + mouse grip)
    - Voice output (text-to-speech narration)
    """

    def __init__(
        self,
        config: AccessibilityConfig | None = None,
        stt: SpeechToText | None = None,
        tts: TextToSpeech | None = None,
    ):
        self.config = config or AccessibilityConfig()
        self.stt = stt or VoskSTT(
            self.config.voice.stt_model_path,
            self.config.voice.sample_rate,
        )
        self.tts = tts or PiperTTS(
            self.config.voice.tts_model_path,
            self.config.voice.tts_speaker,
            self.config.voice.tts_speed,
        )
        self._state = ListenState.IDLE
        self._conversation: list[dict[str, Any]] = []

    @property
    def state(self) -> ListenState:
        return self._state

    def narrate(self, text: str) -> None:
        """Speak text to the user via TTS."""
        logger.info("Narrating: %s", text)
        try:
            self.tts.speak(text)
        except Exception as e:
            logger.error("TTS failed: %s", e)

    def listen(self, audio_path: Path) -> str:
        """Transcribe user speech from a recorded audio file."""
        self._state = ListenState.PROCESSING
        try:
            text = self.stt.transcribe(audio_path)
            logger.info("Heard: %s", text)
            return text
        finally:
            self._state = ListenState.IDLE

    def process_command(self, command: str) -> AgentResponse:
        """Process a voice command: capture screen, ask LLM, return response.

        This method does NOT execute actions — the caller decides whether
        to execute (after confirmation if needed).
        """
        # Capture what's on screen
        try:
            frame_b64 = capture.screenshot_base64()
        except Exception as e:
            logger.error("Screen capture failed: %s", e)
            return AgentResponse(
                narration="I couldn't capture the screen. Is the HDMI cable connected?",
                actions=[],
            )

        # Build message for LLM
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": frame_b64,
                    },
                },
                {"type": "text", "text": command},
            ],
        }
        self._conversation.append(user_message)

        # Call LLM (requires anthropic SDK)
        try:
            import anthropic
            client = anthropic.Anthropic()
            response = client.messages.create(
                model=self.config.model,
                max_tokens=1024,
                system=build_system_prompt(self.config),
                messages=self._conversation,
            )

            # Parse JSON from response
            import json
            raw_text = response.content[0].text
            # Handle LLM wrapping JSON in markdown code blocks
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0]
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0]

            raw = json.loads(raw_text)
            agent_response = parse_agent_response(raw)

            # Track assistant response in conversation
            self._conversation.append({
                "role": "assistant",
                "content": response.content[0].text,
            })

            return agent_response

        except ImportError:
            return AgentResponse(
                narration="The Anthropic SDK is not installed. Run: pip install anthropic",
                actions=[],
            )
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return AgentResponse(
                narration=f"I had trouble thinking about that. Error: {e}",
                actions=[],
            )

    def execute(self, response: AgentResponse) -> None:
        """Execute the agent's actions on the target computer."""
        if self.config.narrate_actions and response.narration:
            self.narrate(response.narration)

        for action in response.actions:
            try:
                execute_action(action)
            except Exception as e:
                logger.error("Action failed: %s — %s", action, e)
                self.narrate(f"I couldn't complete that action. {e}")
                return

        # Brief pause then capture result
        if self.config.narrate_confirmations and response.actions:
            time.sleep(0.5)
            self.narrate("Done.")

    def clear_conversation(self) -> None:
        """Reset conversation history."""
        self._conversation.clear()
