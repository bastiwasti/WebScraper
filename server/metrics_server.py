import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psycopg2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PG_HOST, PG_PORT, PG_DATABASE, PG_USER, PG_PASSWORD, PG_SCHEMA

SERVER_VERSION = "1.0.0"
RUN_STALE_HOURS = 25
RUN_IN_PROGRESS_MAX_HOURS = 3


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
        connect_timeout=5,
    )


def fetch_one(cur, sql):
    cur.execute(sql)
    return cur.fetchone()


def build_health():
    conn = get_conn()
    cur = conn.cursor()
    try:
        last_run = fetch_one(
            cur,
            f"SELECT run_id, start_time, events_found, valid_events, duration "
            f"FROM {PG_SCHEMA}.status WHERE full_run = 1 ORDER BY start_time DESC LIMIT 1"
        )
        last_rating = fetch_one(
            cur,
            f"SELECT run_id, start_time, events_rated, ratings_failed "
            f"FROM {PG_SCHEMA}.status WHERE agent_type = 'rating' ORDER BY start_time DESC LIMIT 1"
        )
        conn.commit()
    finally:
        conn.close()

    now = datetime.now(timezone.utc)
    body = {
        "timestamp": now.isoformat(),
        "version": SERVER_VERSION,
        "db": "ok",
        "check": pipeline_check(now, last_run, last_rating),
    }
    if body["check"]["status"] != "ok":
        return 503, {"status": "down", **body}
    return 200, {"status": "ok", **body}


def pipeline_check(now, last_run, last_rating):
    check = {"status": "ok", "last_scrape": None, "last_rating": None, "problems": []}
    if last_run is None:
        check["status"] = "down"
        check["problems"].append("Kein Scraper-Run in der DB - Pipeline lief nie")
        return check

    run_id, start_time, events_found, valid_events, duration = last_run
    start_time = to_utc(start_time)
    age_h = (now - start_time).total_seconds() / 3600
    check["last_scrape"] = {"run_id": run_id, "started_at": to_iso(start_time), "age_hours": round(age_h, 2), "events_found": events_found}

    if duration is None:
        if age_h > RUN_IN_PROGRESS_MAX_HOURS:
            check["status"] = "down"
            check["problems"].append(f"Run {run_id} haengt seit {age_h:.1f}h")
    else:
        if age_h > RUN_STALE_HOURS:
            check["status"] = "down"
            check["problems"].append(f"Letzter Full-Run {age_h:.1f}h alt (Schwellwert {RUN_STALE_HOURS}h) - Cron faehrt nicht")
        if events_found == 0:
            check["status"] = "down"
            check["problems"].append(f"Letzter Full-Run hat 0 Events gefunden (DNS-/Netzfehler?)")

    if last_rating is not None:
        r_id, r_start, rated, failed = last_rating
        r_start = to_utc(r_start)
        r_age_h = (now - r_start).total_seconds() / 3600
        check["last_rating"] = {"run_id": r_id, "started_at": to_iso(r_start), "events_rated": rated, "ratings_failed": failed}
        if r_age_h <= RUN_STALE_HOURS and rated == 0 and failed > 0:
            check["status"] = "down"
            check["problems"].append(f"Rating-Run {r_id} hat 0 geratet, {failed} Fehlversuche (LLM/DNS)")
    return check


def to_iso(value):
    return value.isoformat()


def build_stats():
    conn = get_conn()
    cur = conn.cursor()
    try:
        row = fetch_one(
            cur,
            f"SELECT run_id, start_time, events_found, valid_events FROM {PG_SCHEMA}.status "
            f"WHERE full_run = 1 AND end_time IS NOT NULL ORDER BY start_time DESC LIMIT 1"
        )
        rated_row = fetch_one(
            cur,
            f"SELECT events_rated FROM {PG_SCHEMA}.status WHERE agent_type = 'rating' "
            f"AND end_time IS NOT NULL ORDER BY start_time DESC LIMIT 1"
        )
        rated_30d = fetch_one(
            cur,
            f"SELECT COUNT(*) FROM {PG_SCHEMA}.status WHERE agent_type = 'rating' "
            f"AND start_time::timestamp > NOW() - INTERVAL '30 days'"
        )[0]
        sources_30d = fetch_one(
            cur,
            f"SELECT COUNT(DISTINCT source) FROM {PG_SCHEMA}.events WHERE created_at::timestamp > NOW() - INTERVAL '30 days'"
        )[0]
        distinct_total = fetch_one(cur, f"SELECT COUNT(*) FROM {PG_SCHEMA}.events_distinct")[0]
        ratings_total = fetch_one(cur, f"SELECT COUNT(*) FROM {PG_SCHEMA}.event_ratings")[0]
        conn.commit()
    finally:
        conn.close()

    timestamp = datetime.now(timezone.utc).isoformat()
    if row is None:
        return 200, {
            "timestamp": timestamp,
            "last_run": None,
            "events_scraped": 0,
            "events_rated": 0,
            "sources": 0,
        }

    run_id, start_time, events_found, valid_events = row
    events_rated = rated_row[0] if rated_row is not None else 0
    return 200, {
        "timestamp": timestamp,
        "last_run": to_utc(start_time).isoformat(),
        "last_run_id": run_id,
        "events_scraped": events_found,
        "valid_events": valid_events,
        "events_rated": events_rated,
        "events_rated_30d": rated_30d,
        "sources": sources_30d,
        "events_distinct_total": distinct_total,
        "ratings_total": ratings_total,
    }


class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/") or "/"
        if path == "/api/health":
            code, body = _safe(build_health)
        elif path == "/api/stats":
            code, body = _safe(build_stats)
        else:
            code, body = 404, {"error": "not found", "paths": ["/api/health", "/api/stats"]}
        payload = json.dumps(body, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        print(f"[metrics] {self.address_string()} {fmt % args}", flush=True)


def _safe(builder):
    try:
        return builder()
    except Exception as e:
        print(f"[metrics] ERROR: {e}", flush=True)
        return 503, {"status": "down", "error": str(e)}


if __name__ == "__main__":
    port = int(os.getenv("METRICS_PORT", "3002"))
    server = ThreadingHTTPServer(("0.0.0.0", port), MetricsHandler)
    print(f"[metrics] listening on 0.0.0.0:{port}", flush=True)
    server.serve_forever()
