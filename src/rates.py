from datetime import date
from decimal import Decimal
from typing import NamedTuple


class PublicHoliday(NamedTuple):
    """Kenyan public holiday."""
    date: date
    name: str
    is_estimated: bool = False  # True for Islamic holidays with uncertain dates


class KenyanHolidays:
    """
    Kenyan public holidays per the Public Holidays Act (Cap 110).

    Fixed holidays:
    - Jan 1: New Year's Day
    - May 1: Labour Day
    - Jun 1: Madaraka Day
    - Oct 10: Huduma Day
    - Oct 20: Mashujaa Day (Heroes' Day)
    - Dec 12: Jamhuri Day (Independence Day)
    - Dec 25: Christmas Day
    - Dec 26: Boxing Day

    Variable holidays:
    - Good Friday, Easter Monday (Christian)
    - Eid ul-Fitr, Eid ul-Adha (Islamic - dates are estimates)
    """

    # Fixed holidays (same date every year)
    FIXED_HOLIDAYS = [
        (1, 1, "New Year's Day"),
        (5, 1, "Labour Day"),
        (6, 1, "Madaraka Day"),
        (10, 10, "Huduma Day"),
        (10, 20, "Mashujaa Day"),
        (12, 12, "Jamhuri Day"),
        (12, 25, "Christmas Day"),
        (12, 26, "Boxing Day"),
    ]

    # Variable holidays by year (pre-calculated)
    # Format: {year: [(month, day, name, is_estimated), ...]}
    VARIABLE_HOLIDAYS = {
        2026: [
            (4, 3, "Good Friday", False),
            (4, 6, "Easter Monday", False),
            (3, 30, "Eid ul-Fitr", True),  # Estimated
            (6, 6, "Eid ul-Adha", True),   # Estimated
        ],
        2027: [
            (3, 26, "Good Friday", False),
            (3, 29, "Easter Monday", False),
            (3, 19, "Eid ul-Fitr", True),  # Estimated
            (5, 26, "Eid ul-Adha", True),  # Estimated
        ],
    }

    @classmethod
    def get_holidays_for_year(cls, year: int) -> list[PublicHoliday]:
        """Get all public holidays for a given year."""
        holidays = []

        # Add fixed holidays
        for month, day, name in cls.FIXED_HOLIDAYS:
            holidays.append(PublicHoliday(date(year, month, day), name, False))

        # Add variable holidays if we have them
        if year in cls.VARIABLE_HOLIDAYS:
            for month, day, name, is_estimated in cls.VARIABLE_HOLIDAYS[year]:
                holidays.append(PublicHoliday(date(year, month, day), name, is_estimated))

        return sorted(holidays, key=lambda h: h.date)

    @classmethod
    def get_holidays_for_month(cls, year: int, month: int) -> list[PublicHoliday]:
        """Get public holidays for a specific month."""
        return [h for h in cls.get_holidays_for_year(year) if h.date.month == month]

    @classmethod
    def count_working_days(cls, year: int, month: int) -> int:
        """
        Count working days in a month (Mon-Fri, excluding public holidays).
        """
        from calendar import monthrange, weekday

        holidays = {h.date for h in cls.get_holidays_for_month(year, month)}
        _, num_days = monthrange(year, month)

        working_days = 0
        for day in range(1, num_days + 1):
            d = date(year, month, day)
            # Monday=0, Sunday=6
            if weekday(year, month, day) < 5 and d not in holidays:  # Mon-Fri
                working_days += 1

        return working_days

    @classmethod
    def get_expected_hours(cls, year: int, month: int, weekly_hours: int = 45) -> Decimal:
        """
        Calculate expected working hours for a month.
        Assumes daily hours = weekly_hours / 5 (for 5-day week).
        """
        working_days = cls.count_working_days(year, month)
        daily_hours = Decimal(weekly_hours) / Decimal(5)
        return working_days * daily_hours


class StatutoryRates:
    """Single source of truth for statutory constants. Date-aware for NSSF transitions."""

    # NSSF Year 4 transition date
    NSSF_YEAR_4_START = date(2026, 2, 1)

    # Minimum wages (Nairobi/Cities) - from Regulation of Wages Order 2024
    MIN_WAGE_NAIROBI_UNSKILLED = Decimal("16113.75")  # General labourer monthly

    # Housing allowance rate (per Employment Act Section 31)
    HOUSING_ALLOWANCE_RATE = Decimal("0.15")

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
