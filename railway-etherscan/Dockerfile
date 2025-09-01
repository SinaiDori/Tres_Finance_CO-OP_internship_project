# Alternative: Use pre-built Playwright image
FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements2.txt .
RUN pip install --no-cache-dir -r requirements2.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python", "main_etherscan.py"]