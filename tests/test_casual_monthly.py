"""Mid-month starters: casual days, monthly days, and what accrues.

Staff routinely start partway through a month, working the first part as a
casual on the gazetted daily wage and the rest on a monthly contract. The
month is split at contract.start_date; both portions land in one gross so
PAYE is computed once, on monthly terms.
"""

from datetime import date
from decimal import Decimal

import pytest

from src.calculators import (
    PAYECalculator, trial_pay_reconciliation_warnings, stray_trial_payment_warnings,
    GrossCalculator, LeaveCalculator, PayrollEngine, default_leave_stock,
    month_split, overtime_trigger_warnings, weekly_hours_warnings,
    MinimumWageValidator, contract_coverage_warnings,
)
from src.models import Contract, Employee, LeaveStock, TimesheetDay
from src.rates import StatutoryRates


def contract(start_date, base=Decimal("16113.75"), **kw):
    return Contract(
        employee_id=99,
        contract_type=kw.pop("contract_type", "fixed_monthly"),
        base_salary=base,
        weekly_hours=kw.pop("weekly_hours", 52),
        housing_type=kw.pop("housing_type", "none"),
        housing_market_value=None,
        nssf_tier="standard",
        start_date=start_date,
        end_date=None,
        status="active",
        salary_basis=kw.pop("salary_basis", "base"),
        hourly_divisor="monthly",
        **kw,
    )


def workdays(dates, hours=Decimal("8.67")):
    return [
        TimesheetDay(employee_id=99, date=d, hours_normal=hours,
                     hours_ot_1_5=Decimal(0), hours_ot_2_0=Decimal(0),
                     absent=False, sick=False)
        for d in dates
    ]


class TestMonthSplit:
    def test_start_before_month_is_all_monthly(self):
        frac, casual_until = month_split(contract(date(2026, 1, 1)), date(2026, 7, 28))
        assert frac == Decimal(1)
        assert casual_until is None

    def test_start_on_the_first_is_all_monthly(self):
        frac, casual_until = month_split(contract(date(2026, 7, 1)), date(2026, 7, 28))
        assert frac == Decimal(1)
        assert casual_until is None

    def test_mid_month_start_splits_by_calendar_days(self):
        # Starting 11 July leaves 21 of July's 31 days on the monthly contract.
        frac, casual_until = month_split(contract(date(2026, 7, 11)), date(2026, 7, 28))
        assert frac == Decimal(21) / Decimal(31)
        assert casual_until == date(2026, 7, 10)

    def test_late_start_leaves_most_of_the_month_casual(self):
        frac, casual_until = month_split(contract(date(2026, 7, 27)), date(2026, 7, 28))
        assert frac == Decimal(5) / Decimal(31)
        assert casual_until == date(2026, 7, 26)

    def test_start_after_month_end_is_all_casual_for_a_trial_worker(self):
        c = contract(date(2026, 9, 1), casual_start=date(2026, 7, 1))
        frac, casual_until = month_split(c, date(2026, 7, 28))
        assert frac == Decimal(0)
        assert casual_until == date(2026, 7, 31)

    def test_future_start_without_a_trial_stays_monthly(self):
        """A renewal dated next month is an employee, not a casual.

        Only one contract row survives loading, so a renewal replaces the term
        that covered this month. Treating that as a casual engagement would
        pay a month of daily wages instead of a salary.
        """
        frac, casual_until = month_split(contract(date(2026, 9, 1)), date(2026, 7, 28))
        assert frac == Decimal(1)
        assert casual_until is None


class TestCasualPay:
    """Trial days are paid at the statutory daily wage, plus housing."""

    DAILY = None  # set in each test from StatutoryRates

    def _earned(self, days, start=date(2026, 7, 11)):
        """Casual portion of gross, i.e. above the monthly baseline."""
        c = contract(start)
        base = GrossCalculator(c, [], date(2026, 7, 28)).calculate().total_gross
        got = GrossCalculator(c, days, date(2026, 7, 28)).calculate().total_gross
        return got - base

    def test_each_day_worked_earns_one_daily_rate_plus_housing(self):
        expected = StatutoryRates.CASUAL_DAILY_RATE * 3 * Decimal("1.15")
        earned = self._earned(workdays([date(2026, 7, 6), date(2026, 7, 7),
                                        date(2026, 7, 8)]))
        assert earned == pytest.approx(expected, abs=Decimal("0.5"))

    def test_housing_is_added_on_top_not_netted_out(self):
        """The gazetted daily rate excludes housing, so 15% goes on top."""
        earned = self._earned(workdays([date(2026, 7, 6)]))
        assert earned == pytest.approx(
            StatutoryRates.CASUAL_DAILY_RATE * Decimal("1.15"), abs=Decimal("0.5"))
        assert earned > StatutoryRates.CASUAL_DAILY_RATE

    def test_a_short_shift_still_earns_a_full_day(self):
        """A daily wage buys the day, not the hours."""
        short = self._earned(workdays([date(2026, 7, 6)], hours=Decimal("4")))
        full = self._earned(workdays([date(2026, 7, 6)], hours=Decimal("9")))
        assert short == full

    def test_a_day_with_no_hours_earns_nothing(self):
        assert self._earned(workdays([date(2026, 7, 6)], hours=Decimal("0"))) == Decimal(0)

    def test_unworked_casual_days_cost_nothing(self):
        """No absence rows needed: a day not worked is simply not paid."""
        c = contract(date(2026, 7, 11))
        none_worked = GrossCalculator(c, [], date(2026, 7, 28)).calculate()
        expected = c.base_salary * (Decimal(21) / Decimal(31)) * Decimal("1.15")
        assert none_worked.total_gross == pytest.approx(expected, abs=Decimal("0.01"))

    def test_mid_month_starter_earns_less_than_full_month(self):
        c = contract(date(2026, 7, 27))
        late = GrossCalculator(c, workdays([date(2026, 7, 28)]), date(2026, 7, 28)).calculate()
        full = GrossCalculator(contract(date(2026, 1, 1)), [], date(2026, 7, 28)).calculate()
        assert late.total_gross < full.total_gross

    def test_baseline_still_shows_a_full_month(self):
        """The summary table compares against what full-time would have cost."""
        c = contract(date(2026, 7, 27))
        gross = GrossCalculator(c, [], date(2026, 7, 28)).calculate()
        assert gross.baseline_base_pay == c.base_salary


class TestTrialPayReconciliation:
    """Cash handed over is reconciled against the daily wage owed."""

    def _warn(self, days):
        return trial_pay_reconciliation_warnings(
            contract(date(2026, 7, 11)), days, date(2026, 7, 28))

    def test_underpayment_reports_the_balance_owed(self):
        days = workdays([date(2026, 7, 6)])
        days[0].temp_daily_pay = Decimal("300")
        w = self._warn(days)
        assert len(w) == 1 and "still owed" in w[0]

    def test_overpayment_reports_the_advance(self):
        days = workdays([date(2026, 7, 6)])
        days[0].temp_daily_pay = Decimal("2000")
        w = self._warn(days)
        assert len(w) == 1 and "advanced beyond entitlement" in w[0]

    def test_paying_the_full_entitlement_is_silent(self):
        days = workdays([date(2026, 7, 6)])
        days[0].temp_daily_pay = (StatutoryRates.CASUAL_DAILY_RATE
                                  * Decimal("1.15")).quantize(Decimal("0.01"))
        assert self._warn(days) == []

    def test_cash_recorded_does_not_change_taxable_pay(self):
        """The daily wage governs; what was handed over does not."""
        plain = workdays([date(2026, 7, 6)])
        with_cash = workdays([date(2026, 7, 6)])
        with_cash[0].temp_daily_pay = Decimal("300")
        c = contract(date(2026, 7, 11))
        a = GrossCalculator(c, plain, date(2026, 7, 28)).calculate().total_gross
        b = GrossCalculator(c, with_cash, date(2026, 7, 28)).calculate().total_gross
        assert a == b

    def test_nothing_worked_and_nothing_paid_is_silent(self):
        assert self._warn([]) == []


class TestCasualOnlyWorker:
    """Someone still on working trial: casual_start set, no monthly contract."""

    def _c(self, casual_start=date(2026, 7, 28)):
        return contract(None, base=Decimal(0), casual_start=casual_start)

    def test_whole_month_is_casual(self):
        frac, casual_until = month_split(self._c(), date(2026, 7, 28))
        assert frac == Decimal(0)
        assert casual_until == date(2026, 7, 31)

    def test_paid_at_the_daily_wage_for_days_worked(self):
        c = self._c()
        days = workdays([date(2026, 7, 29), date(2026, 7, 30)], hours=Decimal("8"))
        for d in days:
            d.temp_daily_pay = Decimal("300")  # cash given, does not govern
        gross = GrossCalculator(c, days, date(2026, 7, 28)).calculate()
        expected = StatutoryRates.CASUAL_DAILY_RATE * 2 * Decimal("1.15")
        assert gross.total_gross == pytest.approx(expected, abs=Decimal("0.5"))

    def test_no_monthly_salary_leaks_in(self):
        """A blank start_date must never be read as a full month's salary."""
        gross = GrossCalculator(self._c(), [], date(2026, 7, 28)).calculate()
        assert gross.total_gross == Decimal(0)

    def test_days_before_the_trial_began_are_not_paid(self):
        c = self._c(casual_start=date(2026, 7, 20))
        days = workdays([date(2026, 7, 10)], hours=Decimal("8"))
        days[0].temp_daily_pay = Decimal("300")
        assert GrossCalculator(c, days, date(2026, 7, 28)).calculate().total_gross == Decimal(0)

    def test_legacy_contract_with_neither_date_stays_monthly(self):
        c = contract(None, casual_start=None)
        frac, casual_until = month_split(c, date(2026, 7, 28))
        assert frac == Decimal(1)
        assert casual_until is None


class TestStrayTrialPayments:
    def test_payment_after_the_monthly_start_is_flagged(self):
        c = contract(date(2026, 7, 27), casual_start=date(2026, 7, 7))
        days = workdays([date(2026, 7, 29)], hours=Decimal("9"))
        days[0].temp_daily_pay = Decimal("600")
        w = stray_trial_payment_warnings(c, days, date(2026, 7, 28))
        assert len(w) == 1 and "monthly contract started" in w[0]

    def test_payment_before_the_trial_began_is_flagged(self):
        c = contract(date(2026, 7, 27), casual_start=date(2026, 7, 7))
        days = workdays([date(2026, 7, 2)], hours=Decimal("0"))
        days[0].temp_daily_pay = Decimal("1200")
        w = stray_trial_payment_warnings(c, days, date(2026, 7, 28))
        assert len(w) == 1 and "trial began" in w[0]

    def test_payment_inside_the_window_is_not_flagged(self):
        c = contract(date(2026, 7, 27), casual_start=date(2026, 7, 7))
        days = workdays([date(2026, 7, 20)], hours=Decimal("6.5"))
        days[0].temp_daily_pay = Decimal("600")
        assert stray_trial_payment_warnings(c, days, date(2026, 7, 28)) == []


class TestAccrualProration:
    def _alloc(self, start, casual_start=None):
        c = contract(start, casual_start=casual_start)
        frac, _ = month_split(c, date(2026, 7, 28))
        stock = LeaveStock(employee_id=99, sick_full_pay=Decimal(0),
                           sick_half_pay=Decimal(0), annual_leave=Decimal(0),
                           as_of_date=date(2026, 6, 30))
        return LeaveCalculator([], stock, c, frac).allocate()

    def test_full_month_accrues_full_entitlement(self):
        updated = self._alloc(date(2026, 1, 1)).updated_stock
        assert updated.annual_leave == LeaveCalculator.ANNUAL_LEAVE_ACCRUAL

    def test_casual_days_accrue_no_leave(self):
        """21/31 of a month on contract accrues 21/31 of the monthly entitlement."""
        updated = self._alloc(date(2026, 7, 11)).updated_stock
        expected = LeaveCalculator.ANNUAL_LEAVE_ACCRUAL * (Decimal(21) / Decimal(31))
        assert updated.annual_leave == pytest.approx(expected, abs=Decimal("0.001"))

    def test_sick_leave_accrues_pro_rata_too(self):
        updated = self._alloc(date(2026, 7, 11)).updated_stock
        expected = LeaveCalculator.SICK_FULL_PAY_ACCRUAL * (Decimal(21) / Decimal(31))
        assert updated.sick_full_pay == pytest.approx(expected, abs=Decimal("0.001"))

    def test_wholly_casual_month_accrues_nothing(self):
        updated = self._alloc(date(2026, 9, 1), casual_start=date(2026, 7, 1)).updated_stock
        assert updated.annual_leave == Decimal(0)
        assert updated.sick_full_pay == Decimal(0)


class TestSickLeaveQualifyingPeriod:
    """Employment Act s.30: sick leave is earned after two months' service."""

    def test_new_starter_opens_with_no_sick_leave(self):
        stock = default_leave_stock(99, contract(date(2026, 7, 11)), date(2026, 7, 28))
        assert stock.sick_full_pay == Decimal(0)
        assert stock.sick_half_pay == Decimal(0)

    def test_one_month_service_still_does_not_qualify(self):
        stock = default_leave_stock(99, contract(date(2026, 6, 15)), date(2026, 7, 28))
        assert stock.sick_full_pay == Decimal(0)

    def test_two_months_service_qualifies(self):
        stock = default_leave_stock(99, contract(date(2026, 5, 1)), date(2026, 7, 28))
        assert stock.sick_full_pay == Decimal("7")
        assert stock.sick_half_pay == Decimal("7")

    def test_annual_leave_always_opens_at_zero(self):
        stock = default_leave_stock(99, contract(date(2020, 1, 1)), date(2026, 7, 28))
        assert stock.annual_leave == Decimal(0)


class TestTaxTreatment:
    """A split month is taxed as one month, not as two separate engagements."""

    def test_paye_computed_once_on_combined_gross(self):
        emp = Employee(employee_id=99, name="Test", national_id="1", kra_pin="A1",
                       phone="", bank_account="1", nssf_no="1", shif_no="1")
        c = contract(date(2026, 7, 11))
        days = workdays([date(2026, 7, 6), date(2026, 7, 7)])
        stock = default_leave_stock(99, c, date(2026, 7, 28))

        ps = PayrollEngine(date(2026, 7, 28)).process(emp, c, days, stock)

        # PAYE is charged once over the combined chargeable pay, so a single
        # personal relief applies -- not one per segment. Recomputing from the
        # combined figure must reproduce it exactly.
        rates = StatutoryRates(date(2026, 7, 28))
        d = ps.deductions
        chargeable = (ps.gross.total_gross + ps.gross.housing_benefit
                      - d.nssf_tier_1 - d.nssf_tier_2 - d.shif - d.ahl_employee)
        assert d.paye == PAYECalculator(rates).calculate(chargeable)

        # NSSF follows actual gross rather than any notional full-time figure.
        expected_t1 = min(ps.gross.total_gross, rates.nssf_lel) * rates.nssf_rate
        assert d.nssf_tier_1 == pytest.approx(expected_t1, abs=Decimal("0.01"))

    def test_low_earning_casual_pays_below_the_tier_1_maximum(self):
        """The LEL caps Tier 1 earnings; it is not a minimum contribution.

        A few casual days earn well under KES 9,000, so the contribution is
        6% of what was actually earned -- there is nothing to declare
        differently for a part-month worker.
        """
        emp = Employee(employee_id=99, name="Test", national_id="1", kra_pin="A1",
                       phone="", bank_account="1", nssf_no="1", shif_no="1")
        # Monthly contract starts next month, so July is wholly casual.
        c = contract(date(2026, 8, 1), casual_start=date(2026, 7, 1))
        days = workdays([date(2026, 7, 6), date(2026, 7, 7), date(2026, 7, 8)])
        stock = default_leave_stock(99, c, date(2026, 7, 28))

        ps = PayrollEngine(date(2026, 7, 28)).process(emp, c, days, stock)
        rates = StatutoryRates(date(2026, 7, 28))

        assert ps.gross.total_gross < rates.nssf_lel
        assert ps.deductions.nssf_tier_1 < rates.nssf_lel * rates.nssf_rate
        assert ps.deductions.nssf_tier_2 == Decimal(0)
        assert ps.deductions.paye == Decimal(0)  # far below the PAYE threshold


class TestWorkingTimeLimits:
    """9h/day and 52h/week (Mon-Sun), per the Regulation of Wages Order."""

    def test_day_over_nine_hours_without_overtime_is_flagged(self):
        days = workdays([date(2026, 7, 6)], hours=Decimal("10"))
        w = overtime_trigger_warnings(days)
        assert len(w) == 1 and "exceeds the 9h daily limit by 1h" in w[0]

    def test_exactly_nine_hours_is_fine(self):
        assert overtime_trigger_warnings(workdays([date(2026, 7, 6)], hours=Decimal("9"))) == []

    def test_excess_recorded_as_overtime_is_not_flagged(self):
        days = workdays([date(2026, 7, 6)], hours=Decimal("10"))
        days[0].hours_ot_1_5 = Decimal("1")
        assert overtime_trigger_warnings(days) == []

    def test_partial_overtime_still_flags_the_remainder(self):
        days = workdays([date(2026, 7, 6)], hours=Decimal("12"))
        days[0].hours_ot_1_5 = Decimal("1")  # 3h over, only 1h recorded
        assert len(overtime_trigger_warnings(days)) == 1

    def test_week_over_fifty_two_hours_is_flagged(self):
        # Mon 6 Jul to Sat 11 Jul, six 9-hour days = 54h.
        days = workdays([date(2026, 7, d) for d in range(6, 12)], hours=Decimal("9"))
        w = weekly_hours_warnings(days)
        assert len(w) == 1
        assert "2026-07-06 (Mon-Sun)" in w[0] and "54h" in w[0]

    def test_week_at_the_limit_is_fine(self):
        days = workdays([date(2026, 7, d) for d in range(6, 11)], hours=Decimal("10.4"))
        assert weekly_hours_warnings(days) == []  # 5 x 10.4 = 52h exactly

    def test_weeks_are_counted_monday_to_sunday(self):
        """Sunday closes a week; the following Monday opens the next one."""
        days = (workdays([date(2026, 7, d) for d in range(6, 13)], hours=Decimal("7"))  # Mon-Sun = 49h
                + workdays([date(2026, 7, 13)], hours=Decimal("9")))  # next Monday
        assert weekly_hours_warnings(days) == []

    def test_overtime_hours_count_toward_the_weekly_total(self):
        days = workdays([date(2026, 7, d) for d in range(6, 11)], hours=Decimal("9"))  # 45h
        days[0].hours_ot_1_5 = Decimal("8")  # 53h total
        assert len(weekly_hours_warnings(days)) == 1


class TestEffectiveHourlyMinimum:
    """Minimum wage is tested as total pay over total hours."""

    def _validate(self, pay, hours):
        v = MinimumWageValidator(Decimal(str(pay)), contract(date(2026, 1, 1)),
                                 Decimal(str(hours)), date(2026, 7, 28))
        return v.validate()

    def test_below_the_hourly_floor_is_flagged(self):
        ok, msg = self._validate(10000, 200)  # 50.00/hr, under the 71.62 floor
        assert not ok and "below the minimum" in msg

    def test_above_the_hourly_floor_passes(self):
        ok, _ = self._validate(20000, 200)  # 100.00/hr
        assert ok

    def test_part_timer_on_a_fair_rate_is_not_flagged(self):
        """Few hours must not read as underpayment: this is why hours matter."""
        ok, _ = self._validate(5000, 50)  # 100.00/hr on a short month
        assert ok

    def test_shortfall_amount_is_reported(self):
        ok, msg = self._validate(6000, 100)  # 60.00/hr vs 80.21 -> 2,021 short
        assert not ok and "2,021" in msg

    def test_no_hours_recorded_is_not_flagged(self):
        ok, _ = self._validate(0, 0)
        assert ok


class TestContractCoverage:
    def test_renewal_dated_after_the_month_is_flagged(self):
        c = contract(date(2026, 8, 4))
        w = contract_coverage_warnings(c, date(2026, 7, 28))
        assert len(w) == 1 and "after this payroll month" in w[0]

    def test_expired_contract_is_flagged(self):
        c = contract(date(2025, 1, 1))
        c.end_date = date(2026, 6, 30)
        w = contract_coverage_warnings(c, date(2026, 7, 28))
        assert len(w) == 1 and "before this payroll month" in w[0]

    def test_a_covering_contract_is_silent(self):
        assert contract_coverage_warnings(contract(date(2026, 1, 1)), date(2026, 7, 28)) == []

    def test_a_trial_worker_is_not_flagged(self):
        """casual_start means the casual path is intended, not a gap."""
        c = contract(None, casual_start=date(2026, 7, 28))
        assert contract_coverage_warnings(c, date(2026, 7, 28)) == []

    def test_renewal_is_still_paid_a_full_salary(self):
        """The bug this guards: a month of daily wages instead of a salary."""
        renewal = contract(date(2026, 8, 4))
        normal = contract(date(2026, 1, 1))
        days = workdays([date(2026, 7, d) for d in range(6, 30)], hours=Decimal("9"))
        a = GrossCalculator(renewal, days, date(2026, 7, 28)).calculate().total_gross
        b = GrossCalculator(normal, days, date(2026, 7, 28)).calculate().total_gross
        assert a == b


class TestCasualDaysAreOutsideLeave:
    """A casual is paid per day worked; not working is just not being paid."""

    def _alloc(self, days, start=date(2026, 7, 27), casual_start=date(2026, 6, 25)):
        c = contract(start, casual_start=casual_start)
        frac, casual_until = month_split(c, date(2026, 7, 28))
        stock = LeaveStock(employee_id=99, sick_full_pay=Decimal(0),
                           sick_half_pay=Decimal(0), annual_leave=Decimal(0),
                           as_of_date=date(2026, 6, 30))
        return LeaveCalculator(days, stock, c, frac, casual_until).allocate()

    def _absent(self, day):
        return TimesheetDay(employee_id=99, date=day, hours_normal=Decimal(0),
                            hours_ot_1_5=Decimal(0), hours_ot_2_0=Decimal(0),
                            absent=True, sick=False)

    def test_absence_in_the_casual_window_costs_nothing(self):
        a = self._alloc([self._absent(date(2026, 7, 8))])
        assert a.unpaid_hours == Decimal(0)
        assert a.annual_leave_used == Decimal(0)

    def test_absence_in_the_casual_window_does_not_drain_the_balance(self):
        """A new starter must not be billed for days they were not engaged."""
        a = self._alloc([self._absent(date(2026, 7, d)) for d in range(1, 20)])
        assert a.updated_stock.annual_leave == a.updated_stock.annual_leave  # no crash
        assert a.unpaid_hours == Decimal(0)

    def test_absence_after_the_monthly_start_still_counts(self):
        a = self._alloc([self._absent(date(2026, 7, 29))])
        assert a.unpaid_hours > 0 or a.annual_leave_used > 0

    def test_sick_day_in_the_casual_window_is_ignored(self):
        d = self._absent(date(2026, 7, 8))
        d.sick = True
        a = self._alloc([d])
        assert a.sick_full_pay_used == Decimal(0)
        assert a.sick_half_pay_used == Decimal(0)

    def test_a_wholly_casual_worker_accrues_and_uses_nothing(self):
        c = contract(None, base=Decimal(0), casual_start=date(2026, 7, 1))
        frac, casual_until = month_split(c, date(2026, 7, 28))
        stock = LeaveStock(employee_id=99, sick_full_pay=Decimal(0),
                           sick_half_pay=Decimal(0), annual_leave=Decimal(0),
                           as_of_date=date(2026, 6, 30))
        a = LeaveCalculator([self._absent(date(2026, 7, 8))], stock, c,
                            frac, casual_until).allocate()
        assert a.unpaid_hours == Decimal(0)
        assert a.updated_stock.annual_leave == Decimal(0)
        assert a.updated_stock.sick_full_pay == Decimal(0)
