# ThricoGrip

**Three grips. One device. Total control.**

ThricoGrip is an open-source hardware KVM device built on a Raspberry Pi that attaches to any target computer and grips all three interfaces — **keyboard**, **mouse**, and **video** — enabling remote human control or AI-agent-driven "computer use" at the hardware level.

```
TARGET LAPTOP
  |-- HDMI out --> [HDMI-to-CSI bridge] --> Pi CSI port (video capture)
  |-- USB port <-- Pi USB-C OTG port (HID keyboard + mouse injection)

YOUR NETWORK
  |-- WiFi/Ethernet --> Pi --> Web UI / WebSocket API / Agent endpoint
```

## Why ThricoGrip?

Existing KVM-over-IP devices (PiKVM, JetKVM, TinyPilot) are built for **human remote access**. ThricoGrip is built for **AI agent integration** — capture what the target displays, send it to an LLM with vision, and execute actions through hardware-level HID injection. Invisible to the target OS. Works at BIOS level. No software installation on the target.

## The Three Grips

| Grip | Direction | How |
|------|-----------|-----|
| **Video** | Target --> ThricoGrip | HDMI capture via TC358743 CSI bridge (1080p30, ~100ms latency) |
| **Keyboard** | ThricoGrip --> Target | USB HID gadget via `/dev/hidg0` (composite USB device) |
| **Mouse** | ThricoGrip --> Target | USB HID gadget via `/dev/hidg1` (composite USB device) |

## Hardware BOM (~$75-110)

| Component | Spec | Price |
|-----------|------|-------|
| Raspberry Pi 4 Model B | 2GB+ RAM | $35-55 |
| HDMI-to-CSI-2 bridge | TC358743 (Geekworm C779 or Waveshare) | $15-25 |
| USB-C to USB-A cable | Data + power, 1m | $5-8 |
| HDMI cable | 0.5-1m | $5-8 |
| MicroSD card | 32GB+ Class 10 | $8-12 |
| Heatsink kit (optional) | Passive aluminum | $3-5 |

## Quick Start

### 1. Flash OS

Flash **Raspberry Pi OS Lite (64-bit, Bookworm)** to your SD card. Enable SSH and WiFi.

### 2. Install ThricoGrip

```bash
ssh pi@thricegrip.local

git clone https://github.com/heymumford/thricegrip.git
cd thricegrip
./scripts/install.sh
sudo reboot
```

### 3. Wire Hardware

1. Insert TC358743 CSI bridge ribbon cable into Pi's **CAMERA** port
2. Connect HDMI cable: target HDMI out --> CSI bridge HDMI in
3. Connect USB cable: target USB-A port --> Pi USB-C port

### 4. Use It

```bash
# Browser-based KVM
open http://thricegrip.local:8080

# Or via Python
from thricegrip import hid, capture

capture.screenshot("/tmp/screen.jpg")
hid.type_string("hello world")
hid.click("left")
```

## Software Architecture

```
src/thricegrip/
  __init__.py          # Package init
  hid.py               # Keyboard + mouse injection via USB gadget
  capture.py           # Video frame capture from CSI bridge
  server.py            # FastAPI: MJPEG stream + WebSocket HID control
  agent.py             # LLM agent integration (capture -> vision -> action)
  gadget.py            # USB composite gadget setup and teardown
```

## Agent Integration

ThricoGrip's killer feature: plug an LLM into the capture-action loop.

```python
from thricegrip import capture, hid
import anthropic

client = anthropic.Anthropic()

while True:
    frame = capture.screenshot_base64()
    response = client.messages.create(
        model="claude-opus-4-6",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64",
                 "media_type": "image/jpeg", "data": frame}},
                {"type": "text", "text": "Click the Settings icon."}
            ]
        }]
    )
    # Parse response -> execute HID commands
```

## Performance

| Metric | Value |
|--------|-------|
| Video latency | ~80-120ms |
| Video resolution | Up to 1080p30 |
| HID latency | <5ms |
| Power draw | ~3W |
| Boot to ready | ~15s |

## Comparison

| Feature | ThricoGrip | PiKVM V2 | JetKVM | TinyPilot |
|---------|-----------|----------|--------|-----------|
| Price | ~$75-110 | ~$100-150 | $69 | ~$400 |
| AI agent ready | **Yes** | No | No | No |
| Open source | Yes | Yes | Yes | Partial |
| Single cable to target | No | No | No | No |
| Works at BIOS | Yes | Yes | Yes | Yes |

## License

MIT

## Name

Rhymes with vicegrip. Grips three things. You get it.
