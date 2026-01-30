import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from .models import Contract, Employee, LeaveStock, TimesheetDay


def load_employees(path: str | Path) -> list[Employee]:
    """Load employees from a TSV file."""
    employees = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            employees.append(
                Employee(
                    employee_id=int(row["employee_id"]),
                    name=row["name"],
                    national_id=row["national_id"],
                    kra_pin=row["kra_pin"],
                    phone=row["phone"],
                    bank_account=row["bank_account"],
                )
            )
    return employees


def load_contracts(path: str | Path) -> list[Contract]:
    """Load contracts from a TSV file."""
    contracts = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            contracts.append(
                Contract(
                    employee_id=int(row["employee_id"]),
                    contract_type=row["contract_type"],
                    base_salary=Decimal(row["base_salary"]),
                    weekly_hours=int(row["weekly_hours"]) if row["weekly_hours"] else None,
                    housing_type=row["housing_type"],
                    housing_market_value=Decimal(row["housing_market_value"]) if row["housing_market_value"] else None,
                    nssf_tier=row["nssf_tier"],
                    start_date=_parse_date(row["start_date"]),
                    end_date=_parse_date(row["end_date"]) if row["end_date"] else None,
                    status=row["status"],
                    salary_basis=row.get("salary_basis", "gross"),
                    hourly_divisor=row.get("hourly_divisor", "monthly"),
                )
            )
    return contracts


def load_leave_stocks(path: str | Path) -> list[LeaveStock]:
    """Load leave stock balances from a TSV file."""
    stocks = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            stocks.append(
                LeaveStock(
                    employee_id=int(row["employee_id"]),
                    sick_full_pay=int(row["sick_full_pay"]),
                    sick_half_pay=int(row["sick_half_pay"]),
                    annual_leave=int(row["annual_leave"]),
                    as_of_date=_parse_date(row["as_of_date"]),
                )
            )
    return stocks


def load_timesheet(path: str | Path) -> list[TimesheetDay]:
    """Load timesheet entries from a TSV file."""
    entries = []
    with open(path, newline="") as f:
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


def _parse_date(date_str: str) -> date:
    """Parse a date string in YYYY-MM-DD format."""
    year, month, day = date_str.split("-")
    return date(int(year), int(month), int(day))
