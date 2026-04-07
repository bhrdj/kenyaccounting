from datetime import date
from decimal import Decimal

from .models import (
    Contract, Deductions, Employee, GrossBreakdown, LeaveAllocation,
    LeaveStock, PaySlip, TimesheetDay,
)
from .rates import StatutoryRates


class GrossCalculator:
    HOUSING_RATE = Decimal("0.15")
    STATUTORY_DIVISOR = Decimal("225.333333")  # 52 * 52 / 12

    def __init__(self, contract: Contract, timesheet_days: list[TimesheetDay], payroll_date: date = None):
        self.contract = contract
        self.timesheet_days = timesheet_days
        self.payroll_date = payroll_date

    def _get_divisor(self) -> Decimal:
        """
        Get the hourly divisor based on contract settings.

        Options:
        - 'statutory' or '225': Use 225.33 (52 weeks * 52 hours / 12 months)
        - 'monthly': Calculate based on working days in the payroll month
        - A number: Use that custom divisor
        """
        from .rates import KenyanHolidays

        divisor_setting = self.contract.hourly_divisor.lower().strip()

        if divisor_setting in ("statutory", "225"):
            return self.STATUTORY_DIVISOR

        if divisor_setting == "monthly":
            if self.payroll_date is None:
                # Fallback to statutory if no payroll date
                return self.STATUTORY_DIVISOR
            # Calculate based on working days in the month
            weekly_hours = self.contract.weekly_hours or 45
            return KenyanHolidays.get_expected_hours(
                self.payroll_date.year,
                self.payroll_date.month,
                weekly_hours,
            )

        # Try to parse as a custom number
        try:
            return Decimal(divisor_setting)
        except:
            # Default to statutory if parsing fails
            return self.STATUTORY_DIVISOR

    def calculate(self) -> GrossBreakdown:
        if self.contract.contract_type in ("hourly", "consolidated_leave", "fixed_monthly"):
            return self._calc_fixed_monthly()
        elif self.contract.contract_type == "prorated_min_wage":
            return self._calc_prorated_min_wage()

    def _compute_housing(self, base_pay: Decimal) -> tuple[Decimal, Decimal, Decimal]:
        """
        Compute base pay, housing allowance, and total gross based on housing_type and salary_basis.

        Returns: (actual_base, housing_allowance, total_gross)

        Per Kenya Employment Act Section 31 and Regulation of Wages Order:
        - If employer does NOT provide housing (housing_type='none'), a 15% housing
          allowance MUST be paid. The salary_basis determines interpretation:
          - salary_basis='base': input is base pay, housing = 15%, gross = base * 1.15
          - salary_basis='gross': input is gross, base = gross / 1.15, housing = gross - base
        - If employer provides housing (housing_type='quarters'), no cash allowance
          (taxable benefit is calculated separately by HousingBenefitCalculator)
        """
        if self.contract.housing_type in ("quarters", "dorm"):
            # Employer provides housing - no cash allowance needed
            actual_base = base_pay
            housing_allowance = Decimal(0)
            total_gross = base_pay
        else:
            # No housing provided (housing_type='none') - 15% allowance required by law
            if self.contract.salary_basis == "base":
                # Input is base pay, compute housing allowance
                actual_base = base_pay
                housing_allowance = base_pay * self.HOUSING_RATE
                total_gross = actual_base + housing_allowance
            else:
                # Input is gross pay, back-calculate base
                total_gross = base_pay  # input is actually gross
                actual_base = total_gross / (Decimal(1) + self.HOUSING_RATE)
                housing_allowance = total_gross - actual_base

        return actual_base, housing_allowance, total_gross

    def _calc_hourly(self) -> GrossBreakdown:
        divisor = self._get_divisor()
        hourly_rate = self.contract.base_salary / divisor

        total_normal = sum(d.hours_normal for d in self.timesheet_days)
        total_ot_1_5 = sum(d.hours_ot_1_5 for d in self.timesheet_days)
        total_ot_2_0 = sum(d.hours_ot_2_0 for d in self.timesheet_days)

        raw_base_pay = hourly_rate * total_normal
        overtime_1_5 = hourly_rate * Decimal("1.5") * total_ot_1_5
        overtime_2_0 = hourly_rate * Decimal("2.0") * total_ot_2_0

        # Baseline: what full-time would pay (before housing)
        baseline, _, _ = self._compute_housing(self.contract.base_salary)

        # For hourly, apply housing to the total earned (base + overtime)
        earned = raw_base_pay + overtime_1_5 + overtime_2_0
        actual_base, housing_allowance, total_gross = self._compute_housing(earned)

        return GrossBreakdown(
            base_pay=actual_base,
            overtime_1_5=overtime_1_5,
            overtime_2_0=overtime_2_0,
            housing_allowance=housing_allowance,
            housing_benefit=Decimal(0),
            total_gross=total_gross,
            baseline_base_pay=baseline,
            worked_base_pay=actual_base,
        )

    def _calc_fixed_monthly(self) -> GrossBreakdown:
        # For fixed monthly, base_salary is interpreted based on salary_basis
        actual_base, housing_allowance, total_gross = self._compute_housing(self.contract.base_salary)

        return GrossBreakdown(
            base_pay=actual_base,
            overtime_1_5=Decimal(0),
            overtime_2_0=Decimal(0),
            housing_allowance=housing_allowance,
            housing_benefit=Decimal(0),
            total_gross=total_gross,
            baseline_base_pay=actual_base,
            worked_base_pay=actual_base,
        )

    def _calc_prorated_min_wage(self) -> GrossBreakdown:
        from .rates import KenyanHolidays

        # Standard monthly hours based on weekly hours
        std_monthly_hours = Decimal(self.contract.weekly_hours * 4)
        worked_hours = sum(d.hours_normal for d in self.timesheet_days)
        fraction = worked_hours / std_monthly_hours
        raw_base_pay = self.contract.base_salary * fraction

        actual_base, housing_allowance, total_gross = self._compute_housing(raw_base_pay)

        # Baseline: full-time monthly salary from contract
        baseline, _, _ = self._compute_housing(self.contract.base_salary)

        # Worked-holiday premium: an extra normal day's pay per holiday worked.
        holiday_premium = Decimal(0)
        if self.payroll_date is not None:
            worked_holiday_count = KenyanHolidays.count_worked_holidays(
                self.payroll_date.year, self.payroll_date.month, self.timesheet_days
            )
            if worked_holiday_count > 0:
                hourly_rate = self.contract.base_salary / std_monthly_hours
                daily_hours = LeaveCalculator._get_daily_hours(self.contract)
                holiday_premium = Decimal(worked_holiday_count) * daily_hours * hourly_rate
                total_gross += holiday_premium

        return GrossBreakdown(
            base_pay=actual_base,
            overtime_1_5=Decimal(0),
            overtime_2_0=Decimal(0),
            housing_allowance=housing_allowance,
            housing_benefit=Decimal(0),
            total_gross=total_gross,
            baseline_base_pay=baseline,
            worked_base_pay=actual_base,
            holiday_premium=holiday_premium,
        )


class LeaveCalculator:
    def __init__(self, timesheet_days: list[TimesheetDay], leave_stock: LeaveStock, contract: Contract):
        self.timesheet_days = timesheet_days
        self.leave_stock = leave_stock
        self.contract = contract
        self.daily_hours = self._get_daily_hours(contract)

    @staticmethod
    def _get_daily_hours(contract: Contract) -> Decimal:
        """Derive hours per work day from contract schedule."""
        if contract.weekly_hours is None:
            return Decimal("8")
        wh = Decimal(str(contract.weekly_hours))
        # 48+ hours/week implies 6-day schedule, otherwise 5-day
        work_days = Decimal("6") if contract.weekly_hours >= 48 else Decimal("5")
        return (wh / work_days).quantize(Decimal("0.01"))

    # Employment Act: 21 annual leave days/year, 7+7 sick days/year
    ANNUAL_LEAVE_ACCRUAL = Decimal("1.75")       # 21 / 12
    SICK_FULL_PAY_ACCRUAL = Decimal("0.583333")  # 7 / 12
    SICK_HALF_PAY_ACCRUAL = Decimal("0.583333")  # 7 / 12

    def allocate(self) -> LeaveAllocation:
        sick_full_used = Decimal(0)  # hours
        sick_half_used = Decimal(0)  # hours
        annual_used = Decimal(0)  # hours
        unpaid_hours = Decimal(0)

        # Stock balances are in days — add monthly accrual first
        # Consolidated leave contracts don't accrue annual leave (it's built into the schedule)
        remaining_sick_full = self.leave_stock.sick_full_pay + self.SICK_FULL_PAY_ACCRUAL
        remaining_sick_half = self.leave_stock.sick_half_pay + self.SICK_HALF_PAY_ACCRUAL
        annual_accrual = Decimal(0) if self.contract.contract_type == "consolidated_leave" else self.ANNUAL_LEAVE_ACCRUAL
        remaining_annual = self.leave_stock.annual_leave + annual_accrual

        for day in self.timesheet_days:
            if not day.absent:
                continue

            # Absent hours = daily_hours minus any hours actually worked
            absent_hours = self.daily_hours - day.hours_normal
            if absent_hours <= 0:
                continue
            absent_days = absent_hours / self.daily_hours  # fraction of day absent

            if day.sick:
                # Draw from sick leave stock
                if remaining_sick_full > 0:
                    sick_full_used += absent_hours
                    remaining_sick_full -= absent_days
                elif remaining_sick_half > 0:
                    sick_half_used += absent_hours
                    remaining_sick_half -= absent_days
                else:
                    unpaid_hours += absent_hours
            else:
                # Non-sick absence: draw from annual leave
                if remaining_annual > 0:
                    annual_used += absent_hours
                    remaining_annual -= absent_days
                else:
                    unpaid_hours += absent_hours

        # Clamp negative balances: reclassify the excess (only up to
        # what was actually allocated this period — don't fix pre-existing deficits)
        # 1. Sick full-pay overflow → half-pay sick
        if remaining_sick_full < 0:
            excess_days = min(-remaining_sick_full, sick_full_used / self.daily_hours) if self.daily_hours else Decimal(0)
            excess_hours = excess_days * self.daily_hours
            sick_full_used -= excess_hours
            sick_half_used += excess_hours
            remaining_sick_half -= excess_days
            remaining_sick_full += excess_days

        # 2. Sick half-pay overflow → unpaid
        if remaining_sick_half < 0:
            excess_days = min(-remaining_sick_half, sick_half_used / self.daily_hours) if self.daily_hours else Decimal(0)
            excess_hours = excess_days * self.daily_hours
            sick_half_used -= excess_hours
            unpaid_hours += excess_hours
            remaining_sick_half += excess_days

        # 3. Annual leave overflow → unpaid
        if remaining_annual < 0:
            excess_days = min(-remaining_annual, annual_used / self.daily_hours) if self.daily_hours else Decimal(0)
            excess_hours = excess_days * self.daily_hours
            annual_used -= excess_hours
            unpaid_hours += excess_hours
            remaining_annual += excess_days

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
            unpaid_hours=unpaid_hours,
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
        if self.contract.housing_type in ("quarters", "dorm"):
            fifteen_pct = self.gross * Decimal("0.15")
            return max(self.contract.housing_market_value, fifteen_pct)
        return Decimal(0)


class MinimumWageValidator:
    """Validates that base pay meets minimum wage requirements."""

    MIN_WAGE_NAIROBI = Decimal("16113.75")  # General labourer monthly
    HOUSING_RATE = Decimal("0.15")

    def __init__(
        self,
        base_pay: Decimal,
        contract: Contract,
        hours_worked: Decimal,
        payroll_date: date,
    ):
        self.base_pay = base_pay
        self.contract = contract
        self.hours_worked = hours_worked
        self.payroll_date = payroll_date

    def validate(self) -> tuple[bool, str | None]:
        """
        Check if earnings meet minimum wage for hours worked.
        Returns (is_valid, warning_message).

        For hourly workers: if worked >= expected full-time hours, base should >= min wage.
        For fixed monthly: base pay should >= min wage.
        """
        from .rates import KenyanHolidays

        if self.contract.contract_type == "prorated_min_wage":
            # Prorated workers are expected to be below full minimum
            return True, None

        if self.contract.contract_type == "hourly":
            # Get expected hours for full-time work this month
            weekly_hours = self.contract.weekly_hours or 45
            expected_hours = KenyanHolidays.get_expected_hours(
                self.payroll_date.year,
                self.payroll_date.month,
                weekly_hours,
            )

            # Calculate hourly minimum wage
            # Monthly min wage / expected monthly hours
            hourly_min = self.MIN_WAGE_NAIROBI / expected_hours

            # Calculate effective hourly rate from actual earnings
            if self.hours_worked > 0:
                effective_hourly = self.base_pay / self.hours_worked
            else:
                return True, None  # No hours worked

            if effective_hourly < hourly_min:
                return False, (
                    f"Effective hourly rate KES {effective_hourly:,.2f} is below "
                    f"minimum KES {hourly_min:,.2f}/hr (based on {expected_hours:.0f} "
                    f"expected hours in {self.payroll_date.strftime('%B %Y')}). "
                    f"Base pay KES {self.base_pay:,.2f} for {self.hours_worked:.0f} hours."
                )
            return True, None
        else:
            # For fixed monthly, check actual base pay
            if self.base_pay < self.MIN_WAGE_NAIROBI:
                return False, (
                    f"Base pay KES {self.base_pay:,.2f} is below Nairobi minimum wage "
                    f"KES {self.MIN_WAGE_NAIROBI:,.2f}. Is this employee part-time?"
                )
            return True, None


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
        leave_calc = LeaveCalculator(timesheet_days, leave_stock, contract)
        leave = leave_calc.allocate()

        # 2. Calculate gross
        gross_calc = GrossCalculator(contract, timesheet_days, self.payroll_date)
        gross = gross_calc.calculate()

        # 3. Apply hour adjustments (OT, leave deductions) using statutory divisor
        if contract.contract_type in ("hourly", "consolidated_leave", "fixed_monthly"):
            gross = self._apply_monthly_adjustments(gross, leave, contract, timesheet_days)

        # 4. Add housing benefit (for quarters - non-cash taxable benefit)
        housing_calc = HousingBenefitCalculator(contract, gross.total_gross)
        housing_benefit = housing_calc.calculate()
        gross = GrossBreakdown(
            base_pay=gross.base_pay,
            overtime_1_5=gross.overtime_1_5,
            overtime_2_0=gross.overtime_2_0,
            housing_allowance=gross.housing_allowance,
            housing_benefit=housing_benefit,
            total_gross=gross.total_gross,
            baseline_base_pay=gross.baseline_base_pay,
            worked_base_pay=gross.worked_base_pay,
            leave_pay=gross.leave_pay,
            leave_half_pay_deduction=gross.leave_half_pay_deduction,
            leave_unpaid_deduction=gross.leave_unpaid_deduction,
            holiday_premium=gross.holiday_premium,
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

        # 9. Validate minimum wage
        warnings = []
        hours_worked = sum(d.hours_normal for d in timesheet_days)
        min_wage_validator = MinimumWageValidator(
            gross.base_pay, contract, hours_worked, self.payroll_date
        )
        is_valid, warning = min_wage_validator.validate()
        if not is_valid and warning:
            warnings.append(warning)

        # 10. Format period string
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
            warnings=warnings if warnings else None,
        )

    def _apply_leave_pay(
        self, gross: GrossBreakdown, leave: LeaveAllocation,
        contract: Contract, timesheet_days: list[TimesheetDay],
    ) -> GrossBreakdown:
        """For hourly/consolidated_leave, add pay for leave-covered absence hours."""
        full_hours = leave.annual_leave_used + leave.sick_full_pay_used
        half_hours = leave.sick_half_pay_used

        if full_hours <= 0 and half_hours <= 0:
            return gross

        gross_calc = GrossCalculator(contract, timesheet_days, self.payroll_date)
        divisor = gross_calc._get_divisor()
        hourly_rate = contract.base_salary / divisor

        # Raw leave pay at contract hourly rate
        leave_pay_raw = (
            hourly_rate * full_hours
            + hourly_rate * Decimal("0.5") * half_hours
        )

        # Split leave pay using same housing logic as main pay
        leave_base, leave_housing, leave_total = gross_calc._compute_housing(leave_pay_raw)

        return GrossBreakdown(
            base_pay=gross.base_pay + leave_base,
            overtime_1_5=gross.overtime_1_5,
            overtime_2_0=gross.overtime_2_0,
            housing_allowance=gross.housing_allowance + leave_housing,
            housing_benefit=gross.housing_benefit,
            total_gross=gross.total_gross + leave_total,
            baseline_base_pay=gross.baseline_base_pay,
            worked_base_pay=gross.base_pay,
            leave_pay=leave_base,
        )

    def _apply_monthly_adjustments(
        self, gross: GrossBreakdown, leave: LeaveAllocation,
        contract: Contract, timesheet_days: list[TimesheetDay],
    ) -> GrossBreakdown:
        """Net all hour adjustments (OT, leave, worked-holiday premium) and
        apply the statutory hourly rate."""
        from .rates import KenyanHolidays

        hourly_rate = gross.base_pay / GrossCalculator.STATUTORY_DIVISOR

        # Gather hours
        ot_1_5_hours = sum(d.hours_ot_1_5 for d in timesheet_days)
        ot_2_0_hours = sum(d.hours_ot_2_0 for d in timesheet_days)

        # Worked-holiday premium: public holidays are paid regardless (the
        # base salary already covers them as paid days off because the
        # monthly divisor excludes holiday dates). Working one earns an
        # extra normal day's pay on top, per Employment Act practice.
        # OT hours on a holiday are tracked separately as ot_2_0 and are
        # NOT double-counted here.
        worked_holiday_count = KenyanHolidays.count_worked_holidays(
            self.payroll_date.year, self.payroll_date.month, timesheet_days
        )
        daily_hours = LeaveCalculator._get_daily_hours(contract)
        holiday_premium_hours = Decimal(worked_holiday_count) * daily_hours
        holiday_premium = holiday_premium_hours * hourly_rate

        # Net weighted hours: OT and holiday premium add, leave deducts
        net_hours = (
            ot_1_5_hours * Decimal("1.5")
            + ot_2_0_hours * Decimal("2.0")
            + holiday_premium_hours
            - leave.sick_half_pay_used * Decimal("0.5")
            - leave.unpaid_hours
        )
        net_adjustment = net_hours * hourly_rate

        # Display components (same rate, for payslip breakdown)
        ot_1_5_pay = ot_1_5_hours * Decimal("1.5") * hourly_rate
        ot_2_0_pay = ot_2_0_hours * Decimal("2.0") * hourly_rate
        half_pay_deduction = leave.sick_half_pay_used * Decimal("0.5") * hourly_rate
        unpaid_deduction = leave.unpaid_hours * hourly_rate

        # Housing scales down with deductions (OT/holiday premium don't add housing)
        total_deduction = half_pay_deduction + unpaid_deduction
        if gross.housing_allowance > 0 and gross.base_pay > 0:
            housing_ratio = (gross.base_pay - total_deduction) / gross.base_pay
            adjusted_housing = gross.housing_allowance * housing_ratio
        else:
            adjusted_housing = gross.housing_allowance

        total_gross = (
            gross.base_pay + ot_1_5_pay + ot_2_0_pay + holiday_premium
            + adjusted_housing - half_pay_deduction - unpaid_deduction
        )

        return GrossBreakdown(
            base_pay=gross.base_pay,
            overtime_1_5=ot_1_5_pay,
            overtime_2_0=ot_2_0_pay,
            housing_allowance=adjusted_housing,
            housing_benefit=gross.housing_benefit,
            total_gross=total_gross,
            baseline_base_pay=gross.baseline_base_pay,
            worked_base_pay=gross.worked_base_pay,
            leave_pay=gross.leave_pay,
            leave_half_pay_deduction=half_pay_deduction,
            leave_unpaid_deduction=unpaid_deduction,
            holiday_premium=holiday_premium,
        )
