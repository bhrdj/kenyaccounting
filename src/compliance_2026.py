from datetime import date
from decimal import Decimal
from typing import Dict, TypedDict

# --- CONSTANTS ---
PERSONAL_RELIEF = Decimal('2400.00')
SHIF_RATE = Decimal('0.0275')  # 2.75%
SHIF_MIN = Decimal('300.00')
AHL_RATE = Decimal('0.015')    # 1.5%

# PAYE Tax Bands (Threshold, Rate)
# Effective Jan 1, 2026 (assumes Finance Act 2025/2023 continuity)
TAX_BANDS = [
    (Decimal('24000'), Decimal('0.10')),
    (Decimal('32333'), Decimal('0.25')),
    (Decimal('500000'), Decimal('0.30')),
    (Decimal('800000'), Decimal('0.325')),
    (Decimal('inf'), Decimal('0.35'))
]

class NSSFRates(TypedDict):
    LEL: int
    UEL: int
    TIER_1_MAX: int
    TIER_2_MAX: int

def get_nssf_rates(payroll_date: date) -> NSSFRates:
    """
    Returns NSSF limits based on the specific month.
    Handles the transition to Year 4 rates in February 2026.
    """
    # Year 4 commences Feb 1, 2026.
    # UEL = 3x National Average (36k) = 108,000
    if payroll_date >= date(2026, 2, 1):
        return {
            "LEL": 9000,
            "UEL": 108000,
            "TIER_1_MAX": 540,   # 6% of 9000
            "TIER_2_MAX": 5940   # 6% of (108000-9000)
        }
    else:
        # Year 3 Rates (for Jan 2026) -> UEL = 2x National Average (72k)
        return {
            "LEL": 7000,
            "UEL": 72000,
            "TIER_1_MAX": 420,   # 6% of 7000
            "TIER_2_MAX": 3900   # 6% of (72000-7000)
        }

def calculate_shif(gross_pay: Decimal) -> Decimal:
    """
    Calculates Social Health Insurance Fund (SHIF).
    Rate: 2.75% of Gross. 
    Floor: 300 KES.
    Ceiling: None.
    """
    calculated = gross_pay * SHIF_RATE
    return max(calculated, SHIF_MIN).quantize(Decimal('0.01'))

def calculate_ahl(gross_pay: Decimal) -> Decimal:
    """
    Calculates Affordable Housing Levy (AHL).
    Rate: 1.5% of Gross.
    """
    return (gross_pay * AHL_RATE).quantize(Decimal('0.01'))

def calculate_paye(chargeable_pay: Decimal) -> Decimal:
    """
    Calculates PAYE on Chargeable Pay (after allowable deductions).
    Applies 2026 Tax Bands and Personal Relief.
    """
    if chargeable_pay <= 0:
        return Decimal('0.00')

    tax_total = Decimal('0.00')
    remaining_income = chargeable_pay
    previous_limit = Decimal('0')

    for limit, rate in TAX_BANDS:
        if remaining_income <= 0:
            break

        # If limit is infinity, tax the rest
        if limit == Decimal('inf'):
            taxable_amount = remaining_income
        else:
            # Band width is (Limit - Previous Limit)
            # But we are consuming 'remaining_income'. 
            # The logic usually is iterating through brackets.
            # Let's use the 'Limits' approach:
            # 0 - 24,000
            # 24,000 - 32,333
            # etc.
            
            # Band width calculation
            band_width = limit - previous_limit
            taxable_amount = min(remaining_income, band_width)
        
        tax_total += taxable_amount * rate
        remaining_income -= taxable_amount
        previous_limit = limit

    # Subtract Personal Relief
    final_tax = max(tax_total - PERSONAL_RELIEF, Decimal('0.00'))
    return final_tax.quantize(Decimal('0.01'))
