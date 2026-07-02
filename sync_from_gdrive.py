#!/usr/bin/env python3
"""Sync payroll inputs from Google Drive into local (git-committed) files.

This is the ONLY script that reads from Google Drive. Everything else
(extract_timesheets_xlsx2tsvs.py, run_payroll.py) reads local files, so
payroll runs are reproducible and every input is diffable in git.

Sources (all native Google Sheets):
    master_employees   1 tab           -> inputs/master_employees.tsv
    contracts          1 tab           -> inputs/contracts.tsv
    attendance         1 tab/employee  -> inputs/timesheets/Attendance{YEAR}.xlsx
    leave_stocks       1 tab/month     -> inputs/leave_stocks/{YEAR}/leave_stocks_YYYY_MM_DD.tsv

Usage:
    python sync_from_gdrive.py --year 2026
    python sync_from_gdrive.py --year 2026 --only master_employees contracts

Then commit the pulled files and run payroll:
    git -C ../el add -A && git -C ../el commit -m "sync inputs $(date +%F)"
    python extract_timesheets_xlsx2tsvs.py --year 2026 --month 5
    python run_payroll.py --year 2026 --month 5
"""

import argparse
import csv
import io
import re
import sys
from pathlib import Path

import gspread
from gspread.utils import ExportFormat

from src.loaders import GSPREAD_CREDS, GSPREAD_TOKEN

INPUTS_DIR = Path("../el/payroll/inputs")
TIMESHEETS_DIR = INPUTS_DIR / "timesheets"
LEAVE_STOCKS_DIR = INPUTS_DIR / "leave_stocks"

# Google Sheet keys: the <key> in docs.google.com/spreadsheets/d/<key>/edit
MASTER_EMPLOYEES_KEY = "1w0tW_23qsBYvxYRIy9R5rJocxP9K58m4UJBeg3220u0"
CONTRACTS_KEY = "1PrZZCFZ_Iel1L-RvpQpZoHmF-XKGId9U_XtUTqn2SdY"
ATTENDANCE_KEY = "1o_0VbUErjHhSL6A3y2WRf4K9Cn56SwtkiHLjA5cESD8"
# leave_stocks is the spreadsheet run_payroll.py uploads to, opened by name.
LEAVE_STOCKS_NAME = "leave_stocks_{year}"

_TAB_DATE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})$")


def _client() -> gspread.Client:
    return gspread.oauth(
        credentials_filename=str(GSPREAD_CREDS),
        authorized_user_filename=str(GSPREAD_TOKEN),
    )


def _trim_to_header(values: list[list[str]]) -> list[list[str]]:
    """Drop trailing columns whose header cell is empty, then square rows."""
    if not values:
        return values
    header = values[0]
    width = 0
    for i, cell in enumerate(header):
        if str(cell).strip():
            width = i + 1
    return [row[:width] + [""] * (width - len(row)) for row in values]


def _write_tsv(dest: Path, values: list[list[str]]) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows = _trim_to_header(values)
    with open(dest, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter="\t").writerows(rows)
    return max(len(rows) - 1, 0)


def sync_single_tsv(gc, key: str, dest: Path, label: str) -> None:
    """Write the first tab of a spreadsheet to a TSV file."""
    ws = gc.open_by_key(key).sheet1
    n = _write_tsv(dest, ws.get_all_values())
    print(f"  {label}: {n} rows -> {dest}")


def sync_attendance(gc, key: str, year: int) -> None:
    """Export the whole attendance spreadsheet to Attendance{YEAR}.xlsx.

    Exporting (rather than reading cell strings) preserves real date cells,
    which extract_timesheets_xlsx2tsvs.py depends on.
    """
    data = gc.export(key, ExportFormat.EXCEL)
    dest = TIMESHEETS_DIR / f"Attendance{year}.xlsx"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    print(f"  attendance: {len(data):,} bytes -> {dest}")


def _feed_year(tab: str) -> int:
    """Payroll year a leave-stocks tab feeds (= month after its as-of date)."""
    y, m, _ = (int(x) for x in _TAB_DATE.match(tab).groups())
    return y + 1 if m == 12 else y


def sync_leave_stocks(gc, year: int) -> None:
    """Pull leave-stock tabs feeding the given payroll year into local TSVs.

    Tabs feeding January come from the prior year's spreadsheet, so both
    leave_stocks_{year-1} and leave_stocks_{year} are checked. Each YYYY_MM_DD
    tab is routed to leave_stocks/{feed_year}/leave_stocks_YYYY_MM_DD.tsv so
    it lands where find_leave_stocks_for_month expects it.
    """
    wrote = 0
    for src_year in (year - 1, year):
        name = LEAVE_STOCKS_NAME.format(year=src_year)
        try:
            sh = gc.open(name)
        except gspread.SpreadsheetNotFound:
            continue
        for ws in sh.worksheets():
            if not _TAB_DATE.match(ws.title):
                continue
            feed = _feed_year(ws.title)
            if feed != year:
                continue
            dest = LEAVE_STOCKS_DIR / str(feed) / f"leave_stocks_{ws.title}.tsv"
            n = _write_tsv(dest, ws.get_all_values())
            print(f"  leave_stocks[{ws.title}]: {n} rows -> {dest}")
            wrote += 1
    if not wrote:
        print(f"  leave_stocks: no tabs found feeding {year} "
              f"(looked in {LEAVE_STOCKS_NAME.format(year=year - 1)}, "
              f"{LEAVE_STOCKS_NAME.format(year=year)})")


SOURCES = ("master_employees", "contracts", "attendance", "leave_stocks")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--only", nargs="+", choices=SOURCES, metavar="SOURCE",
                        help=f"Sync only these sources (default: all). Choices: {', '.join(SOURCES)}")
    args = parser.parse_args()
    wanted = set(args.only) if args.only else set(SOURCES)

    gc = _client()
    print(f"Syncing {sorted(wanted)} for {args.year} from Google Drive")
    print()

    missing = []
    if "master_employees" in wanted:
        sync_single_tsv(gc, MASTER_EMPLOYEES_KEY, INPUTS_DIR / "master_employees.tsv", "master_employees")
    if "contracts" in wanted:
        if CONTRACTS_KEY:
            sync_single_tsv(gc, CONTRACTS_KEY, INPUTS_DIR / "contracts.tsv", "contracts")
        else:
            missing.append("contracts (set CONTRACTS_KEY)")
    if "attendance" in wanted:
        if ATTENDANCE_KEY:
            sync_attendance(gc, ATTENDANCE_KEY, args.year)
        else:
            missing.append("attendance (set ATTENDANCE_KEY)")
    if "leave_stocks" in wanted:
        sync_leave_stocks(gc, args.year)

    print()
    if missing:
        print("Skipped (no key configured):")
        for m in missing:
            print(f"  - {m}")
        return 1
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
