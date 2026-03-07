"""Tests for voice I/O module."""

from pathlib import Path

from thricegrip.voice import (
    ListenState,
    PiperTTS,
    VoiceConfig,
    VoskSTT,
)


class TestVoiceConfig:
    """Verify default configuration."""

    def test_defaults(self):
        config = VoiceConfig()
        assert config.wake_word == "hey grip"
        assert config.sample_rate == 16000
        assert config.silence_timeout_sec == 2.0
        assert config.max_listen_sec == 30.0

    def test_confirmation_keywords(self):
        config = VoiceConfig()
        assert "delete" in config.confirmation_required
        assert "pay" in config.confirmation_required
        assert "submit" in config.confirmation_required


class TestListenState:
    """Verify state machine values."""

    def test_states(self):
        assert ListenState.IDLE.value == "idle"
        assert ListenState.LISTENING.value == "listening"
        assert ListenState.PROCESSING.value == "processing"


class TestVoskSTT:
    """Verify VOSK speech-to-text wrapper."""

    def test_not_available_without_model(self):
        stt = VoskSTT("/nonexistent/model")
        assert stt.is_available() is False

    def test_model_path_stored(self):
        stt = VoskSTT("/some/path", sample_rate=44100)
        assert stt._model_path == "/some/path"
        assert stt._sample_rate == 44100


class TestPiperTTS:
    """Verify Piper TTS wrapper."""

    def test_not_available_without_binary(self):
        tts = PiperTTS("/nonexistent/model.onnx")
        assert tts.is_available() is False

    def test_config_stored(self):
        tts = PiperTTS("/model.onnx", speaker=2, speed=1.5)
        assert tts._model_path == "/model.onnx"
        assert tts._speaker == 2
        assert tts._speed == 1.5
