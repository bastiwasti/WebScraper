FROM python:3.12-slim

WORKDIR /app

# Install system deps: cron + Playwright browser dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser (chromium) with its OS dependencies
RUN playwright install --with-deps chromium

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Set up crontab
COPY docker/crontab /etc/cron.d/webscraper
RUN chmod 0644 /etc/cron.d/webscraper && crontab /etc/cron.d/webscraper

# Entrypoint: exports env vars for cron, then starts crond
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
