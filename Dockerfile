FROM python:3.11-slim

# Install system dependencies including Xvfb for virtual display
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements2.txt .
RUN pip install --no-cache-dir -r requirements2.txt

# Install Playwright browsers
RUN playwright install --with-deps chromium

# Copy application code
COPY . .

# Set up virtual display and run the application
CMD xvfb-run -a python main_sub_scan.py