from dataclasses import dataclass
from datetime import date
from decimal import Decimal


# Core Data Classes

@dataclass
class Employee:
    employee_id: int
    name: str
    national_id: str
    kra_pin: str
    phone: str
    bank_account: str
    nssf_no: str = ""
    shif_no: str = ""


@dataclass
class Contract:
    employee_id: int
    contract_type: str  # 'hourly', 'fixed_monthly', 'prorated_min_wage', 'consolidated_leave'
    base_salary: Decimal  # Interpreted based on salary_basis
    weekly_hours: int | None  # None for fixed_monthly
    housing_type: str  # 'none', 'quarters', 'dorm', 'allowance'
    housing_market_value: Decimal | None  # For 'quarters' only
    nssf_tier: str  # 'standard', 'contracted_out'
    start_date: date
    end_date: date | None
    status: str  # 'active', 'terminated'
    salary_basis: str = "gross"  # 'base' or 'gross' - how base_salary is interpreted
    hourly_divisor: str = "monthly"  # 'statutory' (225), 'monthly', or custom number


@dataclass
class LeaveStock:
    employee_id: int
    sick_full_pay: Decimal  # days remaining (can be fractional)
    sick_half_pay: Decimal
    annual_leave: Decimal
    as_of_date: date


@dataclass
class TimesheetDay:
    employee_id: int
    date: date
    hours_normal: Decimal
    hours_ot_1_5: Decimal
    hours_ot_2_0: Decimal
    absent: bool
    sick: bool


# Calculation Results

@dataclass
class GrossBreakdown:
    base_pay: Decimal              # actual earned base (hours worked + leave pay)
    overtime_1_5: Decimal
    overtime_2_0: Decimal
    housing_allowance: Decimal     # cash housing allowance (15% of base, part of gross)
    housing_benefit: Decimal       # taxable value of quarters (non-cash benefit)
    total_gross: Decimal           # base_pay + overtime + housing_allowance - leave deductions
    baseline_base_pay: Decimal = Decimal(0)  # full-time monthly salary from contract
    worked_base_pay: Decimal = Decimal(0)    # pay from hours actually worked (before leave pay)
    leave_pay: Decimal = Decimal(0)          # pay added for leave-covered hours
    leave_half_pay_deduction: Decimal = Decimal(0)  # deduction for half-pay sick days
    leave_unpaid_deduction: Decimal = Decimal(0)    # deduction for unpaid leave days


@dataclass
class Deductions:
    nssf_tier_1: Decimal
    nssf_tier_2: Decimal
    shif: Decimal
    ahl_employee: Decimal
    paye: Decimal
    total: Decimal


@dataclass
class LeaveAllocation:
    sick_full_pay_used: Decimal  # hours
    sick_half_pay_used: Decimal  # hours
    annual_leave_used: Decimal  # hours
    unpaid_hours: Decimal  # hours
    updated_stock: LeaveStock


@dataclass
class PaySlip:
    employee: Employee
    contract: Contract
    period: str  # e.g., "February 2026"
    gross: GrossBreakdown
    deductions: Deductions
    leave: LeaveAllocation
    net_pay: Decimal
    days_worked: list[TimesheetDay]
    warnings: list[str] | None = None  # Validation warnings (e.g., below min wage)
