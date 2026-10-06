"""Pull payroll inputs from Google Drive/Sheets into a local directory.

Google Sheets is the single source of truth for payroll inputs.
run_payroll.py syncs into a throwaway temp dir, computes, uploads results,
and discards the dir. Re-running a past month re-reads the sheets as they
are *now*; the input snapshot archived with each run is the record of what
was actually used (see src/snapshot.py).

Every spreadsheet is read one tab per request through src.sheetcache, which
keeps tab values in the gitignored .cache/ until the sheet's Drive
modifiedTime moves. Small requests survive the office VPN's stalls, and a
run that dies part-way resumes from the tabs it already has.

Sources (all native Google Sheets):
    master_employees   1 tab           -> master_employees.tsv
    contracts          1 tab           -> contracts.tsv
    attendance         1 tab/employee  -> timesheets/Attendance{YEAR}.xlsx
    leave_stocks       1 tab/month     -> leave_stocks/{YEAR}/leave_stocks_YYYY_MM_DD.tsv

The layout under `dest` is what src.loaders expects, so the loaders stay
plain file readers and the test fixtures keep working unchanged.
"""

import csv
import re
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl

from .gauth import client
from .sheetcache import fetch_tabs

# Google Sheet keys: the <key> in docs.google.com/spreadsheets/d/<key>/edit
MASTER_EMPLOYEES_KEY = "1w0tW_23qsBYvxYRIy9R5rJocxP9K58m4UJBeg3220u0"
CONTRACTS_KEY = "1PrZZCFZ_Iel1L-RvpQpZoHmF-XKGId9U_XtUTqn2SdY"
ATTENDANCE_KEY = "1o_0VbUErjHhSL6A3y2WRf4K9Cn56SwtkiHLjA5cESD8"
# leave_stocks is the spreadsheet run_payroll.py uploads to, opened by name.
LEAVE_STOCKS_NAME = "leave_stocks_{year}"

SOURCES = ("master_employees", "contracts", "attendance", "leave_stocks")

_TAB_DATE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})$")


def attendance_xlsx_path(dest: Path, year: int) -> Path:
    """Where sync_attendance puts the attendance workbook."""
    return Path(dest) / "timesheets" / f"Attendance{year}.xlsx"


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


def sync_single_tsv(gc, key: str, dest: Path, label: str, log=print) -> None:
    """Write the first tab of a spreadsheet to a TSV file."""
    [(_, values)] = fetch_tabs(gc, key, label, want=lambda t: t["index"] == 0, log=log)
    n = _write_tsv(dest, values)
    log(f"  {label}: {n} rows -> {dest}")


# Sheets serial day 0. The 1900 leap-year bug sits before any payroll date.
_SERIAL_EPOCH = datetime(1899, 12, 30)

# The values API spells formula errors out ("#REF! (Reference does not
# exist.)"); an xlsx export carries just the code.
_FORMULA_ERROR = re.compile(r"^(#(?:REF!|N/A|DIV/0!|VALUE!|NAME\?|NUM!|NULL!|ERROR!)) \(.*\)$")


def _attendance_cell(value, row: int, col: int):
    """Map an UNFORMATTED_VALUE cell to what openpyxl reads from an export.

    Columns A and B hold dates, which arrive as serial numbers; extract_month
    tells data rows apart by column A being a datetime, so they must be
    converted back. Blanks arrive as "" but read from an xlsx as None.
    """
    if value == "":
        return None
    if isinstance(value, str) and (m := _FORMULA_ERROR.match(value)):
        return m[1]
    if row > 0 and col < 2 and isinstance(value, (int, float)) and not isinstance(value, bool):
        return _SERIAL_EPOCH + timedelta(days=value)
    return value


def sync_attendance(gc, key: str, dest: Path, year: int, log=print) -> None:
    """Rebuild the attendance spreadsheet as Attendance{YEAR}.xlsx, tab by tab.

    This used to be a single xlsx export of the whole workbook (~2.5 MB),
    which the office VPN would stall part-way through. The rebuilt workbook
    holds the same cell values, so extract_month and the archived input
    snapshots are unchanged.
    """
    tabs = fetch_tabs(gc, key, "attendance", render="UNFORMATTED_VALUE", log=log)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for title, values in tabs:
        ws = wb.create_sheet(title)
        for r, row in enumerate(values):
            ws.append([_attendance_cell(v, r, c) for c, v in enumerate(row)])
    out = attendance_xlsx_path(dest, year)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    log(f"  attendance: {len(tabs)} tabs -> {out}")


def _feed_year(tab: str) -> int:
    """Payroll year a leave-stocks tab feeds (= month after its as-of date)."""
    y, m, _ = (int(x) for x in _TAB_DATE.match(tab).groups())
    return y + 1 if m == 12 else y


def sync_leave_stocks(gc, dest: Path, year: int, log=print) -> None:
    """Pull leave-stock tabs feeding the given payroll year into local TSVs.

    Tabs feeding January come from the prior year's spreadsheet, so both
    leave_stocks_{year-1} and leave_stocks_{year} are checked. Each YYYY_MM_DD
    tab is routed to leave_stocks/{feed_year}/leave_stocks_YYYY_MM_DD.tsv so
    it lands where find_leave_stocks_for_month expects it.
    """
    wrote = 0
    for src_year in (year - 1, year):
        name = LEAVE_STOCKS_NAME.format(year=src_year)
        files = gc.list_spreadsheet_files(title=name)
        if not files:
            continue
        wanted = lambda t: bool(_TAB_DATE.match(t["title"])) and _feed_year(t["title"]) == year
        for title, values in fetch_tabs(gc, files[0]["id"], name, want=wanted,
                                        modified=files[0]["modifiedTime"], log=log):
            out = Path(dest) / "leave_stocks" / str(year) / f"leave_stocks_{title}.tsv"
            n = _write_tsv(out, values)
            log(f"  leave_stocks[{title}]: {n} rows -> {out}")
            wrote += 1
    if not wrote:
        log(f"  leave_stocks: no tabs found feeding {year} "
            f"(looked in {LEAVE_STOCKS_NAME.format(year=year - 1)}, "
            f"{LEAVE_STOCKS_NAME.format(year=year)})")


def sync_inputs(dest: str | Path, year: int, only=None, log=print) -> list[str]:
    """Sync payroll inputs for `year` into `dest`.

    `only` restricts to a subset of SOURCES. Returns the list of sources
    skipped because no spreadsheet key is configured.
    """
    dest = Path(dest)
    wanted = set(only) if only else set(SOURCES)
    gc = client()

    missing = []
    if "master_employees" in wanted:
        sync_single_tsv(gc, MASTER_EMPLOYEES_KEY, dest / "master_employees.tsv",
                        "master_employees", log)
    if "contracts" in wanted:
        if CONTRACTS_KEY:
            sync_single_tsv(gc, CONTRACTS_KEY, dest / "contracts.tsv", "contracts", log)
        else:
            missing.append("contracts (set CONTRACTS_KEY)")
    if "attendance" in wanted:
        if ATTENDANCE_KEY:
            sync_attendance(gc, ATTENDANCE_KEY, dest, year, log)
        else:
            missing.append("attendance (set ATTENDANCE_KEY)")
    if "leave_stocks" in wanted:
        sync_leave_stocks(gc, dest, year, log)

    return missing
