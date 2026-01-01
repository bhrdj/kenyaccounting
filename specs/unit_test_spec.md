# Unit Test Specification for KenyAccounting

This document specifies the unit tests required to verify the software meets its stated goals.

---

## 1. Tax Compliance Tests (`test_compliance_2026.py`)

### 1.1 NSSF Rate Transitions
- Test Year 3 rates (Jan 2026): LEL=7000, UEL=72000
- Test Year 4 rates (Feb 2026+): LEL=9000, UEL=108000
- Test exact boundary: Jan 31 vs Feb 1, 2026
- Test Tier 1 max calculation (6% of LEL)
- Test Tier 2 max calculation (6% of UEL-LEL)

### 1.2 PAYE Calculation
- Test each tax band boundary (24,000 / 32,333 / 500,000 / 800,000)
- Test personal relief deduction (KES 2,400)
- Test zero/negative chargeable pay returns zero tax
- Test high earners above 800k bracket
- Test decimal precision throughout

### 1.3 SHIF Calculation
- Test 2.75% rate application
- Test minimum floor (KES 300)

### 1.4 AHL Calculation
- Test 1.5% rate application

### 1.5 Housing Benefit
- Test quarters: max(market_value, 15% of cash_pay)
- Test non-quarters returns zero

---

## 2. Payroll Engine Tests (`test_engine.py`)

### 2.1 Gross Calculation by Contract Type

#### Hourly Contracts
- Test 52-hour week divisor (~225)
- Test 45-hour week divisor (~195)
- Test normal hours calculation
- Test overtime 1.5x rate (only if worked)
- Test overtime 2.0x rate (only if worked)

#### Prorated Minimum Wage
- Test fraction calculation (worked_hours / std_hours)
- Test reduced hours scenarios

#### Fixed Monthly
- Test flat base_salary return

### 2.2 Full Payroll Run
- Test single employee full month
- Test multiple employees with different contract types
- Test NSSF Tier 2 opt-out scenario
- Test housing benefit inclusion in taxable base
- Test pre-tax deductibility paradigm (SHIF/AHL before PAYE)
- Test net pay = gross - deductions - PAYE

---

## 3. Time Off & Leave Tests (`test_leave.py`)

### 3.1 Annual Leave
- Test accrual calculation per Employment Act
- Test days used tracking
- Test balance carried forward

### 3.2 Sick Leave
- Test full-pay sick days
- Test half-pay sick days
- Test sick leave limits per Employment Act

### 3.3 Public Holidays
- Test holiday detection for payroll period
- Test payment for holidays worked (if applicable)

---

## 4. Output Tests (`test_outputs.py`)

### 4.1 Equity Bank CSV
- Test CSV structure matches bank requirements
- Test decimal formatting
- Test special character handling
- Test multiple employee rows

### 4.2 Paystub PDF
- Test all required sections present:
  - Header (company, period, date)
  - Employee info
  - Daily work log with dates/hours
  - Time off & holidays summary
  - Earnings breakdown
  - Deductions breakdown
  - Net pay
- Test overtime only appears when worked
- Test public holidays listed with dates
- Test leave balances displayed

---

## 5. Data Validation Tests (`test_validation.py`)

### 5.1 Employee Data
- Test valid PIN format
- Test non-negative salary
- Test required fields present

### 5.2 Contract Data
- Test valid date ranges (start < end)
- Test valid pay_basis values
- Test valid housing_type values

### 5.3 Timesheet Data
- Test non-negative hours
- Test valid date format

---

## 6. Integration Tests (`test_integration.py`)

### 6.1 End-to-End Payroll Cycle
- Load sample TSV data
- Run full payroll calculation
- Verify outputs generated correctly
- Verify calculations match expected values

### 6.2 Regression Scenarios
- Known payroll calculations from real 2026 scenarios
- Verify historical calculations remain stable

---

## Test Infrastructure

### Recommended Framework
- pytest
- pytest-cov (coverage reporting)
- freezegun (date mocking for NSSF transition tests)

### Test Data Fixtures
```
tests/
├── fixtures/
│   ├── sample_employees.tsv
│   ├── sample_contracts.tsv
│   └── sample_timesheets/
│       └── 2026_01.tsv
```
