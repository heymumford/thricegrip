#!/usr/bin/env bash
# ThricoGrip installer for Raspberry Pi OS (Bookworm, 64-bit).
#
# Installs system dependencies, configures boot overlays for USB gadget
# mode and HDMI-to-CSI capture, installs ustreamer for low-latency
# video streaming, and sets up systemd services.
#
# Must run as root or with sudo.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[thricegrip]${NC} $*"; }
warn()  { echo -e "${YELLOW}[thricegrip]${NC} $*"; }
error() { echo -e "${RED}[thricegrip]${NC} $*" >&2; }

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

# --- System dependencies ---
info "Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq \
    python3-pip python3-venv \
    v4l-utils ffmpeg git \
    libjpeg-dev libevent-dev \
    build-essential

# --- Boot configuration ---
BOOT_CONFIG="/boot/firmware/config.txt"
if [[ ! -f "$BOOT_CONFIG" ]]; then
    BOOT_CONFIG="/boot/config.txt"
fi

info "Configuring boot overlays in $BOOT_CONFIG..."

# Add dwc2 overlay (USB gadget mode) if not present
if ! grep -q "^dtoverlay=dwc2" "$BOOT_CONFIG"; then
    echo "" >> "$BOOT_CONFIG"
    echo "# ThricoGrip — USB gadget mode" >> "$BOOT_CONFIG"
    echo "dtoverlay=dwc2" >> "$BOOT_CONFIG"
    info "  Added dtoverlay=dwc2"
else
    info "  dtoverlay=dwc2 already present"
fi

# Add tc358743 overlay (HDMI-to-CSI capture) if not present
if ! grep -q "^dtoverlay=tc358743" "$BOOT_CONFIG"; then
    echo "# ThricoGrip — HDMI-to-CSI capture" >> "$BOOT_CONFIG"
    echo "dtoverlay=tc358743" >> "$BOOT_CONFIG"
    info "  Added dtoverlay=tc358743"
else
    info "  dtoverlay=tc358743 already present"
fi

# Ensure enough GPU memory for video capture
if ! grep -q "^gpu_mem=" "$BOOT_CONFIG"; then
    echo "gpu_mem=256" >> "$BOOT_CONFIG"
    info "  Set gpu_mem=256"
fi

# --- Kernel modules ---
MODULES_FILE="/etc/modules"
info "Configuring kernel modules..."

for mod in dwc2 libcomposite; do
    if ! grep -q "^${mod}$" "$MODULES_FILE"; then
        echo "$mod" >> "$MODULES_FILE"
        info "  Added $mod to $MODULES_FILE"
    fi
done

# --- Install ustreamer (PiKVM's low-latency video streamer) ---
USTREAMER_DIR="/opt/ustreamer"
if [[ ! -x "$USTREAMER_DIR/ustreamer" ]]; then
    info "Building ustreamer..."
    git clone --depth=1 https://github.com/pikvm/ustreamer.git "$USTREAMER_DIR"
    cd "$USTREAMER_DIR"
    make -j"$(nproc)"
    ln -sf "$USTREAMER_DIR/ustreamer" /usr/local/bin/ustreamer
    cd "$PROJECT_DIR"
    info "  ustreamer installed to /usr/local/bin/ustreamer"
else
    info "  ustreamer already installed"
fi

# --- Python environment ---
VENV_DIR="/opt/thricegrip/venv"
info "Setting up Python environment..."
mkdir -p /opt/thricegrip
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -e "$PROJECT_DIR"
info "  Python venv at $VENV_DIR"

# --- Systemd services ---
info "Installing systemd services..."
cp "$PROJECT_DIR/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload

for svc in thricegrip-gadget thricegrip-stream thricegrip-api; do
    systemctl enable "$svc"
    info "  Enabled $svc"
done

info ""
info "Installation complete. Reboot to activate:"
info "  sudo reboot"
info ""
info "After reboot:"
info "  1. Connect HDMI cable from target to CSI bridge"
info "  2. Connect USB cable from target to Pi USB-C port"
info "  3. Open http://thricegrip.local:8080 in your browser"
