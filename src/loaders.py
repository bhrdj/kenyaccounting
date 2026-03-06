import csv
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .models import Contract, Employee, LeaveStock, TimesheetDay


def load_employees(path: str | Path) -> list[Employee]:
    """Load employees from a TSV file.

    Handles both test fixtures (minimal columns) and real data
    (extra columns like nssf_no, shif_no, notes).
    Skips rows where employee_id or national_id is '???' or missing.
    """
    employees = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            emp_id_raw = row.get("employee_id", "").strip()
            national_id = row.get("national_id", "").strip()

            # Skip rows with missing employee_id
            if not emp_id_raw or emp_id_raw == "???":
                continue

            employees.append(
                Employee(
                    employee_id=int(emp_id_raw),
                    name=row.get("name", "").strip(),
                    national_id=national_id,
                    kra_pin=row.get("kra_pin", "").strip(),
                    phone=row.get("phone", "").strip(),
                    bank_account=row.get("bank_account", "").strip(),
                    nssf_no=row.get("nssf_no", "").strip(),
                    shif_no=row.get("shif_no", "").strip(),
                )
            )
    return employees


def load_contracts(path: str | Path, active_only: bool = True) -> list[Contract]:
    """Load contracts from a TSV file.

    Handles both test fixtures and real data. When current_base_salary is
    present and non-empty, it is used as the effective base_salary (the
    contractual base_salary column is historical).

    Skips rows where contract_type is '???' or status is not 'active'
    (when active_only=True). Skips duplicate rows (status='duplicate').
    """
    contracts = []
    seen_ids = set()
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            emp_id_raw = row.get("employee_id", "").strip()
            if not emp_id_raw or emp_id_raw == "???":
                continue

            emp_id = int(emp_id_raw)

            # Skip duplicates
            status = row.get("status", "").strip().lower()
            if status == "duplicate":
                continue

            # Filter to active only if requested
            if active_only and status != "active":
                continue

            # Skip rows with unknown contract type
            contract_type = row.get("contract_type", "").strip()
            if not contract_type or contract_type == "???":
                # If we have a current_base_salary, treat as hourly (best guess for
                # employees with no contract on file but known pay)
                current_base = row.get("current_base_salary", "").strip()
                if current_base and current_base != "???":
                    contract_type = "hourly"
                else:
                    continue

            # Skip duplicate employee IDs (keep first seen)
            if emp_id in seen_ids:
                continue
            seen_ids.add(emp_id)

            # Determine effective salary: use current_base_salary if available
            base_salary_raw = row.get("base_salary", "").strip()
            current_base_raw = row.get("current_base_salary", "").strip()

            if current_base_raw and current_base_raw != "???":
                effective_salary = Decimal(current_base_raw)
            elif base_salary_raw and base_salary_raw != "???":
                effective_salary = Decimal(base_salary_raw)
            else:
                continue  # No salary info at all

            # Parse weekly_hours
            wh_raw = row.get("weekly_hours", "").strip()
            weekly_hours = int(wh_raw) if wh_raw and wh_raw != "???" else None

            # Parse housing
            hmv_raw = row.get("housing_market_value", "").strip()
            housing_market_value = Decimal(hmv_raw) if hmv_raw and hmv_raw != "???" else None

            # Parse dates
            start_raw = row.get("start_date", "").strip()
            end_raw = row.get("end_date", "").strip()
            start_date = _parse_date(start_raw) if start_raw and start_raw != "???" else date(2025, 1, 1)
            end_date = _parse_date(end_raw) if end_raw and end_raw != "???" else None

            # Parse optional fields with defaults
            nssf_tier = row.get("nssf_tier", "standard").strip()
            if not nssf_tier or nssf_tier == "???":
                nssf_tier = "standard"

            housing_type = row.get("housing_type", "none").strip()
            if not housing_type or housing_type == "???":
                housing_type = "none"

            salary_basis = row.get("salary_basis", "gross").strip()
            if not salary_basis or salary_basis == "???":
                salary_basis = "gross"

            hourly_divisor = row.get("hourly_divisor", "monthly").strip()
            if not hourly_divisor or hourly_divisor == "???":
                hourly_divisor = "monthly"

            contracts.append(
                Contract(
                    employee_id=emp_id,
                    contract_type=contract_type,
                    base_salary=effective_salary,
                    weekly_hours=weekly_hours,
                    housing_type=housing_type,
                    housing_market_value=housing_market_value,
                    nssf_tier=nssf_tier,
                    start_date=start_date,
                    end_date=end_date,
                    status=status,
                    salary_basis=salary_basis,
                    hourly_divisor=hourly_divisor,
                )
            )
    return contracts


def load_leave_stocks(path: str | Path) -> list[LeaveStock]:
    """Load leave stock balances from a TSV file.

    Handles extra columns (name, notes), negative balances, fractional
    decimals, and blank values (treated as 0).
    """
    stocks = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            emp_id_raw = row.get("employee_id", "").strip()
            if not emp_id_raw or emp_id_raw == "???":
                continue

            stocks.append(
                LeaveStock(
                    employee_id=int(emp_id_raw),
                    sick_full_pay=_parse_decimal(row.get("sick_full_pay", "0")),
                    sick_half_pay=_parse_decimal(row.get("sick_half_pay", "0")),
                    annual_leave=_parse_decimal(row.get("annual_leave", "0")),
                    as_of_date=_parse_date(row.get("as_of_date", "2025-12-31")),
                )
            )
    return stocks


def load_timesheet(path: str | Path) -> list[TimesheetDay]:
    """Load timesheet entries from a TSV file (old flat format with employee_id column)."""
    entries = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            entries.append(
                TimesheetDay(
                    employee_id=int(row["employee_id"]),
                    date=_parse_date(row["date"]),
                    hours_normal=Decimal(row["hours_normal"]),
                    hours_ot_1_5=Decimal(row["hours_ot_1_5"]),
                    hours_ot_2_0=Decimal(row["hours_ot_2_0"]),
                    absent=row["absent"] == "1",
                    sick=row["sick"] == "1",
                )
            )
    return entries


def load_timesheet_folder(
    folder: str | Path, year: int, month: int
) -> dict[int, list[TimesheetDay]]:
    """Load per-employee timesheets from a folder of name_id.tsv files.

    Each file has columns: date, wkdy, hrs_norm, hrs_wrkd, hrs_miss, hrs_sik,
    hrs_ot_1_5, hrs_ot_2_0. Employee ID is extracted from the filename
    (e.g. beth_1.tsv → ID 1). Rows are filtered to the requested year/month.
    """
    import re

    folder = Path(folder)
    result: dict[int, list[TimesheetDay]] = {}

    for tsv_file in sorted(folder.glob("*.tsv")):
        # Extract employee_id from filename: name_id.tsv
        match = re.match(r"^.+_(\d+)\.tsv$", tsv_file.name)
        if not match:
            continue
        emp_id = int(match.group(1))

        entries = []
        with open(tsv_file, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                date_str = row.get("date", "").strip()
                if not date_str:
                    continue
                row_date = _parse_date(date_str)
                if row_date.year != year or row_date.month != month:
                    continue

                hrs_wrkd = row.get("hrs_wrkd", "").strip()
                hrs_miss = row.get("hrs_miss", "").strip()
                hrs_sik = row.get("hrs_sik", "").strip()
                ot_15 = row.get("hrs_ot_1_5", "").strip()
                ot_20 = row.get("hrs_ot_2_0", "").strip()

                # Skip rows with no data filled in yet
                if not hrs_wrkd and not hrs_miss and not hrs_sik:
                    continue

                absent = _parse_decimal(hrs_miss) > 0 or _parse_decimal(hrs_sik) > 0
                sick = _parse_decimal(hrs_sik) > 0

                entries.append(
                    TimesheetDay(
                        employee_id=emp_id,
                        date=row_date,
                        hours_normal=_parse_decimal(hrs_wrkd),
                        hours_ot_1_5=_parse_decimal(ot_15),
                        hours_ot_2_0=_parse_decimal(ot_20),
                        absent=absent,
                        sick=sick,
                    )
                )

        if entries:
            result[emp_id] = entries

    return result


# Required filenames for a valid payroll input folder
REQUIRED_FILES = {"master_employees.tsv", "contracts.tsv"}


def _prior_month_end(year: int, month: int) -> date:
    """Return the last day of the month before the given year/month."""
    if month == 1:
        return date(year - 1, 12, 31)
    _, last_day = monthrange(year, month - 1)
    return date(year, month - 1, last_day)


def find_leave_stocks_for_month(folder: str | Path, year: int, month: int) -> Path | None:
    """Find the leave_stocks file for a given payroll month.

    Looks for leave_stocks/YYYY/leave_stocks_YYYY_MM_DD.tsv where the date
    is the last day of the month prior to the payroll month. Falls back to
    a single leave_stocks.tsv for backwards compatibility.
    """
    folder = Path(folder)
    prior_end = _prior_month_end(year, month)
    filename = f"leave_stocks_{prior_end.year}_{prior_end.month:02d}_{prior_end.day:02d}.tsv"

    # Look in leave_stocks/YYYY/ subfolder first
    candidate = folder / "leave_stocks" / str(year) / filename
    if candidate.is_file():
        return candidate

    # Try recursive search for the filename
    for p in folder.rglob(filename):
        if p.is_file():
            return p

    # Backwards compatibility: single leave_stocks.tsv
    return find_file(folder, "leave_stocks.tsv")


def validate_input_folder(folder: str | Path) -> tuple[bool, list[str]]:
    """Scan a folder recursively and check for required payroll input files.

    Returns (is_valid, messages) where messages list missing files,
    duplicates, and the timesheet folder found (if any).
    """
    folder = Path(folder)
    messages = []

    if not folder.is_dir():
        return False, [f"Not a directory: {folder}"]

    # Collect all filenames and their paths
    file_map: dict[str, list[Path]] = {}
    timesheet_dirs: list[Path] = []

    for p in folder.rglob("*"):
        if p.is_file():
            file_map.setdefault(p.name, []).append(p)
        elif p.is_dir():
            # Check for year-named subdirectories inside timesheets/
            if p.name.isdigit() and len(p.name) == 4 and p.parent.name == "timesheets":
                tsv_files = list(p.glob("*_*.tsv"))
                if tsv_files:
                    timesheet_dirs.append(p)

    # Check required files
    missing = []
    for req in sorted(REQUIRED_FILES):
        if req not in file_map:
            missing.append(req)

    # Check for leave_stocks directory or legacy single file
    leave_stocks_dir = folder / "leave_stocks"
    has_leave_dir = leave_stocks_dir.is_dir() and any(leave_stocks_dir.rglob("leave_stocks_*.tsv"))
    has_leave_file = "leave_stocks.tsv" in file_map
    if not has_leave_dir and not has_leave_file:
        missing.append("leave_stocks/ directory (or legacy leave_stocks.tsv)")

    if missing:
        messages.append(f"Missing: {', '.join(missing)}")

    # Check for duplicates of required files
    for req in sorted(REQUIRED_FILES):
        if req in file_map and len(file_map[req]) > 1:
            paths = [str(p) for p in file_map[req]]
            messages.append(f"Duplicate '{req}': {', '.join(paths)}")

    # Check timesheets
    if not timesheet_dirs:
        messages.append("No timesheet year folder found (expected e.g. 2026/ with name_id.tsv files)")
    elif len(timesheet_dirs) > 1:
        dirs = [str(d) for d in timesheet_dirs]
        messages.append(f"Multiple timesheet year folders: {', '.join(dirs)}")

    is_valid = not missing and all(
        len(file_map.get(req, [])) <= 1 for req in REQUIRED_FILES
    ) and len(timesheet_dirs) >= 1 and (has_leave_dir or has_leave_file)

    if is_valid:
        messages.insert(0, f"Valid input folder: {len(file_map)} files found")

    return is_valid, messages


def find_file(folder: str | Path, filename: str) -> Path | None:
    """Find a file by name recursively in folder. Returns first match."""
    for p in Path(folder).rglob(filename):
        if p.is_file():
            return p
    return None


def find_timesheet_dir(folder: str | Path, year: int) -> Path | None:
    """Find a timesheet year directory (e.g. 2026/) containing name_id.tsv files."""
    for p in Path(folder).rglob(str(year)):
        if p.is_dir() and list(p.glob("*_*.tsv")):
            return p
    return None


def _parse_decimal(value: str, default: str = "0") -> Decimal:
    """Parse a decimal value, returning default for blank/invalid strings."""
    value = value.strip() if value else ""
    if not value:
        return Decimal(default)
    try:
        return Decimal(value)
    except InvalidOperation:
        return Decimal(default)


def _parse_date(date_str: str) -> date:
    """Parse a date string in YYYY-MM-DD format."""
    year, month, day = date_str.split("-")
    return date(int(year), int(month), int(day))
