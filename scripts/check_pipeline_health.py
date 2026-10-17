import os
import sys
from datetime import datetime, timezone

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD, PG_SCHEMA


ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")
STALE_RUN_HOURS = 25
MIN_FULL_RUN_EVENTS = 50


def to_utc(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


def get_conn():
    return psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DATABASE,
        user=PG_USER, password=PG_PASSWORD,
    )


def query_last_full_run(cur):
    cur.execute(
        f"SELECT run_id, start_time, events_found, valid_events, duration "
        f"FROM {PG_SCHEMA}.status WHERE full_run = 1 ORDER BY start_time DESC LIMIT 1"
    )
    return cur.fetchone()


def query_last_rating_run(cur):
    cur.execute(
        f"SELECT run_id, start_time, events_rated, ratings_failed "
        f"FROM {PG_SCHEMA}.status WHERE agent_type = 'rating' ORDER BY start_time DESC LIMIT 1"
    )
    return cur.fetchone()


def main():
    alerts = []
    conn = get_conn()
    cur = conn.cursor()
    try:
        run = query_last_full_run(cur)
        if run is None:
            alerts.append("Kein Scraper-Run in der DB gefunden")
        else:
            run_id, start_time, events_found, valid_events, duration = run
            start_time = to_utc(start_time)
            age_h = (datetime.now(timezone.utc) - start_time).total_seconds() / 3600
            if age_h > STALE_RUN_HOURS:
                alerts.append(
                    f"Letzter Scraper-Run ist {age_h:.1f}h alt (erwartet < {STALE_RUN_HOURS}h) - "
                    f"Cron faehrt offenbar nicht"
                )
            if events_found == 0:
                alerts.append(
                    f"Scraper-Run {run_id} ({start_time:%d.%m. %H:%M} UTC) hat 0 Events gefunden "
                    f"(Dauer {duration if duration is not None else 0:.0f}s) - "
                    f"Netz-/DNS- oder Seitenproblem"
                )
            elif events_found < MIN_FULL_RUN_EVENTS:
                alerts.append(
                    f"Scraper-Run {run_id} hat nur {events_found} Events gefunden "
                    f"(Schwellwert {MIN_FULL_RUN_EVENTS})"
                )
        rating = query_last_rating_run(cur)
        if rating is not None:
            r_id, r_start, rated, failed = rating
            r_start = to_utc(r_start)
            r_age_h = (datetime.now(timezone.utc) - r_start).total_seconds() / 3600
            if r_age_h <= STALE_RUN_HOURS and failed > 0 and rated == 0:
                alerts.append(
                    f"Rating-Run {r_id} hat 0 geratet, {failed} Fehlversuche (LLM/DNS-Fehler?)."
                )
    finally:
        conn.close()

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if alerts:
        msg = f"⚠ WebScraper Pipeline am {ts}:\n" + "\n".join(f"- {a}" for a in alerts)
        print(msg)
        if ALERT_WEBHOOK_URL:
            import requests
            try:
                requests.post(ALERT_WEBHOOK_URL,
                              data=msg.encode("utf-8"),
                              headers={"Title": "WebScraper Pipeline Alert"},
                              timeout=10)
                print("Alert versendet:", ALERT_WEBHOOK_URL)
            except Exception as e:
                print(f"Alert-Versand fehlgeschlagen: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"OK - Pipeline gesund ({ts})")


if __name__ == "__main__":
    main()
