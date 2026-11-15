#!/usr/bin/env python3
"""Map AppGoblin SKAdNetwork IDs to network names and companies, and add
the result to the top-100 enriched CSV.

Registry: skan-registry-2026-11-13.json (Unity partner list + Google 3p
list + IAB list). Adds three columns after "SKAdNetwork (n)":
"SKAdNetwork Companies (n)" (distinct companies), "SKAdNetwork
Unresolved (n)" (IDs no registry names), "SKAdNetwork Companies"
(the company list). The per-name "Networks" columns were dropped
2026-11-13: they differed from Companies on only 17 of 100 apps, never
by more than 2, so Companies alone carries the signal.

Usage: map_skan.py <top100.csv> <raw.json> [<raw.json> ...]
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skanlib import resolve


def main():
    csv_path = sys.argv[1]
    raw = {}
    for path in sys.argv[2:]:
        raw.update(json.load(open(path)))
    rows = list(csv.DictReader(open(csv_path)))
    resolved_total = unresolved_total = 0
    for r in rows:
        sk = (((raw.get(r["App ID"]) or {}).get("sdks") or {}).get("skadnetwork")) or []
        names, companies, unresolved = resolve(sk)
        r["SKAdNetwork Networks"] = "; ".join(names)
        r["SKAdNetwork Networks (n)"] = len(names)
        r["SKAdNetwork Companies"] = "; ".join(companies)
        r["SKAdNetwork Companies (n)"] = len(companies)
        r["SKAdNetwork Unresolved (n)"] = unresolved
        resolved_total += len(names)
        unresolved_total += unresolved
    fields = list(rows[0].keys())
    dropped = ("SKAdNetwork Networks", "SKAdNetwork Networks (n)")
    for c in dropped + ("SKAdNetwork Companies", "SKAdNetwork Companies (n)", "SKAdNetwork Unresolved (n)"):
        fields.remove(c)
    for r in rows:
        for c in dropped:
            r.pop(c, None)
    i = fields.index("SKAdNetwork (n)") + 1
    fields[i:i] = ["SKAdNetwork Companies (n)", "SKAdNetwork Unresolved (n)", "SKAdNetwork Companies"]
    with open(csv_path + ".tmp", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(csv_path + ".tmp", csv_path)
    print(f"mapped {resolved_total} ID occurrences to names, {unresolved_total} unresolved -> {csv_path}")


if __name__ == "__main__":
    main()
