# Unit Test Specification for KenyAccounting

---

## Test Employee Scenarios

10 employees with different contract types and worked periods for February 2026 (Year 4 NSSF rates).

| # | Name | Contract Type | Base Salary | Weekly Hours | Special Conditions |
|---|------|---------------|-------------|--------------|-------------------|
| 1 | Alice | Hourly | 16,113.75 (min wage) | 52 | Full month, no leave |
| 2 | Bob | Hourly | 25,000 | 45 | Full month, no leave |
| 3 | Carol | Prorated min wage | 16,113.75 | 45 | 3 weeks only (18 days) |
| 4 | David | Fixed monthly | 50,000 | - | Full month |
| 5 | Eve | Fixed monthly | 550,000 | - | High earner (32.5% bracket) |
| 6 | Frank | Hourly | 20,000 | 52 | With overtime (12hrs @1.5x, 4hrs @2.0x) |
| 7 | Grace | Fixed monthly | 35,000 | - | 4 days absent (sick) |
| 8 | Henry | Fixed monthly | 30,000 | - | 6 days absent (sick) |
| 9 | Irene | Fixed monthly | 40,000 | - | 5 days absent (not sick) |
| 10 | James | Fixed monthly | 60,000 | - | Housing quarters (market value 8,000) |

---

## Leave Stocks (balances at start of Feb 2026)

The model determines leave type from stocks. Input timesheet only says "absent" and "sick yes/no".

| # | Name | Sick Leave (full pay) | Sick Leave (half pay) | Annual Leave | Notes |
|---|------|----------------------|----------------------|--------------|-------|
| 1 | Alice | 7 | 7 | 10 | Won't use any |
| 2 | Bob | 7 | 7 | 12 | Won't use any |
| 3 | Carol | 7 | 7 | 8 | Reduced schedule, not leave |
| 4 | David | 7 | 7 | 15 | Won't use any |
| 5 | Eve | 7 | 7 | 21 | Won't use any |
| 6 | Frank | 7 | 7 | 5 | Won't use any |
| 7 | Grace | 7 | 7 | 10 | 4 sick days → uses 4 full-pay sick |
| 8 | Henry | 3 | 7 | 10 | 6 sick days → uses 3 full-pay + 3 half-pay |
| 9 | Irene | 7 | 7 | 10 | 5 non-sick absent → uses 5 annual leave |
| 10 | James | 7 | 7 | 14 | Won't use any |

---

## Expected Leave Stocks After Feb 2026

| # | Name | Sick Leave (full pay) | Sick Leave (half pay) | Annual Leave | Unpaid Days |
|---|------|----------------------|----------------------|--------------|-------------|
| 7 | Grace | 3 | 7 | 10 + accrued | 0 |
| 8 | Henry | 0 | 4 | 10 + accrued | 0 |
| 9 | Irene | 7 | 7 | 5 + accrued | 0 |

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

# Test 8: Henry - Half pay sick days
days_full_pay = 18 + 3  # worked + sick full
days_half_pay = 3
daily_rate = 30000 / 24
gross = (days_full_pay * daily_rate) + (days_half_pay * daily_rate * 0.5)
ASSERT gross EQUALS expected_gross_henry
```

---

## Leave Allocation Tests

```
FOR EACH employee IN test_employees:

    LOAD employee, timesheet, leave_stocks_before

    # Model determines leave type from stocks and timesheet
    FOR EACH day IN timesheet WHERE day.absent == TRUE:

        IF day.sick == TRUE:
            # Draw from sick leave stocks in order
            IF leave_stocks.sick_full_pay > 0:
                ALLOCATE to sick_full_pay
                DECREMENT leave_stocks.sick_full_pay
            ELSE IF leave_stocks.sick_half_pay > 0:
                ALLOCATE to sick_half_pay
                DECREMENT leave_stocks.sick_half_pay
            ELSE:
                ALLOCATE to unpaid_leave

        ELSE:  # absent but not sick
            # Draw from annual leave first
            IF leave_stocks.annual_leave > 0:
                ALLOCATE to annual_leave
                DECREMENT leave_stocks.annual_leave
            ELSE:
                ALLOCATE to unpaid_leave

    # Test Grace: 4 sick days, 7 full-pay stock → all full-pay
    IF employee.name == "Grace":
        ASSERT allocated_sick_full_pay EQUALS 4
        ASSERT allocated_sick_half_pay EQUALS 0
        ASSERT leave_stocks_after.sick_full_pay EQUALS 3

    # Test Henry: 6 sick days, 3 full-pay stock → 3 full + 3 half
    IF employee.name == "Henry":
        ASSERT allocated_sick_full_pay EQUALS 3
        ASSERT allocated_sick_half_pay EQUALS 3
        ASSERT leave_stocks_after.sick_full_pay EQUALS 0
        ASSERT leave_stocks_after.sick_half_pay EQUALS 4

    # Test Irene: 5 non-sick absent, 10 annual stock → 5 annual
    IF employee.name == "Irene":
        ASSERT allocated_annual_leave EQUALS 5
        ASSERT leave_stocks_after.annual_leave EQUALS 5 + monthly_accrual
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
LOAD all 10 test_employees
LOAD all test_timesheets
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
tests/fixtures/
├── test_employees.tsv       # 10 employees
├── test_contracts.tsv       # 10 contracts
├── test_leave_stocks.tsv    # Leave balances at start of Feb 2026
└── test_timesheets/
    └── 2026_02.tsv          # February 2026 daily records (hours, absent, sick y/n)
```

---

## Verification Checklist

- [ ] All 10 employee expected values verified with accountant/KRA calculator
- [ ] NSSF Year 4 rates confirmed (Feb 2026: LEL=9000, UEL=108000)
- [ ] PAYE bands confirmed for 2026
- [ ] SHIF 2.75% rate confirmed
- [ ] AHL 1.5% rate confirmed
- [ ] Housing benefit 15% rule confirmed
