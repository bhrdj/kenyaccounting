import csv
from io import StringIO

from .models import PaySlip


class PayslipRenderer:
    def render(self, payslip: PaySlip) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(f"PAYSLIP - {payslip.period}")
        lines.append("=" * 60)
        lines.append("")

        # Employee info
        lines.append(f"Employee:    {payslip.employee.name}")
        lines.append(f"ID:          {payslip.employee.employee_id}")
        lines.append(f"KRA PIN:     {payslip.employee.kra_pin}")
        lines.append(f"Bank A/C:    {payslip.employee.bank_account}")
        lines.append("")

        # Work summary
        lines.append("-" * 60)
        lines.append("WORK SUMMARY")
        lines.append("-" * 60)
        total_normal = sum(d.hours_normal for d in payslip.days_worked)
        total_ot_1_5 = sum(d.hours_ot_1_5 for d in payslip.days_worked)
        total_ot_2_0 = sum(d.hours_ot_2_0 for d in payslip.days_worked)
        lines.append(f"Days worked:     {len([d for d in payslip.days_worked if not d.absent])}")
        lines.append(f"Normal hours:    {total_normal}")
        if total_ot_1_5 > 0:
            lines.append(f"Overtime @1.5x:  {total_ot_1_5}")
        if total_ot_2_0 > 0:
            lines.append(f"Overtime @2.0x:  {total_ot_2_0}")
        lines.append("")

        # Leave used
        if payslip.leave.sick_full_pay_used or payslip.leave.sick_half_pay_used or payslip.leave.annual_leave_used or payslip.leave.unpaid_days:
            lines.append("-" * 60)
            lines.append("LEAVE USED")
            lines.append("-" * 60)
            if payslip.leave.sick_full_pay_used:
                lines.append(f"Sick (full pay):   {payslip.leave.sick_full_pay_used} days")
            if payslip.leave.sick_half_pay_used:
                lines.append(f"Sick (half pay):   {payslip.leave.sick_half_pay_used} days")
            if payslip.leave.annual_leave_used:
                lines.append(f"Annual leave:      {payslip.leave.annual_leave_used} days")
            if payslip.leave.unpaid_days:
                lines.append(f"Unpaid:            {payslip.leave.unpaid_days} days")
            lines.append("")

        # Earnings
        lines.append("-" * 60)
        lines.append("EARNINGS")
        lines.append("-" * 60)
        lines.append(f"Base pay:            {payslip.gross.base_pay:>12,.2f}")
        if payslip.gross.overtime_1_5 > 0:
            lines.append(f"Overtime @1.5x:      {payslip.gross.overtime_1_5:>12,.2f}")
        if payslip.gross.overtime_2_0 > 0:
            lines.append(f"Overtime @2.0x:      {payslip.gross.overtime_2_0:>12,.2f}")
        if payslip.gross.housing_allowance > 0:
            lines.append(f"Housing allowance:   {payslip.gross.housing_allowance:>12,.2f}")
        if payslip.gross.housing_benefit > 0:
            lines.append(f"Housing benefit:     {payslip.gross.housing_benefit:>12,.2f} (non-cash)")
        lines.append(f"                     {'-' * 12}")
        lines.append(f"GROSS PAY:           {payslip.gross.total_gross:>12,.2f}")
        lines.append("")

        # Deductions
        lines.append("-" * 60)
        lines.append("DEDUCTIONS")
        lines.append("-" * 60)
        lines.append(f"NSSF Tier 1:         {payslip.deductions.nssf_tier_1:>12,.2f}")
        lines.append(f"NSSF Tier 2:         {payslip.deductions.nssf_tier_2:>12,.2f}")
        lines.append(f"SHIF:                {payslip.deductions.shif:>12,.2f}")
        lines.append(f"AHL:                 {payslip.deductions.ahl_employee:>12,.2f}")
        lines.append(f"PAYE:                {payslip.deductions.paye:>12,.2f}")
        lines.append(f"                     {'-' * 12}")
        lines.append(f"TOTAL DEDUCTIONS:    {payslip.deductions.total:>12,.2f}")
        lines.append("")

        # Net pay
        lines.append("=" * 60)
        lines.append(f"NET PAY:             {payslip.net_pay:>12,.2f}")
        lines.append("=" * 60)

        # Warnings
        if payslip.warnings:
            lines.append("")
            lines.append("WARNINGS:")
            for warning in payslip.warnings:
                lines.append(f"  * {warning}")

        return "\n".join(lines)


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
