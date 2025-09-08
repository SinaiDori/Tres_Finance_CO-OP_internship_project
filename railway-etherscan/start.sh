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

# Identify the container's outbound (NAT) IP
PUBLIC_IP="$(curl -s https://api.ipify.org || true)"
echo "Egress public IP: ${PUBLIC_IP:-unknown}"

# 6) Run your script (HEADFUL), capture status
set +e
python /app/main_etherscan.py 2>&1 | tee /tmp/agent.log
STATUS=$?
set -e

# 7) Post produced API keys to Slack (same logic as your GH Actions)
if [[ -n "${SLACK_BOT_TOKEN:-}" && -n "${SLACK_ETHERSCAN_CHANNEL_ID:-}" ]]; then
  if [[ -s /app/etherscan_api_keys.csv ]]; then
    JSON_PAYLOAD=$(python - <<'PY'
import os, json
ch = os.environ["SLACK_ETHERSCAN_CHANNEL_ID"]
try:
    with open("/app/etherscan_api_keys.csv","r") as f:
        keys = [ln.strip() for ln in f if ln.strip()]
except FileNotFoundError:
    keys = []
text = "\n".join(keys) if keys else "No API keys produced."
print(json.dumps({"channel": ch, "text": text}))
PY
)
  else
    JSON_PAYLOAD=$(python - <<'PY'
import os, json
print(json.dumps({"channel": os.environ["SLACK_ETHERSCAN_CHANNEL_ID"], "text": "No API keys produced."}))
PY
)
  fi

  curl -sS -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
    -H "Content-type: application/json; charset=utf-8" \
    --data "$JSON_PAYLOAD" \
    >/tmp/slack_post.log || true
fi

# 8) Exit with the agent's status
exit $STATUS

# If you want the desktop to stay up after the run for inspection, replace the last line with:
# wait || true; tail -f /dev/null
