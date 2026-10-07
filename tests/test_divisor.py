"""The monthly hours a salary pays for, which prices a missed or extra hour.

The statutory 225.33 assumes a 52-hour week; someone contracted for fewer
hours has fewer hours in their month, so each one is worth more.
"""

from decimal import Decimal

from src.calculators import GrossCalculator

from tests.test_casual_monthly import contract


def test_52_hour_week_is_the_statutory_divisor():
    c = contract(None, weekly_hours=52)
    assert GrossCalculator.statutory_divisor_for(c) == GrossCalculator.STATUTORY_DIVISOR


def test_45_hour_week_scales_down():
    c = contract(None, weekly_hours=45)
    assert GrossCalculator.statutory_divisor_for(c).quantize(Decimal("0.01")) == Decimal("195.00")


def test_consolidated_leave_target_is_three_contract_weeks():
    c = contract(None, weekly_hours=52, contract_type="consolidated_leave")
    assert GrossCalculator.statutory_divisor_for(c) == Decimal(156)


def test_missing_weekly_hours_falls_back_to_52():
    c = contract(None, weekly_hours=None)
    assert GrossCalculator.statutory_divisor_for(c) == GrossCalculator.STATUTORY_DIVISOR
