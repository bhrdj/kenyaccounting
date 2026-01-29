# Technical Specification: KenyAccounting

## Prototyping Philosophy

**This is a prototype.** Prioritize readability and directness over defensive coding.

- No try-except blocks unless absolutely necessary for flow control
- No input validation beyond what breaks the logic
- No logging framework - use print() for debugging
- No type hints initially
- No docstrings - code should be self-explanatory
- No helper functions for one-off operations
- No abstract base classes or interfaces
- Direct attribute access, no getters/setters

We can add robustness, validation, and polish later. Right now we need to verify the calculations are correct.

---

## Directory Structure

```
KenyAccounting/
├── src/
│   ├── __init__.py
│   ├── models.py           # Data classes
│   ├── rates.py            # Statutory rates and constants
│   ├── calculators.py      # Calculation logic
│   └── outputs.py          # File generators
├── tests/
│   ├── fixtures/
│   │   ├── test_employees.tsv
│   │   ├── test_contracts.tsv
│   │   ├── test_leave_stocks.tsv
│   │   ├── test_timesheets/         # Monthly timesheet TSVs
│   │   └── test_weekly_schedules/   # Per-week schedule TSVs
│   └── test_payroll.py     # pytest tests
├── data/                   # User's actual data (gitignored)
└── app.py                  # Streamlit UI (later)
```

---

## Object Model

### Core Data Classes (models.py)

```
Employee
    employee_id: int
    name: str
    national_id: str
    kra_pin: str
    phone: str
    bank_account: str

Contract
    employee_id: int
    contract_type: str          # 'hourly', 'fixed_monthly', 'prorated_min_wage'
    base_salary: Decimal
    weekly_hours: int           # contractual weekly hours (all contract types)
    standard_workday_hours: Decimal  # for leave conversion (e.g., 8.0, 9.0)
    housing_type: str           # 'none', 'quarters', 'allowance'
    housing_market_value: Decimal | None
    nssf_tier: str              # 'standard', 'contracted_out'
    start_date: date
    end_date: date | None
    status: str                 # 'active', 'terminated'

LeaveStock
    employee_id: int
    sick_full_pay: Decimal      # days remaining (converted to hours via standard_workday_hours)
    sick_half_pay: Decimal
    annual_leave: Decimal
    as_of_date: date

TimesheetDay
    employee_id: int
    date: date
    hours_normal: Decimal       # regular hours worked
    hours_ot_1_5: Decimal       # overtime at 1.5x (weekday)
    hours_ot_2_0: Decimal       # overtime at 2.0x (Sunday/holiday)
    hours_sick: Decimal         # sick leave hours (engine allocates full/half/overflow)
    hours_annual: Decimal       # annual leave hours (engine handles overflow to unpaid)
    hours_unpaid: Decimal       # explicit unpaid leave hours
    is_public_holiday: bool     # true if date is a public holiday

WeeklySchedule
    employee_id: int
    week_start: date            # Monday of the week
    mon: Decimal                # scheduled hours for each day
    tue: Decimal
    wed: Decimal
    thu: Decimal
    fri: Decimal
    sat: Decimal
```

Notes on timesheet:
- Timesheet records intent (sick, annual, unpaid). Engine handles stock attribution.
- `hours_sick`: engine allocates against sick_full stock first, then sick_half, then overflows to annual leave
- `hours_annual`: engine allocates against annual leave stock, overflows to unpaid
- `hours_unpaid`: explicit unpaid leave, no stock needed
- If `is_public_holiday=true` and `hours_normal > 0`, warn that these should be `hours_ot_2_0`
- Leave hours are converted to days via `contract.standard_workday_hours` for stock deduction

### Calculation Results (models.py)

```
GrossBreakdown
    base_pay: Decimal
    overtime_1_5: Decimal
    overtime_2_0: Decimal
    housing_benefit: Decimal    # taxable value of quarters
    total_gross: Decimal

Deductions
    nssf_tier_1: Decimal
    nssf_tier_2: Decimal
    shif: Decimal
    ahl_employee: Decimal
    paye: Decimal
    total: Decimal

LeaveAllocation
    sick_full_pay_hours: Decimal    # hours used this period
    sick_half_pay_hours: Decimal
    annual_leave_hours: Decimal
    unpaid_hours: Decimal
    updated_stock: LeaveStock       # balances after this period

PaySlip
    employee: Employee
    contract: Contract
    period: str                 # e.g., "February 2026"
    gross: GrossBreakdown
    deductions: Deductions
    leave: LeaveAllocation
    net_pay: Decimal
    days_worked: list[TimesheetDay]
```

---

## Rates Module (rates.py)

Single source of truth for statutory constants. Date-aware for NSSF transitions.

```
StatutoryRates
    __init__(payroll_date: date)

    # NSSF (auto-selects Year 3 vs Year 4 based on date)
    nssf_lel: Decimal           # Lower Earnings Limit
    nssf_uel: Decimal           # Upper Earnings Limit
    nssf_rate: Decimal          # 0.06

    # SHIF
    shif_rate: Decimal          # 0.0275
    shif_min: Decimal           # 300

    # AHL
    ahl_rate: Decimal           # 0.015

    # PAYE
    personal_relief: Decimal    # 2400
    tax_bands: list[tuple]      # [(24000, 0.10), (32333, 0.25), ...]
```

Year 4 NSSF transition happens February 2026:
- Before Feb 2026: LEL=8000, UEL=72000
- Feb 2026 onwards: LEL=9000, UEL=108000

---

## Calculators Module (calculators.py)

### GrossCalculator

```
GrossCalculator
    __init__(contract: Contract, timesheet_days: list[TimesheetDay])

    calculate() -> GrossBreakdown
        # Routes to appropriate method based on contract_type

    _calc_hourly(leave_alloc: LeaveAllocation) -> GrossBreakdown
        divisor = (weekly_hours * 52) / 12
        hourly_rate = base_salary / divisor

        # Work hours
        base_pay = hourly_rate * sum(hours_normal)
        ot_1_5 = hourly_rate * 1.5 * sum(hours_ot_1_5)
        ot_2_0 = hourly_rate * 2.0 * sum(hours_ot_2_0)

        # Leave hours (from engine allocation, not raw timesheet)
        sick_full_pay = hourly_rate * leave_alloc.sick_full_pay_hours
        sick_half_pay = hourly_rate * 0.5 * leave_alloc.sick_half_pay_hours
        annual_pay = hourly_rate * leave_alloc.annual_leave_hours
        # unpaid = 0 (no pay)

        total = base_pay + ot_1_5 + ot_2_0 + sick_full_pay + sick_half_pay + annual_pay

    _calc_fixed_monthly(leave_alloc: LeaveAllocation) -> GrossBreakdown
        hourly_rate = base_salary / (weekly_hours * 52 / 12)

        # Leave adjustments (engine determines which sick hours are half pay)
        sick_half_deduction = hourly_rate * 0.5 * leave_alloc.sick_half_pay_hours
        unpaid_deduction = hourly_rate * (leave_alloc.unpaid_hours + sum(hours_unpaid))

        total = base_salary - sick_half_deduction - unpaid_deduction

    _calc_prorated_min_wage(leave_alloc: LeaveAllocation) -> GrossBreakdown
        std_monthly_hours = weekly_hours * 52 / 12
        paid_hours = sum(hours_normal + hours_ot_1_5 + hours_ot_2_0)
                     + leave_alloc.sick_full_pay_hours
                     + leave_alloc.sick_half_pay_hours * 0.5
                     + leave_alloc.annual_leave_hours
        fraction = paid_hours / std_monthly_hours
        base_pay = base_salary * fraction
```

### LeaveCalculator

Engine-driven allocation: timesheet says "sick" or "annual", engine determines
which stock categories to draw from and handles overflow.

```
LeaveCalculator
    __init__(timesheet_days: list[TimesheetDay], leave_stock: LeaveStock, contract: Contract)

    allocate() -> LeaveAllocation
        sick_hours = sum(day.hours_sick for day in timesheet_days)
        annual_hours = sum(day.hours_annual for day in timesheet_days)
        unpaid_hours = sum(day.hours_unpaid for day in timesheet_days)
        wdh = contract.standard_workday_hours

        # 1. Allocate sick hours: full pay first, then half pay, then overflow
        sick_days = sick_hours / wdh
        sick_full_days_used = min(sick_days, leave_stock.sick_full_pay)
        remaining_sick = sick_days - sick_full_days_used
        sick_half_days_used = min(remaining_sick, leave_stock.sick_half_pay)
        sick_overflow_days = remaining_sick - sick_half_days_used

        # 2. Allocate annual hours + any sick overflow
        annual_days = annual_hours / wdh
        total_annual_needed = annual_days + sick_overflow_days
        annual_days_used = min(total_annual_needed, leave_stock.annual_leave)
        annual_overflow_days = total_annual_needed - annual_days_used

        # 3. Any remaining overflow becomes unpaid
        total_unpaid_hours = (unpaid_hours + annual_overflow_days * wdh)

        # 4. Convert back to hours for gross calculation
        sick_full_pay_hours = sick_full_days_used * wdh
        sick_half_pay_hours = sick_half_days_used * wdh

        # 5. Update leave stocks
        updated_stock = LeaveStock(
            sick_full_pay = leave_stock.sick_full_pay - sick_full_days_used,
            sick_half_pay = leave_stock.sick_half_pay - sick_half_days_used,
            annual_leave = leave_stock.annual_leave - annual_days_used,
        )

        return LeaveAllocation(
            sick_full_pay_hours, sick_half_pay_hours,
            annual_days_used * wdh, total_unpaid_hours,
            updated_stock
        )
```

### DeductionCalculator

```
DeductionCalculator
    __init__(gross: Decimal, rates: StatutoryRates, contract: Contract)

    calculate() -> Deductions
        nssf_t1 = min(gross, rates.nssf_lel) * rates.nssf_rate

        if contract.nssf_tier == 'standard':
            pensionable = min(gross, rates.nssf_uel) - rates.nssf_lel
            nssf_t2 = max(0, pensionable) * rates.nssf_rate
        else:
            nssf_t2 = 0  # contracted out

        shif = max(gross * rates.shif_rate, rates.shif_min)
        ahl = gross * rates.ahl_rate
```

### PAYECalculator

```
PAYECalculator
    __init__(rates: StatutoryRates)

    calculate(chargeable_pay: Decimal) -> Decimal
        # Apply tax bands progressively
        tax = 0
        remaining = chargeable_pay
        prev_limit = 0

        for limit, rate in rates.tax_bands:
            band_width = limit - prev_limit
            taxable = min(remaining, band_width)
            tax += taxable * rate
            remaining -= taxable
            prev_limit = limit
            if remaining <= 0:
                break

        return max(tax - rates.personal_relief, 0)
```

### HousingBenefitCalculator

```
HousingBenefitCalculator
    __init__(contract: Contract, gross: Decimal)

    calculate() -> Decimal
        if contract.housing_type == 'quarters':
            fifteen_pct = gross * 0.15
            return max(contract.housing_market_value, fifteen_pct)
        return 0
```

---

## PayrollEngine (calculators.py)

Orchestrates the full calculation for one employee.

```
PayrollEngine
    __init__(payroll_date: date)

    process(employee, contract, timesheet_days, leave_stock) -> PaySlip
        rates = StatutoryRates(payroll_date)

        # 1. Allocate leave hours against stocks (engine determines full/half/overflow)
        leave_calc = LeaveCalculator(timesheet_days, leave_stock, contract)
        leave = leave_calc.allocate()

        # 2. Calculate gross (uses leave allocation for sick full/half split)
        gross_calc = GrossCalculator(contract, timesheet_days)
        gross = gross_calc.calculate(leave)

        # 3. Add housing benefit
        housing_calc = HousingBenefitCalculator(contract, gross.total_gross)
        gross.housing_benefit = housing_calc.calculate()

        # 4. Calculate deductions
        ded_calc = DeductionCalculator(gross.total_gross, rates, contract)
        deductions = ded_calc.calculate()

        # 5. Calculate PAYE
        chargeable = gross.total_gross + gross.housing_benefit - (
            deductions.nssf_tier_1 + deductions.nssf_tier_2 +
            deductions.shif + deductions.ahl_employee
        )
        paye_calc = PAYECalculator(rates)
        deductions.paye = paye_calc.calculate(chargeable)
        deductions.total = sum of all deductions

        # 6. Calculate net (housing benefit is non-cash, don't subtract)
        net_pay = gross.total_gross - deductions.total

        return PaySlip(...)
```

---

## Outputs Module (outputs.py)

### PayslipRenderer

```
PayslipRenderer
    render(payslip: PaySlip) -> str
        # Returns formatted text/markdown paystub
        # Shows daily work log, earnings, deductions, net
```

### BankFileGenerator

```
BankFileGenerator
    __init__(payslips: list[PaySlip])

    to_equity_csv() -> str
        # Equity Bank bulk payment format
```

### StatutoryReturnGenerator

```
KRAReturnGenerator
    __init__(payslips: list[PaySlip])
    to_p10_csv() -> str

NSSFReturnGenerator
    __init__(payslips: list[PaySlip])
    to_nssf_csv() -> str

SHAReturnGenerator
    __init__(payslips: list[PaySlip])
    to_sha_csv() -> str
```

---

## Data Loading

Simple functions in a `loaders.py` or at top of `app.py`:

```
load_employees(path) -> list[Employee]
    # Read TSV, return list of Employee objects

load_contracts(path) -> dict[int, Contract]
    # Keyed by employee_id

load_leave_stocks(path) -> dict[int, LeaveStock]
    # Keyed by employee_id

load_timesheet(path) -> dict[int, list[TimesheetDay]]
    # Keyed by employee_id, value is list of days

load_weekly_schedules(path) -> dict[int, list[WeeklySchedule]]
    # Keyed by employee_id, value is list of weekly schedules
```

---

## Calculation Flow Summary

```
For each employee:
    1. Load employee, contract, leave_stock, timesheet_days
    2. LeaveCalculator: allocate sick/annual hours against stocks (full→half→overflow)
    3. GrossCalculator: timesheet hours + leave allocation -> gross breakdown
    4. HousingBenefitCalculator: add taxable housing value
    5. DeductionCalculator: gross -> NSSF, SHIF, AHL
    6. Chargeable = Gross + Housing - Deductions
    7. PAYECalculator: chargeable -> PAYE
    8. Net = Gross - All Deductions
    9. Build PaySlip
```

---

## Test Strategy

```python
# tests/test_payroll.py

def test_alice_full_month_hourly():
    # Load fixtures
    # Run PayrollEngine for Alice
    # Assert gross, each deduction, net
    # (expected values filled in after external verification)

def test_henry_sick_leave_half_pay():
    # Verify 3 full-pay + 3 half-pay allocation
    # Verify gross reflects half-pay days
```

Run with: `pytest tests/`

---

## Notes

- All monetary values use `Decimal` for precision
- Dates use `datetime.date`
- TSV parsing with `csv.DictReader` (delimiter='\t')
- No ORM, no database - just TSV files and in-memory objects
- Streamlit UI comes after core logic is validated
