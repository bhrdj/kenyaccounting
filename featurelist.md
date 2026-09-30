# KenyAccounting Feature List

This document outlines the core features required for the KenyAccounting payroll system, compliant with Kenya's 2026 fiscal statutes.

## 1. Compliance Engine (The Core)
* **Status**: Critical
* **Description**: Centralized logic for all statutory calculations based on 2026 laws.
* **Features**:
    *   **NSSF Year 4 Logic**: 
        *   Switch between Year 3 (Jan 2026) and Year 4 (Feb 2026+) rates.
        *   Implement Tier 1 (LEL 9,000) and Tier 2 (UEL 108,000) limits.
        *   Support "Contracted Out" status for Tier 2 redirection.
    *   **SHIF Implementation**:
        *   2.75% of Gross Salary.
        *   Minimum floor of KES 300.
        *   No upper ceiling.
        *   **Deductibility**: Treat as an allowable deduction (pre-tax).
    *   **Affordable Housing Levy (AHL)**:
        *   1.5% Gross deduction (Employee + Employer).
        *   **Deductibility**: Treat as an allowable deduction (pre-tax).
    *   **PAYE Calculation (2026)**:
        *   Dynamic "Chargeable Pay" calculation (Gross - Allowable Deductions).
        *   Apply 2026 Tax Bands (10%, 25%, 30%, 32.5%, 35%).
        *   Apply Personal Relief (KES 2,400).
        *   Support Mortgage Interest Deduction (KES 25,000/month cap).

## 2. Input Data Management
* **Status**: High Priority
* **Description**: Robust handling of TSV-based data sources.
* **Features**:
    *   **Master Data Ingestion**: Read `master_employees.tsv` (PINs, Names, Departments).
    *   **Contract Management**: Read `contracts.tsv` supporting:
        *   Hourly (Time & Attendance based).
        *   Fixed Monthly.
        *   Minimum Wage Prorated.
        *   Casual vs. Term definitions.
    *   **Timesheet Processing**: Read monthly logs (`data/timesheets/YYYY_MM.tsv`).
    *   **Validation**: 
        *   Check for duplicate PINs.
        *   Validate "Casual Monitor" (Alert if >26 days/month).
        *   Verify Per Diem thresholds (limit tax-free to KES 10,000).

## 3. Payroll Engine
* **Status**: High Priority
* **Description**: The gross-to-net processing workflow.
* **Features**:
    *   **Gross Pay Calculation**: 
        *   Standardize hourly divisors (225 vs 240).
        *   Calculate Overtime (1.5x, 2.0x).
        *   Compute Housing Benefit (15% rule vs Market Value).
    *   **Net Pay Derivation**:
        *   Execute deduction order: Gross -> Statutories (NSSF, SHIF, AHL) -> Taxable Base -> PAYE -> Net.
    *   **Batch Processing**: Run calculations for all active employees for a selected period.

## 4. Reporting & Outputs
* **Status**: Medium Priority
* **Description**: Generation of improved files for banks and authorities.
* **Features**:
    *   **Bank Files**: Equity Bank CSV format (Account, Name, Amount).
    *   **Statutory Returns**:
        *   NSSF Return File (Excel/CSV).
        *   SHIF Return File.
        *   AHL Return File.
        *   KRA iTax P10 Support (CSV).
    *   **Payslips**: PDF generation using `reportlab`.

## 5. User Interface (Streamlit)
* **Status**: Medium Priority
* **Description**: Simple, local-first web interface.
* **Features**:
    *   **Dashboard**: View summary stats (Total Payroll Cost, Total PAYE, Headcount).
    *   **Run Payroll**: Selector for Month/Year and "Process" button.
    *   **Preview Grid**: `st.dataframe` view of calculated results before finalization.
    *   **Download Center**: One-click downloads for all generated reports.
    *   **Logs**: View detailed calculation logs for audit (iTax penalty waiver support).

## 6. System & Architecture
* **Status**: Foundation
* **Description**: Technical requirements for sustainability.
* **Features**:
    *   **Audit Trail**: structured logging of all calculations.
    *   **Separation of Concerns**: `src/` directory logic isolated from UI.
    *   **Configuration**: `config.py` or `.env` for global constants (though laws are hardcoded in compliance module).
