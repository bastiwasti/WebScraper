#!/bin/bash
set -e

# Persist environment variables for cron jobs (cron doesn't inherit shell env)
# Python repr() ensures proper quoting/escaping of all values
python3 -c "
import os
with open('/app/.cron_env', 'w') as f:
    for k, v in os.environ.items():
        # Skip internal/system vars and values with embedded newlines
        if k.startswith('_') or '\n' in v or '\r' in v:
            continue
        f.write(f'export {k}={repr(v)}\n')
"
chmod 600 /app/.cron_env

echo "WebScraper cron container started. Scheduled jobs:"
crontab -l

exec cron -f
