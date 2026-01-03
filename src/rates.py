from datetime import date
from decimal import Decimal


class StatutoryRates:
    """Single source of truth for statutory constants. Date-aware for NSSF transitions."""

    # NSSF Year 4 transition date
    NSSF_YEAR_4_START = date(2026, 2, 1)

    def __init__(self, payroll_date: date):
        self.payroll_date = payroll_date

        # NSSF - auto-selects Year 3 vs Year 4 based on date
        if payroll_date >= self.NSSF_YEAR_4_START:
            # Year 4: LEL = 9,000, UEL = 108,000
            self.nssf_lel = Decimal("9000")
            self.nssf_uel = Decimal("108000")
        else:
            # Year 3: LEL = 7,000, UEL = 72,000
            self.nssf_lel = Decimal("7000")
            self.nssf_uel = Decimal("72000")

        self.nssf_rate = Decimal("0.06")

        # SHIF
        self.shif_rate = Decimal("0.0275")
        self.shif_min = Decimal("300")

        # AHL
        self.ahl_rate = Decimal("0.015")

        # PAYE
        self.personal_relief = Decimal("2400")
        # Tax bands: (upper_limit, rate)
        # The bands are cumulative limits
        self.tax_bands = [
            (Decimal("24000"), Decimal("0.10")),
            (Decimal("32333"), Decimal("0.25")),
            (Decimal("500000"), Decimal("0.30")),
            (Decimal("800000"), Decimal("0.325")),
            (Decimal("999999999"), Decimal("0.35")),  # effectively unlimited
        ]

    @property
    def nssf_tier_1_max(self):
        """Maximum Tier 1 contribution (employee portion)."""
        return self.nssf_lel * self.nssf_rate

    @property
    def nssf_tier_2_max(self):
        """Maximum Tier 2 contribution (employee portion)."""
        return (self.nssf_uel - self.nssf_lel) * self.nssf_rate

    @property
    def nssf_total_max(self):
        """Maximum total NSSF contribution (employee portion)."""
        return self.nssf_tier_1_max + self.nssf_tier_2_max
