#!/usr/bin/env python3
"""Build the daily Top Free XLSX: fetch chart IDs, enrich via iTunes Lookup,
and write the 42-sheet / 200-row / 32-column file mirroring Liam's Nov 12 file
(Kids dropped 2026-11-12 per Liam).

Usage:
  python3 build_daily.py [--date YYYY-MM-DD] [--prev PATH] [--out PATH]
                         [--ids-json PATH] [--ids-out PATH]

- --date: chart date (default: today, America/New_York).
- --prev: previous day's XLSX to compare against (default: newest
  US_Free_Charts_*.xlsx in the goal's hidden_files/, excluding --date).
- --out: output XLSX (default: goal files/US_Free_Charts_<date>.xlsx).
- --ids-json: reuse a pre-fetched IDs JSON (from charts.py) instead of
  fetching chart pages again (for testing).
- --ids-out: also save the fetched IDs JSON here.

Format, mirroring US_Free_Charts_2026-11-12.xlsx:
- 42 sheets in the baseline's exact order (Kids dropped 2026-11-12),
  200 rows each, ranks 1-200.
- Columns 1-26 as in the baseline; appended: Advisories, Rating Count
  Change, Avg Rating Change, Days Since Release, Days Since Update,
  Days in Top 200.
- Enrichment from iTunes Lookup: App=trackName, Developer=artistName,
  Seller=sellerName, Seller URL=sellerUrl (falling back to artistViewUrl,
  with Seller URL Note "artistViewUrl (developer page)" instead of
  "sellerUrl"), Category=first 7000-series genre for Games else
  primaryGenreName, Genres=", ".join(genres), Age Rating=trackContentRating,
  Avg Rating=round(averageUserRating, 5), Rating Count=userRatingCount,
  Price=formattedPrice, Released=releaseDate (date), Updated=
  currentVersionReleaseDate (date), Version=version,
  Size MB=round(fileSizeBytes/1048576, 1), Min iOS=minimumOsVersion,
  Bundle ID=bundleId, App Store link=trackViewUrl (display "App Store"),
  Primary Genre=primaryGenreName, Current Version Rating=
  round(averageUserRatingForCurrentVersion, 5), Current Version Rating
  Count=userRatingCountForCurrentVersion, Advisories="; ".join(advisories).
- Apps with no lookup result: App "(unavailable)", Category "Unknown",
  App Store link https://apps.apple.com/us/app/id<id>, everything else blank.
- Prev Rank / Change / New and the derived fields are computed against
  the previous day's file, matched by App ID within the same sheet.
  New = "Yes" when the app was not in yesterday's top 200. Days in Top 200
  is 1 for a new app, otherwise yesterday's value + 1 (yesterday counts as
  day 1 when the previous file has no Days in Top 200 column, as on Nov 12).
- Never invent ranks or fields. If a chart page yields fewer than 200 IDs,
  the sheet is written with only those rows and reported as partial.
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from datetime import date, datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import openpyxl
from openpyxl.worksheet.hyperlink import Hyperlink

from charts import GENRE_IDS, get_top_free_chart, lookup

GOAL_DIR = os.path.expanduser(
    "~/workspace/goals/daily-top-free-apps-digest")
BASELINE = os.path.join(GOAL_DIR, "hidden_files", "US_Free_Charts_2026-11-12.xlsx")

COLUMNS = [
    "Rank", "Prev Rank", "Change", "New", "App ID", "App", "Developer",
    "Seller", "Seller URL", "Category", "Genres", "Age Rating",
    "Avg Rating", "Rating Count", "Price", "Released", "Updated",
    "Version", "Size MB", "Min iOS", "Bundle ID", "App Store link",
    "Seller URL Note", "Primary Genre", "Current Version Rating",
    "Current Version Rating Count", "Advisories", "Rating Count Change",
    "Avg Rating Change", "Days Since Release", "Days Since Update",
    "Days in Top 200",
]
SHEET_ORDER = list(GENRE_IDS.keys())


def _parse_date(value):
    """Return a date from an iTunes ISO timestamp or a baseline cell value."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def _category(result):
    """Category as in Liam's file: first 7000-series genre for Games,
    otherwise the primary genre."""
    genres = result.get("genres") or []
    genre_ids = result.get("genreIds") or []
    for name, gid in zip(genres, genre_ids):
        if str(gid).startswith("7"):
            return name
    return result.get("primaryGenreName")


def _row(rank, app_id, result, prev, chart_date, hydrated=None):
    """Build one 32-column row. prev is the previous day's row dict for
    this App ID in this sheet, or None. hydrated is the chart page's own
    title/developerName for ranks 1-25, used as a fallback name/developer
    when the Lookup returns nothing (as in Liam's file: News #17
    "Apps by SpaceXSI" / "X Corp.", Category "Unknown", rest blank)."""
    if result is None:
        hyd = (hydrated or {}).get(str(app_id), {})
        # 26 columns, in order: Rank, Prev Rank, Change, New, App ID, App,
        # Developer, Seller, Seller URL, Category, Genres, Age Rating,
        # Avg Rating, Rating Count, Price, Released, Updated, Version,
        # Size MB, Min iOS, Bundle ID, App Store link, Seller URL Note,
        # Primary Genre, Current Version Rating, Current Version Rating Count.
        row = [rank, None, None, None, int(app_id),
               hyd.get("title") or "(unavailable)",
               hyd.get("developerName"),
               None, None, "Unknown", None, None, None, None, None, None,
               None, None, None, None, None, "App Store", None, None, None, None]
    else:
        seller_url = result.get("sellerUrl")
        if seller_url:
            seller_note = "sellerUrl"
        else:
            seller_url = result.get("artistViewUrl")
            seller_note = "artistViewUrl (developer page)" if seller_url else None
        released = _parse_date(result.get("releaseDate"))
        updated = _parse_date(result.get("currentVersionReleaseDate"))
        row = [
            rank, None, None, None, int(app_id),
            result.get("trackName"),
            result.get("artistName"),
            result.get("sellerName"),
            seller_url,
            _category(result),
            ", ".join(result.get("genres") or []) or None,
            result.get("trackContentRating"),
            round(result["averageUserRating"], 5)
            if result.get("averageUserRating") is not None else None,
            result.get("userRatingCount"),
            result.get("formattedPrice"),
            datetime(released.year, released.month, released.day)
            if released else None,
            datetime(updated.year, updated.month, updated.day)
            if updated else None,
            result.get("version"),
            round(int(result["fileSizeBytes"]) / 1048576, 1)
            if result.get("fileSizeBytes") is not None else None,
            str(result.get("minimumOsVersion"))
            if result.get("minimumOsVersion") is not None else None,
            result.get("bundleId"),
            "App Store",
            seller_note,
            result.get("primaryGenreName"),
            round(result["averageUserRatingForCurrentVersion"], 5)
            if result.get("averageUserRatingForCurrentVersion") is not None else None,
            result.get("userRatingCountForCurrentVersion"),
        ]
    # Prev Rank / Change / New + derived fields (columns B-D, AA-AF).
    if prev is None:
        row[1] = None
        row[2] = None
        row[3] = "Yes"
        rating_count_change = None
        avg_rating_change = None
        days_in_top = 1
    else:
        row[1] = prev["rank"]
        row[2] = prev["rank"] - rank
        row[3] = None
        rc, ac = row[13], prev.get("rating_count")
        rating_count_change = (rc - ac) if (rc is not None and ac is not None) else None
        ar, pa = row[12], prev.get("avg_rating")
        avg_rating_change = round(ar - pa, 5) if (ar is not None and pa is not None) else None
        days_in_top = (prev.get("days_in_top") or 1) + 1
    advisories = result.get("advisories") if result else None
    released = _parse_date(row[15]) if row[15] is not None else None
    updated = _parse_date(row[16]) if row[16] is not None else None
    row += [
        "; ".join(advisories) if advisories else None,
        rating_count_change,
        avg_rating_change,
        (chart_date - released).days if released else None,
        (chart_date - updated).days if updated else None,
        days_in_top,
    ]
    return row, result.get("trackViewUrl") if result else \
        f"https://apps.apple.com/us/app/id{app_id}"


def _load_prev(path):
    """Previous day's file -> {sheet: {app_id: {rank, rating_count,
    avg_rating, days_in_top}}}, plus sheet order and column widths."""
    wb = openpyxl.load_workbook(path, data_only=True)
    prev = {}
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        headers = [c.value for c in ws[1]]
        idx = {h: i for i, h in enumerate(headers)}
        days_col = idx.get("Days in Top 200")
        per_sheet = {}
        for r in range(2, ws.max_row + 1):
            vals = [c.value for c in ws[r]]
            app_id = vals[idx["App ID"]]
            if app_id is None:
                continue
            per_sheet[int(app_id)] = {
                "rank": vals[idx["Rank"]],
                "rating_count": vals[idx["Rating Count"]],
                "avg_rating": vals[idx["Avg Rating"]],
                "days_in_top": vals[days_col] if days_col is not None else None,
            }
        prev[sheet] = per_sheet
    return prev, wb.sheetnames, wb


def _newest_prev(chart_date):
    hidden = os.path.join(GOAL_DIR, "hidden_files")
    candidates = []
    for name in os.listdir(hidden):
        if name.startswith("US_Free_Charts_") and name.endswith(".xlsx"):
            d = name[len("US_Free_Charts_"):-len(".xlsx")]
            try:
                parsed = datetime.strptime(d, "%Y-%m-%d").date()
            except ValueError:
                continue
            if parsed < chart_date:
                candidates.append((parsed, os.path.join(hidden, name)))
    if not candidates:
        return BASELINE
    return max(candidates)[1]


def build(chart_date, prev_path, out_path, ids_json=None, ids_out=None):
    prev, sheet_order, prev_wb = _load_prev(prev_path)
    hydrated_all = {}
    if ids_json:
        with open(ids_json) as f:
            all_ids = json.load(f)
    else:
        all_ids = {}
        for sheet in SHEET_ORDER:
            all_ids[sheet], hydrated_all[sheet] = get_top_free_chart(GENRE_IDS[sheet])
            time.sleep(0.2)
    if ids_out:
        with open(ids_out, "w") as f:
            json.dump(all_ids, f, indent=1)

    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    stats = {}
    for sheet in SHEET_ORDER:
        ids = all_ids[sheet]
        # Lookup in batches of 200 (one batch per sheet here).
        enriched = {}
        for i in range(0, len(ids), 200):
            for attempt in range(3):
                try:
                    enriched.update(lookup(ids[i:i + 200]))
                    break
                except Exception as exc:  # rate limit / transient
                    if attempt == 2:
                        raise
                    time.sleep(5 * (attempt + 1))
            time.sleep(0.5)
        ws = wb.create_sheet(sheet)
        ws.append(COLUMNS)
        ws.freeze_panes = "C2"
        # Copy column widths and header/data number formats from prev file.
        prev_ws = prev_wb[sheet] if sheet in prev_wb.sheetnames else None
        if prev_ws is not None:
            for col, dim in prev_ws.column_dimensions.items():
                ws.column_dimensions[col].width = dim.width
        new_count = 0
        climbers = []
        for rank, app_id in enumerate(ids, start=1):
            result = enriched.get(str(app_id))
            row, link = _row(rank, app_id, result, prev.get(sheet, {}).get(int(app_id)), chart_date,
                             hydrated_all.get(sheet))
            ws.append(row)
            ws.cell(row=rank + 1, column=22).hyperlink = Hyperlink(
                ref=f"V{rank + 1}", target=link, display="App Store")
            if prev_wb is not None and sheet in prev_wb.sheetnames:
                prev_ws = prev_wb[sheet]
                for col in range(1, 33):
                    cell = ws.cell(row=rank + 1, column=col)
                    if col <= 26:
                        fmt = prev_ws.cell(row=2, column=col).number_format
                        cell.number_format = fmt
                    elif col == 28:
                        cell.number_format = "#,##0"
                    elif col == 29:
                        cell.number_format = "0.00000"
                    elif col in (30, 31, 32):
                        cell.number_format = "0"
            if row[3] == "Yes":
                new_count += 1
            if row[2] is not None:
                climbers.append((row[2], row[5], rank))
        ws.auto_filter.ref = f"A1:AF{len(ids) + 1}"
        stats[sheet] = {
            "rows": len(ids),
            "new": new_count,
            "biggest_climb": max(climbers) if climbers else None,
            "biggest_fall": min(climbers) if climbers else None,
        }
        print(f"{sheet}: {len(ids)} rows, {new_count} new", flush=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    wb.save(out_path)
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None,
                        help="chart date YYYY-MM-DD (default: today, America/New_York)")
    parser.add_argument("--prev", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--ids-json", default=None)
    parser.add_argument("--ids-out", default=None)
    args = parser.parse_args()
    chart_date = (datetime.strptime(args.date, "%Y-%m-%d").date() if args.date
                  else datetime.now(ZoneInfo("America/New_York")).date())
    prev_path = args.prev or _newest_prev(chart_date)
    out_path = args.out or os.path.join(
        GOAL_DIR, "files", f"US_Free_Charts_{chart_date.isoformat()}.xlsx")
    print(f"chart date: {chart_date}  prev: {prev_path}  out: {out_path}")
    stats = build(chart_date, prev_path, out_path, args.ids_json, args.ids_out)
    total_new = sum(s["new"] for s in stats.values())
    print(f"done: {len(stats)} sheets, "
          f"{sum(s['rows'] for s in stats.values())} rows, {total_new} new entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
