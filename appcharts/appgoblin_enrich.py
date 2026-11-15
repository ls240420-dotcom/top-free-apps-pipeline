#!/usr/bin/env python3
"""Enrich a list of App Store apps with AppGoblin get_app + get_app_sdks.

Usage: enrich_top.py <apps.json> <out_prefix>
  apps.json: list of {rank, app_id, app, ...}
  Writes <out_prefix>-raw.json, <out_prefix>.csv.
  40 calls for 20 apps; sleeps 2.2s between calls to stay under the
  free key's 30 req/min limit. Failures are recorded, never invented.
"""
import csv
import json
import subprocess
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

CLIENT = "/home/hatch/workspace/custom-connectors/custom.appgoblin/bin/client.py"
SLEEP = 2.2


def call(cmd, app_id):
    out = subprocess.run(["python3", CLIENT, cmd, str(app_id)],
                         capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        return None, out.stderr.strip()[:300]
    return json.loads(out.stdout), None


def sdk_summary(d):
    if d is None:
        return {"attribution": [], "ad_networks": [], "vendors": [], "n_vendors": 0,
                "categories": [], "n_permissions": 0, "n_skadnetwork": 0}
    cats = d.get("company_categories", {}) or {}
    vendors = sorted({v for c in cats.values() for v in c.keys()})
    return {
        "attribution": sorted(cats.get("ad-attribution", {}).keys()),
        "ad_networks": sorted(cats.get("ad-networks", {}).keys()),
        "vendors": vendors,
        "n_vendors": len(vendors),
        "n_permissions": len(d.get("permissions", []) or []),
        "n_skadnetwork": len(d.get("skadnetwork", []) or []),
        "categories": sorted(cats.keys()),
    }


def main():
    apps = json.load(open(sys.argv[1]))
    prefix = sys.argv[2]
    # Stamp the enrichment date (America/New_York) on every row and raw
    # entry, so a later refresh can tell fresh data from stale data.
    today = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    raw = {}
    rows = []
    for a in apps:
        app_id = a["app_id"]
        app_data, app_err = call("app", app_id)
        time.sleep(SLEEP)
        sdk_data, sdk_err = call("sdks", app_id)
        time.sleep(SLEEP)
        raw[app_id] = {"app": app_data, "app_error": app_err,
                       "sdks": sdk_data, "sdks_error": sdk_err,
                       "enriched_date": today}
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
            "Enriched Date": today,
        })
        if sdk_err:
            r["AppGoblin SDK Error"] = sdk_err
        rows.append(r)
        print(f"rank {a['rank']} {a['app']}: app={'OK' if app_data else 'ERR'} "
              f"sdks={'OK' if sdk_data else 'ERR'} vendors={sd['n_vendors']}", flush=True)
    json.dump(raw, open(prefix + "-raw.json", "w"), indent=2)
    # Fieldnames must be the union of all rows' keys: error rows carry
    # "AppGoblin App Error" / "AppGoblin SDK Error" keys that rows[0]
    # may not have (a rows[0]-only field list crashes writerows).
    fields = list(rows[0].keys())
    for r in rows[1:]:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    for r in rows:
        for k in fields:
            r.setdefault(k, "")
    with open(prefix + ".csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {prefix}-raw.json and {prefix}.csv")


if __name__ == "__main__":
    main()
