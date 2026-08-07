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
    PAYECalculator, casual_underpayment_warnings, stray_trial_payment_warnings,
    GrossCalculator, LeaveCalculator, PayrollEngine, default_leave_stock,
    month_split, overtime_trigger_warnings, weekly_hours_warnings,
    MinimumWageValidator,
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

    def test_start_after_month_end_is_all_casual(self):
        frac, casual_until = month_split(contract(date(2026, 9, 1)), date(2026, 7, 28))
        assert frac == Decimal(0)
        assert casual_until == date(2026, 7, 31)


class TestCasualPay:
    def test_casual_days_paid_per_day_worked(self):
        """Days before the start date are paid only when actually worked."""
        c = contract(date(2026, 7, 11))
        # Three full casual days worked, plus the monthly period.
        days = workdays([date(2026, 7, 6), date(2026, 7, 7), date(2026, 7, 8)])
        gross = GrossCalculator(c, days, date(2026, 7, 28)).calculate()

        expected_casual = StatutoryRates.CASUAL_DAILY_RATE * 3
        expected_monthly = c.base_salary * (Decimal(21) / Decimal(31))
        expected = (expected_casual + expected_monthly) * Decimal("1.15")  # +housing
        assert gross.total_gross == pytest.approx(expected, abs=Decimal("0.5"))

    def test_full_standard_day_pays_exactly_the_daily_minimum(self):
        c = contract(date(2026, 7, 11))
        base = GrossCalculator(c, [], date(2026, 7, 28)).calculate().total_gross
        one_day = GrossCalculator(
            c, workdays([date(2026, 7, 6)]), date(2026, 7, 28)).calculate().total_gross
        earned = (one_day - base) / Decimal("1.15")  # strip the housing uplift
        assert earned == pytest.approx(StatutoryRates.CASUAL_DAILY_RATE, abs=Decimal("0.5"))

    def test_short_trial_shift_pays_in_proportion(self):
        """A half-day trial earns half a day's wage, not a whole one."""
        c = contract(date(2026, 7, 11))
        base = GrossCalculator(c, [], date(2026, 7, 28)).calculate().total_gross
        half = workdays([date(2026, 7, 6)], hours=Decimal("4.335"))  # half of 8.67
        earned = (GrossCalculator(c, half, date(2026, 7, 28)).calculate().total_gross
                  - base) / Decimal("1.15")
        assert earned == pytest.approx(StatutoryRates.CASUAL_DAILY_RATE / 2,
                                       abs=Decimal("0.5"))

    def test_longer_day_earns_proportionally_more(self):
        c = contract(date(2026, 7, 11))
        base = GrossCalculator(c, [], date(2026, 7, 28)).calculate().total_gross
        short = GrossCalculator(c, workdays([date(2026, 7, 6)], hours=Decimal("2")),
                                date(2026, 7, 28)).calculate().total_gross
        long_ = GrossCalculator(c, workdays([date(2026, 7, 6)], hours=Decimal("8")),
                                date(2026, 7, 28)).calculate().total_gross
        assert short > base
        assert long_ > short

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


class TestTrialLumpSum:
    """Trial days are settled as a round lump sum recorded per day."""

    def _earned(self, days):
        c = contract(date(2026, 7, 11))
        base = GrossCalculator(c, [], date(2026, 7, 28)).calculate().total_gross
        got = GrossCalculator(c, days, date(2026, 7, 28)).calculate().total_gross
        return (got - base) / Decimal("1.15")  # strip the housing uplift

    def test_recorded_lump_sum_is_paid_as_entered(self):
        days = workdays([date(2026, 7, 6)], hours=Decimal("6.5"))
        days[0].temp_daily_pay = Decimal("600")
        assert self._earned(days) == pytest.approx(Decimal("600"), abs=Decimal("0.5"))

    def test_lump_sums_add_up_across_days(self):
        days = workdays([date(2026, 7, 6), date(2026, 7, 7)], hours=Decimal("6.5"))
        for d in days:
            d.temp_daily_pay = Decimal("600")
        assert self._earned(days) == pytest.approx(Decimal("1200"), abs=Decimal("0.5"))

    def test_lump_sum_overrides_the_hourly_calculation(self):
        """A round figure is paid even where it differs from hours x rate."""
        days = workdays([date(2026, 7, 6)], hours=Decimal("8.67"))  # would be 775.39
        days[0].temp_daily_pay = Decimal("800")
        assert self._earned(days) == pytest.approx(Decimal("800"), abs=Decimal("0.5"))

    def test_missing_lump_sum_falls_back_to_the_gazetted_rate(self):
        """A forgotten entry must not underpay: the lawful amount applies."""
        days = workdays([date(2026, 7, 6)])  # full 8.67h day, no amount recorded
        assert self._earned(days) == pytest.approx(
            StatutoryRates.CASUAL_DAILY_RATE, abs=Decimal("0.5"))

    def test_mixed_recorded_and_missing_days(self):
        days = workdays([date(2026, 7, 6), date(2026, 7, 7)])
        days[0].temp_daily_pay = Decimal("600")  # recorded
        expected = Decimal("600") + StatutoryRates.CASUAL_DAILY_RATE  # 2nd falls back
        assert self._earned(days) == pytest.approx(expected, abs=Decimal("0.5"))


class TestCasualUnderpaymentWarning:
    def _warn(self, hours, pay):
        c = contract(date(2026, 7, 11))
        days = workdays([date(2026, 7, 6)], hours=Decimal(str(hours)))
        days[0].temp_daily_pay = Decimal(str(pay))
        return casual_underpayment_warnings(c, days, date(2026, 7, 28))

    def test_lump_sum_below_minimum_for_the_hours_is_flagged(self):
        # 600 for a full 8.67h day is 69.20/hr, under the 89.43 minimum.
        w = self._warn("8.67", 600)
        assert len(w) == 1
        assert "below the minimum" in w[0]

    def test_lump_sum_above_minimum_is_not_flagged(self):
        # 600 for 6.5h is 92.31/hr, comfortably above.
        assert self._warn("6.5", 600) == []

    def test_full_day_at_the_daily_minimum_is_not_flagged(self):
        assert self._warn("8.67", "775.39") == []

    def test_days_after_the_start_date_are_not_checked(self):
        """Once on monthly terms, the daily casual floor no longer applies."""
        c = contract(date(2026, 7, 11))
        days = workdays([date(2026, 7, 20)], hours=Decimal("8.67"))
        days[0].temp_daily_pay = Decimal("100")
        assert casual_underpayment_warnings(c, days, date(2026, 7, 28)) == []


class TestCasualOnlyWorker:
    """Someone still on working trial: casual_start set, no monthly contract."""

    def _c(self, casual_start=date(2026, 7, 28)):
        return contract(None, base=Decimal(0), casual_start=casual_start)

    def test_whole_month_is_casual(self):
        frac, casual_until = month_split(self._c(), date(2026, 7, 28))
        assert frac == Decimal(0)
        assert casual_until == date(2026, 7, 31)

    def test_paid_only_from_recorded_trial_amounts(self):
        c = self._c()
        days = workdays([date(2026, 7, 29), date(2026, 7, 30)], hours=Decimal("8"))
        for d in days:
            d.temp_daily_pay = Decimal("300")
        gross = GrossCalculator(c, days, date(2026, 7, 28)).calculate()
        assert gross.total_gross == pytest.approx(Decimal("600") * Decimal("1.15"),
                                                  abs=Decimal("0.5"))

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
    def _alloc(self, start):
        c = contract(start)
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
        updated = self._alloc(date(2026, 9, 1)).updated_stock
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
        c = contract(date(2026, 8, 1))
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
        ok, msg = self._validate(10000, 200)  # 50.00/hr
        assert not ok and "below the minimum" in msg

    def test_above_the_hourly_floor_passes(self):
        ok, _ = self._validate(20000, 200)  # 100.00/hr
        assert ok

    def test_part_timer_on_a_fair_rate_is_not_flagged(self):
        """Few hours must not read as underpayment: this is why hours matter."""
        ok, _ = self._validate(5000, 50)  # 100.00/hr on a short month
        assert ok

    def test_shortfall_amount_is_reported(self):
        ok, msg = self._validate(7000, 100)  # 70/hr vs 77.54 -> 754 short
        assert not ok and "754" in msg

    def test_no_hours_recorded_is_not_flagged(self):
        ok, _ = self._validate(0, 0)
        assert ok
