"""Voice input and output for accessibility mode.

Provides:
- Wake word detection (openWakeWord) for hands-free activation
- Speech-to-text (VOSK) for command input
- Text-to-speech (Piper) for agent narration

All processing runs locally on the Pi — no cloud dependency.
"""

from __future__ import annotations

import json
import subprocess
import wave
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Protocol


class ListenState(Enum):
    """Voice input state machine."""

    IDLE = "idle"            # Waiting for wake word
    LISTENING = "listening"  # Recording user speech
    PROCESSING = "processing"  # Transcribing / sending to agent


@dataclass
class VoiceConfig:
    """Configuration for voice I/O."""

    # Wake word
    wake_word: str = "hey grip"
    wake_word_threshold: float = 0.5

    # Speech-to-text
    stt_model_path: str = "/opt/thricegrip/models/vosk-model-small-en-us-0.15"
    sample_rate: int = 16000

    # Text-to-speech
    tts_model_path: str = "/opt/thricegrip/models/piper/en_US-lessac-medium.onnx"
    tts_speaker: int = 0
    tts_speed: float = 1.0

    # Audio devices
    mic_device: str = "default"
    speaker_device: str = "default"

    # Behavior
    confirmation_required: list[str] = field(default_factory=lambda: [
        "submit", "send", "delete", "pay", "purchase", "confirm",
        "sign", "transfer", "remove", "cancel",
    ])
    silence_timeout_sec: float = 2.0
    max_listen_sec: float = 30.0


class SpeechToText(Protocol):
    """Protocol for speech recognition backends."""

    def transcribe(self, audio_path: Path) -> str: ...
    def is_available(self) -> bool: ...


class TextToSpeech(Protocol):
    """Protocol for speech synthesis backends."""

    def speak(self, text: str) -> None: ...
    def speak_to_file(self, text: str, output_path: Path) -> None: ...
    def is_available(self) -> bool: ...


class VoskSTT:
    """VOSK-based offline speech recognition.

    Uses vosk-api for lightweight, offline speech recognition on Pi.
    Model size: ~50MB for small English model.
    """

    def __init__(self, model_path: str, sample_rate: int = 16000):
        self._model_path = model_path
        self._sample_rate = sample_rate
        self._model = None
        self._recognizer = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            from vosk import Model, KaldiRecognizer
            self._model = Model(self._model_path)
            self._recognizer = KaldiRecognizer(self._model, self._sample_rate)
        except ImportError:
            raise RuntimeError("vosk not installed. Run: pip install vosk")
        except Exception as e:
            raise RuntimeError(f"Failed to load VOSK model at {self._model_path}: {e}")

    def transcribe(self, audio_path: Path) -> str:
        """Transcribe a WAV file to text."""
        self._ensure_loaded()
        from vosk import KaldiRecognizer

        recognizer = KaldiRecognizer(self._model, self._sample_rate)

        with wave.open(str(audio_path), "rb") as wf:
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                recognizer.AcceptWaveform(data)

        result = json.loads(recognizer.FinalResult())
        return result.get("text", "").strip()

    def is_available(self) -> bool:
        try:
            from vosk import Model  # noqa: F401
            return Path(self._model_path).exists()
        except ImportError:
            return False


class PiperTTS:
    """Piper-based local neural text-to-speech.

    Fast enough for real-time on Pi 4 (~0.1x real-time factor).
    Model size: ~60MB for medium quality English.
    """

    def __init__(self, model_path: str, speaker: int = 0, speed: float = 1.0):
        self._model_path = model_path
        self._speaker = speaker
        self._speed = speed

    def speak(self, text: str) -> None:
        """Synthesize and play text through the default audio output."""
        result = subprocess.run(
            [
                "piper",
                "--model", self._model_path,
                "--speaker", str(self._speaker),
                "--length-scale", str(1.0 / self._speed),
                "--output-raw",
            ],
            input=text.encode(),
            capture_output=True,
            timeout=30,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Piper TTS failed: {result.stderr.decode()}")

        # Play raw audio through aplay
        subprocess.run(
            ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
            input=result.stdout,
            timeout=60,
        )

    def speak_to_file(self, text: str, output_path: Path) -> None:
        """Synthesize text to a WAV file."""
        subprocess.run(
            [
                "piper",
                "--model", self._model_path,
                "--speaker", str(self._speaker),
                "--length-scale", str(1.0 / self._speed),
                "--output_file", str(output_path),
            ],
            input=text.encode(),
            timeout=30,
            check=True,
        )

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["piper", "--version"], capture_output=True, timeout=5
            )
            return result.returncode == 0 and Path(self._model_path).exists()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
