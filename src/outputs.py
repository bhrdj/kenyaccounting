import csv
from calendar import monthrange
from io import BytesIO, StringIO
from pathlib import Path

from .models import PaySlip


class PayslipRenderer:
    def __init__(self, company_name: str = ""):
        self.company_name = company_name

    def render(self, payslip: PaySlip) -> str:
        lines = []
        lines.append("=" * 60)
        if self.company_name:
            lines.append(f"  {self.company_name}")
        lines.append(f"  PAYSLIP - {payslip.period}")
        lines.append("=" * 60)
        lines.append("")

        # Employee info
        lines.append(f"Employee:    {payslip.employee.name}")
        lines.append(f"ID:          {payslip.employee.employee_id}")
        lines.append(f"KRA PIN:     {payslip.employee.kra_pin}")
        if payslip.employee.nssf_no:
            lines.append(f"NSSF No:     {payslip.employee.nssf_no}")
        if payslip.employee.shif_no:
            lines.append(f"SHIF No:     {payslip.employee.shif_no}")
        lines.append(f"Bank A/C:    {payslip.employee.bank_account}")
        lines.append("")

        # Work & leave summary
        from .rates import KenyanHolidays
        lines.append("-" * 60)
        lines.append("WORK SUMMARY")
        lines.append("-" * 60)
        total_normal = sum(d.hours_normal for d in payslip.days_worked)
        total_ot_1_5 = sum(d.hours_ot_1_5 for d in payslip.days_worked)
        total_ot_2_0 = sum(d.hours_ot_2_0 for d in payslip.days_worked)
        days_worked = len([d for d in payslip.days_worked if d.hours_normal > 0])
        holidays = KenyanHolidays.get_holidays_for_month(
            payslip.days_worked[0].date.year, payslip.days_worked[0].date.month
        ) if payslip.days_worked else []
        lines.append(f"Days worked:     {days_worked}")
        if holidays:
            holiday_dates = {h.date for h in holidays}
            worked_holidays = sum(
                1 for d in payslip.days_worked
                if d.date in holiday_dates and d.hours_normal > 0
            )
            holiday_line = f"Public holidays: {len(holidays)}  ({', '.join(h.name for h in holidays)})"
            if worked_holidays:
                holiday_line += f" — worked {worked_holidays}"
            lines.append(holiday_line)
        lines.append(f"Normal hours:    {total_normal:.2f}")
        if total_ot_1_5 > 0:
            lines.append(f"Overtime @1.5x:  {total_ot_1_5}")
        if total_ot_2_0 > 0:
            lines.append(f"Overtime @2.0x:  {total_ot_2_0}")
        leave = payslip.leave
        lines.append(f"Annual leave:    {leave.annual_leave_used:.2f} hrs")
        lines.append(f"Sick full pay:   {leave.sick_full_pay_used:.2f} hrs")
        lines.append(f"Sick half pay:   {leave.sick_half_pay_used:.2f} hrs")
        lines.append(f"Unpaid:          {leave.unpaid_hours:.2f} hrs")
        lines.append("")

        # Earnings
        lines.append("-" * 60)
        lines.append("EARNINGS")
        lines.append("-" * 60)
        lines.append(f"  Base pay              KES {payslip.gross.base_pay:>12,.2f}")
        if payslip.gross.overtime_1_5 > 0:
            lines.append(f"  Overtime @1.5x        KES {payslip.gross.overtime_1_5:>12,.2f}")
        if payslip.gross.overtime_2_0 > 0:
            lines.append(f"  Overtime @2.0x        KES {payslip.gross.overtime_2_0:>12,.2f}")
        if payslip.gross.holiday_premium > 0:
            lines.append(f"  Holiday premium       KES {payslip.gross.holiday_premium:>12,.2f}")
        if payslip.gross.housing_allowance > 0:
            lines.append(f"  Housing allowance     KES {payslip.gross.housing_allowance:>12,.2f}")
        if payslip.gross.leave_half_pay_deduction > 0:
            lines.append(f"  Less: half-pay sick   KES {-payslip.gross.leave_half_pay_deduction:>12,.2f}")
        if payslip.gross.leave_unpaid_deduction > 0:
            lines.append(f"  Less: unpaid leave    KES {-payslip.gross.leave_unpaid_deduction:>12,.2f}")
        if payslip.gross.housing_benefit > 0:
            lines.append(f"  Housing benefit       KES {payslip.gross.housing_benefit:>12,.2f}  (non-cash)")
        lines.append(f"                        {'':>4}{'-' * 16}")
        lines.append(f"  GROSS PAY             KES {payslip.gross.total_gross:>12,.2f}")
        lines.append("")

        # Employee deductions
        lines.append("-" * 60)
        lines.append("EMPLOYEE DEDUCTIONS")
        lines.append("-" * 60)
        lines.append(f"  NSSF Tier 1           KES {payslip.deductions.nssf_tier_1:>12,.2f}")
        lines.append(f"  NSSF Tier 2           KES {payslip.deductions.nssf_tier_2:>12,.2f}")
        lines.append(f"  SHIF                  KES {payslip.deductions.shif:>12,.2f}")
        lines.append(f"  AHL (1.5%)            KES {payslip.deductions.ahl_employee:>12,.2f}")
        lines.append(f"  PAYE                  KES {payslip.deductions.paye:>12,.2f}")
        lines.append(f"                        {'':>4}{'-' * 16}")
        lines.append(f"  TOTAL DEDUCTIONS      KES {payslip.deductions.total:>12,.2f}")
        lines.append("")

        # Net pay
        lines.append("=" * 60)
        lines.append(f"  NET PAY               KES {payslip.net_pay:>12,.2f}")
        lines.append("=" * 60)

        # Employer contributions
        nssf_employer = payslip.deductions.nssf_tier_1 + payslip.deductions.nssf_tier_2
        ahl_employer = payslip.gross.total_gross * payslip.deductions.ahl_employee / payslip.gross.total_gross if payslip.gross.total_gross > 0 else payslip.deductions.ahl_employee
        lines.append("")
        lines.append("-" * 60)
        lines.append("EMPLOYER CONTRIBUTIONS")
        lines.append("-" * 60)
        lines.append(f"  NSSF (employer match) KES {nssf_employer:>12,.2f}")
        lines.append(f"  AHL (1.5%)            KES {ahl_employer:>12,.2f}")

        # Leave balance
        lines.append("")
        lines.append("-" * 60)
        lines.append("LEAVE BALANCE (after this period)")
        lines.append("-" * 60)
        stock = payslip.leave.updated_stock
        lines.append(f"  Sick (full pay):  {float(stock.sick_full_pay):>6.1f} days")
        lines.append(f"  Sick (half pay):  {float(stock.sick_half_pay):>6.1f} days")
        lines.append(f"  Annual leave:     {float(stock.annual_leave):>6.1f} days")

        # Warnings
        if payslip.warnings:
            lines.append("")
            lines.append("WARNINGS:")
            for warning in payslip.warnings:
                lines.append(f"  * {warning}")

        return "\n".join(lines)

    def render_all_pdf(self, payslips: list[PaySlip]) -> bytes:
        """Render all payslips into a single PDF, one per page."""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        page_width, page_height = A4

        font_name = "Courier"
        font_size = 9
        line_height = font_size * 1.35
        margin_left = 20 * mm
        margin_top = 20 * mm

        for i, payslip in enumerate(payslips):
            if i > 0:
                c.showPage()

            text = self.render(payslip)
            y = page_height - margin_top

            for line in text.split("\n"):
                if y < 15 * mm:
                    c.showPage()
                    y = page_height - margin_top
                c.setFont(font_name, font_size)
                c.drawString(margin_left, y, line)
                y -= line_height

        c.save()
        return buf.getvalue()


class BankFileGenerator:
    def __init__(self, payslips: list[PaySlip]):
        self.payslips = payslips

    def to_equity_csv(self) -> str:
        output = StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            "Account Number",
            "Beneficiary Name",
            "Amount",
            "Reference",
        ])

        # Data rows
        for ps in self.payslips:
            writer.writerow([
                ps.employee.bank_account,
                ps.employee.name,
                f"{ps.net_pay:.2f}",
                f"Salary {ps.period}",
            ])

        return output.getvalue()


class KRAReturnGenerator:
    def __init__(self, payslips: list[PaySlip]):
        self.payslips = payslips

    def to_p10_csv(self) -> str:
        output = StringIO()
        writer = csv.writer(output)

        # P10 header row (based on common KRA template elements)
        writer.writerow([
            "KRA PIN",
            "Employee Name",
            "National ID",
            "Gross Pay",
            "NSSF Employee",
            "SHIF",
            "AHL",
            "Housing Benefit",
            "Chargeable Pay",
            "PAYE Tax",
            "Personal Relief",
            "PAYE Payable",
        ])

        for ps in self.payslips:
            nssf_total = ps.deductions.nssf_tier_1 + ps.deductions.nssf_tier_2
            chargeable = (
                ps.gross.total_gross
                + ps.gross.housing_benefit
                - nssf_total
                - ps.deductions.shif
                - ps.deductions.ahl_employee
            )
            writer.writerow([
                ps.employee.kra_pin,
                ps.employee.name,
                ps.employee.national_id,
                f"{ps.gross.total_gross:.2f}",
                f"{nssf_total:.2f}",
                f"{ps.deductions.shif:.2f}",
                f"{ps.deductions.ahl_employee:.2f}",
                f"{ps.gross.housing_benefit:.2f}",
                f"{chargeable:.2f}",
                f"{ps.deductions.paye + 2400:.2f}",  # Gross tax before relief
                "2400.00",
                f"{ps.deductions.paye:.2f}",
            ])

        return output.getvalue()


class NSSFReturnGenerator:
    def __init__(self, payslips: list[PaySlip]):
        self.payslips = payslips

    def to_nssf_csv(self) -> str:
        output = StringIO()
        writer = csv.writer(output)

        # NSSF header row
        writer.writerow([
            "National ID",
            "KRA PIN",
            "Employee Name",
            "Gross Salary",
            "NSSF Tier 1 Employee",
            "NSSF Tier 1 Employer",
            "NSSF Tier 2 Employee",
            "NSSF Tier 2 Employer",
            "Total Employee",
            "Total Employer",
            "Total Contribution",
        ])

        for ps in self.payslips:
            # Employer matches employee contributions
            t1_emp = ps.deductions.nssf_tier_1
            t1_er = ps.deductions.nssf_tier_1
            t2_emp = ps.deductions.nssf_tier_2
            t2_er = ps.deductions.nssf_tier_2
            total_emp = t1_emp + t2_emp
            total_er = t1_er + t2_er
            writer.writerow([
                ps.employee.national_id,
                ps.employee.kra_pin,
                ps.employee.name,
                f"{ps.gross.total_gross:.2f}",
                f"{t1_emp:.2f}",
                f"{t1_er:.2f}",
                f"{t2_emp:.2f}",
                f"{t2_er:.2f}",
                f"{total_emp:.2f}",
                f"{total_er:.2f}",
                f"{total_emp + total_er:.2f}",
            ])

        return output.getvalue()


class SHAReturnGenerator:
    def __init__(self, payslips: list[PaySlip]):
        self.payslips = payslips

    def to_sha_csv(self) -> str:
        output = StringIO()
        writer = csv.writer(output)

        # SHA/SHIF header row
        writer.writerow([
            "National ID",
            "Employee Name",
            "Gross Salary",
            "SHIF Contribution",
        ])

        for ps in self.payslips:
            writer.writerow([
                ps.employee.national_id,
                ps.employee.name,
                f"{ps.gross.total_gross:.2f}",
                f"{ps.deductions.shif:.2f}",
            ])

        return output.getvalue()


def generate_leave_stocks_tsv(payslips: list[PaySlip], year: int, month: int) -> str:
    """Generate updated leave_stocks TSV content from processed payslips."""
    _, last_day = monthrange(year, month)
    as_of = f"{year}-{month:02d}-{last_day:02d}"
    output = StringIO()
    writer = csv.writer(output, delimiter="\t")
    writer.writerow([
        "employee_id", "name", "sick_full_pay", "sick_half_pay",
        "annual_leave", "as_of_date", "notes",
    ])
    for ps in payslips:
        stock = ps.leave.updated_stock
        writer.writerow([
            ps.employee.employee_id,
            ps.employee.name,
            f"{stock.sick_full_pay}",
            f"{stock.sick_half_pay}",
            f"{stock.annual_leave}",
            as_of,
            "",
        ])
    return output.getvalue()


def save_leave_stocks(
    payslips: list[PaySlip], year: int, month: int, leave_stocks_dir: str | Path,
) -> Path:
    """Write updated leave_stocks TSV into leave_stocks/YYYY/ directory.

    Returns the path written.
    """
    _, last_day = monthrange(year, month)
    dest_dir = Path(leave_stocks_dir) / "leave_stocks" / str(year)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"leave_stocks_{year}_{month:02d}_{last_day:02d}.tsv"
    dest.write_text(generate_leave_stocks_tsv(payslips, year, month))
    return dest


GSPREAD_CREDS = Path.home() / ".config/google/everyday_creds.json"
GSPREAD_TOKEN = Path.home() / ".config/google/gspread_authorized_user.json"


def upload_leave_stocks_to_gsheet(
    payslips: list[PaySlip], year: int, month: int,
    spreadsheet_name: str | None = None,
) -> str:
    """Upload updated leave stocks as a tab in a Google Sheets spreadsheet.

    Creates the tab if it doesn't exist, or clears and replaces if it does.
    Tab name is YYYY_MM_DD (end of payroll month).
    Returns the tab name written.
    """
    import gspread

    _, last_day = monthrange(year, month)
    tab_name = f"{year}_{month:02d}_{last_day:02d}"
    if spreadsheet_name is None:
        spreadsheet_name = f"leave_stocks_{year}"

    gc = gspread.oauth(
        credentials_filename=str(GSPREAD_CREDS),
        authorized_user_filename=str(GSPREAD_TOKEN),
    )
    sh = gc.open(spreadsheet_name)

    # Build rows from payslips
    header = ["employee_id", "name", "sick_full_pay", "sick_half_pay",
              "annual_leave", "as_of_date", "notes"]
    as_of = f"{year}-{month:02d}-{last_day:02d}"
    rows = [header]
    for ps in payslips:
        stock = ps.leave.updated_stock
        rows.append([
            ps.employee.employee_id,
            ps.employee.name,
            float(stock.sick_full_pay),
            float(stock.sick_half_pay),
            float(stock.annual_leave),
            as_of,
            "",
        ])

    # Create or clear the tab
    try:
        ws = sh.worksheet(tab_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab_name, rows=len(rows), cols=len(header))

    ws.update(rows, value_input_option="RAW")

    # Format numeric leave columns as 2 decimal places (columns C, D, E)
    num_rows = len(rows)
    ws.format(f"C1:E{num_rows}", {"numberFormat": {"type": "NUMBER", "pattern": "0.00"}})

    # Reorder tabs in decreasing alphabetical order
    worksheets = sh.worksheets()
    desired_order = sorted(worksheets, key=lambda w: w.title, reverse=True)
    sh.reorder_worksheets(desired_order)

    return tab_name


def save_payroll_outputs(
    payslips: list[PaySlip],
    year: int,
    month: int,
    output_dir: str | Path,
    company_name: str = "",
) -> list[Path]:
    """Write all payroll output files to output_dir/YYYY_MM/.

    Returns list of written Path objects.
    """
    output_dir = Path(output_dir) / f"{year}_{month:02d}"
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []

    # Payslips (individual text + combined PDF)
    payslips_dir = output_dir / "payslips"
    payslips_dir.mkdir(exist_ok=True)
    renderer = PayslipRenderer(company_name=company_name)
    for ps in payslips:
        safe_name = ps.employee.name.replace(" ", "_")
        path = payslips_dir / f"{ps.employee.employee_id}_{safe_name}.txt"
        path.write_text(renderer.render(ps))
        written.append(path)

    pdf_path = output_dir / "payslips_all.pdf"
    pdf_path.write_bytes(renderer.render_all_pdf(payslips))
    written.append(pdf_path)

    # Bank payment CSV
    bank_path = output_dir / "bank_payment.csv"
    bank_path.write_text(BankFileGenerator(payslips).to_equity_csv())
    written.append(bank_path)

    # KRA P10 CSV
    kra_path = output_dir / "kra_p10.csv"
    kra_path.write_text(KRAReturnGenerator(payslips).to_p10_csv())
    written.append(kra_path)

    # NSSF return CSV
    nssf_path = output_dir / "nssf_return.csv"
    nssf_path.write_text(NSSFReturnGenerator(payslips).to_nssf_csv())
    written.append(nssf_path)

    # SHA return CSV
    sha_path = output_dir / "sha_return.csv"
    sha_path.write_text(SHAReturnGenerator(payslips).to_sha_csv())
    written.append(sha_path)

    # Leave stocks updated TSV (named for use as next month's input)
    _, last_day = monthrange(year, month)
    leave_path = output_dir / f"leave_stocks_{year}_{month:02d}_{last_day:02d}.tsv"
    leave_path.write_text(generate_leave_stocks_tsv(payslips, year, month))
    written.append(leave_path)

    # Summary table TSV
    from .rates import KenyanHolidays
    holidays = {h.date for h in KenyanHolidays.get_holidays_for_month(year, month)}

    summary_path = output_dir / "summary_table.tsv"
    with open(summary_path, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow([
            "ID", "Employee", "FulTimBase", "WrkdBase",
            "AnnLea", "SikFul", "SikHaf", "UnpLea", "HolWkd",
            "Gross Pay", "Net Pay",
        ])
        from .calculators import LeaveCalculator

        for ps in payslips:
            daily_hours = LeaveCalculator._get_daily_hours(ps.contract)
            hol_worked = sum(
                1 for d in ps.days_worked
                if d.date in holidays and d.hours_normal > 0
            )
            writer.writerow([
                ps.employee.employee_id,
                ps.employee.name,
                f"{ps.gross.baseline_base_pay:.2f}",
                f"{ps.gross.base_pay:.2f}",
                f"{float(ps.leave.annual_leave_used / daily_hours):.1f}" if ps.leave.annual_leave_used else "0",
                f"{float(ps.leave.sick_full_pay_used / daily_hours):.1f}" if ps.leave.sick_full_pay_used else "0",
                f"{float(ps.leave.sick_half_pay_used / daily_hours):.1f}" if ps.leave.sick_half_pay_used else "0",
                f"{float(ps.leave.unpaid_hours / daily_hours):.1f}" if ps.leave.unpaid_hours else "0",
                str(hol_worked),
                f"{ps.gross.total_gross:.2f}",
                f"{ps.net_pay:.2f}",
            ])
    written.append(summary_path)

    return written
