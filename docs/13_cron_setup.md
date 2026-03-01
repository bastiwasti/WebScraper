# Cron Job Setup - Daily Event Scraping

## Status: ✅ COMPLETED

Cron job successfully installed and configured for daily automatic scraping.

---

## Configuration Summary

### Time Settings
- **Run Time:** 3:00 AM daily
- **Timezone:** Europe/Berlin (CET/CEST)
- **DST Handling:** Automatic (switches between CET and CEST)

### Scope
- **Cities:** All (monheim, langenfeld, leverkusen, hilden, dormagen)
- **Agents:** Both scraper and analyzer
- **Database:** Events saved to PostgreSQL (vmpostgres, webscraper schema)
- **Logging:** Daily log files with rotation

---

## Crontab Entries

### Daily Scraping Job
```bash
0 3 * * * cd /home/vscode/projects/WebScraper && /home/vscode/projects/WebScraper/venv/bin/python3 main.py --agent all --full-run >> logs/daily_scrape_$(date +\%Y\%m\%d).log 2>&1
```

**Details:**
- Runs every day at 3:00 AM CET
- Changes to project directory
- Uses venv Python (full path for cron)
- Runs both scraper and analyzer agents
- Saves events to database
- Appends output to dated log file: `logs/daily_scrape_YYYYMMDD.log`

### Log Rotation Job
```bash
0 4 * * 0 find /home/vscode/projects/WebScraper/logs/ -name 'daily_scrape_*.log' -mtime +30 -delete
```

**Details:**
- Runs every Sunday at 4:00 AM CET
- Deletes logs older than 30 days
- Prevents disk space bloat

---

## System Configuration

### Timezone
```bash
$ timedatectl
               Local time: Sat 2026-02-14 10:51:25 CET
           Universal time: Sat 2026-02-14 09:51:25 UTC
                 RTC time: Sat 2026-02-14 09:51:25
                Time zone: Europe/Berlin (CET, +0100)
System clock synchronized: yes
              NTP service: active
          RTC in local TZ: no
```

### Cron Service
```bash
$ systemctl status cron
● cron.service - Regular background program processing daemon
     Loaded: loaded (/usr/lib/systemd/system/cron.service; enabled)
     Active: active (running) since Thu 2026-02-05 20:10:51 CET
```

---

## Log File Locations

### Daily Scraping Logs
- **Path:** `/home/vscode/projects/WebScraper/logs/daily_scrape_YYYYMMDD.log`
- **Example:** `daily_scrape_20260214.log`
- **Retention:** 30 days
- **Rotation:** Automatic deletion on Sundays

### Scraper Agent Logs
- **Path:** `/home/vscode/projects/WebScraper/logs/scrape_YYYY-MM-DD_HH-MM-SS.log`
- **Generated:** Each scraper run
- **Retention:** Not managed by log rotation

---

## Commands

### View Current Crontab
```bash
crontab -l
```

### Edit Crontab
```bash
crontab -e
```

### Check Cron Service Status
```bash
systemctl status cron
```

### View Today's Scraping Log
```bash
tail -f /home/vscode/projects/WebScraper/logs/daily_scrape_$(date +%Y%m%d).log
```

### View All Scraping Logs
```bash
ls -lht /home/vscode/projects/WebScraper/logs/daily_scrape_*.log | head -10
```

### Manually Trigger Daily Scraping
```bash
cd /home/vscode/projects/WebScraper && /home/vscode/projects/WebScraper/venv/bin/python3 main.py --agent all --full-run
```

### Test Cron Command
```bash
cd /home/vscode/projects/WebScraper && /home/vscode/projects/WebScraper/venv/bin/python3 main.py --agent all --full-run >> /home/vscode/projects/WebScraper/logs/test_run.log 2>&1
```

---

## Expected Runtime

### Estimated Execution Times
- **Scraper Agent:** 5-10 minutes (all 5 cities with Level 2)
- **Analyzer Agent:** 2-5 minutes
- **Total:** 7-15 minutes per day

### Performance Notes
- Dormagen: ~50 events × 5s/event = ~250s (Level 2)
- Other cities: Faster (no Level 2 or fewer events)
- Total events expected: ~800-1000 events/day

---

## Troubleshooting

### Check if Job Ran Today
```bash
ls -lht /home/vscode/projects/WebScraper/logs/daily_scrape_*.log | head -1
```

### View Cron Logs
```bash
sudo tail -f /var/log/syslog | grep CRON
```

### Test Cron Command Manually
```bash
cd /home/vscode/projects/WebScraper && /home/vscode/projects/WebScraper/venv/bin/python3 main.py --agent all --full-run
```

### Check Environment Issues
```bash
# Cron runs with minimal environment
# Check if all needed environment variables are set
printenv | grep -E "(LLM_|DEEPSEEK|DEFAULT_)"
```

---

## Modification Examples

### Change Run Time
Edit crontab (`crontab -e`) and change the time:
```bash
# Run at 6:00 AM instead of 3:00 AM
0 6 * * * cd /home/vscode/projects/WebScraper && ...
```

### Change Log Retention
Edit crontab and change the mtime parameter:
```bash
# Keep logs for 60 days instead of 30
0 4 * * 0 find /home/vscode/projects/WebScraper/logs/ -name 'daily_scrape_*.log' -mtime +60 -delete
```

### Skip Specific Cities
Edit crontab and add `--cities` parameter:
```bash
# Scrape only monheim and langenfeld
0 3 * * * cd /home/vscode/projects/WebScraper && /home/vscode/projects/WebScraper/venv/bin/python3 main.py --agent all --full-run --cities monheim langenfeld >> logs/daily_scrape_$(date +\%Y\%m\%d).log 2>&1
```

---

## Setup Date
- **Date:** February 14, 2026
- **Status:** Active
- **Next Run:** February 15, 2026 at 3:00 AM CET
