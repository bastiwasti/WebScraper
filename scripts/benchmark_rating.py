#!/usr/bin/env python3
"""Benchmark: per-event metrics for tool-calling vs legacy across batch sizes."""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import get_connection as get_db_connection

BATCH_SIZES = [10, 25, 50, 100]
SAMPLE_COUNT = 3  # events to sample for quality check


def delete_ratings_for_ids(event_ids: list[int]):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM webscraper.event_ratings WHERE event_id = ANY(%s)", (event_ids,))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted


def count_ratings_for_ids(event_ids: list[int]) -> int:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM webscraper.event_ratings WHERE event_id = ANY(%s)", (event_ids,))
    count = cur.fetchone()['count']
    cur.close()
    conn.close()
    return count


def get_test_event_ids(n: int) -> list[int]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ed.id FROM webscraper.events_distinct ed
        WHERE NOT EXISTS (SELECT 1 FROM webscraper.event_ratings er WHERE er.event_id = ed.id)
        ORDER BY ed.id LIMIT %s
    """, (n,))
    ids = [row['id'] for row in cur.fetchall()]
    cur.close()
    conn.close()
    return ids


def get_sample_ratings(event_ids: list[int]) -> list[dict]:
    """Query back ratings for sample events."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT r.event_id, e.name, r.rating, r.rating_inhaltlich, r.rating_ort,
               r.rating_ausstattung, r.rating_interaktion, r.rating_kosten, r.rating_reason
        FROM webscraper.event_ratings r
        JOIN webscraper.events_distinct e ON e.id = r.event_id
        WHERE r.event_id = ANY(%s)
        ORDER BY r.event_id
    """, (event_ids,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def run_single(test_ids: list[int], use_tools: bool, batch_size: int) -> dict:
    """Run one benchmark: rate exactly batch_size events in 1 batch."""
    from agents.rating_agent import RatingAgent

    mode = "tools" if use_tools else "legacy"
    ids_subset = test_ids[:batch_size]

    # Clean slate
    delete_ratings_for_ids(ids_subset)

    agent = RatingAgent(use_tools=use_tools)
    start = time.time()
    result = agent.run(filters={}, max_events=batch_size, batch_size=batch_size, verbose=False)
    elapsed = time.time() - start

    saved = count_ratings_for_ids(ids_subset)

    # Sample ratings for quality check
    sample_ids = ids_subset[:SAMPLE_COUNT]
    samples = get_sample_ratings(sample_ids)

    # Clean up
    delete_ratings_for_ids(ids_subset)

    inp = result.get("input_tokens", 0)
    out = result.get("output_tokens", 0)
    total_tokens = inp + out

    r = {
        "mode": mode,
        "batch_size": batch_size,
        "elapsed": round(elapsed, 1),
        "saved": saved,
        "input_tokens": inp,
        "output_tokens": out,
        "total_tokens": total_tokens,
        "failed": len(result.get("failed_events", [])),
        "time_per_event": round(elapsed / saved, 2) if saved > 0 else None,
        "tokens_per_event": round(total_tokens / saved) if saved > 0 else None,
        "samples": samples,
    }

    print(f"  {mode:>6} b={batch_size:<4} => {saved}/{batch_size} saved, "
          f"{r['time_per_event']}s/evt, {r['tokens_per_event']} tok/evt, {elapsed:.1f}s total")
    return r


def main():
    # Get enough events for the largest batch
    max_bs = max(BATCH_SIZES)
    test_ids = get_test_event_ids(max_bs)
    print(f"Test pool: {len(test_ids)} event IDs (need {max_bs})")

    if len(test_ids) < max_bs:
        print(f"ERROR: Only {len(test_ids)} unrated events, need {max_bs}")
        return

    all_results = []

    for bs in BATCH_SIZES:
        for use_tools in [False, True]:
            r = run_single(test_ids, use_tools=use_tools, batch_size=bs)
            all_results.append(r)

    # --- Main metrics table ---
    by_key = {(r["mode"], r["batch_size"]): r for r in all_results}

    col_labels = []
    for bs in BATCH_SIZES:
        col_labels.append(f"Leg b={bs}")
        col_labels.append(f"Tool b={bs}")

    col_w = 12
    print(f"\n{'='*120}")
    print(f"  BENCHMARK RESULTS (per-event metrics)")
    print(f"{'='*120}")

    header = f"{'Metric':<20}"
    for label in col_labels:
        header += f" {label:>{col_w}}"
    print(header)
    print("-" * (20 + (col_w + 1) * len(col_labels)))

    rows = [
        ("Time/event (s)", "time_per_event"),
        ("Tokens/event", "tokens_per_event"),
        ("Saved", "saved"),
        ("Failed", "failed"),
        ("Time total (s)", "elapsed"),
        ("Tokens total", "total_tokens"),
    ]

    for label, key in rows:
        line = f"{label:<20}"
        for bs in BATCH_SIZES:
            for mode in ["legacy", "tools"]:
                r = by_key.get((mode, bs), {})
                val = r.get(key, "N/A")
                line += f" {str(val):>{col_w}}"
        print(line)

    # --- Quality sample ---
    sample_ids = test_ids[:SAMPLE_COUNT]

    print(f"\n{'='*120}")
    print(f"  QUALITY SAMPLE (first {SAMPLE_COUNT} events)")
    print(f"{'='*120}")

    for sid in sample_ids:
        # Find event name from any result that has it
        name = "?"
        for r in all_results:
            for s in r.get("samples", []):
                if s["event_id"] == sid:
                    name = s["name"][:50]
                    break
            if name != "?":
                break

        print(f"\nEvent ID {sid}: {name}")
        for r in all_results:
            sample = next((s for s in r.get("samples", []) if s["event_id"] == sid), None)
            label = f"  {r['mode']:>6} b={r['batch_size']:<4}"
            if sample:
                rating = sample['rating']
                reason = (sample.get('rating_reason') or '')[:80]
                subs = f"[inh={sample['rating_inhaltlich']} ort={sample['rating_ort']} aus={sample['rating_ausstattung']} int={sample['rating_interaktion']} kos={sample['rating_kosten']}]"
                print(f"{label} {rating}/5 {subs} {reason}")
            else:
                print(f"{label} NOT RATED")


if __name__ == "__main__":
    main()
