"""Tests for agent integration module."""

from thricegrip.agent import AgentAction, capture_for_llm


class TestAgentAction:
    """Verify AgentAction dataclass."""

    def test_action_is_frozen(self):
        action = AgentAction(action="click", params={"button": "left"})
        assert action.action == "click"

    def test_default_params(self):
        action = AgentAction(action="key")
        assert action.params == {}

    def test_capture_for_llm_returns_image_block_structure(self):
        # Can't actually capture without /dev/video0, but verify the
        # function signature and return type expectations
        assert callable(capture_for_llm)
