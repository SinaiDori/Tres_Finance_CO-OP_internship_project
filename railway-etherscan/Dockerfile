# syntax=docker/dockerfile:1
FROM python:3.11-slim

# CONTAINERIZED BROWSER AUTOMATION ENVIRONMENT
# This Dockerfile creates a complete headless browser automation environment with visual debugging 
# capabilities. It installs a full desktop stack (Xvfb, VNC, Fluxbox, noVNC) for remote browser 
# monitoring, all necessary Chromium dependencies for Playwright automation, and Python runtime 
# requirements. The container provides both automated execution capabilities and web-based remote 
# desktop access for troubleshooting browser automation workflows in cloud environments.

ENV DEBIAN_FRONTEND=noninteractive

# System packages:
# - Xvfb/x11vnc/fluxbox/novnc/websockify = headful desktop you can stream
# - GTK/Chromium deps + GStreamer + fonts = what Playwright/Chromium need
RUN apt-get update && apt-get install -y --no-install-recommends \
    xvfb x11vnc fluxbox novnc websockify \
    ffmpeg ca-certificates curl unzip \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libcairo2 libcups2 \
    libdrm2 libgbm1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
    libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxdamage1 libxext6 \
    libxfixes3 libxkbcommon0 libxrandr2 libxrender1 libxshmfence1 libxtst6 \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-libav \
    fonts-liberation fonts-unifont fonts-noto-core fonts-noto-color-emoji fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements2.txt .
RUN pip install --no-cache-dir -r requirements2.txt

# Download Chromium for patchright/playwright (no OS deps here)
RUN rm -rf ~/.cache/ms-playwright && \
    python -m patchright install chromium

# Project files
COPY . .

# Start script (created below)
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Optional: skip host checks if Playwright nags
# ENV PLAYWRIGHT_SKIP_VALIDATE_HOST_REQUIREMENTS=1

# Entry
CMD ["/app/start.sh"]
