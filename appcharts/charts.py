#!/usr/bin/env python3
"""Fetch US iOS Top Free chart IDs from the App Store's public chart pages.

Method (Liam's, stated 2026-11-12):
- Fetch the chart page with curl using a Safari User-Agent. A browser
  cannot show the data: it lives in the raw HTML from the server.
- The data sits in a JSON script tag:
      <script type="application/json" id="serialized-server-data">
- Inside that JSON, the page object is root["data"][0]["data"] and its
  $kind is TopChartsPage. It has a segments list with one entry per
  chart; take the one where chart == "top-free".
- In that segment, shelves[0].items holds the first 25 hydrated apps
  (adamId, ordinal, title, developerName). nextPage.remainingContent
  holds the other 175 as {"id": ..., "type": "apps"} in rank order,
  so their ranks continue from 26.
- Send those IDs to Apple's public iTunes Lookup API
  (https://itunes.apple.com/lookup?id=ID1,ID2,...&country=us) in
  batches to get names, categories, and the other fields.
- Never use Apple's private app-data API or any login.

Functions parse_server_data and parse_top_free_segment implement the
parsing exactly as described above.
"""

import json
import re
import subprocess
import sys
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15"

CHART_URL = "https://apps.apple.com/us/iphone/charts/{genre_id}"

# Sheet name -> chart-page path after /iphone/charts/, for the 42 sheets in
# the daily digest. Values are genre IDs. (Kids was dropped 2026-11-12
# per Liam — it used genre 36 with ?ageBandId=0.)
# Verified 2026-11-12/13 against Apple's own categories list in the page
# JSON and against the Nov 12 baseline file (full-200 overlap checks):
# Apps 36, Games 6014, Finance 6015, Business 6000, Education 6017,
# Shopping 6024 (not 6022), Board 7004, Card 7005, Casual 7003,
# Puzzle 7012, Music 6011, Magazines & Newspapers 6021.
# Note: the categories list in the page JSON also carries amp-api-edge URLs
# for each category — those are Apple's private API and are NOT used here.
GENRE_IDS = {
    "Top Free Apps": "36",
    "Top Free Games": "6014",
    "Books": "6018",
    "Business": "6000",
    "Developer Tools": "6026",
    "Education": "6017",
    "Entertainment": "6016",
    "Finance": "6015",
    "Food & Drink": "6023",
    "Graphics & Design": "6027",
    "Health & Fitness": "6013",
    "Lifestyle": "6012",
    "Magazines & Newspapers": "6021",
    "Medical": "6020",
    "Music": "6011",
    "Navigation": "6010",
    "News": "6009",
    "Photo & Video": "6008",
    "Productivity": "6007",
    "Reference": "6006",
    "Shopping": "6024",
    "Social Networking": "6005",
    "Sports": "6004",
    "Travel": "6003",
    "Utilities": "6002",
    "Weather": "6001",
    "Games - Action": "7001",
    "Games - Adventure": "7002",
    "Games - Board": "7004",
    "Games - Card": "7005",
    "Games - Casino": "7006",
    "Games - Casual": "7003",
    "Games - Family": "7009",
    "Games - Music": "7011",
    "Games - Puzzle": "7012",
    "Games - Racing": "7013",
    "Games - Roleplaying": "7014",
    "Games - Simulation": "7015",
    "Games - Sports": "7016",
    "Games - Strategy": "7017",
    "Games - Trivia": "7018",
    "Games - Word": "7019",
}


def fetch_chart_html(genre_id):
    """Download a chart page's raw HTML with curl + Safari User-Agent.

    genre_id is a chart-page path after /iphone/charts/ — a numeric genre ID.
    """
    url = CHART_URL.format(genre_id=genre_id)
    result = subprocess.run(
        ["curl", "-sL", "--compressed", "-A", UA, url],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr.strip()}")
    if not result.stdout:
        raise RuntimeError(f"curl returned empty body for {url}")
    return result.stdout


def parse_server_data(html):
    """Extract the serialized-server-data JSON from raw chart-page HTML."""
    match = re.search(
        r'<script type="application/json" id="serialized-server-data">(.*?)</script>',
        html, re.S,
    )
    if not match:
        raise ValueError("serialized-server-data script tag not found in page HTML")
    return json.loads(match.group(1))


def parse_top_free_segment(page):
    """Return the 200 app IDs in rank order from a TopChartsPage object.

    page is root["data"][0]["data"]. Takes the segment where
    chart == "top-free": shelves[0].items gives ranks 1-25 (adamId),
    nextPage.remainingContent gives ranks 26-200 (id).
    """
    ids, _hydrated = _segment_data(page)
    return ids


def _segment_data(page):
    """Return (ids, hydrated) for the top-free segment.

    ids: the 200 app IDs in rank order. hydrated: {adamId: {"title",
    "developerName"}} for ranks 1-25 only — the only apps the page
    carries full details for. Useful as a fallback name/developer when
    the iTunes Lookup returns nothing for one of those apps.
    """
    segments = page.get("segments") or []
    seg = next((s for s in segments if s.get("chart") == "top-free"), None)
    if seg is None:
        raise ValueError(
            "no top-free segment in page; segments found: "
            + ", ".join(str(s.get("chart")) for s in segments)
        )
    items = seg["shelves"][0]["items"]
    first = [str(item["adamId"]) for item in items]
    hydrated = {str(item["adamId"]): {"title": item.get("title"),
                                       "developerName": item.get("developerName")}
                for item in items}
    rest = [str(r["id"]) for r in seg.get("nextPage", {}).get("remainingContent", [])]
    return first + rest, hydrated


def get_top_free_ids(genre_id):
    """Fetch a chart page and return its 200 Top Free app IDs in rank order."""
    html = fetch_chart_html(genre_id)
    root = parse_server_data(html)
    page = root["data"][0]["data"]
    return parse_top_free_segment(page)


def get_top_free_chart(genre_id):
    """Fetch a chart page and return (ids, hydrated) — see _segment_data."""
    html = fetch_chart_html(genre_id)
    root = parse_server_data(html)
    page = root["data"][0]["data"]
    return _segment_data(page)


def lookup(ids, country="us"):
    """Enrich app IDs via Apple's public iTunes Lookup API, in batches of 200.

    Returns a dict mapping trackId (as str) to the lookup result object.
    IDs with no lookup result are simply absent — callers must not invent
    fields for them.
    """
    out = {}
    for i in range(0, len(ids), 200):
        batch = ids[i:i + 200]
        url = "https://itunes.apple.com/lookup?id=" + ",".join(batch) + f"&country={country}"
        with urllib.request.urlopen(url, timeout=60) as resp:
            data = json.load(resp)
        for result in data.get("results", []):
            out[str(result["trackId"])] = result
    return out


def main(argv):
    """Usage: charts.py <genre_id|sheet name> [more ...]

    With no arguments, prints the genre-ID map. Each argument is either a
    numeric genre ID or a sheet name from GENRE_IDS. Prints one JSON object
    per chart: {"genre_id": ..., "count": 200, "ids": [...]}.
    """
    if not argv:
        print(json.dumps(GENRE_IDS, indent=2, sort_keys=True))
        return 0
    for arg in argv:
        genre_id = GENRE_IDS.get(arg, arg)
        ids = get_top_free_ids(genre_id)
        print(json.dumps({"genre_id": genre_id, "count": len(ids), "ids": ids}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
