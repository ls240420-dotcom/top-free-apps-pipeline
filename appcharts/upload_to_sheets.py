"""Upload the daily Top Free charts XLSX into a Google Sheets workbook.

Reads the XLSX (one sheet per chart category), converts datetimes to ISO
date strings and cell hyperlinks to =HYPERLINK() formulas, then writes each
tab with spreadsheets.values.update (USER_ENTERED) via hatch_gws_cli.

Usage: python3 upload_to_sheets.py <xlsx_path> <spreadsheet_id> [--skip Kids]
Only the category tabs are uploaded: the Top Free Apps / Top Free Games
tabs are skipped (Liam, Nov 14 — the Sheet is Master List, Enrichments,
then one tab per category). The daily XLSX still carries all 42 sheets;
the Master List is built from the XLSX files, not the Sheet tabs.
"""
import json
import subprocess
import sys
from datetime import datetime

import openpyxl

CLI = "/opt/hatch/bin/hatch_gws_cli"
SKIP = {"Kids", "Top Free Apps", "Top Free Games"}


def cell_value(cell):
    if cell.value is None:
        return ""
    if isinstance(cell.value, datetime):
        return cell.value.strftime("%Y-%m-%d")
    link = cell.hyperlink
    if link is not None and link.target:
        display = str(cell.value)
        target = link.target
        if display != target:
            return f'=HYPERLINK("{target}","{display}")'
        return target
    return cell.value


def upload_tab(spreadsheet_id, title, values):
    rng = f"'{title}'!A1:AF{len(values)}"
    params = json.dumps({
        "spreadsheetId": spreadsheet_id,
        "range": rng,
        "valueInputOption": "USER_ENTERED",
    })
    body = json.dumps({"values": values})
    cmd = [CLI, "sheets", "spreadsheets", "values", "update",
           "--params", params, "--json", body]
    for attempt in (1, 2):
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if p.returncode == 0:
            try:
                d = json.loads(p.stdout)
                return d.get("updatedRange", "?"), d.get("updatedCells", "?")
            except json.JSONDecodeError:
                return "?", "?"
        print(f"  attempt {attempt} failed for {title}: {p.stderr[:300]}",
              flush=True)
    raise RuntimeError(f"failed to upload tab {title}")


def main():
    xlsx_path, spreadsheet_id = sys.argv[1], sys.argv[2]
    skip = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else SKIP
    wb = openpyxl.load_workbook(xlsx_path, data_only=False)
    done = 0
    for title in wb.sheetnames:
        if title in skip:
            print(f"SKIP {title}", flush=True)
            continue
        ws = wb[title]
        values = [[cell_value(c) for c in row]
                  for row in ws.iter_rows(min_row=1, max_row=ws.max_row)]
        rng, cells = upload_tab(spreadsheet_id, title, values)
        done += 1
        print(f"{title}: {len(values)} rows -> {rng} ({cells} cells)",
              flush=True)
    print(f"done: {done} tabs uploaded", flush=True)


if __name__ == "__main__":
    main()
