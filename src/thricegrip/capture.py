"""Video capture from the HDMI-to-CSI bridge via v4l2.

Captures frames from /dev/video0 (TC358743 CSI bridge) and returns
them as JPEG bytes or base64-encoded strings for LLM vision input.
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

DEFAULT_DEVICE = "/dev/video0"
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080


def screenshot(
    output_path: str | Path | None = None,
    device: str = DEFAULT_DEVICE,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> bytes:
    """Capture a single JPEG frame from the target display.

    Args:
        output_path: Optional file path to save the JPEG. If None, returns bytes only.
        device: V4L2 device path.
        width: Capture width.
        height: Capture height.

    Returns:
        JPEG image bytes.
    """
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "v4l2",
            "-input_format", "uyvy422",
            "-video_size", f"{width}x{height}",
            "-framerate", "30",
            "-i", device,
            "-frames:v", "1",
            "-f", "image2",
            "-c:v", "mjpeg",
            "-q:v", "2",
            "pipe:1",
        ],
        capture_output=True,
        timeout=10,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg capture failed (exit {result.returncode}): {result.stderr.decode()}"
        )

    jpeg_bytes = result.stdout

    if output_path is not None:
        Path(output_path).write_bytes(jpeg_bytes)

    return jpeg_bytes


def screenshot_base64(
    device: str = DEFAULT_DEVICE,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> str:
    """Capture a frame and return it as a base64-encoded JPEG string.

    Suitable for direct use in LLM vision API calls.
    """
    jpeg_bytes = screenshot(device=device, width=width, height=height)
    return base64.b64encode(jpeg_bytes).decode("ascii")


def stream_url(host: str = "0.0.0.0", port: int = 8080) -> str:
    """Return the URL for the MJPEG video stream.

    The stream is served by ustreamer (started via systemd).
    """
    return f"http://{host}:{port}/stream"
