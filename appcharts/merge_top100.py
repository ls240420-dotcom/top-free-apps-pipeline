#!/usr/bin/env python3
"""Merge per-batch enriched CSVs into one file, adding the
Rating Count Weekly (est) column from the raw AppGoblin JSONs.

Usage: merge_top100.py <out.csv> <batch.csv> <batch-raw.json> [<batch.csv> <batch-raw.json> ...]
Rows are sorted by (Type, Rank); batches without a Type sort first.
One row per App ID is kept (lowest Rank wins) — the Enrichments tab is
one row per enriched app, not per chart position.
"""
import csv
import json
import os
import re
import sys


def _file_date(path):
    """Date embedded in a raw filename, e.g. top-books-1-80-2026-11-13-raw.json."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    return m.group(1) if m else None


def dedupe(rows):
    """One row per App ID: keep the lowest Rank; on a tie keep the first
    row in input order (input is in sheet order, so the earliest chart
    wins)."""
    best = {}
    for r in rows:
        aid = r["App ID"]
        if aid not in best or int(r["Rank"]) < int(best[aid]["Rank"]):
            best[aid] = r
    return list(best.values())


def main():
    out = sys.argv[1]
    pairs = list(zip(sys.argv[2::2], sys.argv[3::2]))
    rows, raw, entry_dates = [], {}, {}
    for csv_path, raw_path in pairs:
        rows += list(csv.DictReader(open(csv_path)))
        batch = json.load(open(raw_path))
        raw.update(batch)
        file_date = _file_date(raw_path)
        for app_id, entry in batch.items():
            # Only entries with actual data carry a date; a failed attempt
            # must not stamp a date. Later files win (refresh order).
            if entry.get("app") is not None or entry.get("sdks") is not None:
                entry_dates[str(app_id)] = entry.get("enriched_date") or file_date or ""
    for r in rows:
        # Pre-Type batches (top 100) are all Top Free Apps.
        r.setdefault("Type", "Apps")
        entry = raw.get(str(r["App ID"]), {})
        app = entry.get("app") or {}
        r["Rating Count Weekly (est)"] = app.get("rating_count_weekly", "")
        # Enriched Date is per app, never the merge date: the raw entry's
        # own stamp first, then its file's date.
        r["Enriched Date"] = entry_dates.get(str(r["App ID"]), "")
    rows = dedupe(rows)
    rows.sort(key=lambda r: (r.get("Type", ""), int(r["Rank"])))
    fields = list(rows[0].keys())
    for r in rows[1:]:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    for r in rows:
        for k in fields:
            r.setdefault(k, "")
    # Place Type right after Rank, Rating Count Weekly right after Rating Count,
    # Enriched Date last.
    fields.remove("Type")
    fields.insert(fields.index("Rank") + 1, "Type")
    fields.remove("Rating Count Weekly (est)")
    fields.insert(fields.index("Rating Count") + 1, "Rating Count Weekly (est)")
    fields.remove("Enriched Date")
    fields.append("Enriched Date")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out}: {len(rows)} rows")


if __name__ == "__main__":
    main()
