# Unit Test Specification for KenyAccounting

This document specifies the test suite structure, inputs, and expected outputs.

---

## Test Categories

### 1. EXTERNALLY VALIDATED EXAMPLES

These tests use third-party published payroll calculations and are our primary validation against industry-accepted figures.

**Sources:**
- Net Pay Kenya (https://netpay.co.ke)
- HR Fleek (https://hrfleek.co.ke)

**Validation Status:** VERIFIED against external payroll calculators

### 2. SYNTHETIC TEST SCENARIOS

Artificial test cases designed to exercise specific edge cases and code paths. These are NOT externally validated - expected values are calculated based on our understanding of Kenya 2026 regulations.

---

## SECTION 1: EXTERNALLY VALIDATED EXAMPLES

### Year 4 NSSF Parameters (February 2026+)

| Parameter | Value |
|-----------|-------|
| Lower Earnings Limit (LEL) | KES 9,000 |
| Upper Earnings Limit (UEL) | KES 108,000 |
| Tier I Rate | 6% of earnings up to LEL |
| Tier II Rate | 6% of earnings between LEL and UEL |
| Max Employee Contribution | KES 6,480 (540 + 5,940) |

---

### VALIDATED Example 1: Entry Level (KES 30,000)

**Source:** Net Pay Kenya, HR Fleek

| Item | Amount (KES) | Calculation |
|------|--------------|-------------|
| **Gross Salary** | 30,000 | Input |
| NSSF Tier I | 540 | 9,000 × 6% |
| NSSF Tier II | 1,260 | (30,000 - 9,000) × 6% |
| **Total NSSF** | 1,800 | 6% of gross (below UEL) |
| **SHIF** | 825 | 2.75% of gross |
| **AHL** | 450 | 1.5% of gross |
| **Taxable Pay** | 26,925 | 30,000 - 1,800 - 825 - 450 |
| Gross PAYE | 3,132 | Tax calculation on 26,925 |
| Personal Relief | (2,400) | Standard monthly relief |
| **PAYE** | 732 | 3,132 - 2,400 |
| **Net Pay** | 26,193 | 30,000 - 1,800 - 825 - 450 - 732 |

---

### VALIDATED Example 2: Senior Executive (KES 200,000)

**Source:** Net Pay Kenya, HR Fleek

| Item | Amount (KES) | Calculation |
|------|--------------|-------------|
| **Gross Salary** | 200,000 | Input |
| NSSF Tier I | 540 | 9,000 × 6% |
| NSSF Tier II | 5,940 | (108,000 - 9,000) × 6% (capped) |
| **Total NSSF** | 6,480 | Maximum contribution |
| **SHIF** | 5,500 | 2.75% of gross |
| **AHL** | 3,000 | 1.5% of gross |
| **Taxable Pay** | 185,020 | 200,000 - 6,480 - 5,500 - 3,000 |
| Gross PAYE | 50,289 | Tax calculation on 185,020 |
| Personal Relief | (2,400) | Standard monthly relief |
| **PAYE** | 47,889 | 50,289 - 2,400 |
| **Net Pay** | 137,131 | 200,000 - 6,480 - 5,500 - 3,000 - 47,889 |

---

### VALIDATED Example 3: C-Suite Level (KES 500,000)

**Source:** Net Pay Kenya, HR Fleek

| Item | Amount (KES) | Calculation |
|------|--------------|-------------|
| **Gross Salary** | 500,000 | Input |
| NSSF Tier I | 540 | 9,000 × 6% |
| NSSF Tier II | 5,940 | (108,000 - 9,000) × 6% (capped) |
| **Total NSSF** | 6,480 | Maximum contribution |
| **SHIF** | 13,750 | 2.75% of gross |
| **AHL** | 7,500 | 1.5% of gross |
| **Taxable Pay** | 472,270 | 500,000 - 6,480 - 13,750 - 7,500 |
| Gross PAYE | 136,464 | Tax calculation on 472,270 |
| Personal Relief | (2,400) | Standard monthly relief |
| **PAYE** | 134,064 | 136,464 - 2,400 |
| **Net Pay** | 338,206 | 500,000 - 6,480 - 13,750 - 7,500 - 134,064 |

---

## SECTION 2: SYNTHETIC TEST SCENARIOS

### Test Employees (February 2026)

| ID | Name | Contract Type | Base Salary | Weekly Hours | Special Conditions |
|----|------|---------------|-------------|--------------|-------------------|
| 1 | Alice Wanjiku | Hourly | 16,113.75 | 52 | Full month, no leave |
| 2 | Bob Ochieng | Hourly | 25,000 | 45 | Full month, no leave |
| 3 | Carol Muthoni | Prorated min wage | 16,113.75 | 45 | 18 days worked (partial month) |
| 4 | David Kimani | Fixed monthly | 50,000 | - | Full month |
| 5 | Eve Akinyi | Fixed monthly | 550,000 | - | High earner (32.5% bracket) |
| 6 | Frank Mwangi | Hourly | 20,000 | 52 | With overtime (12hrs @1.5x, 4hrs @2.0x) |
| 7 | Grace Njeri | Fixed monthly | 35,000 | - | 4 days sick |
| 8 | Henry Otieno | Fixed monthly | 30,000 | - | 6 days sick |
| 9 | Irene Wambui | Fixed monthly | 40,000 | - | 5 days absent (not sick) |
| 10 | James Kipchoge | Fixed monthly | 60,000 | - | Housing quarters (market value 8,000) |

---

### Leave Stocks (as of February 1, 2026)

| ID | Name | Sick Full Pay | Sick Half Pay | Annual Leave | Test Scenario |
|----|------|---------------|---------------|--------------|---------------|
| 1-6 | (Various) | 7 | 7 | (varies) | No leave used |
| 7 | Grace | 7 | 7 | 10 | 4 sick → uses 4 full-pay |
| 8 | Henry | 3 | 7 | 10 | 6 sick → uses 3 full + 3 half |
| 9 | Irene | 7 | 7 | 10 | 5 non-sick → uses 5 annual |
| 10 | James | 7 | 7 | 14 | No leave used |

---

### Expected Leave Stocks After February 2026

| ID | Name | Sick Full | Sick Half | Annual | Unpaid Days |
|----|------|-----------|-----------|--------|-------------|
| 7 | Grace | 3 | 7 | 10 | 0 |
| 8 | Henry | 0 | 4 | 10 | 0 |
| 9 | Irene | 7 | 7 | 5 | 0 |

---

## Test Input Formats

### Timesheet Format (TSV)

Actual calendar dates with hours worked per employee:

```
employee_id  date        hours_normal  hours_ot_1_5  hours_ot_2_0  absent  sick
1            2026-02-02  9             0             0             0       0
1            2026-02-03  9             0             0             0       0
...
6            2026-02-02  9             3             0             0       0
6            2026-02-08  0             0             4             0       0
...
7            2026-02-09  0             0             0             1       1
```

### Contract Format (TSV)

```
employee_id  contract_type     base_salary  weekly_hours  housing_type  housing_market_value  nssf_tier
1            hourly            16113.75     52            none                                standard
4            fixed_monthly     50000                      none                                standard
10           fixed_monthly     60000                      quarters      8000                  standard
```

### Employee Format (TSV)

```
employee_id  name            national_id  kra_pin       phone          bank_account
1            Alice Wanjiku   12345678     A001234567X   +254712345001  0011223344551
```

### Leave Stock Format (TSV)

```
employee_id  sick_full_pay  sick_half_pay  annual_leave  as_of_date
1            7              7              10            2026-02-01
8            3              7              10            2026-02-01
```

---

## Test Fixtures Location

```
tests/fixtures/
├── test_employees.tsv           # 10 synthetic employees
├── test_contracts.tsv           # 10 contracts
├── test_leave_stocks.tsv        # Leave balances as of Feb 2026
├── test_timesheets/
│   ├── 2026_01.tsv              # January 2026 (Year 3 NSSF)
│   └── 2026_02.tsv              # February 2026 (Year 4 NSSF)
└── official/
    ├── test_employees.tsv       # 3 employees for validated examples
    ├── test_contracts.tsv       # Simple fixed monthly contracts
    ├── test_leave_stocks.tsv    # No leave used
    └── test_timesheets/
        └── 2026_02.tsv          # Full month worked
```

---

## NSSF Rate Transition Tests

| Date | Year | LEL | UEL | Max Employee Contribution |
|------|------|-----|-----|--------------------------|
| January 2026 | Year 3 | 8,000 | 72,000 | 4,320 |
| February 2026+ | Year 4 | 9,000 | 108,000 | 6,480 |

---

## 2026 PAYE Tax Bands

| Band | Monthly Income (KES) | Rate |
|------|---------------------|------|
| 1 | 0 - 24,000 | 10% |
| 2 | 24,001 - 32,333 | 25% |
| 3 | 32,334 - 500,000 | 30% |
| 4 | 500,001 - 800,000 | 32.5% |
| 5 | 800,001+ | 35% |

**Personal Relief:** KES 2,400/month

---

## Statutory Rate Summary

| Deduction | Rate | Floor | Ceiling |
|-----------|------|-------|---------|
| NSSF | 6% | - | KES 6,480 (Year 4) |
| SHIF | 2.75% | KES 300 | None |
| AHL (Employee) | 1.5% | - | None |
| AHL (Employer) | 1.5% | - | None |

---

## Validation Checklist

- [x] Entry Level (30k) - EXTERNALLY VALIDATED
- [x] Senior Executive (200k) - EXTERNALLY VALIDATED
- [x] C-Suite Level (500k) - EXTERNALLY VALIDATED
- [x] Year 3 → Year 4 NSSF transition dates confirmed
- [x] PAYE bands confirmed for 2026
- [x] SHIF 2.75% rate with KES 300 floor confirmed
- [x] AHL 1.5% rate confirmed
- [x] Housing benefit 15% rule confirmed
- [ ] Overtime rates (1.5x weekday, 2.0x Sunday/holiday) - awaiting external validation
- [ ] Sick leave allocation (7 full + 7 half per year) - per Employment Act
- [ ] Annual leave accrual (21 days/year) - per Employment Act
