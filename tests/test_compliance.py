from datetime import date
from decimal import Decimal
import pytest
from src.compliance_2026 import (
    get_nssf_rates,
    calculate_shif,
    calculate_ahl,
    calculate_paye,
    PERSONAL_RELIEF
)

# --- NSSF TESTS ---
def test_nssf_year_3_limits():
    """Verify Jan 2026 uses Year 3 rates (LEL 7k, UEL 72k)."""
    rates = get_nssf_rates(date(2026, 1, 31))
    assert rates['LEL'] == 7000
    assert rates['UEL'] == 72000
    assert rates['TIER_1_MAX'] == 420  # 6% of 7000
    assert rates['TIER_2_MAX'] == 3900 # 6% of (72000-7000)

def test_nssf_year_4_limits():
    """Verify Feb 2026 uses Year 4 rates (LEL 9k, UEL 108k)."""
    rates = get_nssf_rates(date(2026, 2, 1))
    assert rates['LEL'] == 9000
    assert rates['UEL'] == 108000
    assert rates['TIER_1_MAX'] == 540   # 6% of 9000
    assert rates['TIER_2_MAX'] == 5940  # 6% of (108000-9000)

# --- SHIF TESTS ---
def test_shif_minimum():
    """Verify minimum floor of 300."""
    # Gross 10,000 * 2.75% = 275. Should be 300.
    assert calculate_shif(Decimal('10000')) == Decimal('300.00')

def test_shif_standard():
    """Verify standard 2.75% rate."""
    # Gross 50,000 * 2.75% = 1,375.
    assert calculate_shif(Decimal('50000')) == Decimal('1375.00')

def test_shif_uncapped():
    """Verify no upper limit."""
    # Gross 1,000,000 * 2.75% = 27,500.
    assert calculate_shif(Decimal('1000000')) == Decimal('27500.00')

# --- AHL TESTS ---
def test_ahl_standard():
    """Verify 1.5% deduction."""
    assert calculate_ahl(Decimal('50000')) == Decimal('750.00')

# --- PAYE TESTS ---
def test_paye_below_relief():
    """Income below 24k should pay 0 tax after relief."""
    # 24,000 * 10% = 2,400. Minus 2,400 relief = 0.
    assert calculate_paye(Decimal('24000')) == Decimal('0.00')

def test_paye_band_1():
    """Test first band (10%)."""
    # Chargeable 30,000.
    # First 24,000 @ 10% = 2,400.
    # Next 6,000 @ 25% = 1,500.
    # Total Tax = 3,900.
    # Less Relief (2,400) = 1,500.
    # WAIT: Bands are:
    # 0-24,000 @ 10% = 2,400
    # 24,001-32,333 @ 25% (Band width 8,333)
    #
    # Calculation for 30,000:
    # Band 1 (24k) = 2,400
    # Band 2 (6k) = 1,500 (6000 * 0.25)
    # Total Gross Tax = 3,900
    # Net Tax = 3,900 - 2,400 = 1,500.
    assert calculate_paye(Decimal('30000')) == Decimal('1500.00')

def test_paye_high_earner():
    """Test 35% band entry (>800k)."""
    # Chargeable 1,000,000
    # 1. 24,000 @ 10% = 2,400
    # 2. 8,333 @ 25%  = 2,083.25
    # 3. 467,667 @ 30% = 140,300.10
    # 4. 300,000 @ 32.5% = 97,500
    # 5. 200,000 @ 35% = 70,000
    # Total Gross Tax = 312,283.35
    # Net Tax = 312,283.35 - 2,400 = 309,883.35
    assert calculate_paye(Decimal('1000000')) == Decimal('309883.35')
