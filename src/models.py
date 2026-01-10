# src/models.py
from typing import TypedDict, Optional
from decimal import Decimal

class Contract(TypedDict):
    pay_basis: str  # 'hourly', 'min_wage_prorated', 'fixed_monthly'
    base_salary: Decimal
    std_weekly_hours: int
    nssf_tier: str  # 'standard' or 'opt_out'
    housing_type: str # 'cash_allowance', 'quarters', 'none'
    housing_value: Decimal # For quarters

class Timesheet(TypedDict):
    hours_normal: Decimal
    hours_ot_1_5: Decimal
    hours_ot_2_0: Decimal
    total_hours: Decimal

class Employee(TypedDict):
    pin: str
    name: str
    contract: Contract

class PayrollResult(TypedDict):
    gross_pay: Decimal
    nssf_deduction: Decimal
    shif_deduction: Decimal
    ahl_deduction: Decimal
    housing_benefit: Decimal
    chargeable_pay: Decimal
    paye_tax: Decimal
    personal_relief: Decimal
    net_pay: Decimal
