"""Contracts that end inside the payroll month.

A resignation, a death or an unrenewed term ends monthly pay partway through
a month. Pay runs to the end date on the same calendar-day basis as a
mid-month start, and the days after it are neither paid nor absences.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal

from src.calculators import (
    LeaveCalculator, PayrollEngine, contract_coverage_warnings, month_split,
    monthly_period_end, monthly_period_start,
)
from src.models import Employee, LeaveStock, TimesheetDay

from tests.test_casual_monthly import contract, workdays

SEPT = date(2026, 9, 28)


def ending(end_date, start_date=date(2026, 1, 5), market_value=None, **kw):
    return replace(contract(start_date, **kw), end_date=end_date,
                   housing_market_value=market_value)


def absent(day):
    return TimesheetDay(employee_id=99, date=day, hours_normal=Decimal(0),
                        hours_ot_1_5=Decimal(0), hours_ot_2_0=Decimal(0),
                        absent=True, sick=False)


def stock():
    return LeaveStock(employee_id=99, sick_full_pay=Decimal(5),
                      sick_half_pay=Decimal(5), annual_leave=Decimal(5),
                      as_of_date=date(2026, 8, 31))


class TestMonthSplitWithEndDate:
    def test_end_inside_month_prorates_by_calendar_days(self):
        frac, casual_until = month_split(ending(date(2026, 9, 4)), SEPT)
        assert frac == Decimal(4) / Decimal(30)
        assert casual_until is None

    def test_start_and_end_in_same_month(self):
        frac, casual_until = month_split(
            ending(date(2026, 9, 20), start_date=date(2026, 9, 7)), SEPT)
        assert frac == Decimal(14) / Decimal(30)
        assert casual_until == date(2026, 9, 6)

    def test_end_on_last_day_is_a_full_month(self):
        frac, _ = month_split(ending(date(2026, 9, 30)), SEPT)
        assert frac == Decimal(1)

    def test_end_before_month_is_not_an_ending(self):
        """By the sheet's convention that is a renewal not yet entered."""
        frac, _ = month_split(ending(date(2026, 8, 15)), SEPT)
        assert frac == Decimal(1)
        assert monthly_period_end(ending(date(2026, 8, 15)), SEPT) is None

    def test_end_before_start_pays_nothing_monthly(self):
        frac, _ = month_split(
            ending(date(2026, 9, 5), start_date=date(2026, 9, 10)), SEPT)
        assert frac == Decimal(0)

    def test_no_end_date_unchanged(self):
        frac, _ = month_split(ending(None), SEPT)
        assert frac == Decimal(1)


class TestLeaveAfterEnd:
    def _alloc(self, c, days):
        frac, _ = month_split(c, SEPT)
        return LeaveCalculator(
            days, stock(), c, frac, monthly_period_start(c, SEPT),
            all_monthly=False, monthly_until=monthly_period_end(c, SEPT),
        ).allocate()

    def test_days_after_end_are_not_absences(self):
        c = ending(date(2026, 9, 4))
        a = self._alloc(c, [absent(date(2026, 9, d)) for d in range(5, 31)])
        assert a.unpaid_hours == Decimal(0)
        assert a.annual_leave_used == Decimal(0)

    def test_absence_before_end_still_counts(self):
        c = ending(date(2026, 9, 4))
        a = self._alloc(c, [absent(date(2026, 9, 2))])
        assert a.annual_leave_used > 0


class TestEndingPayslip:
    def _consolidated(self, end_date, worked_days):
        c = ending(end_date, base=Decimal(24500),
                   contract_type="consolidated_leave", housing_type="dorm",
                   market_value=Decimal(1800))
        days = (workdays([date(2026, 9, d) for d in worked_days], hours=Decimal(9))
                + [absent(date(2026, 9, d)) for d in range(1, 31)
                   if d not in worked_days])
        emp = Employee(employee_id=99, name="T", national_id="1", kra_pin="A1",
                       phone="", bank_account="")
        return PayrollEngine(SEPT).process(emp, c, days, stock())

    def test_consolidated_leave_part_month_paid_against_target_hours(self):
        """The Sept 2026 case: a caregiver on 3 weeks on / 1 off died on the
        4th, having worked 36h of the month's 52h x 3 = 156h target."""
        ps = self._consolidated(date(2026, 9, 4), list(range(1, 5)))
        assert ps.gross.total_gross.quantize(Decimal("0.01")) == Decimal("5653.85")
        assert ps.leave.unpaid_hours == Decimal(0)
        assert any("Contract ends 2026-09-04" in w for w in ps.warnings)

    def test_consolidated_leave_part_month_capped_at_full_salary(self):
        ps = self._consolidated(date(2026, 9, 29),
                                [d for d in range(1, 30) if d % 7 != 6])
        assert ps.gross.total_gross == Decimal(24500)

    def test_consolidated_leave_full_month_ignores_off_week(self):
        ps = self._consolidated(None, list(range(1, 19)))
        assert ps.gross.total_gross == Decimal(24500)

    def test_warning_names_the_end_date(self):
        w = contract_coverage_warnings(ending(date(2026, 9, 4)), SEPT)
        assert len(w) == 1 and "2026-09-04" in w[0]
