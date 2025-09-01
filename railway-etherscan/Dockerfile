# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# System deps that Chromium/Playwright need on Debian 13 (trixie)
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb ffmpeg ca-certificates curl unzip \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libcairo2 libcups2 \
    libdrm2 libgbm1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
    libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxdamage1 libxext6 \
    libxfixes3 libxkbcommon0 libxrandr2 libxrender1 libxshmfence1 libxtst6 \
    gstreamer1.0-libav gstreamer1.0-plugins-good gstreamer1.0-plugins-base \
    fonts-liberation fonts-ubuntu fonts-unifont \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# If your file is named requirements2.txt:
COPY requirements2.txt .
RUN pip install --no-cache-dir -r requirements2.txt

# Download the Chromium binary, but DON'T try to apt-get OS deps here
RUN rm -rf ~/.cache/ms-playwright && \
    python -m patchright install chromium

# Project files
COPY . .

ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Small launcher (headful under Xvfb, which Cloudflare often prefers)
RUN printf '#!/bin/bash\nset -euo pipefail\nXvfb :99 -screen 0 1650x800x24 -ac +extension RANDR &\nexport DISPLAY=:99\nsleep 2\npython main_etherscan.py\n' > /app/start.sh \
    && chmod +x /app/start.sh

CMD ["/app/start.sh"]
