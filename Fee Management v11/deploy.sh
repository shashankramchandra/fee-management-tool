#!/bin/bash
# ============================================================
#  Royal Public School — VPS Deploy Script
#  Run this on a fresh Ubuntu 22.04 VPS as root
#  Usage: bash deploy.sh
# ============================================================

set -e  # stop on any error
echo ""
echo "============================================"
echo "  RPS Fee App — VPS Deployment"
echo "============================================"
echo ""

APP_DIR="/root/school_fee_app"

# ── 1. System update & Python ──────────────────────────────
echo "[1/7] Updating system and installing Python..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv unzip -qq
echo "      Done."

# ── 2. Create app directory ────────────────────────────────
echo "[2/7] Setting up app directory at $APP_DIR..."
mkdir -p "$APP_DIR"
echo "      Done."

# ── 3. Copy files (expects school_fee_app_v3.zip in same folder as this script) ──
echo "[3/7] Extracting app files..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/school_fee_app_v3.zip" ]; then
    unzip -q -o "$SCRIPT_DIR/school_fee_app_v3.zip" -d /tmp/rps_extract
    cp -r /tmp/rps_extract/school_fee_app_v3/. "$APP_DIR/"
    rm -rf /tmp/rps_extract
    echo "      Files extracted to $APP_DIR"
else
    echo "      school_fee_app_v3.zip not found next to deploy.sh"
    echo "      Please place the zip file in the same folder as deploy.sh and re-run."
    exit 1
fi

# ── 4. Python virtual environment + packages ───────────────
echo "[4/7] Creating Python virtual environment and installing packages..."
cd "$APP_DIR"
python3 -m venv venv
venv/bin/pip install --quiet --upgrade pip
venv/bin/pip install --quiet -r requirements.txt
echo "      Done."

# ── 5. Permissions ─────────────────────────────────────────
echo "[5/7] Setting file permissions..."
chmod -R 755 "$APP_DIR"
chmod 664 "$APP_DIR/database/school_fees.db"
chmod -R 775 "$APP_DIR/receipts"
echo "      Done."

# ── 6. Install systemd service (auto-start on reboot) ──────
echo "[6/7] Installing system service (auto-start on boot)..."
cp "$APP_DIR/rps_fee_app.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable rps_fee_app
systemctl start rps_fee_app
sleep 2
echo "      Done."

# ── 7. Open firewall port 5000 ─────────────────────────────
echo "[7/7] Opening firewall port 5000..."
# UFW (Ubuntu default firewall)
if command -v ufw &> /dev/null; then
    ufw allow 5000/tcp
    echo "      UFW: port 5000 opened."
fi
echo ""

# ── Summary ────────────────────────────────────────────────
echo "============================================"
echo "  DEPLOYMENT COMPLETE"
echo "============================================"
echo ""
echo "  App status:"
systemctl is-active rps_fee_app && echo "  ✓ Service is RUNNING" || echo "  ✗ Service NOT running — check: journalctl -u rps_fee_app"
echo ""
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "unable to detect")
echo "  Your server's public IP: $PUBLIC_IP"
echo ""
echo "  Access the app at:"
echo "  http://$PUBLIC_IP:5000"
echo ""
echo "  Useful commands:"
echo "  Check status  : systemctl status rps_fee_app"
echo "  View logs     : journalctl -u rps_fee_app -f"
echo "  Restart app   : systemctl restart rps_fee_app"
echo "  Stop app      : systemctl stop rps_fee_app"
echo ""
