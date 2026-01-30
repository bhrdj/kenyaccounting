# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KenyAccounting is an open source payroll and accounting system designed specifically for Kenyan businesses. It handles the complex interplay of Kenyan statutory deductions (NSSF, SHIF, AHL), PAYE tax calculations, and Employment Act compliance.

**Current Status:** Pre-implementation planning phase. The `specs/` directory contains regulatory research and initial design specifications, but no code has been written yet.

## Planned Architecture

```
KenyAccounting/
├── data/                       # User data (TSVs, Git tracked locally)
│   ├── master_employees.tsv    # Names, PINs, Base Salaries
│   ├── contracts.tsv           # Hourly divisors, contract types
│   └── timesheets/             # Monthly logs (e.g., 2026_01.tsv)
├── src/
│   ├── compliance_2026.py      # Tax bands, NSSF limits, statutory rates
│   ├── models.py               # Data classes (Employee, Contract)
│   ├── engine.py               # Gross-to-Net calculation logic
│   └── outputs.py              # Bank CSV, statutory returns, PDF generators
├── app.py                      # Streamlit UI
└── requirements.txt            # streamlit, pandas, reportlab, openpyxl
```

## Key Domain Concepts

### 2026 "Deductibility Paradigm"
SHIF and AHL are **allowable deductions** (reduce taxable income before PAYE), not tax credits. The calculation order is:
1. Calculate Gross Pay
2. Calculate statutory deductions: NSSF + SHIF + AHL
3. Chargeable Pay = Gross - (NSSF + SHIF + AHL + Approved Pension)
4. Calculate PAYE on Chargeable Pay
5. PAYE Payable = Gross PAYE - Personal Relief (KES 2,400/month)

### NSSF Year 4 Transition (February 2026)
- LEL: KES 9,000
- UEL: KES 108,000 (3x National Average)
- Tier 1 max: KES 540 (6% of LEL)
- Tier 2 max: KES 5,940 (6% of UEL-LEL)
- Supports "Contracted Out" status for Tier 2 to private pension schemes

### Statutory Rates
- SHIF: 2.75% of gross, minimum KES 300, no ceiling
- AHL: 1.5% employee + 1.5% employer
- PAYE bands: 10% (first 24k), 25%, 30%, 32.5%, 35% (over 800k)

### Contract Types to Support
- Fixed monthly salary
- Hourly/timesheet-based (with configurable divisors: 225 for 52hr/week, ~195 for 45hr/week)
- Prorated minimum wage
- Casual (daily) with Section 37 conversion monitoring (>26 consecutive days triggers conversion)

### Employment Act Compliance
- Sick leave: 7 days full pay + 7 days half pay (after 2 months service)
- Annual leave: 21 days
- Overtime: 1.5x weekdays, 2.0x Sundays/holidays
- Housing benefit valuation: higher of market value or 15% of total income

## Specifications Reference

- `specs/dev_strategy.md` - Strategic decisions (data storage, testing, phasing)
- `specs/technical_spec.md` - Object-oriented design and calculation flow
- `specs/unit_test_spec.md` - Test scenarios with 10 employees
- `specs/initial_spec-2025_12_31.md` - Initial system design and code structure
- `backgrounders/backgrounder-Employment_Law_Update_2026-AI_Generated.md` - Comprehensive Kenya tax/labor law reference for 2026
- `specs/PromptHistory.md` - Development prompt history

## Test Fixtures

Located in `tests/fixtures/`:
- `test_employees.tsv` - 10 test employees
- `test_contracts.tsv` - Contract parameters for each
- `test_leave_stocks.tsv` - Leave balances as of Feb 2026
- `test_timesheets/2026_02.tsv` - Daily timesheet entries for February 2026

## Output Formats

### Equity Bank Bulk Payments
CSV format for bulk salary disbursement upload.

### KRA P10 PAYE Returns
Excel template with CSV import, downloaded from iTax portal. Includes employee details, gross pay, all deductions, and computed vs self-assessed PAYE. Template has macros for validation.

### NSSF Returns
Excel template from NSSF self-service portal. Format uses gross salaries (system calculates contributions), NSSF Membership Number, KRA PIN, and voluntary contribution amounts. See NSSF Return Specifications Guide for column details.

### SHA (SHIF) Returns
Upload via SHA portal. Format includes employee ID, gross salary, and calculated 2.75% contribution (min KES 300).

All statutory remittances due by 9th of following month.

## Important Notes

- This software provides no tax advice - all calculations must be verified by a qualified accountant
- Licensed under Apache 2.0
- Do not include Claude attribution or "Co-Authored-By" lines in commit messages
- Ask before running `git reset` commands
