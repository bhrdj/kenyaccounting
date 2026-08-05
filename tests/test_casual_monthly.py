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
    PAYECalculator,
    GrossCalculator, LeaveCalculator, PayrollEngine, default_leave_stock,
    month_split,
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
        # Three casual days worked, plus the monthly period.
        days = workdays([date(2026, 7, 6), date(2026, 7, 7), date(2026, 7, 8)])
        gross = GrossCalculator(c, days, date(2026, 7, 28)).calculate()

        expected_casual = StatutoryRates.CASUAL_DAILY_RATE * 3
        expected_monthly = c.base_salary * (Decimal(21) / Decimal(31))
        expected = (expected_casual + expected_monthly) * Decimal("1.15")  # +housing
        assert gross.total_gross == pytest.approx(expected, abs=Decimal("0.01"))

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
