"""URL health checker for locations."""

import requests

from locations.storage import get_locations_with_urls, update_url_status


def check_all_urls() -> dict:
    """Check all location URLs and update their status.

    Returns:
        Summary dict with counts by status.
    """
    locations = get_locations_with_urls()
    if not locations:
        print("No locations with URLs to check.")
        return {"total": 0}

    print(f"Checking {len(locations)} URLs ...")
    results = {"ok": 0, "broken": 0, "redirect": 0, "total": len(locations)}

    for loc in locations:
        url = loc["website_url"]
        status = _check_single_url(url)
        update_url_status(loc["id"], status)
        results[status] = results.get(status, 0) + 1

        symbol = {"ok": "✓", "broken": "✗", "redirect": "→"}.get(status, "?")
        print(f"  {symbol} [{status:>8}] {loc['name'][:40]:<40} {url}")

    print(f"\nResults: {results['ok']} ok, {results['broken']} broken, {results['redirect']} redirect")
    return results


def _check_single_url(url: str) -> str:
    """Check a single URL. Returns 'ok', 'broken', or 'redirect'."""
    try:
        resp = requests.head(url, timeout=10, allow_redirects=False)
        if 200 <= resp.status_code < 300:
            return "ok"
        elif 300 <= resp.status_code < 400:
            return "redirect"
        else:
            # Try GET as fallback — some servers reject HEAD
            resp = requests.get(url, timeout=10, allow_redirects=True)
            if resp.status_code == 200:
                return "ok"
            return "broken"
    except requests.RequestException:
        return "broken"
