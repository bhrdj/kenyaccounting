#!/usr/bin/env python3
"""CLI runner for generating payslips from real employee data.

Inputs come from Google Sheets and outputs go to Google Drive. Nothing is
read from or written to the working tree: the whole run happens inside a
temp directory that is deleted on exit, so no private employee data lands
on disk. Use --workdir to keep the staged files around when debugging.

Every saved run archives the exact inputs it used as a zip alongside its
outputs, so a past month can be recomputed with --replay even after the
source sheets have moved on.

Usage:
    python run_payroll.py --year 2026 --month 2
    python run_payroll.py --year 2026 --month 2 --no-save     # preview only
    python run_payroll.py --year 2026 --month 2 --replay      # rerun archived inputs
    python run_payroll.py --year 2026 --month 2 --workdir /tmp/pay  # keep files
    python run_payroll.py --year 2026 --month 2 --workdir /tmp/pay --no-sync
"""

import argparse
import sys
import tempfile
from contextlib import nullcontext
from datetime import date
from pathlib import Path

from extract_timesheets_xlsx2tsvs import extract_month
from src.calculators import PayrollEngine, default_leave_stock
from src.gsync import attendance_xlsx_path, sync_inputs
from src.loaders import (
    find_leave_stocks_for_month, load_contracts, load_employees,
    load_leave_stocks, load_timesheet_folder,
)
from src.outputs import (
    PayslipRenderer, download_archived_file, save_payroll_outputs,
    upload_leave_stocks_to_gsheet, upload_payroll_outputs_to_gdrive,
)
from src.snapshot import (
    SNAPSHOT_NAME, describe, read_snapshot, restore_snapshot, write_snapshot,
)


COMPANY_NAME = "B'aida Daycare & Learning Centre"


def run(year: int, month: int, workdir: Path, sync: bool, save: bool,
        replay: bool = False, replay_file: Path | None = None) -> int:
    """Stage inputs in workdir, run payroll, publish results. Returns exit code."""
    inputs = workdir / "inputs"
    outputs = workdir / "outputs"
    out_month = outputs / f"{year}_{month:02d}"
    payroll_date = date(year, month, 28)  # Use 28th as safe end-of-month

    if replay or replay_file:
        source = replay_file or f"Drive archive for {year}-{month:02d}"
        print(f"Replaying archived inputs from {source}...")
        try:
            if replay_file:
                payload = read_snapshot(replay_file)
            else:
                payload = read_snapshot(
                    download_archived_file(year, month, SNAPSHOT_NAME))
        except (FileNotFoundError, ValueError) as e:
            print(f"Cannot replay: {e}", file=sys.stderr)
            return 1
        if (payload["year"], payload["month"]) != (year, month):
            print(f"Snapshot is for {payload['year']}-{payload['month']:02d}, "
                  f"not {year}-{month:02d}", file=sys.stderr)
            return 1
        n = restore_snapshot(payload, inputs)
        print(f"  restored {n} files: {describe(payload)}")
        print()
    elif sync:
        print(f"Syncing inputs for {year} from Google Sheets...")
        missing = sync_inputs(inputs, year)
        if missing:
            print("\nCannot run - no spreadsheet key configured for:", file=sys.stderr)
            for m in missing:
                print(f"  - {m}", file=sys.stderr)
            return 1
        print()
    else:
        print(f"Using already-staged inputs in {inputs}")

    # Freeze whatever we are about to compute from, so this run can be
    # reproduced. Skipped on replay: the archived snapshot is already the
    # authority, and rewriting it from itself would only risk clobbering it.
    if not (replay or replay_file):
        write_snapshot(inputs, out_month / SNAPSHOT_NAME, year, month)
        print(f"Snapshotted inputs: {out_month / SNAPSHOT_NAME}")

    print(f"Loading data for {payroll_date.strftime('%B %Y')}...")
    print()

    employees = {e.employee_id: e for e in load_employees(inputs / "master_employees.tsv")}
    contracts = {c.employee_id: c for c in load_contracts(inputs / "contracts.tsv")}
    leave_path = find_leave_stocks_for_month(inputs, year, month)
    leave_stocks = (
        {l.employee_id: l for l in load_leave_stocks(leave_path)} if leave_path else {}
    )

    print(f"Loaded {len(employees)} employees, {len(contracts)} active contracts, "
          f"{len(leave_stocks)} leave records")
    if leave_path:
        print(f"Leave stocks from: {leave_path.name}")
    else:
        print(f"No leave stocks found for {year}-{month:02d} - starting from defaults")

    # Split the attendance workbook into one TSV per employee for this month
    xlsx = attendance_xlsx_path(inputs, year)
    if not xlsx.is_file():
        print(f"Attendance workbook not found: {xlsx}", file=sys.stderr)
        return 1
    ts_dir = inputs / "timesheets" / f"{year}_{month:02d}"
    extract_month(xlsx, ts_dir, year, month, log=lambda _: None)
    timesheets = load_timesheet_folder(ts_dir, year, month)

    if not timesheets:
        print(f"No timesheet rows for {year}-{month:02d} in {xlsx.name}", file=sys.stderr)
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
            leave_stocks[emp_id] = default_leave_stock(
                emp_id, contracts[emp_id], payroll_date)

        payslip = engine.process(
            employees[emp_id], contracts[emp_id], timesheets[emp_id], leave_stocks[emp_id]
        )
        payslips.append(payslip)

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
            print(f"  {ps.employee.employee_id:>4}  {ps.employee.name:<30} "
                  f"{ps.gross.total_gross:>12,.2f} {total_ded:>12,.2f} {ps.net_pay:>12,.2f}")
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

    # Publish results. The leave-stocks tab is what next month's run reads
    # back in, so it is written last - a failed Drive upload should not
    # leave the input sheet advanced past outputs nobody can see.
    if payslips and save:
        written = save_payroll_outputs(payslips, year, month, outputs, COMPANY_NAME)
        print(f"\nGenerated {len(written)} output files")
        drive_url, n_uploaded = upload_payroll_outputs_to_gdrive(year, month, outputs)
        print(f"Uploaded {n_uploaded} output files to Google Drive: {drive_url}")
        tab = upload_leave_stocks_to_gsheet(payslips, year, month)
        print(f"Uploaded leave stocks to gsheet tab: {tab}")

    if skipped:
        print()
        print("Skipped employees:")
        for emp_id, reason in skipped:
            print(f"  ID {emp_id}: {reason}")

    return 0 if payslips else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=1)
    parser.add_argument("--no-save", action="store_true",
                        help="Skip generating and uploading output files")
    parser.add_argument("--workdir", type=Path,
                        help="Stage files here and keep them, instead of a temp dir")
    parser.add_argument("--no-sync", action="store_true",
                        help="Reuse inputs already in --workdir instead of re-downloading")
    parser.add_argument("--replay", action="store_true",
                        help="Recompute from the inputs archived on Drive for this "
                             "month, instead of the current sheets")
    parser.add_argument("--replay-file", type=Path,
                        help="Recompute from a local snapshot file")
    args = parser.parse_args()

    if args.no_sync and not args.workdir:
        parser.error("--no-sync requires --workdir (a temp dir starts empty)")
    if args.replay and args.replay_file:
        parser.error("--replay and --replay-file are alternatives; pass only one")
    if (args.replay or args.replay_file) and args.no_sync:
        parser.error("--no-sync conflicts with replay (replay supplies the inputs)")

    if args.workdir:
        args.workdir.mkdir(parents=True, exist_ok=True)
        ctx = nullcontext(str(args.workdir))
    else:
        ctx = tempfile.TemporaryDirectory(prefix="kenyacc_")

    with ctx as tmp:
        return run(args.year, args.month, Path(tmp),
                   sync=not args.no_sync, save=not args.no_save,
                   replay=args.replay, replay_file=args.replay_file)


if __name__ == "__main__":
    sys.exit(main())
