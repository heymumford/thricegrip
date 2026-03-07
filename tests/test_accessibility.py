"""Tests for accessibility mode — voice-driven agent loop."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from thricegrip.accessibility import (
    AccessibilityAgent,
    AccessibilityConfig,
    AgentResponse,
    SafetyLevel,
    build_system_prompt,
    parse_agent_response,
    requires_confirmation,
)
from thricegrip.agent import AgentAction
from thricegrip.voice import VoiceConfig


class TestSafetyLevel:
    """Verify safety level enum."""

    def test_values(self):
        assert SafetyLevel.CAUTIOUS.value == "cautious"
        assert SafetyLevel.STANDARD.value == "standard"
        assert SafetyLevel.AUTONOMOUS.value == "autonomous"


class TestAccessibilityConfig:
    """Verify accessibility configuration defaults."""

    def test_defaults(self):
        config = AccessibilityConfig()
        assert config.safety == SafetyLevel.STANDARD
        assert config.narrate_actions is True
        assert config.narrate_screen is True
        assert config.describe_on_wake is False
        assert config.model == "claude-sonnet-4-20250514"

    def test_voice_config_embedded(self):
        config = AccessibilityConfig()
        assert config.voice.wake_word == "hey grip"


class TestParseAgentResponse:
    """Verify LLM response parsing."""

    def test_parse_simple_response(self):
        raw = {
            "narration": "I see a login form.",
            "actions": [
                {"action": "click", "params": {"button": "left"}},
            ],
            "needs_confirmation": False,
        }
        response = parse_agent_response(raw)
        assert response.narration == "I see a login form."
        assert len(response.actions) == 1
        assert response.actions[0].action == "click"
        assert response.needs_confirmation is False

    def test_parse_empty_actions(self):
        raw = {"narration": "The screen shows a desktop.", "actions": []}
        response = parse_agent_response(raw)
        assert response.actions == []

    def test_parse_with_confirmation(self):
        raw = {
            "narration": "I'm about to delete this file.",
            "actions": [{"action": "key", "params": {"key": "delete"}}],
            "needs_confirmation": True,
            "confirmation_prompt": "Delete the file 'report.pdf'?",
        }
        response = parse_agent_response(raw)
        assert response.needs_confirmation is True
        assert "report.pdf" in response.confirmation_prompt

    def test_parse_with_follow_up(self):
        raw = {
            "narration": "I see two buttons.",
            "actions": [],
            "follow_up_question": "Do you want the red button or the blue button?",
        }
        response = parse_agent_response(raw)
        assert "red button" in response.follow_up_question

    def test_parse_missing_fields_use_defaults(self):
        raw = {"narration": "Hello"}
        response = parse_agent_response(raw)
        assert response.actions == []
        assert response.needs_confirmation is False
        assert response.confirmation_prompt == ""
        assert response.follow_up_question == ""

    def test_parse_multiple_actions(self):
        raw = {
            "narration": "Filling in the form.",
            "actions": [
                {"action": "click", "params": {"button": "left"}},
                {"action": "type", "params": {"text": "john@example.com"}},
                {"action": "key", "params": {"key": "tab"}},
                {"action": "type", "params": {"text": "password123"}},
                {"action": "key", "params": {"key": "enter"}},
            ],
        }
        response = parse_agent_response(raw)
        assert len(response.actions) == 5


class TestRequiresConfirmation:
    """Verify confirmation logic for different safety levels."""

    def test_cautious_always_confirms(self):
        config = AccessibilityConfig(safety=SafetyLevel.CAUTIOUS)
        response = AgentResponse(narration="test", actions=[])
        assert requires_confirmation(response, config) is True

    def test_standard_confirms_when_flagged(self):
        config = AccessibilityConfig(safety=SafetyLevel.STANDARD)
        response = AgentResponse(
            narration="test",
            actions=[],
            needs_confirmation=True,
        )
        assert requires_confirmation(response, config) is True

    def test_standard_confirms_destructive_keywords(self):
        config = AccessibilityConfig(safety=SafetyLevel.STANDARD)
        response = AgentResponse(
            narration="test",
            actions=[AgentAction(action="type", params={"text": "delete this file"})],
        )
        assert requires_confirmation(response, config) is True

    def test_standard_no_confirm_for_safe_actions(self):
        config = AccessibilityConfig(safety=SafetyLevel.STANDARD)
        response = AgentResponse(
            narration="test",
            actions=[AgentAction(action="click", params={"button": "left"})],
        )
        assert requires_confirmation(response, config) is False

    def test_standard_confirms_payment_keyword(self):
        config = AccessibilityConfig(safety=SafetyLevel.STANDARD)
        response = AgentResponse(
            narration="test",
            actions=[AgentAction(action="type", params={"text": "pay now"})],
        )
        assert requires_confirmation(response, config) is True

    def test_autonomous_skips_safe_actions(self):
        config = AccessibilityConfig(safety=SafetyLevel.AUTONOMOUS)
        response = AgentResponse(
            narration="test",
            actions=[AgentAction(action="type", params={"text": "hello"})],
        )
        assert requires_confirmation(response, config) is False

    def test_autonomous_still_confirms_if_flagged(self):
        config = AccessibilityConfig(safety=SafetyLevel.AUTONOMOUS)
        response = AgentResponse(
            narration="test",
            actions=[],
            needs_confirmation=True,
        )
        assert requires_confirmation(response, config) is True


class TestBuildSystemPrompt:
    """Verify system prompt generation."""

    def test_prompt_contains_key_instructions(self):
        config = AccessibilityConfig()
        prompt = build_system_prompt(config)
        assert "ThriceGrip" in prompt
        assert "narrate" in prompt.lower()
        assert "confirmation" in prompt.lower() or "confirm" in prompt.lower()
        assert "CAPTCHA" in prompt
        assert "JSON" in prompt

    def test_prompt_includes_response_format(self):
        config = AccessibilityConfig()
        prompt = build_system_prompt(config)
        assert '"narration"' in prompt
        assert '"actions"' in prompt
        assert '"needs_confirmation"' in prompt


class TestAccessibilityAgent:
    """Verify agent orchestration logic."""

    def test_initial_state_is_idle(self):
        mock_stt = MagicMock()
        mock_tts = MagicMock()
        agent = AccessibilityAgent(stt=mock_stt, tts=mock_tts)
        assert agent.state.value == "idle"

    def test_narrate_calls_tts(self):
        mock_stt = MagicMock()
        mock_tts = MagicMock()
        agent = AccessibilityAgent(stt=mock_stt, tts=mock_tts)
        agent.narrate("Hello, I can see your screen.")
        mock_tts.speak.assert_called_once_with("Hello, I can see your screen.")

    def test_narrate_handles_tts_failure(self):
        mock_stt = MagicMock()
        mock_tts = MagicMock()
        mock_tts.speak.side_effect = RuntimeError("Audio device not found")
        agent = AccessibilityAgent(stt=mock_stt, tts=mock_tts)
        # Should not raise
        agent.narrate("Test")

    def test_listen_calls_stt(self):
        mock_stt = MagicMock()
        mock_stt.transcribe.return_value = "open chrome"
        mock_tts = MagicMock()
        agent = AccessibilityAgent(stt=mock_stt, tts=mock_tts)
        result = agent.listen(Path("/tmp/audio.wav"))
        assert result == "open chrome"
        mock_stt.transcribe.assert_called_once()

    def test_listen_returns_to_idle(self):
        mock_stt = MagicMock()
        mock_stt.transcribe.return_value = "test"
        mock_tts = MagicMock()
        agent = AccessibilityAgent(stt=mock_stt, tts=mock_tts)
        agent.listen(Path("/tmp/audio.wav"))
        assert agent.state.value == "idle"

    def test_clear_conversation(self):
        mock_stt = MagicMock()
        mock_tts = MagicMock()
        agent = AccessibilityAgent(stt=mock_stt, tts=mock_tts)
        agent._conversation.append({"role": "user", "content": "test"})
        agent.clear_conversation()
        assert len(agent._conversation) == 0

    @patch("thricegrip.accessibility.capture")
    def test_process_command_handles_capture_failure(self, mock_capture):
        mock_capture.screenshot_base64.side_effect = RuntimeError("No video device")
        mock_stt = MagicMock()
        mock_tts = MagicMock()
        agent = AccessibilityAgent(stt=mock_stt, tts=mock_tts)
        response = agent.process_command("open chrome")
        assert "HDMI" in response.narration or "capture" in response.narration.lower()
        assert response.actions == []

    @patch("thricegrip.accessibility.execute_action")
    def test_execute_calls_actions(self, mock_exec):
        mock_stt = MagicMock()
        mock_tts = MagicMock()
        agent = AccessibilityAgent(stt=mock_stt, tts=mock_tts)
        response = AgentResponse(
            narration="Clicking the button.",
            actions=[AgentAction(action="click", params={"button": "left"})],
        )
        agent.execute(response)
        mock_exec.assert_called_once()
        mock_tts.speak.assert_called()  # narration

    @patch("thricegrip.accessibility.execute_action")
    def test_execute_narrates_before_action(self, mock_exec):
        mock_stt = MagicMock()
        mock_tts = MagicMock()
        agent = AccessibilityAgent(stt=mock_stt, tts=mock_tts)
        response = AgentResponse(
            narration="I'll click submit now.",
            actions=[AgentAction(action="click", params={"button": "left"})],
        )
        agent.execute(response)
        # TTS should be called before action execution
        assert mock_tts.speak.call_count >= 1
        first_narration = mock_tts.speak.call_args_list[0][0][0]
        assert "click submit" in first_narration.lower()

    @patch("thricegrip.accessibility.execute_action")
    def test_execute_handles_action_failure(self, mock_exec):
        mock_exec.side_effect = RuntimeError("HID device not found")
        mock_stt = MagicMock()
        mock_tts = MagicMock()
        agent = AccessibilityAgent(stt=mock_stt, tts=mock_tts)
        response = AgentResponse(
            narration="Clicking.",
            actions=[AgentAction(action="click", params={"button": "left"})],
        )
        # Should not raise
        agent.execute(response)
        # Should narrate the error
        error_narrations = [
            call[0][0] for call in mock_tts.speak.call_args_list
            if "couldn't" in call[0][0].lower()
        ]
        assert len(error_narrations) > 0
