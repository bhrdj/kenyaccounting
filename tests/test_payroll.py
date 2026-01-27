"""
Payroll calculation tests for Kenya 2026.

This module contains two categories of tests:

1. EXTERNALLY VALIDATED EXAMPLES (Section 1)
   Third-party verified calculations from Net Pay Kenya and HR Fleek (February 2026).
   These use Year 4 NSSF rates and serve as our primary validation against
   industry-accepted figures. Source: https://netpay.co.ke, https://hrfleek.co.ke

2. SYNTHETIC TEST SCENARIOS (Section 2)
   Artificial test cases designed to exercise specific edge cases and code paths.
   These are NOT externally validated - expected values are calculated based on
   our understanding of the regulations.
"""
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
from src.models import Contract
from src.rates import StatutoryRates


# =============================================================================
# SECTION 1: EXTERNALLY VALIDATED EXAMPLES
# =============================================================================
#
# Source: Net Pay Kenya, HR Fleek (2026 compliance documentation)
# These examples use Year 4 NSSF rates (effective February 2026)
#
# VALIDATION STATUS: ✓ EXTERNALLY VALIDATED
# These figures match third-party payroll calculators and published examples.
# =============================================================================

class TestExternallyValidatedExamples:
    """
    Tests based on third-party published payroll examples for Kenya 2026.

    VALIDATION STATUS: ✓ EXTERNALLY VALIDATED
    Source: Net Pay Kenya, HR Fleek (February 2026 publications)

    These are authoritative reference calculations that our system must match.
    All figures have been verified against external payroll calculators.

    Year 4 NSSF Parameters (Feb 2026+):
    - LEL (Tier I): KES 9,000
    - UEL (Tier II): KES 108,000
    - Max NSSF: KES 6,480 (employee) = 540 + 5,940
    """

    @pytest.fixture
    def rates(self):
        """Year 4 NSSF rates (February 2026)."""
        return StatutoryRates(date(2026, 2, 28))

    @pytest.fixture
    def base_contract(self):
        """Base contract template for fixed monthly employees."""
        return Contract(
            employee_id=0,
            contract_type="fixed_monthly",
            base_salary=Decimal("0"),
            weekly_hours=None,
            housing_type="none",
            housing_market_value=None,
            nssf_tier="standard",
            start_date=date(2026, 1, 1),
            end_date=None,
            status="active",
        )

    # -------------------------------------------------------------------------
    # EXTERNALLY VALIDATED: Entry Level (KES 30,000)
    # Source: Net Pay Kenya, HR Fleek
    # -------------------------------------------------------------------------
    ENTRY_LEVEL = {
        "gross": Decimal("30000"),
        "nssf": Decimal("1800"),      # 6% of 30,000 (below UEL)
        "shif": Decimal("825"),       # 2.75% of 30,000
        "ahl": Decimal("450"),        # 1.5% of 30,000
        "taxable": Decimal("26925"),  # 30,000 - 1,800 - 825 - 450
        "paye": Decimal("732"),       # Calculated on taxable, less relief
        "net": Decimal("26193"),      # 30,000 - 1,800 - 825 - 450 - 732
    }

    # -------------------------------------------------------------------------
    # EXTERNALLY VALIDATED: Senior Executive (KES 200,000)
    # Source: Net Pay Kenya, HR Fleek
    # -------------------------------------------------------------------------
    SENIOR_EXEC = {
        "gross": Decimal("200000"),
        "nssf": Decimal("6480"),       # Max capped (540 + 5,940)
        "shif": Decimal("5500"),       # 2.75% of 200,000
        "ahl": Decimal("3000"),        # 1.5% of 200,000
        "taxable": Decimal("185020"),  # 200,000 - 6,480 - 5,500 - 3,000
        "paye": Decimal("47889"),      # Calculated on taxable, less relief
        "net": Decimal("137131"),      # 200,000 - 6,480 - 5,500 - 3,000 - 47,889
    }

    # -------------------------------------------------------------------------
    # EXTERNALLY VALIDATED: C-Suite Level (KES 500,000)
    # Source: Net Pay Kenya, HR Fleek
    # -------------------------------------------------------------------------
    C_SUITE = {
        "gross": Decimal("500000"),
        "nssf": Decimal("6480"),        # Max capped (540 + 5,940)
        "shif": Decimal("13750"),       # 2.75% of 500,000
        "ahl": Decimal("7500"),         # 1.5% of 500,000
        "taxable": Decimal("472270"),   # 500,000 - 6,480 - 13,750 - 7,500
        "paye": Decimal("134064"),      # Calculated on taxable, less relief
        "net": Decimal("338206"),       # 500,000 - 6,480 - 13,750 - 7,500 - 134,064
    }

    VALIDATED_EXAMPLES = [
        pytest.param(ENTRY_LEVEL, id="entry_level_30k_VALIDATED"),
        pytest.param(SENIOR_EXEC, id="senior_executive_200k_VALIDATED"),
        pytest.param(C_SUITE, id="c_suite_500k_VALIDATED"),
    ]

    @pytest.mark.parametrize("example", VALIDATED_EXAMPLES)
    def test_nssf_calculation(self, rates, base_contract, example):
        """[EXTERNALLY VALIDATED] NSSF deduction matches published example."""
        contract = Contract(
            employee_id=base_contract.employee_id,
            contract_type=base_contract.contract_type,
            base_salary=example["gross"],
            weekly_hours=base_contract.weekly_hours,
            housing_type=base_contract.housing_type,
            housing_market_value=base_contract.housing_market_value,
            nssf_tier=base_contract.nssf_tier,
            start_date=base_contract.start_date,
            end_date=base_contract.end_date,
            status=base_contract.status,
        )
        calc = DeductionCalculator(example["gross"], rates, contract)
        deductions = calc.calculate()
        total_nssf = deductions.nssf_tier_1 + deductions.nssf_tier_2
        assert total_nssf == example["nssf"]

    @pytest.mark.parametrize("example", VALIDATED_EXAMPLES)
    def test_shif_calculation(self, rates, base_contract, example):
        """[EXTERNALLY VALIDATED] SHIF deduction matches published example."""
        contract = Contract(
            employee_id=base_contract.employee_id,
            contract_type=base_contract.contract_type,
            base_salary=example["gross"],
            weekly_hours=base_contract.weekly_hours,
            housing_type=base_contract.housing_type,
            housing_market_value=base_contract.housing_market_value,
            nssf_tier=base_contract.nssf_tier,
            start_date=base_contract.start_date,
            end_date=base_contract.end_date,
            status=base_contract.status,
        )
        calc = DeductionCalculator(example["gross"], rates, contract)
        deductions = calc.calculate()
        assert deductions.shif == example["shif"]

    @pytest.mark.parametrize("example", VALIDATED_EXAMPLES)
    def test_ahl_calculation(self, rates, base_contract, example):
        """[EXTERNALLY VALIDATED] AHL deduction matches published example."""
        contract = Contract(
            employee_id=base_contract.employee_id,
            contract_type=base_contract.contract_type,
            base_salary=example["gross"],
            weekly_hours=base_contract.weekly_hours,
            housing_type=base_contract.housing_type,
            housing_market_value=base_contract.housing_market_value,
            nssf_tier=base_contract.nssf_tier,
            start_date=base_contract.start_date,
            end_date=base_contract.end_date,
            status=base_contract.status,
        )
        calc = DeductionCalculator(example["gross"], rates, contract)
        deductions = calc.calculate()
        assert deductions.ahl_employee == example["ahl"]

    @pytest.mark.parametrize("example", VALIDATED_EXAMPLES)
    def test_taxable_pay(self, rates, base_contract, example):
        """[EXTERNALLY VALIDATED] Taxable pay matches published example."""
        contract = Contract(
            employee_id=base_contract.employee_id,
            contract_type=base_contract.contract_type,
            base_salary=example["gross"],
            weekly_hours=base_contract.weekly_hours,
            housing_type=base_contract.housing_type,
            housing_market_value=base_contract.housing_market_value,
            nssf_tier=base_contract.nssf_tier,
            start_date=base_contract.start_date,
            end_date=base_contract.end_date,
            status=base_contract.status,
        )
        calc = DeductionCalculator(example["gross"], rates, contract)
        deductions = calc.calculate()
        total_nssf = deductions.nssf_tier_1 + deductions.nssf_tier_2
        taxable = example["gross"] - total_nssf - deductions.shif - deductions.ahl_employee
        assert taxable == example["taxable"]

    @pytest.mark.parametrize("example", VALIDATED_EXAMPLES)
    def test_paye_calculation(self, rates, example):
        """[EXTERNALLY VALIDATED] PAYE matches published example."""
        paye_calc = PAYECalculator(rates)
        paye = paye_calc.calculate(example["taxable"])
        # Allow 1 KES tolerance for rounding differences
        assert abs(paye - example["paye"]) <= 1

    @pytest.mark.parametrize("example", VALIDATED_EXAMPLES)
    def test_net_pay(self, rates, base_contract, example):
        """[EXTERNALLY VALIDATED] Net pay matches published example."""
        contract = Contract(
            employee_id=base_contract.employee_id,
            contract_type=base_contract.contract_type,
            base_salary=example["gross"],
            weekly_hours=base_contract.weekly_hours,
            housing_type=base_contract.housing_type,
            housing_market_value=base_contract.housing_market_value,
            nssf_tier=base_contract.nssf_tier,
            start_date=base_contract.start_date,
            end_date=base_contract.end_date,
            status=base_contract.status,
        )
        ded_calc = DeductionCalculator(example["gross"], rates, contract)
        deductions = ded_calc.calculate()
        paye_calc = PAYECalculator(rates)
        paye = paye_calc.calculate(example["taxable"])
        total_nssf = deductions.nssf_tier_1 + deductions.nssf_tier_2
        net = example["gross"] - total_nssf - deductions.shif - deductions.ahl_employee - paye
        # Allow 1 KES tolerance for rounding differences
        assert abs(net - example["net"]) <= 1


# =============================================================================
# SECTION 2: SYNTHETIC TEST SCENARIOS
# =============================================================================
#
# VALIDATION STATUS: NOT EXTERNALLY VALIDATED
# These tests exercise specific edge cases. Expected values are calculated
# based on our understanding of Kenya 2026 regulations.
# =============================================================================

# --- Fixtures for loading test data ---

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
def timesheet_feb():
    entries = load_timesheet("tests/fixtures/test_timesheets/2026_02.tsv")
    ts_map = {}
    for entry in entries:
        if entry.employee_id not in ts_map:
            ts_map[entry.employee_id] = []
        ts_map[entry.employee_id].append(entry)
    return ts_map


@pytest.fixture
def rates_year3():
    """Year 3 NSSF rates (January 2026)."""
    return StatutoryRates(date(2026, 1, 31))


@pytest.fixture
def rates_year4():
    """Year 4 NSSF rates (February 2026)."""
    return StatutoryRates(date(2026, 2, 28))


@pytest.fixture
def engine():
    return PayrollEngine(date(2026, 2, 28))


# =============================================================================
# Synthetic: NSSF Rate Transition Tests
# =============================================================================

class TestNSSFRateTransition:
    """
    [SYNTHETIC] Test NSSF rate changes between Year 3 and Year 4.

    NOT EXTERNALLY VALIDATED - based on NSSF Act 2013 schedule.
    """

    def test_year3_rates_january_2026(self, rates_year3):
        """Year 3 rates apply through January 2026."""
        assert rates_year3.nssf_lel == Decimal("8000")
        assert rates_year3.nssf_uel == Decimal("72000")

    def test_year4_rates_february_2026(self, rates_year4):
        """Year 4 rates apply from February 2026."""
        assert rates_year4.nssf_lel == Decimal("9000")
        assert rates_year4.nssf_uel == Decimal("108000")
        assert rates_year4.nssf_tier_1_max == Decimal("540")   # 9000 * 0.06
        assert rates_year4.nssf_tier_2_max == Decimal("5940")  # (108000-9000) * 0.06


# =============================================================================
# Synthetic: Deduction Calculation Tests
# =============================================================================

class TestDeductionCalculations:
    """
    [SYNTHETIC] Test statutory deduction calculations at different income levels.

    NOT EXTERNALLY VALIDATED - expected values based on regulatory formulas.
    """

    def test_below_lel(self, rates_year4, contracts):
        """Employee earning below LEL (KES 9,000)."""
        gross = Decimal("8000")
        calc = DeductionCalculator(gross, rates_year4, contracts[1])
        deductions = calc.calculate()

        assert deductions.nssf_tier_1 == Decimal("480")   # 8000 * 0.06
        assert deductions.nssf_tier_2 == Decimal(0)       # below LEL
        assert deductions.shif == Decimal("300")          # minimum floor
        assert deductions.ahl_employee == Decimal("120")  # 8000 * 0.015

    def test_between_lel_and_uel(self, rates_year4, contracts):
        """Employee earning between LEL and UEL."""
        gross = Decimal("50000")
        calc = DeductionCalculator(gross, rates_year4, contracts[4])
        deductions = calc.calculate()

        assert deductions.nssf_tier_1 == Decimal("540")    # 9000 * 0.06
        assert deductions.nssf_tier_2 == Decimal("2460")   # (50000-9000) * 0.06
        assert deductions.shif == Decimal("1375")          # 50000 * 0.0275
        assert deductions.ahl_employee == Decimal("750")   # 50000 * 0.015

    def test_above_uel(self, rates_year4, contracts):
        """Employee earning above UEL (capped NSSF)."""
        gross = Decimal("550000")
        calc = DeductionCalculator(gross, rates_year4, contracts[5])
        deductions = calc.calculate()

        assert deductions.nssf_tier_1 == Decimal("540")     # capped at max
        assert deductions.nssf_tier_2 == Decimal("5940")    # capped at max
        assert deductions.shif == Decimal("15125")          # 550000 * 0.0275
        assert deductions.ahl_employee == Decimal("8250")   # 550000 * 0.015


# =============================================================================
# Synthetic: PAYE Calculation Tests
# =============================================================================

class TestPAYECalculations:
    """
    [SYNTHETIC] Test PAYE tax band calculations.

    NOT EXTERNALLY VALIDATED - expected values based on 2026 tax bands.

    2026 PAYE Bands:
    - 0 - 24,000: 10%
    - 24,001 - 32,333: 25%
    - 32,334 - 500,000: 30%
    - 500,001 - 800,000: 32.5%
    - 800,001+: 35%
    Personal Relief: KES 2,400/month
    """

    def test_paye_below_relief_threshold(self, rates_year4):
        """Low chargeable pay results in zero PAYE after relief."""
        calc = PAYECalculator(rates_year4)
        # 20000 * 0.10 = 2000 < 2400 relief
        paye = calc.calculate(Decimal("20000"))
        assert paye == Decimal(0)

    def test_paye_first_band_only(self, rates_year4):
        """Chargeable pay taxed entirely in first band."""
        calc = PAYECalculator(rates_year4)
        # Tax: 24000 * 0.10 = 2400, after relief = 0
        paye = calc.calculate(Decimal("24000"))
        assert paye == Decimal(0)

    def test_paye_spans_two_bands(self, rates_year4):
        """Chargeable pay spans first and second bands."""
        calc = PAYECalculator(rates_year4)
        chargeable = Decimal("30000")
        # Band 1: 24000 * 0.10 = 2400
        # Band 2: 6000 * 0.25 = 1500
        # Total: 3900 - 2400 relief = 1500
        paye = calc.calculate(chargeable)
        assert paye == Decimal("1500")

    def test_paye_high_earner(self, rates_year4):
        """High earner spanning multiple bands."""
        calc = PAYECalculator(rates_year4)
        chargeable = Decimal("520000")
        # Band 1: 24000 * 0.10 = 2400
        # Band 2: 8333 * 0.25 = 2083.25
        # Band 3: 467667 * 0.30 = 140300.10
        # Band 4: 20000 * 0.325 = 6500
        # Total gross: 151283.35 - 2400 relief
        paye = calc.calculate(chargeable)
        assert paye > Decimal("140000")
        assert paye < Decimal("160000")


# =============================================================================
# Synthetic: Gross Calculation from Timesheet Tests
# =============================================================================

class TestGrossFromTimesheet:
    """
    [SYNTHETIC] Test gross pay calculation from timesheet entries.

    NOT EXTERNALLY VALIDATED - tests timesheet → gross conversion logic.
    """

    def test_hourly_full_month_52hr_week(self, contracts, timesheet_feb):
        """Hourly worker: 52hr/week, full month worked."""
        # Alice: employee_id=1, base_salary=16113.75, weekly_hours=52
        calc = GrossCalculator(contracts[1], timesheet_feb[1], date(2026, 2, 28))
        gross = calc.calculate()
        # Full month at base rate
        assert gross.base_pay == pytest.approx(Decimal("16113.75"), rel=Decimal("0.01"))

    def test_hourly_full_month_45hr_week(self, contracts, timesheet_feb):
        """Hourly worker: 45hr/week, full month worked."""
        # Bob: employee_id=2, base_salary=25000, weekly_hours=45
        calc = GrossCalculator(contracts[2], timesheet_feb[2], date(2026, 2, 28))
        gross = calc.calculate()
        assert gross.base_pay == pytest.approx(Decimal("25000"), rel=Decimal("0.01"))

    def test_prorated_min_wage(self, contracts, timesheet_feb):
        """Prorated minimum wage: 18 days worked out of 20."""
        # Carol: employee_id=3, prorated_min_wage, 18 days in timesheet
        calc = GrossCalculator(contracts[3], timesheet_feb[3], date(2026, 2, 28))
        gross = calc.calculate()
        # 18/20 = 0.9 of base
        expected = Decimal("16113.75") * Decimal("0.9")
        assert gross.base_pay == pytest.approx(expected, rel=Decimal("0.01"))

    def test_fixed_monthly_full_month(self, contracts, timesheet_feb):
        """Fixed monthly salary: full month worked."""
        # David: employee_id=4, fixed_monthly=50000
        calc = GrossCalculator(contracts[4], timesheet_feb[4], date(2026, 2, 28))
        gross = calc.calculate()
        assert gross.base_pay == Decimal("50000")

    def test_hourly_with_overtime(self, contracts, timesheet_feb):
        """Hourly worker with overtime hours recorded."""
        # Frank: employee_id=6, has overtime in timesheet
        calc = GrossCalculator(contracts[6], timesheet_feb[6], date(2026, 2, 28))
        gross = calc.calculate()
        assert gross.overtime_1_5 > 0  # 12 hours at 1.5x
        assert gross.overtime_2_0 > 0  # 4 hours at 2.0x


# =============================================================================
# Synthetic: Leave Allocation Tests
# =============================================================================

class TestLeaveAllocation:
    """
    [SYNTHETIC] Test sick leave and annual leave allocation from stocks.

    NOT EXTERNALLY VALIDATED - tests leave allocation logic per Employment Act.
    """

    def test_sick_leave_full_pay_sufficient(self, leave_stocks, timesheet_feb):
        """Sick days covered by full-pay stock."""
        # Grace (7): 4 sick days, 7 full-pay stock → all full-pay
        calc = LeaveCalculator(timesheet_feb[7], leave_stocks[7])
        leave = calc.allocate()

        assert leave.sick_full_pay_used == 4
        assert leave.sick_half_pay_used == 0
        assert leave.unpaid_days == 0
        assert leave.updated_stock.sick_full_pay == 3  # 7 - 4

    def test_sick_leave_split_full_and_half(self, leave_stocks, timesheet_feb):
        """Sick days split between full-pay and half-pay stocks."""
        # Henry (8): 6 sick days, 3 full-pay stock → 3 full + 3 half
        calc = LeaveCalculator(timesheet_feb[8], leave_stocks[8])
        leave = calc.allocate()

        assert leave.sick_full_pay_used == 3
        assert leave.sick_half_pay_used == 3
        assert leave.unpaid_days == 0
        assert leave.updated_stock.sick_full_pay == 0
        assert leave.updated_stock.sick_half_pay == 4  # 7 - 3

    def test_annual_leave_for_non_sick_absence(self, leave_stocks, timesheet_feb):
        """Non-sick absence draws from annual leave stock."""
        # Irene (9): 5 non-sick absent, 10 annual leave stock
        calc = LeaveCalculator(timesheet_feb[9], leave_stocks[9])
        leave = calc.allocate()

        assert leave.annual_leave_used == 5
        assert leave.sick_full_pay_used == 0
        assert leave.unpaid_days == 0
        assert leave.updated_stock.annual_leave == 5  # 10 - 5


# =============================================================================
# Synthetic: Housing Benefit Tests
# =============================================================================

class TestHousingBenefit:
    """
    [SYNTHETIC] Test housing benefit calculations.

    NOT EXTERNALLY VALIDATED - tests 15% rule and market value comparison.
    """

    def test_housing_quarters_15pct_exceeds_market(self, contracts):
        """Housing benefit: 15% of gross exceeds market value."""
        # James (10): quarters with market_value=8000, gross=60000
        calc = HousingBenefitCalculator(contracts[10], Decimal("60000"))
        benefit = calc.calculate()
        # 15% of 60000 = 9000 > 8000 market value
        assert benefit == Decimal("9000")

    def test_no_housing_benefit(self, contracts):
        """No housing benefit when housing_type is none."""
        # Alice (1): housing_type=none
        calc = HousingBenefitCalculator(contracts[1], Decimal("16000"))
        benefit = calc.calculate()
        assert benefit == Decimal(0)


# =============================================================================
# Synthetic: Full Payroll Engine Integration Tests
# =============================================================================

class TestPayrollEngineIntegration:
    """
    [SYNTHETIC] End-to-end payroll processing tests.

    NOT EXTERNALLY VALIDATED - tests full calculation pipeline.
    """

    def test_payslip_hourly_worker(self, engine, employees, contracts, leave_stocks, timesheet_feb):
        """Full payslip for hourly worker."""
        # Alice: employee_id=1
        payslip = engine.process(employees[1], contracts[1], timesheet_feb[1], leave_stocks[1])

        assert payslip.employee.name == "Alice Wanjiku"
        assert payslip.period == "February 2026"
        assert payslip.gross.base_pay == pytest.approx(Decimal("16113.75"), rel=Decimal("0.01"))
        assert payslip.net_pay > 0
        assert payslip.net_pay < payslip.gross.total_gross

    def test_payslip_high_earner(self, engine, employees, contracts, leave_stocks, timesheet_feb):
        """Full payslip for high earner."""
        # Eve: employee_id=5, base=550000
        payslip = engine.process(employees[5], contracts[5], timesheet_feb[5], leave_stocks[5])

        assert payslip.gross.base_pay == Decimal("550000")
        assert payslip.deductions.nssf_tier_1 == Decimal("540")
        assert payslip.deductions.nssf_tier_2 == Decimal("5940")
        # High PAYE expected (32.5% bracket)
        assert payslip.deductions.paye > Decimal("150000")

    def test_payslip_with_sick_leave(self, engine, employees, contracts, leave_stocks, timesheet_feb):
        """Full payslip with sick leave affecting pay."""
        # Henry (8): 6 sick days, 3 full-pay + 3 half-pay
        payslip = engine.process(employees[8], contracts[8], timesheet_feb[8], leave_stocks[8])

        assert payslip.leave.sick_full_pay_used == 3
        assert payslip.leave.sick_half_pay_used == 3
        # Base reduced for half-pay days
        assert payslip.gross.base_pay < Decimal("30000")

    def test_payslip_with_housing_benefit(self, engine, employees, contracts, leave_stocks, timesheet_feb):
        """Full payslip with housing quarters benefit."""
        # James (10): housing quarters
        payslip = engine.process(employees[10], contracts[10], timesheet_feb[10], leave_stocks[10])

        assert payslip.gross.housing_benefit == Decimal("9000")
        # Housing benefit increases taxable income but not cash gross
        assert payslip.gross.total_gross == Decimal("60000")

    def test_batch_all_employees(self, engine, employees, contracts, leave_stocks, timesheet_feb):
        """Process payroll for all 10 employees without errors."""
        payslips = []
        for emp_id in range(1, 11):
            payslip = engine.process(
                employees[emp_id],
                contracts[emp_id],
                timesheet_feb[emp_id],
                leave_stocks[emp_id],
            )
            payslips.append(payslip)

            # Basic sanity checks
            assert payslip.gross.total_gross > 0
            assert payslip.deductions.total > 0
            assert payslip.net_pay > 0
            assert payslip.net_pay < payslip.gross.total_gross

        assert len(payslips) == 10
