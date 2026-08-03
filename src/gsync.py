"""Pull payroll inputs from Google Drive/Sheets into a local directory.

Google Sheets is the single source of truth for payroll inputs. Nothing is
kept on disk between runs: run_payroll.py syncs into a throwaway temp dir,
computes, uploads results, and discards the dir. That keeps private employee
data out of the working tree entirely, at the cost of reproducibility --
re-running a past month re-reads the sheets as they are *now*, not as they
were then. The archived outputs on Drive are the record of what was actually
paid.

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
from pathlib import Path

import gspread
from gspread.utils import ExportFormat

from .loaders import GSPREAD_CREDS, GSPREAD_TOKEN

# Google Sheet keys: the <key> in docs.google.com/spreadsheets/d/<key>/edit
MASTER_EMPLOYEES_KEY = "1w0tW_23qsBYvxYRIy9R5rJocxP9K58m4UJBeg3220u0"
CONTRACTS_KEY = "1PrZZCFZ_Iel1L-RvpQpZoHmF-XKGId9U_XtUTqn2SdY"
ATTENDANCE_KEY = "1o_0VbUErjHhSL6A3y2WRf4K9Cn56SwtkiHLjA5cESD8"
# leave_stocks is the spreadsheet run_payroll.py uploads to, opened by name.
LEAVE_STOCKS_NAME = "leave_stocks_{year}"

SOURCES = ("master_employees", "contracts", "attendance", "leave_stocks")

_TAB_DATE = re.compile(r"^(\d{4})_(\d{2})_(\d{2})$")


def client() -> gspread.Client:
    """Authorized gspread client using the shared OAuth token."""
    return gspread.oauth(
        credentials_filename=str(GSPREAD_CREDS),
        authorized_user_filename=str(GSPREAD_TOKEN),
    )


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
    ws = gc.open_by_key(key).sheet1
    n = _write_tsv(dest, ws.get_all_values())
    log(f"  {label}: {n} rows -> {dest}")


def sync_attendance(gc, key: str, dest: Path, year: int, log=print) -> None:
    """Export the whole attendance spreadsheet to Attendance{YEAR}.xlsx.

    Exporting (rather than reading cell strings) preserves real date cells,
    which extract_timesheets_xlsx2tsvs.extract_month depends on.
    """
    data = gc.export(key, ExportFormat.EXCEL)
    out = attendance_xlsx_path(dest, year)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    log(f"  attendance: {len(data):,} bytes -> {out}")


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
        try:
            sh = gc.open(name)
        except gspread.SpreadsheetNotFound:
            continue
        for ws in sh.worksheets():
            if not _TAB_DATE.match(ws.title):
                continue
            if _feed_year(ws.title) != year:
                continue
            out = Path(dest) / "leave_stocks" / str(year) / f"leave_stocks_{ws.title}.tsv"
            n = _write_tsv(out, ws.get_all_values())
            log(f"  leave_stocks[{ws.title}]: {n} rows -> {out}")
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
