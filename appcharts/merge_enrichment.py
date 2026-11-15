#!/usr/bin/env python3
"""Merge AppGoblin *-raw.json enrichment files into the persistent store
appgoblin-enrichment.json, keyed by App ID. Latest values win.

Usage: merge_enrichment.py <raw1.json> [<raw2.json> ...] [--store PATH]
Each raw file is {app_id: {"app": {...}|None, "sdks": {...}|None, ...}}
produced by appgoblin_enrich.py. The store is what build_master.py reads
to add enrichment columns to the Master List.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from skanlib import load_registry, resolve

DEFAULT_STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "appgoblin-enrichment.json")


def _file_date(path):
    """Date embedded in a raw filename, e.g. top-books-1-80-2026-11-13-raw.json."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    return m.group(1) if m else None


def extract(app_id, entry, date):
    app = entry.get("app") or {}
    sdks = entry.get("sdks") or {}
    cats = sdks.get("company_categories", {}) or {}
    vendors = sorted({v for c in cats.values() for v in c.keys()})
    skadnetwork = sdks.get("skadnetwork") or []
    _names, companies, unresolved = resolve(skadnetwork)
    return {
        "enriched_date": date,
        "rating_count_weekly": app.get("rating_count_weekly"),
        "skan_companies": companies,
        "skan_companies_n": len(companies),
        "skan_ids_n": len(skadnetwork),
        "skan_unresolved_n": unresolved,
        "installs": app.get("installs"),
        "installs_weekly": app.get("installs_weekly"),
        "installs_monthly": app.get("installs_monthly"),
        "wau": app.get("weekly_active_users"),
        "mau": app.get("monthly_active_users"),
        "monthly_ad_revenue": app.get("monthly_ad_revenue"),
        "monthly_iap_revenue": app.get("monthly_iap_revenue"),
        "ad_supported": app.get("ad_supported"),
        "in_app_purchases": app.get("in_app_purchases"),
        "attribution_sdks": sorted(cats.get("ad-attribution", {}).keys()),
        "ad_network_sdks": sorted(cats.get("ad-networks", {}).keys()),
        "sdk_vendors_n": len(vendors),
        "sdk_vendors": vendors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", nargs="+")
    parser.add_argument("--store", default=DEFAULT_STORE)
    parser.add_argument("--date", default="2026-11-13")
    args = parser.parse_args()
    store = json.load(open(args.store)) if os.path.exists(args.store) else {}
    n = 0
    skipped = 0
    for path in args.raw:
        raw = json.load(open(path))
        file_date = _file_date(path)
        for app_id, entry in raw.items():
            # A total failure (no app data AND no SDK data) stores nothing:
            # a failed refresh must not clobber good data or its date, and
            # a first-time failure leaves the app absent so a later run
            # can enrich it cleanly. Drop any stale failed entry too.
            if entry.get("app") is None and entry.get("sdks") is None:
                store.pop(str(app_id), None)
                skipped += 1
                continue
            # Enriched date is per app, never the run date: the entry's
            # own stamp first, then the raw file's date, then --date.
            date = entry.get("enriched_date") or file_date or args.date
            store[str(app_id)] = extract(app_id, entry, date)
            n += 1
    json.dump(store, open(args.store, "w"), indent=2)
    print(f"merged {n} entries from {len(args.raw)} file(s) ({skipped} total failures skipped); store now has {len(store)} apps -> {args.store}")


if __name__ == "__main__":
    main()
