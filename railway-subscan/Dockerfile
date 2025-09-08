# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TZ=Asia/Jerusalem \
    PLAYWRIGHT_BROWSERS_PATH=0

# OS deps for headful Chromium + video + fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata xvfb x11vnc fluxbox novnc websockify \
    ffmpeg ca-certificates curl unzip \
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libcairo2 libcups2 \
    libdrm2 libgbm1 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
    libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxdamage1 libxext6 \
    libxfixes3 libxkbcommon0 libxrandr2 libxrender1 libxshmfence1 libxtst6 \
    gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-libav \
    fonts-liberation fonts-unifont fonts-noto-core fonts-noto-color-emoji fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/* \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# ------- choose ONE of the two blocks below -------

# (A) If you created a fully pinned requirements-subscan.txt:
COPY requirements-subscan.txt /app/requirements.txt
RUN python -m pip install -U pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# (B) If you prefer to keep requirements2.txt + constraints, use this instead:
# COPY requirements2.txt constraints-subscan.txt /app/
# RUN python -m pip install -U pip \
#  && pip install --no-cache-dir -r /app/requirements2.txt -c /app/constraints-subscan.txt

# ------- end choose-one block -------

# Install the EXACT Chromium required by your pinned playwright/patchright
RUN rm -rf ~/.cache/ms-playwright \
    && python -m patchright install --with-deps --force chromium

# Project files (only subscan service)
COPY . /app/

# Start script
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
