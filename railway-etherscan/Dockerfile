# Use Python 3.11 (matches your working GitHub Actions setup)
FROM python:3.11-slim

# Install system dependencies (same as your GitHub Actions)
RUN apt-get update && apt-get install -y \
    xvfb \
    ffmpeg \
    wget \
    gnupg \
    unzip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements2.txt .

# Install Python deps (same as your GitHub Actions)
RUN python -m pip install -U pip && \
    pip install -r requirements2.txt

# Install browsers using the EXACT same process as your working GitHub Actions
RUN rm -rf ~/.cache/ms-playwright && \
    python -m patchright install --with-deps --force chromium

# Sanity check (same as your GitHub Actions)
RUN python -c "import os, glob; bins = glob.glob(os.path.expanduser('~/.cache/ms-playwright/chromium-*/chrome-linux/chrome')); print('Found Chromium bins:', bins); assert bins, 'Chromium browser not installed'"

# Patchright smoke test (same as your GitHub Actions)
RUN python -c "from patchright.sync_api import sync_playwright; p = sync_playwright(); b = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-dev-shm-usage']); page = b.new_page(); page.goto('https://example.com', timeout=60000); print('Smoke test page title:', page.title()); b.close(); p.stop()"

# Copy application code
COPY . .

# Set environment variables (same as your GitHub Actions)
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Create startup script (mirrors your GitHub Actions process)
RUN echo '#!/bin/bash\n\
    set -euo pipefail\n\
    # Start Xvfb display\n\
    Xvfb :99 -screen 0 1650x800x24 -ac +extension RANDR &\n\
    export DISPLAY=:99\n\
    sleep 2\n\
    # Run the script\n\
    python main_etherscan.py' > start.sh && chmod +x start.sh

# Run the application
CMD ["./start.sh"]