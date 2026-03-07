"""FastAPI server exposing video stream and WebSocket HID control.

Provides:
- GET /           — Web UI (static HTML)
- GET /stream     — Proxied MJPEG video stream from ustreamer
- GET /screenshot — Single JPEG frame
- WS  /ws/hid    — WebSocket for keyboard/mouse commands
- GET /health     — Device status
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from thricegrip import __version__
from thricegrip import capture, hid, gadget

STATIC_DIR = Path(__file__).parent.parent.parent / "static"

app = FastAPI(title="ThriceGrip", version=__version__)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def index():
    """Serve the web UI."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse({"message": "ThriceGrip API", "version": __version__})


@app.get("/health")
async def health():
    """Device health check."""
    video_available = Path(capture.DEFAULT_DEVICE).exists()
    keyboard_available = hid.KEYBOARD_DEV.exists()
    mouse_available = hid.MOUSE_DEV.exists()
    gadget_active = gadget.is_active()

    return {
        "status": "ok" if all([video_available, keyboard_available, mouse_available]) else "degraded",
        "version": __version__,
        "grips": {
            "video": {"available": video_available, "device": capture.DEFAULT_DEVICE},
            "keyboard": {"available": keyboard_available, "device": str(hid.KEYBOARD_DEV)},
            "mouse": {"available": mouse_available, "device": str(hid.MOUSE_DEV)},
        },
        "gadget_active": gadget_active,
    }


@app.get("/screenshot")
async def screenshot():
    """Capture and return a single JPEG frame."""
    jpeg_bytes = capture.screenshot()
    return Response(content=jpeg_bytes, media_type="image/jpeg")


@app.websocket("/ws/hid")
async def hid_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time keyboard and mouse control.

    Accepted message formats (JSON):
        {"type": "key", "key": "a", "modifiers": ["ctrl"]}
        {"type": "type", "text": "hello world"}
        {"type": "hotkey", "keys": ["ctrl", "alt", "delete"]}
        {"type": "mouse_move", "dx": 10, "dy": -5}
        {"type": "click", "button": "left"}
        {"type": "double_click", "button": "left"}
        {"type": "scroll", "amount": -3}
    """
    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type", "")

            match msg_type:
                case "key":
                    hid.press_key(data["key"], data.get("modifiers"))
                case "type":
                    hid.type_string(data["text"])
                case "hotkey":
                    hid.hotkey(*data["keys"])
                case "mouse_move":
                    hid.move_mouse(data["dx"], data["dy"])
                case "click":
                    hid.click(data.get("button", "left"))
                case "double_click":
                    hid.double_click(data.get("button", "left"))
                case "scroll":
                    hid.scroll(data["amount"])
                case _:
                    await websocket.send_json({"error": f"Unknown type: {msg_type}"})
                    continue

            await websocket.send_json({"ok": True, "type": msg_type})

    except WebSocketDisconnect:
        pass
