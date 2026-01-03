from datetime import date
from decimal import Decimal

from .models import (
    Contract, Deductions, Employee, GrossBreakdown, LeaveAllocation,
    LeaveStock, PaySlip, TimesheetDay,
)
from .rates import StatutoryRates


class GrossCalculator:
    def __init__(self, contract: Contract, timesheet_days: list[TimesheetDay]):
        self.contract = contract
        self.timesheet_days = timesheet_days

    def calculate(self) -> GrossBreakdown:
        if self.contract.contract_type == "hourly":
            return self._calc_hourly()
        elif self.contract.contract_type == "fixed_monthly":
            return self._calc_fixed_monthly()
        elif self.contract.contract_type == "prorated_min_wage":
            return self._calc_prorated_min_wage()

    def _calc_hourly(self) -> GrossBreakdown:
        divisor = Decimal(self.contract.weekly_hours * 52) / Decimal(12)
        hourly_rate = self.contract.base_salary / divisor

        total_normal = sum(d.hours_normal for d in self.timesheet_days)
        total_ot_1_5 = sum(d.hours_ot_1_5 for d in self.timesheet_days)
        total_ot_2_0 = sum(d.hours_ot_2_0 for d in self.timesheet_days)

        base_pay = hourly_rate * total_normal
        overtime_1_5 = hourly_rate * Decimal("1.5") * total_ot_1_5
        overtime_2_0 = hourly_rate * Decimal("2.0") * total_ot_2_0

        return GrossBreakdown(
            base_pay=base_pay,
            overtime_1_5=overtime_1_5,
            overtime_2_0=overtime_2_0,
            housing_benefit=Decimal(0),
            total_gross=base_pay + overtime_1_5 + overtime_2_0,
        )

    def _calc_fixed_monthly(self) -> GrossBreakdown:
        # For fixed monthly, the base_salary is the full monthly amount
        # We assume full salary unless there are unpaid days to deduct
        # (unpaid day handling happens via LeaveCalculator adjusting pay)
        return GrossBreakdown(
            base_pay=self.contract.base_salary,
            overtime_1_5=Decimal(0),
            overtime_2_0=Decimal(0),
            housing_benefit=Decimal(0),
            total_gross=self.contract.base_salary,
        )

    def _calc_prorated_min_wage(self) -> GrossBreakdown:
        # Standard monthly hours based on weekly hours
        std_monthly_hours = Decimal(self.contract.weekly_hours * 4)
        worked_hours = sum(d.hours_normal for d in self.timesheet_days)
        fraction = worked_hours / std_monthly_hours
        base_pay = self.contract.base_salary * fraction

        return GrossBreakdown(
            base_pay=base_pay,
            overtime_1_5=Decimal(0),
            overtime_2_0=Decimal(0),
            housing_benefit=Decimal(0),
            total_gross=base_pay,
        )


class LeaveCalculator:
    def __init__(self, timesheet_days: list[TimesheetDay], leave_stock: LeaveStock):
        self.timesheet_days = timesheet_days
        self.leave_stock = leave_stock

    def allocate(self) -> LeaveAllocation:
        sick_full_used = 0
        sick_half_used = 0
        annual_used = 0
        unpaid_days = 0

        # Copy current stock values
        remaining_sick_full = self.leave_stock.sick_full_pay
        remaining_sick_half = self.leave_stock.sick_half_pay
        remaining_annual = self.leave_stock.annual_leave

        for day in self.timesheet_days:
            if not day.absent:
                continue

            if day.sick:
                # Draw from sick leave
                if remaining_sick_full > 0:
                    sick_full_used += 1
                    remaining_sick_full -= 1
                elif remaining_sick_half > 0:
                    sick_half_used += 1
                    remaining_sick_half -= 1
                else:
                    unpaid_days += 1
            else:
                # Non-sick absence: draw from annual leave
                if remaining_annual > 0:
                    annual_used += 1
                    remaining_annual -= 1
                else:
                    unpaid_days += 1

        updated_stock = LeaveStock(
            employee_id=self.leave_stock.employee_id,
            sick_full_pay=remaining_sick_full,
            sick_half_pay=remaining_sick_half,
            annual_leave=remaining_annual,
            as_of_date=self.leave_stock.as_of_date,
        )

        return LeaveAllocation(
            sick_full_pay_used=sick_full_used,
            sick_half_pay_used=sick_half_used,
            annual_leave_used=annual_used,
            unpaid_days=unpaid_days,
            updated_stock=updated_stock,
        )


class DeductionCalculator:
    def __init__(self, gross: Decimal, rates: StatutoryRates, contract: Contract):
        self.gross = gross
        self.rates = rates
        self.contract = contract

    def calculate(self) -> Deductions:
        # NSSF Tier 1: 6% of earnings up to LEL
        nssf_t1 = min(self.gross, self.rates.nssf_lel) * self.rates.nssf_rate

        # NSSF Tier 2: 6% of earnings between LEL and UEL (if not contracted out)
        if self.contract.nssf_tier == "standard":
            pensionable = min(self.gross, self.rates.nssf_uel) - self.rates.nssf_lel
            nssf_t2 = max(Decimal(0), pensionable) * self.rates.nssf_rate
        else:
            nssf_t2 = Decimal(0)

        # SHIF: 2.75% of gross, minimum 300
        shif = max(self.gross * self.rates.shif_rate, self.rates.shif_min)

        # AHL: 1.5% employee contribution
        ahl = self.gross * self.rates.ahl_rate

        return Deductions(
            nssf_tier_1=nssf_t1,
            nssf_tier_2=nssf_t2,
            shif=shif,
            ahl_employee=ahl,
            paye=Decimal(0),  # Calculated separately by PAYECalculator
            total=Decimal(0),  # Set after PAYE is calculated
        )


class PAYECalculator:
    def __init__(self, rates: StatutoryRates):
        self.rates = rates

    def calculate(self, chargeable_pay: Decimal) -> Decimal:
        tax = Decimal(0)
        remaining = chargeable_pay
        prev_limit = Decimal(0)

        for limit, rate in self.rates.tax_bands:
            band_width = limit - prev_limit
            taxable = min(remaining, band_width)
            tax += taxable * rate
            remaining -= taxable
            prev_limit = limit
            if remaining <= 0:
                break

        return max(tax - self.rates.personal_relief, Decimal(0))


class HousingBenefitCalculator:
    def __init__(self, contract: Contract, gross: Decimal):
        self.contract = contract
        self.gross = gross

    def calculate(self) -> Decimal:
        if self.contract.housing_type == "quarters":
            fifteen_pct = self.gross * Decimal("0.15")
            return max(self.contract.housing_market_value, fifteen_pct)
        return Decimal(0)


class PayrollEngine:
    def __init__(self, payroll_date: date):
        self.payroll_date = payroll_date
        self.rates = StatutoryRates(payroll_date)

    def process(
        self,
        employee: Employee,
        contract: Contract,
        timesheet_days: list[TimesheetDay],
        leave_stock: LeaveStock,
    ) -> PaySlip:
        # 1. Calculate leave allocation
        leave_calc = LeaveCalculator(timesheet_days, leave_stock)
        leave = leave_calc.allocate()

        # 2. Calculate gross
        gross_calc = GrossCalculator(contract, timesheet_days)
        gross = gross_calc.calculate()

        # 3. Apply leave adjustments for fixed monthly contracts
        if contract.contract_type == "fixed_monthly":
            gross = self._apply_leave_adjustments(gross, leave, contract)

        # 4. Add housing benefit
        housing_calc = HousingBenefitCalculator(contract, gross.total_gross)
        housing_benefit = housing_calc.calculate()
        gross = GrossBreakdown(
            base_pay=gross.base_pay,
            overtime_1_5=gross.overtime_1_5,
            overtime_2_0=gross.overtime_2_0,
            housing_benefit=housing_benefit,
            total_gross=gross.total_gross,
        )

        # 5. Calculate deductions (NSSF, SHIF, AHL)
        ded_calc = DeductionCalculator(gross.total_gross, self.rates, contract)
        deductions = ded_calc.calculate()

        # 6. Calculate chargeable pay and PAYE
        # Chargeable = Gross + Housing Benefit - (NSSF + SHIF + AHL)
        chargeable = (
            gross.total_gross
            + gross.housing_benefit
            - deductions.nssf_tier_1
            - deductions.nssf_tier_2
            - deductions.shif
            - deductions.ahl_employee
        )

        paye_calc = PAYECalculator(self.rates)
        paye = paye_calc.calculate(chargeable)

        # 7. Build final deductions with PAYE and total
        deductions = Deductions(
            nssf_tier_1=deductions.nssf_tier_1,
            nssf_tier_2=deductions.nssf_tier_2,
            shif=deductions.shif,
            ahl_employee=deductions.ahl_employee,
            paye=paye,
            total=(
                deductions.nssf_tier_1
                + deductions.nssf_tier_2
                + deductions.shif
                + deductions.ahl_employee
                + paye
            ),
        )

        # 8. Calculate net pay (housing benefit is non-cash, not added)
        net_pay = gross.total_gross - deductions.total

        # 9. Format period string
        period = self.payroll_date.strftime("%B %Y")

        return PaySlip(
            employee=employee,
            contract=contract,
            period=period,
            gross=gross,
            deductions=deductions,
            leave=leave,
            net_pay=net_pay,
            days_worked=timesheet_days,
        )

    def _apply_leave_adjustments(
        self, gross: GrossBreakdown, leave: LeaveAllocation, contract: Contract
    ) -> GrossBreakdown:
        # For fixed monthly, deduct for unpaid days and half-pay sick days
        # Assume 22 working days in a month
        daily_rate = contract.base_salary / Decimal(22)

        # Half pay for sick_half_pay_used days (deduct 50%)
        half_pay_deduction = daily_rate * Decimal("0.5") * leave.sick_half_pay_used

        # Full deduction for unpaid days
        unpaid_deduction = daily_rate * leave.unpaid_days

        adjusted_base = gross.base_pay - half_pay_deduction - unpaid_deduction

        return GrossBreakdown(
            base_pay=adjusted_base,
            overtime_1_5=gross.overtime_1_5,
            overtime_2_0=gross.overtime_2_0,
            housing_benefit=gross.housing_benefit,
            total_gross=adjusted_base + gross.overtime_1_5 + gross.overtime_2_0,
        )
