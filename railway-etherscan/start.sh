#!/bin/bash
set -euo pipefail

# 1) Virtual display
export DISPLAY=:99
Xvfb :99 -screen 0 1600x900x24 -ac +extension RANDR >/tmp/xvfb.log 2>&1 &

# 2) Lightweight window manager (focus/menus)
fluxbox >/tmp/fluxbox.log 2>&1 &

# 3) VNC server (no password; for private debugging only)
x11vnc -display :99 -nopw -forever -shared -rfbport 5900 >/tmp/x11vnc.log 2>&1 &

# 4) noVNC web gateway on Railway’s $PORT
/usr/share/novnc/utils/novnc_proxy --vnc localhost:5900 --listen "${PORT:-8080}" >/tmp/novnc.log 2>&1 &

# 5) Give services a moment to come up
sleep 2

# 6) Run your script (must be HEADFUL!)
python /app/main_etherscan.py
