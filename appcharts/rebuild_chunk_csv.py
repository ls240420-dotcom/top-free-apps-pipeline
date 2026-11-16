#!/usr/bin/env python3
"""Rebuild a chunk CSV from its saved list JSON + raw JSON, without
re-calling the API. Used when appgoblin_enrich.py died after writing
the raw JSON but before (or during) the CSV write.

Usage: rebuild_chunk_csv.py <list.json> <raw.json> <out.csv>
Row construction mirrors appgoblin_enrich.py exactly (same sdk_summary).
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from appgoblin_enrich import sdk_summary


def main():
    list_path, raw_path, out_path = sys.argv[1:4]
    with open(list_path) as f:
        apps = json.load(f)
    with open(raw_path) as f:
        raw = json.load(f)
    rows = []
    for a in apps:
        app_id = str(a["app_id"])
        entry = raw.get(app_id, {})
        app_data = entry.get("app")
        app_err = entry.get("app_error")
        sdk_data = entry.get("sdks")
        sdk_err = entry.get("sdks_error")
        sd = sdk_summary(sdk_data)
        r = {
            "Rank": a["rank"], "Type": a.get("type", ""), "App": a["app"], "App ID": app_id,
            "Developer": a.get("developer", ""), "Seller": a.get("seller", ""),
            "Category": a.get("category", ""),
            "Avg Rating": a.get("avg_rating", ""), "Rating Count": a.get("rating_count", ""),
        }
        if app_data:
            r.update({
                "Installs (est)": app_data.get("installs"),
                "Installs Weekly (est)": app_data.get("installs_weekly"),
                "Installs Monthly (est)": app_data.get("installs_monthly"),
                "WAU (est)": app_data.get("weekly_active_users"),
                "MAU (est)": app_data.get("monthly_active_users"),
                "Monthly Ad Revenue (est)": app_data.get("monthly_ad_revenue"),
                "Monthly IAP Revenue (est)": app_data.get("monthly_iap_revenue"),
                "Ad Supported": app_data.get("ad_supported"),
                "In-App Purchases": app_data.get("in_app_purchases"),
                "Developer URL": app_data.get("developer_url", ""),
                "Release Date": app_data.get("release_date", ""),
            })
        else:
            r["AppGoblin App Error"] = app_err
        r.update({
            "Attribution SDKs": "; ".join(sd["attribution"]),
            "Ad Network SDKs": "; ".join(sd["ad_networks"]),
            "SDK Vendors (n)": sd["n_vendors"],
            "SDK Vendors": "; ".join(sd["vendors"]),
            "SDK Categories": "; ".join(sd["categories"]),
            "SKAdNetwork (n)": sd.get("n_skadnetwork", 0),
            # Carry the enrichment date from the raw JSON so the rebuilt CSV
            # matches what appgoblin_enrich.py would have written (fix: was
            # missing, causing Enriched Date to appear blank in the Master List).
            "Enriched Date": entry.get("enriched_date", ""),
        })
        if sdk_err:
            r["AppGoblin SDK Error"] = sdk_err
        rows.append(r)
    fields = list(rows[0].keys())
    for r in rows[1:]:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    for r in rows:
        for k in fields:
            r.setdefault(k, "")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"rebuilt {out_path}: {len(rows)} rows")


if __name__ == "__main__":
    main()
