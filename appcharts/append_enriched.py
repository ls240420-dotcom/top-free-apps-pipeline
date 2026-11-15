#!/usr/bin/env python3
"""Append newly enriched batch rows to the previous merged enriched CSV.

Usage: append_enriched.py <old-merged.csv> <new-batch-merged.csv> <out.csv>
Concatenates, unions the columns (missing values blank), dedupes to one
row per App ID (keeping the lowest Rank), sorts by (Type, Rank). The
Enrichments tab is one row per enriched app, not per chart position —
an app charting in two charts keeps only its best-rank row.
"""
import csv
import sys


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
    old_path, new_path, out_path = sys.argv[1:4]
    rows = list(csv.DictReader(open(old_path))) + list(csv.DictReader(open(new_path)))
    rows = dedupe(rows)
    fields = list(rows[0].keys())
    for r in rows[1:]:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    for r in rows:
        for k in fields:
            r.setdefault(k, "")
    rows.sort(key=lambda r: (r.get("Type", ""), int(r["Rank"])))
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out_path}: {len(rows)} rows")


if __name__ == "__main__":
    main()
