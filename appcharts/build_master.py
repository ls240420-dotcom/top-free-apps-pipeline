#!/usr/bin/env python3
"""Build the historical Master List of all Top Free apps and upload it as the
first tab ("Master List") of the daily charts Google Sheet.

Sources: every US_Free_Charts_YYYY-MM-DD.xlsx in the goal's hidden_files/
(the Nov 12 baseline + each daily file). The Kids sheet is excluded from
the master, per Liam (Kids was dropped from the digest Nov 12 evening).

One row per App ID. Columns:
  App ID, App, Type (Apps or Games), Developer, Seller, Category, Genres,
  Age Rating, Bundle ID,
  First Seen, Last Seen, Days in Top 200, Days in Top 10, Days in Top 50,
  Status (Active / Returned / Dropped), Best Rank, Best Rank Date,
  Debut Rank, Current Rank, Rank 7d Ago, Rank 30d Ago, 7d Change,
  30d Change, Sheets (Last Seen),
  Rank YYYY-MM-DD ... (best rank that day, last 14 dates in the archive)

- Type is "Games" when the app's Primary Genre is "Games", else "Apps"
  (falling back to whether it ever charted in a Games sheet).

- "Days in Top 200" counts distinct dates the app appeared in any sheet.
- Best Rank / Debut Rank / Current Rank are the app's best rank across
  sheets that day (an app can chart in several categories at once).
- Rank 7d/30d Ago use the file exactly 7 / 30 days before the latest date;
  blank when no file exists for that date. Changes are positive = climbed.
- Status: Active if in the latest file; Returned if active now but missing
  on some date after first seen; Dropped if not in the latest file.
- Identity fields come from the latest date the app appears, falling back
  to earlier dates for blank or "(unavailable)" values.

Usage:
  python3 build_master.py [--date YYYY-MM-DD] [--out PATH]
                          [--spreadsheet-id ID] [--no-upload]
- --date: latest chart date to include (default: newest file date).
- --out: local XLSX snapshot (default: hidden_files/master-list-<date>.xlsx).
- --spreadsheet-id: Google Sheet to upload the Master List tab to
  (default: the daily charts sheet). --no-upload skips the upload.
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import openpyxl
from openpyxl.styles import Font

GOAL_DIR = os.path.expanduser(
    "~/workspace/goals/daily-top-free-apps-digest")
HIDDEN = os.path.join(GOAL_DIR, "hidden_files")
DEFAULT_SPREADSHEET_ID = "1-oP-mUqIcGBz6riqd_fdrD9nwI54tveHpkfzWZk4B84"
CLI = "/opt/hatch/bin/hatch_gws_cli"
SKIP_SHEETS = {"Kids"}
HISTORY_DAYS = 14

BASE_COLUMNS = [
    "App ID", "App", "Type", "Developer", "Seller", "Category", "Genres",
    "Age Rating", "Bundle ID", "First Seen", "Last Seen",
    "Days in Top 200", "Days in Top 10", "Days in Top 50", "Status",
    "Best Rank", "Best Rank Date", "Debut Rank", "Current Rank",
    "Rank 7d Ago", "Rank 30d Ago", "7d Change", "30d Change",
    "Sheets (Last Seen)",
]
# AppGoblin enrichment columns, merged by App ID from
# appgoblin-enrichment.json (built by merge_enrichment.py from the
# *-raw.json files appgoblin_enrich.py writes). Blank when an app has
# not been enriched yet. All figures are AppGoblin modelled estimates.
ENRICH_COLUMNS = [
    "Avg Rating", "Rating Count", "Rating Count Weekly (est)",
    "Installs (est)", "Installs Weekly (est)", "Installs Monthly (est)",
    "WAU (est)", "MAU (est)", "Monthly Ad Revenue (est)",
    "Monthly IAP Revenue (est)", "Attribution SDKs", "Ad Network SDKs",
    "SDK Vendors (n)", "SKAdNetwork (n)", "SKAdNetwork Companies (n)",
    "SKAdNetwork Unresolved (n)", "SKAdNetwork Companies", "Enriched Date",
]
ENRICH_STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "appgoblin-enrichment.json")


def _load_enrichment():
    if not os.path.exists(ENRICH_STORE):
        return {}
    with open(ENRICH_STORE) as f:
        return json.load(f)
IDENTITY_FIELDS = ["App", "Developer", "Seller", "Category", "Genres",
                   "Age Rating", "Bundle ID"]


def _parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()


def _daily_files(upto):
    files = []
    for name in os.listdir(HIDDEN):
        if not (name.startswith("US_Free_Charts_") and name.endswith(".xlsx")):
            continue
        try:
            d = datetime.strptime(
                name[len("US_Free_Charts_"):-len(".xlsx")], "%Y-%m-%d").date()
        except ValueError:
            continue
        if d <= upto:
            files.append((d, os.path.join(HIDDEN, name)))
    return sorted(files)


def _collect(files):
    """Return {app_id: {dates, best_by_date, sheets_by_date, rows_by_date}}."""
    apps = {}
    for d, path in files:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        for sheet in wb.sheetnames:
            if sheet in SKIP_SHEETS:
                continue
            ws = wb[sheet]
            rows = ws.iter_rows(values_only=True)
            headers = [c for c in next(rows)]
            idx = {h: i for i, h in enumerate(headers)}
            for vals in rows:
                # read_only rows can be shorter than the header when
                # trailing cells are empty — pad before indexing.
                if len(vals) < len(headers):
                    vals = vals + (None,) * (len(headers) - len(vals))
                app_id = vals[idx["App ID"]]
                rank = vals[idx["Rank"]]
                if app_id is None or rank is None:
                    continue
                app_id = int(app_id)
                rec = apps.setdefault(app_id, {
                    "dates": set(),
                    "best_by_date": {},
                    "sheets_by_date": {},
                    "rows_by_date": {},
                })
                rec["dates"].add(d)
                rec["sheets_by_date"].setdefault(d, set()).add(sheet)
                if d not in rec["best_by_date"] or rank < rec["best_by_date"][d]:
                    rec["best_by_date"][d] = rank
                    rec["rows_by_date"][d] = {h: vals[idx[h]] for h in idx}
        wb.close()
    return apps


def _identity(rec, field):
    """Latest non-blank value for an identity field, skipping '(unavailable)'."""
    for d in sorted(rec["rows_by_date"], reverse=True):
        v = rec["rows_by_date"][d].get(field)
        if v is None or v == "" or v == "(unavailable)":
            continue
        return v
    return None


def build_rows(apps, latest, dates, enrichment=None):
    enrichment = enrichment or {}
    hist_dates = dates[-HISTORY_DAYS:]
    rows = []
    for app_id, rec in apps.items():
        seen = sorted(rec["dates"])
        first, last = seen[0], seen[-1]
        best_by_date = rec["best_by_date"]
        best_rank = min(best_by_date.values())
        best_date = min(d for d, r in best_by_date.items() if r == best_rank)
        current = best_by_date.get(latest)
        if current is None:
            status = "Dropped"
        elif len(seen) != (latest - first).days + 1:
            status = "Returned"
        else:
            status = "Active"
        rank_7d = best_by_date.get(latest - timedelta(days=7))
        rank_30d = best_by_date.get(latest - timedelta(days=30))
        sheets_last = ", ".join(sorted(rec["sheets_by_date"][last]))
        primary = _identity(rec, "Primary Genre")
        if primary == "Games":
            app_type = "Games"
        elif primary is not None:
            app_type = "Apps"
        else:
            in_games = any(
                s == "Top Free Games" or s.startswith("Games - ")
                for sheets in rec["sheets_by_date"].values() for s in sheets)
            app_type = "Games" if in_games else "Apps"
        row = [
            app_id,
            _identity(rec, "App"),
            app_type,
            _identity(rec, "Developer"),
            _identity(rec, "Seller"),
            _identity(rec, "Category"),
            _identity(rec, "Genres"),
            _identity(rec, "Age Rating"),
            _identity(rec, "Bundle ID"),
            first.isoformat(),
            last.isoformat(),
            len(seen),
            sum(1 for r in best_by_date.values() if r <= 10),
            sum(1 for r in best_by_date.values() if r <= 50),
            status,
            best_rank,
            best_date.isoformat(),
            best_by_date[first],
            current,
            rank_7d,
            rank_30d,
            (rank_7d - current) if (rank_7d is not None and current is not None) else None,
            (rank_30d - current) if (rank_30d is not None and current is not None) else None,
            sheets_last,
        ]
        enr = enrichment.get(str(app_id), {})
        row += [
            _identity(rec, "Avg Rating"),
            _identity(rec, "Rating Count"),
            enr.get("rating_count_weekly"),
            enr.get("installs"),
            enr.get("installs_weekly"),
            enr.get("installs_monthly"),
            enr.get("wau"),
            enr.get("mau"),
            enr.get("monthly_ad_revenue"),
            enr.get("monthly_iap_revenue"),
            "; ".join(enr.get("attribution_sdks", [])) or None,
            "; ".join(enr.get("ad_network_sdks", [])) or None,
            enr.get("sdk_vendors_n"),
            enr.get("skan_ids_n"),
            enr.get("skan_companies_n"),
            enr.get("skan_unresolved_n"),
            "; ".join(enr.get("skan_companies", [])) or None,
            enr.get("enriched_date"),
        ]
        row += [best_by_date.get(d) for d in hist_dates]
        rows.append(row)
    # Active first by current rank, then Dropped/Returned by last seen.
    def sort_key(r):
        status_order = {"Active": 0, "Returned": 1, "Dropped": 2}
        rank = r[18] if r[18] is not None else 9999
        return (status_order[r[14]], rank, r[10])
    rows.sort(key=sort_key)
    columns = BASE_COLUMNS + ENRICH_COLUMNS + [f"Rank {d.isoformat()}" for d in hist_dates]
    return columns, rows


def save_xlsx(columns, rows, out_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Master List"
    ws.append(columns)
    for row in rows:
        ws.append(row)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{openpyxl.utils.get_column_letter(len(columns))}{len(rows) + 1}"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    wb.save(out_path)
    return out_path


def _run_cli(args):
    p = subprocess.run([CLI] + args, capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"{CLI} {' '.join(args[:3])} failed: {p.stderr[:300]}")
    return json.loads(p.stdout) if p.stdout.strip() else {}


def upload_to_sheets(spreadsheet_id, columns, rows):
    values = [columns] + [[("" if v is None else v) for v in row] for row in rows]
    ncols = openpyxl.utils.get_column_letter(len(columns))
    # Ensure the tab exists, first in the workbook.
    meta = _run_cli(["sheets", "spreadsheets", "get", "--params", json.dumps(
        {"spreadsheetId": spreadsheet_id,
         "fields": "sheets(properties(title,sheetId,index))"})])
    tabs = {s["properties"]["title"]: s["properties"]
            for s in meta.get("sheets", [])}
    if "Master List" not in tabs:
        add_body = {"requests": [{"addSheet": {"properties": {
            "title": "Master List", "index": 0,
            "gridProperties": {"rowCount": 20000, "columnCount": 30}}}}]}
        _run_cli(["sheets", "spreadsheets", "batchUpdate", "--params",
                  json.dumps({"spreadsheetId": spreadsheet_id}), "--json",
                  json.dumps(add_body)])
        meta = _run_cli(["sheets", "spreadsheets", "get", "--params",
                         json.dumps({"spreadsheetId": spreadsheet_id,
                                     "fields": "sheets(properties(title,sheetId))"})])
        tabs = {s["properties"]["title"]: s["properties"]
                for s in meta.get("sheets", [])}
    sheet_id = tabs["Master List"]["sheetId"]
    # A fresh tab defaults to 1000 rows x 26 cols; the master already has
    # 7,400+ rows, so expand the grid before writing.
    _run_cli(["sheets", "spreadsheets", "batchUpdate", "--params",
              json.dumps({"spreadsheetId": spreadsheet_id}), "--json",
              json.dumps({"requests": [{"updateSheetProperties": {
                  "properties": {"sheetId": sheet_id, "gridProperties": {
                      "rowCount": max(20000, len(values) + 1000),
                      "columnCount": max(30, len(columns) + 1)}},
                  "fields": "gridProperties.rowCount,gridProperties.columnCount"}}]})])
    # Clear the whole tab first: values.update only overwrites the new
    # width, so a narrower table would leave stale columns behind.
    _run_cli(["sheets", "spreadsheets", "values", "clear", "--params",
              json.dumps({"spreadsheetId": spreadsheet_id,
                          "range": "'Master List'!A1:ZZ25000"})])
    # Upload in chunks: Linux caps a single argv string at 128KB
    # (MAX_ARG_STRLEN). Rows vary wildly in size now (enriched rows carry
    # long SKAN company lists), so chunk by payload bytes, not row count:
    # keep each values.update call under ~90KB of JSON.
    MAX_BYTES = 90 * 1024
    total_cells = 0
    start = 0
    while start < len(values):
        chunk, size = [], 0
        while start + len(chunk) < len(values):
            row_json = json.dumps(values[start + len(chunk)])
            if chunk and size + len(row_json) > MAX_BYTES:
                break
            chunk.append(values[start + len(chunk)])
            size += len(row_json)
        first_row = start + 1
        last_row = start + len(chunk)
        rng = f"'Master List'!A{first_row}:{ncols}{last_row}"
        out = _run_cli(["sheets", "spreadsheets", "values", "update", "--params",
                        json.dumps({"spreadsheetId": spreadsheet_id, "range": rng,
                                    "valueInputOption": "USER_ENTERED"}),
                        "--json", json.dumps({"values": chunk})])
        total_cells += out.get("updatedCells", 0)
        start += len(chunk)
    print(f"Master List: {len(values)} rows ({total_cells} cells)", flush=True)
    # Pin explicit number formats on the numeric/date columns. Without this,
    # a stray DATE format can stick to a rank column (Nov 14: Best Rank
    # rendered 1 as 1899-12-31) because values.update preserves existing
    # cell formats. Apply after every upload so the tab self-heals.
    _apply_number_formats(spreadsheet_id, sheet_id, columns)
    _run_cli(["sheets", "spreadsheets", "batchUpdate", "--params",
              json.dumps({"spreadsheetId": spreadsheet_id}), "--json",
              json.dumps({"requests": [
                  {"updateSheetProperties": {
                      "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                      "fields": "gridProperties.frozenRowCount"}},
                  {"repeatCell": {
                      "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                      "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                      "fields": "userEnteredFormat.textFormat.bold"}},
              ]})])
    return len(rows)


def _apply_number_formats(spreadsheet_id, sheet_id, columns):
    """Set explicit number formats per column, by header name."""
    num0 = {"App ID", "Days in Top 200", "Days in Top 10", "Days in Top 50",
            "Best Rank", "Debut Rank", "Current Rank", "Rank 7d Ago",
            "Rank 30d Ago", "7d Change", "30d Change", "Rating Count",
            "Rating Count Weekly (est)", "Installs (est)",
            "Installs Weekly (est)", "Installs Monthly (est)", "WAU (est)",
            "MAU (est)", "Monthly Ad Revenue (est)", "Monthly IAP Revenue (est)",
            "SDK Vendors (n)", "SKAdNetwork (n)", "SKAdNetwork Companies (n)",
            "SKAdNetwork Unresolved (n)"}
    num2 = {"Avg Rating"}
    dates = {"First Seen", "Last Seen", "Best Rank Date", "Enriched Date"}
    requests = []
    for i, col in enumerate(columns):
        if col in num0 or col.startswith("Rank "):
            fmt = {"type": "NUMBER", "pattern": "0"}
        elif col in num2:
            fmt = {"type": "NUMBER", "pattern": "0.00"}
        elif col in dates:
            fmt = {"type": "DATE", "pattern": "yyyy-mm-dd"}
        else:
            continue
        requests.append({"repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0,
                      "endRowIndex": 20000, "startColumnIndex": i,
                      "endColumnIndex": i + 1},
            "cell": {"userEnteredFormat": {"numberFormat": fmt}},
            "fields": "userEnteredFormat.numberFormat"}})
    if requests:
        _run_cli(["sheets", "spreadsheets", "batchUpdate", "--params",
                  json.dumps({"spreadsheetId": spreadsheet_id}), "--json",
                  json.dumps({"requests": requests})])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--spreadsheet-id", default=DEFAULT_SPREADSHEET_ID)
    parser.add_argument("--no-upload", action="store_true")
    args = parser.parse_args()
    latest = (datetime.strptime(args.date, "%Y-%m-%d").date() if args.date
              else datetime.now(ZoneInfo("America/New_York")).date())
    files = _daily_files(latest)
    if not files:
        raise SystemExit("no daily files found")
    latest = files[-1][0]
    dates = [d for d, _ in files]
    print(f"files: {len(files)} ({dates[0]}..{dates[-1]})", flush=True)
    apps = _collect(files)
    enrichment = _load_enrichment()
    columns, rows = build_rows(apps, latest, dates, enrichment)
    out_path = args.out or os.path.join(HIDDEN, f"master-list-{latest.isoformat()}.xlsx")
    save_xlsx(columns, rows, out_path)
    active = sum(1 for r in rows if r[14] == "Active")
    enriched = sum(1 for r in rows if r[41] is not None)
    print(f"done: {len(rows)} apps ({active} active, {enriched} enriched), {len(columns)} columns -> {out_path}", flush=True)
    if not args.no_upload:
        upload_to_sheets(args.spreadsheet_id, columns, rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
