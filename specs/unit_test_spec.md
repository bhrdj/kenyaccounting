# Unit Test Specification for KenyAccounting

---

## Test Employee Scenarios

26 employees across January and February 2026, covering Year 3 NSSF rates (Jan) and Year 4 (Feb).

### Employees 1-12: February 2026 (Year 4 NSSF)

| # | Name | Contract Type | Base Salary | Weekly Hours | Special Conditions |
|---|------|---------------|-------------|--------------|-------------------|
| 1 | Alice | Hourly | 16,113.75 (min wage) | 52 | Full month, no leave |
| 2 | Bob | Hourly | 25,000 | 45 | Full month, no leave |
| 3 | Carol | Prorated min wage | 16,113.75 | 45 | 3 weeks only (18 days) |
| 4 | David | Fixed monthly | 50,000 | - | Full month |
| 5 | Eve | Fixed monthly | 550,000 | - | High earner (32.5% bracket) |
| 6 | Frank | Hourly | 20,000 | 52 | With overtime (12hrs @1.5x, 4hrs @2.0x) |
| 7 | Grace | Fixed monthly | 35,000 | - | 4 days sick |
| 8 | Henry | Fixed monthly | 30,000 | - | 6 days sick (engine splits 3 full + 3 half) |
| 9 | Irene | Fixed monthly | 40,000 | - | 5 days annual leave |
| 10 | James | Fixed monthly | 60,000 | - | Housing quarters (market value 8,000) |
| 11 | Ken | Fixed monthly | 200,000 | - | Published Senior Exec example |
| 12 | Lucy | Fixed monthly | 500,000 | - | Published C-Suite example |

### Employees 13-19: January + February 2026 (Aren calculator verification)

All fixed monthly, 52hr/week (9h weekday, 7h Saturday), full months, no leave.

| # | Name | Base Salary | Notes |
|---|------|-------------|-------|
| 13 | Aren Test 10k | 10,000 | Jan values verified against Aren calculator |
| 14 | Aren Test 15k | 15,000 | |
| 15 | Aren Test 20k | 20,000 | |
| 16 | Aren Test 25k | 25,000 | |
| 17 | Aren Test 30k | 30,000 | |
| 18 | Aren Test 50k | 50,000 | |
| 19 | Aren Test 80k | 80,000 | |

### Employees 20-26: January + February 2026 (leave scenarios)

All fixed monthly, 52hr/week (9h weekday, 7h Saturday).

| # | Name | Base Salary | Special Conditions |
|---|------|-------------|-------------------|
| 20 | Nancy | 22,000 | 2 sick Jan, 1 sick Feb |
| 21 | Oscar | 28,000 | 1 sick Jan, 3 sick Feb |
| 22 | Pamela | 45,000 | 1 sick Jan, 2 annual Feb |
| 23 | Quentin | 18,000 | **Sick overflow → annual**: 3 sick Jan + 5 sick Feb exhausts sick stock |
| 24 | Rose | 55,000 | **Annual overflow → unpaid**: 3 annual Jan + 4 annual Feb exhausts annual stock |
| 25 | Samuel | 32,000 | 2 annual Jan, 1 sick Feb |
| 26 | Tabitha | 70,000 | 3 sick Jan, 2 annual Feb |

---

## Leave Stocks (balances as of Jan 1 / Feb 1, 2026)

Engine allocates sick hours against stocks automatically: sick_full first, then sick_half, then overflow to annual, then unpaid.

### Employees 1-12 (as of Feb 1, 2026)

| # | Name | Sick (full) | Sick (half) | Annual | Notes |
|---|------|-------------|-------------|--------|-------|
| 1 | Alice | 7 | 7 | 10 | Won't use any |
| 2 | Bob | 7 | 7 | 12 | Won't use any |
| 3 | Carol | 7 | 7 | 8 | Reduced schedule, not leave |
| 4 | David | 7 | 7 | 15 | Won't use any |
| 5 | Eve | 7 | 7 | 21 | Won't use any |
| 6 | Frank | 7 | 7 | 5 | Won't use any |
| 7 | Grace | 7 | 7 | 10 | 4 sick days → engine allocates all from sick_full |
| 8 | Henry | 3 | 7 | 10 | 6 sick days → engine allocates 3 full + 3 half |
| 9 | Irene | 7 | 7 | 10 | 5 days annual leave |
| 10 | James | 7 | 7 | 14 | Won't use any |
| 11 | Ken | 7 | 7 | 15 | Won't use any |
| 12 | Lucy | 7 | 7 | 21 | Won't use any |

### Employees 13-19 (as of Jan 1, 2026)

All have 7/7/10 (sick_full/sick_half/annual). No leave used.

### Employees 20-26 (as of Jan 1, 2026)

| # | Name | Sick (full) | Sick (half) | Annual | Notes |
|---|------|-------------|-------------|--------|-------|
| 20 | Nancy | 7 | 7 | 12 | |
| 21 | Oscar | 7 | 7 | 10 | |
| 22 | Pamela | 7 | 7 | 15 | |
| 23 | Quentin | 3 | 3 | 10 | Low sick stock — will overflow to annual |
| 24 | Rose | 7 | 7 | 5 | Low annual stock — will overflow to unpaid |
| 25 | Samuel | 7 | 7 | 14 | |
| 26 | Tabitha | 7 | 7 | 10 | |

---

## Expected Leave Stocks After Processing

### After February 2026 (employees 1-12)

| # | Name | Sick (full) | Sick (half) | Annual | Unpaid Days |
|---|------|-------------|-------------|--------|-------------|
| 7 | Grace | 3 | 7 | 10 + accrued | 0 |
| 8 | Henry | 0 | 4 | 10 + accrued | 0 |
| 9 | Irene | 7 | 7 | 5 + accrued | 0 |

### After January 2026 (employees 20-26)

| # | Name | Sick (full) | Sick (half) | Annual | Unpaid Days |
|---|------|-------------|-------------|--------|-------------|
| 20 | Nancy | 5 | 7 | 12 | 0 |
| 21 | Oscar | 6 | 7 | 10 | 0 |
| 22 | Pamela | 6 | 7 | 15 | 0 |
| 23 | Quentin | 0 | 3 | 10 | 0 |
| 24 | Rose | 7 | 7 | 2 | 0 |
| 25 | Samuel | 7 | 7 | 12 | 0 |
| 26 | Tabitha | 4 | 7 | 10 | 0 |

### After February 2026 (employees 20-26)

| # | Name | Sick (full) | Sick (half) | Annual | Unpaid Days | Notes |
|---|------|-------------|-------------|--------|-------------|-------|
| 20 | Nancy | 4 | 7 | 12 | 0 | |
| 21 | Oscar | 3 | 7 | 10 | 0 | |
| 22 | Pamela | 6 | 7 | 13 | 0 | |
| 23 | Quentin | 0 | 0 | 8 | 0 | 3 sick_half exhausted + 2 sick days overflowed to annual |
| 24 | Rose | 7 | 7 | 0 | 2 | 2 annual used + 2 overflowed to unpaid |
| 25 | Samuel | 6 | 7 | 12 | 0 | |
| 26 | Tabitha | 4 | 7 | 8 | 0 | |

---

## Expected Values (to be verified with accountant calculator)

| # | Name | Gross | NSSF T1 | NSSF T2 | SHIF | AHL | Taxable | PAYE | Net |
|---|------|-------|---------|---------|------|-----|---------|------|-----|
| 1 | Alice | 16,113.75 | ? | ? | ? | ? | ? | ? | ? |
| 2 | Bob | 25,000 | ? | ? | ? | ? | ? | ? | ? |
| 3 | Carol | ~12,085 | ? | ? | ? | ? | ? | ? | ? |
| 4 | David | 50,000 | ? | ? | ? | ? | ? | ? | ? |
| 5 | Eve | 550,000 | ? | ? | ? | ? | ? | ? | ? |
| 6 | Frank | ~22,400 | ? | ? | ? | ? | ? | ? | ? |
| 7 | Grace | 35,000 | ? | ? | ? | ? | ? | ? | ? |
| 8 | Henry | ~28,500 | ? | ? | ? | ? | ? | ? | ? |
| 9 | Irene | 40,000 | ? | ? | ? | ? | ? | ? | ? |
| 10 | James | 60,000 | ? | ? | ? | ? | ? | ? | ? |

---

## NSSF Tests

```
FOR EACH employee IN test_employees:

    LOAD employee, contract, timesheet
    CALCULATE gross

    # Year 4 rates (Feb 2026): LEL=9000, UEL=108000

    nssf_tier1 = MIN(gross, 9000) * 0.06

    IF gross > 9000:
        pensionable_excess = MIN(gross, 108000) - 9000
        nssf_tier2 = pensionable_excess * 0.06
    ELSE:
        nssf_tier2 = 0

    ASSERT nssf_tier1 EQUALS expected_nssf_tier1[employee]
    ASSERT nssf_tier2 EQUALS expected_nssf_tier2[employee]
```

---

## SHIF Tests

```
FOR EACH employee IN test_employees:

    LOAD employee, contract, timesheet
    CALCULATE gross

    shif = MAX(gross * 0.0275, 300)

    ASSERT shif EQUALS expected_shif[employee]
```

---

## AHL Tests

```
FOR EACH employee IN test_employees:

    LOAD employee, contract, timesheet
    CALCULATE gross

    ahl = gross * 0.015

    ASSERT ahl EQUALS expected_ahl[employee]
```

---

## PAYE Tests

```
FOR EACH employee IN test_employees:

    LOAD employee, contract, timesheet
    CALCULATE gross
    CALCULATE housing_benefit (for James: MAX(8000, gross * 0.15))
    CALCULATE total_deductions = nssf_tier1 + nssf_tier2 + shif + ahl

    chargeable_pay = gross + housing_benefit - total_deductions

    # Apply tax bands progressively
    tax = 0
    remaining = chargeable_pay

    IF remaining > 0:
        band1 = MIN(remaining, 24000)
        tax = tax + (band1 * 0.10)
        remaining = remaining - 24000

    IF remaining > 0:
        band2 = MIN(remaining, 8333)  # 32333 - 24000
        tax = tax + (band2 * 0.25)
        remaining = remaining - 8333

    IF remaining > 0:
        band3 = MIN(remaining, 467667)  # 500000 - 32333
        tax = tax + (band3 * 0.30)
        remaining = remaining - 467667

    IF remaining > 0:
        band4 = MIN(remaining, 300000)  # 800000 - 500000
        tax = tax + (band4 * 0.325)
        remaining = remaining - 300000

    IF remaining > 0:
        tax = tax + (remaining * 0.35)

    paye = MAX(tax - 2400, 0)  # subtract personal relief

    ASSERT paye EQUALS expected_paye[employee]
```

---

## Gross Calculation Tests

```
# Test 1: Alice - Hourly 52hr week
divisor = (52 * 52) / 12  # ~225.33
hourly_rate = 16113.75 / divisor
gross = hourly_rate * hours_worked_normal
ASSERT gross EQUALS 16113.75  # full month

# Test 3: Carol - Prorated minimum wage
std_monthly_hours = 45 * 4  # 180
worked_hours = 18 * 8  # 144 (3 weeks)
fraction = worked_hours / std_monthly_hours  # 0.8
gross = 16113.75 * fraction
ASSERT gross EQUALS ~12085

# Test 6: Frank - With overtime
divisor = (52 * 52) / 12
hourly_rate = 20000 / divisor
gross = (hourly_rate * 208) + (hourly_rate * 1.5 * 12) + (hourly_rate * 2.0 * 4)
ASSERT gross EQUALS expected_gross_frank

# Test 8: Henry - Half pay sick days (fixed monthly)
# Timesheet has 48 hrs hours_sick. Engine allocates 24 hrs full + 24 hrs half.
# Gross deduction is only for the half-pay portion.
hourly_rate = 30000 / (45 * 52 / 12)  # ~153.85
sick_half_deduction = hourly_rate * 0.5 * 24  # 3 days @ 8hrs (engine-determined)
gross = 30000 - sick_half_deduction
ASSERT gross EQUALS expected_gross_henry
```

---

## Leave Allocation Tests

Engine allocates `hours_sick` from timesheet against leave stocks automatically.
No explicit split in the timesheet — the engine determines attribution.

```
# Test Grace: 4 sick days (32 hrs), 7 full-pay in stock
TEST grace_sick_allocation:
    LOAD Grace timesheet: 32 hrs hours_sick
    LOAD Grace leave_stock: sick_full=7, sick_half=7

    allocation = LeaveCalculator.allocate()

    # All 4 days fit within sick_full stock
    ASSERT allocation.sick_full_pay_hours EQUALS 32
    ASSERT allocation.sick_half_pay_hours EQUALS 0
    ASSERT allocation.updated_stock.sick_full_pay EQUALS 3
    ASSERT allocation.updated_stock.sick_half_pay EQUALS 7

# Test Henry: 6 sick days (48 hrs), only 3 full-pay in stock
TEST henry_sick_split:
    LOAD Henry timesheet: 48 hrs hours_sick
    LOAD Henry leave_stock: sick_full=3, sick_half=7

    allocation = LeaveCalculator.allocate()

    # Engine splits: 3 days full pay (24 hrs) + 3 days half pay (24 hrs)
    ASSERT allocation.sick_full_pay_hours EQUALS 24
    ASSERT allocation.sick_half_pay_hours EQUALS 24
    ASSERT allocation.updated_stock.sick_full_pay EQUALS 0
    ASSERT allocation.updated_stock.sick_half_pay EQUALS 4

# Test Irene: 5 days annual leave (40 hrs)
TEST irene_annual_leave:
    LOAD Irene timesheet: 40 hrs hours_annual
    LOAD Irene leave_stock: annual_leave=10

    allocation = LeaveCalculator.allocate()

    ASSERT allocation.annual_leave_hours EQUALS 40
    ASSERT allocation.updated_stock.annual_leave EQUALS 5

# Test Quentin: Sick leave overflow → annual leave
TEST quentin_sick_overflow:
    # January: 3 sick days (27 hrs @ 9hr workday), stock: sick_full=3, sick_half=3
    LOAD Jan timesheet: 27 hrs hours_sick
    jan_alloc = LeaveCalculator.allocate()
    ASSERT jan_alloc.sick_full_pay_hours EQUALS 27
    ASSERT jan_alloc.updated_stock.sick_full_pay EQUALS 0
    ASSERT jan_alloc.updated_stock.sick_half_pay EQUALS 3

    # February: 5 sick days (45 hrs), stock: sick_full=0, sick_half=3, annual=10
    LOAD Feb timesheet: 45 hrs hours_sick
    feb_alloc = LeaveCalculator.allocate(stock=jan_alloc.updated_stock)
    ASSERT feb_alloc.sick_full_pay_hours EQUALS 0     # none left
    ASSERT feb_alloc.sick_half_pay_hours EQUALS 27    # 3 days
    ASSERT feb_alloc.annual_leave_hours EQUALS 18     # 2 days overflow from sick
    ASSERT feb_alloc.updated_stock.sick_half_pay EQUALS 0
    ASSERT feb_alloc.updated_stock.annual_leave EQUALS 8

# Test Rose: Annual leave overflow → unpaid
TEST rose_annual_overflow:
    # January: 3 annual days (27 hrs), stock: annual=5
    LOAD Jan timesheet: 27 hrs hours_annual
    jan_alloc = LeaveCalculator.allocate()
    ASSERT jan_alloc.annual_leave_hours EQUALS 27
    ASSERT jan_alloc.updated_stock.annual_leave EQUALS 2  # 5 - 3

    # February: 4 annual days (36 hrs), stock: annual=2
    LOAD Feb timesheet: 36 hrs hours_annual
    feb_alloc = LeaveCalculator.allocate(stock=jan_alloc.updated_stock)
    ASSERT feb_alloc.annual_leave_hours EQUALS 18     # 2 days from stock
    ASSERT feb_alloc.unpaid_hours EQUALS 18           # 2 days overflow
    ASSERT feb_alloc.updated_stock.annual_leave EQUALS 0
```

---

## Paystub Hours Verification Tests

```
FOR EACH employee IN test_employees:

    LOAD employee, timesheet
    GENERATE paystub

    # Verify each day in timesheet appears on paystub
    FOR EACH day IN timesheet:
        ASSERT day.date EXISTS IN paystub.daily_work_log
        ASSERT day.hours EQUALS paystub.daily_work_log[day.date].hours

    # Verify totals match
    ASSERT SUM(timesheet.hours) EQUALS paystub.total_hours

    # Verify overtime only shows if worked (Frank only)
    IF employee.name == "Frank":
        ASSERT paystub.overtime_section EXISTS
        ASSERT paystub.overtime_1_5x_hours EQUALS 12
        ASSERT paystub.overtime_2_0x_hours EQUALS 4
    ELSE:
        ASSERT paystub.overtime_section NOT EXISTS

    # Verify leave balances (Irene)
    IF employee.name == "Irene":
        ASSERT paystub.leave_used EQUALS 5
        ASSERT paystub.leave_accrued EQUALS 1.75
        ASSERT paystub.leave_balance EQUALS (10 - 5 + 1.75)
```

---

## Batch Paystub Verification Test

```
LOAD all 26 test_employees
LOAD all test_timesheets (Jan + Feb)
GENERATE paystubs for all employees

FOR EACH paystub IN generated_paystubs:

    # Structure checks
    ASSERT paystub.header.company_name EXISTS
    ASSERT paystub.header.payroll_period EQUALS "February 2026"
    ASSERT paystub.header.pay_date EXISTS

    ASSERT paystub.employee_info.name EXISTS
    ASSERT paystub.employee_info.pin EXISTS

    ASSERT paystub.daily_work_log EXISTS
    ASSERT paystub.time_off_summary EXISTS
    ASSERT paystub.earnings_breakdown EXISTS
    ASSERT paystub.deductions_breakdown EXISTS
    ASSERT paystub.net_pay EXISTS

    # Value checks against calculated expectations
    employee_id = paystub.employee_info.id

    ASSERT paystub.deductions.nssf EQUALS expected_nssf[employee_id]
    ASSERT paystub.deductions.shif EQUALS expected_shif[employee_id]
    ASSERT paystub.deductions.ahl EQUALS expected_ahl[employee_id]
    ASSERT paystub.deductions.paye EQUALS expected_paye[employee_id]
    ASSERT paystub.net_pay EQUALS expected_net[employee_id]

    # Hours match timesheet
    ASSERT paystub.total_hours EQUALS timesheet[employee_id].total_hours
```

---

## Test Fixtures

```
tests/fixtures/generated_supplementals/
├── test_employees.tsv          # 26 employees
├── test_contracts.tsv          # 26 contracts (includes standard_workday_hours)
├── test_leave_stocks.tsv       # Leave balances as of Jan 1 / Feb 1, 2026
├── test_timesheets/
│   ├── 2026_01.tsv             # January 2026 daily records (employees 13-26)
│   └── 2026_02.tsv             # February 2026 daily records (employees 1-26)
└── test_weekly_schedules/
    ├── 2026_01.tsv             # Weekly schedules for Jan (employees 13-26)
    └── 2026_02.tsv             # Weekly schedules for Feb (employees 13-26)
```

Timesheet columns: `employee_id, date, hours_normal, hours_ot_1_5, hours_ot_2_0, hours_sick, hours_annual, hours_unpaid, is_public_holiday`

Source truth data in `tests/fixtures/single_source_truth_tests/`:
- `specific_published_examples.txt` — Published Feb 2026 payroll examples (30k, 200k, 500k)
- `test_cases_aren.txt` — Aren calculator Jan 2026 outputs (10k-80k)

---

## Verification Checklist

- [ ] All 26 employee expected values verified with accountant/KRA calculator
- [ ] NSSF Year 3 rates confirmed (Jan 2026: LEL=8000, UEL=72000)
- [ ] NSSF Year 4 rates confirmed (Feb 2026: LEL=9000, UEL=108000)
- [ ] PAYE bands confirmed for 2026
- [ ] SHIF 2.75% rate confirmed
- [ ] AHL 1.5% rate confirmed
- [ ] Housing benefit 15% rule confirmed
- [ ] Aren calculator values match for employees 13-19 (January)
- [ ] Published examples match for employees 11-12 (February)
- [ ] Quentin sick overflow allocation correct across Jan→Feb
- [ ] Rose annual overflow allocation correct across Jan→Feb
