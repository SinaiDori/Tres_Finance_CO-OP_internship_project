# Use Python 3.11 (match your local environment)
FROM python:3.11-slim

# Install system dependencies for browser automation
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome browser (updated method for newer Ubuntu)
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for better caching)
COPY requirements2.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Create script to start Xvfb and run the app
RUN echo '#!/bin/bash\n\
    Xvfb :99 -screen 0 1920x1080x24 &\n\
    exec python main_etherscan.py' > start.sh && chmod +x start.sh

# Run the application
CMD ["./start.sh"]