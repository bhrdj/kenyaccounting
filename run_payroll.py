#!/usr/bin/env python3
"""CLI runner for generating payslips from real employee data.

Usage:
    python run_payroll.py                    # January 2026 (default)
    python run_payroll.py --year 2026 --month 2
    python run_payroll.py --year 2026 --month 1 --no-save
"""

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.calculators import PayrollEngine
from src.loaders import load_contracts, load_employees, load_leave_stocks, load_timesheet, load_timesheet_folder, find_leave_stocks_for_month
from src.models import LeaveStock
from src.outputs import PayslipRenderer, save_payroll_outputs


INPUTS_DIR = Path("../el/payroll/working")
TIMESHEETS_DIR = INPUTS_DIR / "timesheets"
OUTPUT_DIR = Path("../el/payroll/outputs")
COMPANY_NAME = "B'aida Daycare & Learning Centre"


def main():
    parser = argparse.ArgumentParser(description="Generate payslips from real data")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=1)
    parser.add_argument("--no-save", action="store_true", help="Skip writing output files")
    args = parser.parse_args()

    year = args.year
    month = args.month
    payroll_date = date(year, month, 28)  # Use 28th as safe end-of-month

    print(f"Loading data for {payroll_date.strftime('%B %Y')}...")
    print()

    # Load employee data
    employees = {e.employee_id: e for e in load_employees(INPUTS_DIR / "master_employees.tsv")}
    contracts = {c.employee_id: c for c in load_contracts(INPUTS_DIR / "contracts.tsv")}
    leave_path = find_leave_stocks_for_month(INPUTS_DIR, year, month)
    if leave_path:
        leave_stocks = {l.employee_id: l for l in load_leave_stocks(leave_path)}
    else:
        leave_stocks = {}

    print(f"Loaded {len(employees)} employees, {len(contracts)} active contracts, {len(leave_stocks)} leave records")
    if leave_path:
        print(f"Leave stocks from: {leave_path.name}")

    # Load timesheets: try per-month folder, then per-year folder, then flat file
    ts_month_folder = TIMESHEETS_DIR / f"{year}_{month:02d}"
    ts_year_folder = TIMESHEETS_DIR / str(year)
    ts_flat = TIMESHEETS_DIR / f"{year}_{month:02d}.tsv"
    if ts_month_folder.is_dir():
        timesheets = load_timesheet_folder(ts_month_folder, year, month)
    elif ts_year_folder.is_dir():
        timesheets = load_timesheet_folder(ts_year_folder, year, month)
    elif ts_flat.exists():
        ts_entries = load_timesheet(ts_flat)
        timesheets = {}
        for entry in ts_entries:
            timesheets.setdefault(entry.employee_id, []).append(entry)
    else:
        print(f"No timesheets found at {ts_month_folder}, {ts_year_folder}, or {ts_flat}")
        return 1

    print(f"Loaded timesheets for {len(timesheets)} employees")
    print()

    # Run payroll
    engine = PayrollEngine(payroll_date)
    renderer = PayslipRenderer(company_name=COMPANY_NAME)
    payslips = []
    skipped = []

    for emp_id in sorted(contracts.keys()):
        if emp_id not in employees:
            skipped.append((emp_id, "no employee record"))
            continue
        if emp_id not in timesheets:
            skipped.append((emp_id, f"no timesheet ({employees[emp_id].name})"))
            continue
        if emp_id not in leave_stocks:
            # Create a default leave stock for employees without one
            leave_stocks[emp_id] = LeaveStock(
                employee_id=emp_id,
                sick_full_pay=Decimal("7"),
                sick_half_pay=Decimal("7"),
                annual_leave=Decimal("0"),
                as_of_date=date(2025, 12, 31),
            )

        employee = employees[emp_id]
        contract = contracts[emp_id]
        timesheet = timesheets[emp_id]
        leave = leave_stocks[emp_id]

        payslip = engine.process(employee, contract, timesheet, leave)
        payslips.append(payslip)

        # Print individual payslip
        print(renderer.render(payslip))
        print()
        print()

    # Print summary
    if payslips:
        print("=" * 60)
        print(f"  PAYROLL SUMMARY - {payroll_date.strftime('%B %Y')}")
        print("=" * 60)
        print(f"  Employees processed:     {len(payslips)}")
        print()

        # Per-employee summary
        print(f"  {'ID':>4}  {'Employee':<30} {'Gross':>12} {'Deductions':>12} {'Net':>12}")
        print(f"  {'----':>4}  {'-' * 30} {'-' * 12} {'-' * 12} {'-' * 12}")
        for ps in payslips:
            total_ded = ps.deductions.total
            print(f"  {ps.employee.employee_id:>4}  {ps.employee.name:<30} {ps.gross.total_gross:>12,.2f} {total_ded:>12,.2f} {ps.net_pay:>12,.2f}")
        print()

        total_gross = sum(ps.gross.total_gross for ps in payslips)
        total_net = sum(ps.net_pay for ps in payslips)
        total_paye = sum(ps.deductions.paye for ps in payslips)
        total_nssf_ee = sum(ps.deductions.nssf_tier_1 + ps.deductions.nssf_tier_2 for ps in payslips)
        total_nssf_er = total_nssf_ee  # employer matches
        total_shif = sum(ps.deductions.shif for ps in payslips)
        total_ahl_ee = sum(ps.deductions.ahl_employee for ps in payslips)
        total_ahl_er = total_ahl_ee  # employer matches

        print(f"  Total Gross Pay       KES {total_gross:>14,.2f}")
        print(f"  Total Net Pay         KES {total_net:>14,.2f}")
        print()
        print(f"  Total PAYE            KES {total_paye:>14,.2f}")
        print(f"  Total NSSF (employee) KES {total_nssf_ee:>14,.2f}")
        print(f"  Total NSSF (employer) KES {total_nssf_er:>14,.2f}")
        print(f"  Total SHIF            KES {total_shif:>14,.2f}")
        print(f"  Total AHL (employee)  KES {total_ahl_ee:>14,.2f}")
        print(f"  Total AHL (employer)  KES {total_ahl_er:>14,.2f}")
        print()

        # Cost to company
        total_employer = total_gross + total_nssf_er + total_ahl_er
        print(f"  Cost to Company       KES {total_employer:>14,.2f}")
        print("=" * 60)

    # Save output files
    if payslips and not args.no_save:
        written = save_payroll_outputs(payslips, year, month, OUTPUT_DIR, COMPANY_NAME)
        print(f"\nSaved {len(written)} files to {OUTPUT_DIR / f'{year}_{month:02d}'}")

    if skipped:
        print()
        print("Skipped employees:")
        for emp_id, reason in skipped:
            print(f"  ID {emp_id}: {reason}")

    return 0 if payslips else 1


if __name__ == "__main__":
    sys.exit(main())
