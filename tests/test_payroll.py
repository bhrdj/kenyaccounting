from datetime import date
from decimal import Decimal

import pytest

from src.loaders import load_contracts, load_employees, load_leave_stocks, load_timesheet
from src.calculators import (
    DeductionCalculator,
    GrossCalculator,
    HousingBenefitCalculator,
    LeaveCalculator,
    PAYECalculator,
    PayrollEngine,
)
from src.rates import StatutoryRates


@pytest.fixture
def employees():
    return {e.employee_id: e for e in load_employees("tests/fixtures/test_employees.tsv")}


@pytest.fixture
def contracts():
    return {c.employee_id: c for c in load_contracts("tests/fixtures/test_contracts.tsv")}


@pytest.fixture
def leave_stocks():
    return {l.employee_id: l for l in load_leave_stocks("tests/fixtures/test_leave_stocks.tsv")}


@pytest.fixture
def timesheet():
    entries = load_timesheet("tests/fixtures/test_timesheets/2026_02.tsv")
    ts_map = {}
    for entry in entries:
        if entry.employee_id not in ts_map:
            ts_map[entry.employee_id] = []
        ts_map[entry.employee_id].append(entry)
    return ts_map


@pytest.fixture
def rates():
    return StatutoryRates(date(2026, 2, 28))


@pytest.fixture
def engine():
    return PayrollEngine(date(2026, 2, 28))


# --- StatutoryRates Tests ---

def test_nssf_year_4_rates():
    rates = StatutoryRates(date(2026, 2, 1))
    assert rates.nssf_lel == Decimal("9000")
    assert rates.nssf_uel == Decimal("108000")
    assert rates.nssf_tier_1_max == Decimal("540")  # 9000 * 0.06
    assert rates.nssf_tier_2_max == Decimal("5940")  # (108000-9000) * 0.06


def test_nssf_year_3_rates():
    rates = StatutoryRates(date(2026, 1, 31))
    assert rates.nssf_lel == Decimal("7000")
    assert rates.nssf_uel == Decimal("72000")


# --- Gross Calculation Tests ---

def test_alice_hourly_gross(contracts, timesheet):
    """Alice: Hourly 52hr/week, full month"""
    calc = GrossCalculator(contracts[1], timesheet[1])
    gross = calc.calculate()
    # 24 days worked, 9hr days + 7hr Saturday half-days
    # Divisor = 52 * 52 / 12 = 225.33
    assert gross.total_gross == pytest.approx(Decimal("14874.23"), rel=Decimal("0.01"))
    assert gross.overtime_1_5 == Decimal(0)
    assert gross.overtime_2_0 == Decimal(0)


def test_bob_hourly_gross(contracts, timesheet):
    """Bob: Hourly 45hr/week"""
    calc = GrossCalculator(contracts[2], timesheet[2])
    gross = calc.calculate()
    # Divisor = 45 * 52 / 12 = 195
    assert gross.total_gross == pytest.approx(Decimal("23076.92"), rel=Decimal("0.01"))


def test_carol_prorated_min_wage(contracts, timesheet):
    """Carol: Prorated minimum wage, 18 days worked"""
    calc = GrossCalculator(contracts[3], timesheet[3])
    gross = calc.calculate()
    # Standard monthly hours = 45 * 4 = 180
    # Worked hours = 18 * 9 = 162
    # Fraction = 162 / 180 = 0.9
    assert gross.total_gross == pytest.approx(Decimal("14502.38"), rel=Decimal("0.01"))


def test_david_fixed_monthly(contracts, timesheet):
    """David: Fixed monthly 50,000"""
    calc = GrossCalculator(contracts[4], timesheet[4])
    gross = calc.calculate()
    assert gross.total_gross == Decimal("50000")


def test_frank_with_overtime(contracts, timesheet):
    """Frank: Hourly with overtime (12hrs @1.5x, 4hrs @2.0x)"""
    calc = GrossCalculator(contracts[6], timesheet[6])
    gross = calc.calculate()
    # Check overtime is calculated
    assert gross.overtime_1_5 > 0
    assert gross.overtime_2_0 > 0
    assert gross.total_gross == pytest.approx(Decimal("20769.23"), rel=Decimal("0.01"))


# --- Leave Allocation Tests ---

def test_grace_sick_leave_allocation(leave_stocks, timesheet):
    """Grace: 4 sick days, 7 full-pay stock -> all full-pay"""
    calc = LeaveCalculator(timesheet[7], leave_stocks[7])
    leave = calc.allocate()

    assert leave.sick_full_pay_used == 4
    assert leave.sick_half_pay_used == 0
    assert leave.unpaid_days == 0
    assert leave.updated_stock.sick_full_pay == 3  # 7 - 4


def test_henry_sick_leave_split(leave_stocks, timesheet):
    """Henry: 6 sick days, 3 full-pay stock -> 3 full + 3 half"""
    calc = LeaveCalculator(timesheet[8], leave_stocks[8])
    leave = calc.allocate()

    assert leave.sick_full_pay_used == 3
    assert leave.sick_half_pay_used == 3
    assert leave.unpaid_days == 0
    assert leave.updated_stock.sick_full_pay == 0
    assert leave.updated_stock.sick_half_pay == 4  # 7 - 3


def test_irene_annual_leave_allocation(leave_stocks, timesheet):
    """Irene: 5 non-sick absent -> 5 annual leave"""
    calc = LeaveCalculator(timesheet[9], leave_stocks[9])
    leave = calc.allocate()

    assert leave.annual_leave_used == 5
    assert leave.sick_full_pay_used == 0
    assert leave.unpaid_days == 0
    assert leave.updated_stock.annual_leave == 5  # 10 - 5


# --- Deduction Tests ---

def test_deductions_low_earner(rates, contracts):
    """Low earner: below LEL"""
    calc = DeductionCalculator(Decimal("8000"), rates, contracts[1])
    deductions = calc.calculate()

    assert deductions.nssf_tier_1 == Decimal("480")  # 8000 * 0.06
    assert deductions.nssf_tier_2 == Decimal(0)  # below LEL
    assert deductions.shif == Decimal("300")  # minimum
    assert deductions.ahl_employee == Decimal("120")  # 8000 * 0.015


def test_deductions_mid_earner(rates, contracts):
    """Mid earner: between LEL and UEL"""
    calc = DeductionCalculator(Decimal("50000"), rates, contracts[4])
    deductions = calc.calculate()

    assert deductions.nssf_tier_1 == Decimal("540")  # 9000 * 0.06
    assert deductions.nssf_tier_2 == Decimal("2460")  # (50000 - 9000) * 0.06
    assert deductions.shif == Decimal("1375")  # 50000 * 0.0275
    assert deductions.ahl_employee == Decimal("750")  # 50000 * 0.015


def test_deductions_high_earner(rates, contracts):
    """High earner: above UEL"""
    calc = DeductionCalculator(Decimal("550000"), rates, contracts[5])
    deductions = calc.calculate()

    assert deductions.nssf_tier_1 == Decimal("540")  # 9000 * 0.06
    assert deductions.nssf_tier_2 == Decimal("5940")  # (108000 - 9000) * 0.06 (capped)
    assert deductions.shif == Decimal("15125")  # 550000 * 0.0275
    assert deductions.ahl_employee == Decimal("8250")  # 550000 * 0.015


# --- PAYE Tests ---

def test_paye_below_threshold(rates):
    """Chargeable pay below personal relief threshold"""
    calc = PAYECalculator(rates)
    # Low chargeable pay results in 0 PAYE after relief
    paye = calc.calculate(Decimal("20000"))
    assert paye == Decimal(0)  # 20000 * 0.10 = 2000 < 2400 relief


def test_paye_first_band(rates):
    """Chargeable pay in first band only"""
    calc = PAYECalculator(rates)
    paye = calc.calculate(Decimal("30000"))
    # Tax: 24000 * 0.10 + 6000 * 0.25 = 2400 + 1500 = 3900
    # After relief: 3900 - 2400 = 1500
    assert paye == Decimal("1500")


def test_paye_high_earner(rates):
    """High earner spanning multiple bands"""
    calc = PAYECalculator(rates)
    # Eve's approximate chargeable pay
    chargeable = Decimal("520145")
    paye = calc.calculate(chargeable)
    # Verify it's in expected range for 32.5% bracket
    assert paye > Decimal("140000")
    assert paye < Decimal("160000")


# --- Housing Benefit Tests ---

def test_housing_benefit_quarters(contracts):
    """James: Housing quarters with market value"""
    calc = HousingBenefitCalculator(contracts[10], Decimal("60000"))
    benefit = calc.calculate()
    # Max of market value (8000) or 15% of gross (9000)
    assert benefit == Decimal("9000")


def test_housing_benefit_none(contracts):
    """Employee without housing benefit"""
    calc = HousingBenefitCalculator(contracts[1], Decimal("16000"))
    benefit = calc.calculate()
    assert benefit == Decimal(0)


# --- Full Payroll Engine Tests ---

def test_payslip_alice(engine, employees, contracts, leave_stocks, timesheet):
    """Full payslip for Alice - hourly worker"""
    payslip = engine.process(employees[1], contracts[1], timesheet[1], leave_stocks[1])

    assert payslip.employee.name == "Alice Wanjiku"
    assert payslip.period == "February 2026"
    assert payslip.gross.total_gross == pytest.approx(Decimal("14874.23"), rel=Decimal("0.01"))
    assert payslip.net_pay == pytest.approx(Decimal("13349.62"), rel=Decimal("0.01"))


def test_payslip_eve_high_earner(engine, employees, contracts, leave_stocks, timesheet):
    """Full payslip for Eve - high earner"""
    payslip = engine.process(employees[5], contracts[5], timesheet[5], leave_stocks[5])

    assert payslip.gross.total_gross == Decimal("550000")
    assert payslip.deductions.nssf_tier_1 == Decimal("540")
    assert payslip.deductions.nssf_tier_2 == Decimal("5940")
    assert payslip.deductions.paye == pytest.approx(Decimal("148930.48"), rel=Decimal("0.01"))


def test_payslip_henry_sick_leave(engine, employees, contracts, leave_stocks, timesheet):
    """Full payslip for Henry - sick leave with half pay"""
    payslip = engine.process(employees[8], contracts[8], timesheet[8], leave_stocks[8])

    # Verify leave allocation
    assert payslip.leave.sick_full_pay_used == 3
    assert payslip.leave.sick_half_pay_used == 3

    # Gross should be reduced for half-pay days
    assert payslip.gross.total_gross < Decimal("30000")
    assert payslip.gross.total_gross == pytest.approx(Decimal("27954.55"), rel=Decimal("0.01"))


def test_payslip_james_housing(engine, employees, contracts, leave_stocks, timesheet):
    """Full payslip for James - with housing quarters"""
    payslip = engine.process(employees[10], contracts[10], timesheet[10], leave_stocks[10])

    assert payslip.gross.housing_benefit == Decimal("9000")  # 15% of 60000 > 8000 market value
    # Housing benefit increases taxable income but not cash gross
    assert payslip.gross.total_gross == Decimal("60000")


# --- Batch Test for All Employees ---

def test_all_employees_payroll(engine, employees, contracts, leave_stocks, timesheet):
    """Run payroll for all 10 employees without errors"""
    payslips = []
    for emp_id in range(1, 11):
        payslip = engine.process(
            employees[emp_id],
            contracts[emp_id],
            timesheet[emp_id],
            leave_stocks[emp_id],
        )
        payslips.append(payslip)

        # Basic sanity checks
        assert payslip.gross.total_gross > 0
        assert payslip.deductions.total > 0
        assert payslip.net_pay > 0
        assert payslip.net_pay < payslip.gross.total_gross

    assert len(payslips) == 10
