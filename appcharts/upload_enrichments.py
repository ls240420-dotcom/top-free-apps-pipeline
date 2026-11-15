#!/usr/bin/env python3
"""Upload the enriched top-100 CSV as the "Enrichments" tab of the daily
charts Google Sheet. Creates the tab if missing, expands the grid, and
uploads in 50-row chunks (Linux caps a single CLI argument at 128KB).

Usage: upload_enrichments.py <enriched.csv> [--spreadsheet-id ID]
"""
import argparse
import csv
import json
import os
import subprocess
import sys

import openpyxl

DEFAULT_SPREADSHEET_ID = "1-oP-mUqIcGBz6riqd_fdrD9nwI54tveHpkfzWZk4B84"
CLI = "/opt/hatch/bin/hatch_gws_cli"
TAB = "Enrichments"


def _run_cli(args):
    p = subprocess.run([CLI] + args, capture_output=True, text=True, timeout=180)
    if p.returncode != 0:
        raise RuntimeError(f"{CLI} {' '.join(args[:3])} failed: {p.stderr[:300]}")
    return json.loads(p.stdout) if p.stdout.strip() else {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path")
    parser.add_argument("--spreadsheet-id", default=DEFAULT_SPREADSHEET_ID)
    args = parser.parse_args()
    with open(args.csv_path, newline="") as f:
        values = [list(r.values()) for r in csv.DictReader(f)]
    header = list(csv.DictReader(open(args.csv_path)).fieldnames)
    values.insert(0, header)
    ncols = openpyxl.utils.get_column_letter(len(header))
    meta = _run_cli(["sheets", "spreadsheets", "get", "--params", json.dumps(
        {"spreadsheetId": args.spreadsheet_id,
         "fields": "sheets(properties(title,sheetId,index))"})])
    tabs = {s["properties"]["title"]: s["properties"]
            for s in meta.get("sheets", [])}
    if TAB not in tabs:
        _run_cli(["sheets", "spreadsheets", "batchUpdate", "--params",
                  json.dumps({"spreadsheetId": args.spreadsheet_id}), "--json",
                  json.dumps({"requests": [{"addSheet": {"properties": {
                      "title": TAB, "index": 1,
                      "gridProperties": {"rowCount": 2000, "columnCount": 30}}}}]})])
        meta = _run_cli(["sheets", "spreadsheets", "get", "--params",
                         json.dumps({"spreadsheetId": args.spreadsheet_id,
                                     "fields": "sheets(properties(title,sheetId))"})])
        tabs = {s["properties"]["title"]: s["properties"]
                for s in meta.get("sheets", [])}
    sheet_id = tabs[TAB]["sheetId"]
    _run_cli(["sheets", "spreadsheets", "batchUpdate", "--params",
              json.dumps({"spreadsheetId": args.spreadsheet_id}), "--json",
              json.dumps({"requests": [{"updateSheetProperties": {
                  "properties": {"sheetId": sheet_id, "gridProperties": {
                      "rowCount": max(2000, len(values) + 100),
                      "columnCount": max(30, len(header) + 1)}},
                  "fields": "gridProperties.rowCount,gridProperties.columnCount"}}]})])
    # Clear the whole tab first: values.update only overwrites the new
    # width, so a narrower CSV would leave stale columns behind.
    _run_cli(["sheets", "spreadsheets", "values", "clear", "--params",
              json.dumps({"spreadsheetId": args.spreadsheet_id,
                          "range": f"'{TAB}'!A1:ZZ2000"})])
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
        rng = f"'{TAB}'!A{start + 1}:{ncols}{start + len(chunk)}"
        out = _run_cli(["sheets", "spreadsheets", "values", "update", "--params",
                        json.dumps({"spreadsheetId": args.spreadsheet_id, "range": rng,
                                    "valueInputOption": "USER_ENTERED"}),
                        "--json", json.dumps({"values": chunk})])
        total_cells += out.get("updatedCells", 0)
        start += len(chunk)
    print(f"{TAB}: {len(values)} rows ({total_cells} cells)", flush=True)
    _run_cli(["sheets", "spreadsheets", "batchUpdate", "--params",
              json.dumps({"spreadsheetId": args.spreadsheet_id}), "--json",
              json.dumps({"requests": [
                  {"updateSheetProperties": {
                      "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                      "fields": "gridProperties.frozenRowCount"}},
                  {"repeatCell": {
                      "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1},
                      "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                      "fields": "userEnteredFormat.textFormat.bold"}},
              ]})])
    return 0


if __name__ == "__main__":
    sys.exit(main())
