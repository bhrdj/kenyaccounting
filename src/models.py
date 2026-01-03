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


@dataclass
class Contract:
    employee_id: int
    contract_type: str  # 'hourly', 'fixed_monthly', 'prorated_min_wage'
    base_salary: Decimal
    weekly_hours: int | None  # None for fixed_monthly
    housing_type: str  # 'none', 'quarters', 'allowance'
    housing_market_value: Decimal | None
    nssf_tier: str  # 'standard', 'contracted_out'
    start_date: date
    end_date: date | None
    status: str  # 'active', 'terminated'


@dataclass
class LeaveStock:
    employee_id: int
    sick_full_pay: int  # days remaining
    sick_half_pay: int
    annual_leave: int
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
    base_pay: Decimal
    overtime_1_5: Decimal
    overtime_2_0: Decimal
    housing_benefit: Decimal  # taxable value of quarters
    total_gross: Decimal


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
    sick_full_pay_used: int
    sick_half_pay_used: int
    annual_leave_used: int
    unpaid_days: int
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
