import csv
from decimal import Decimal
from typing import List, Dict
from .models import Employee, Contract, Timesheet

def load_employees(path: str) -> List[Employee]:
    """Loads employees from a TSV file."""
    employees = []
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        # Validation
        required = {'PIN', 'Name', 'Department'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Missing columns: {required - set(reader.fieldnames)}") # type: ignore

        for row in reader:
            # Note: We don't populate contract here, it's linked later
            emp: Employee = { # type: ignore
                'pin': row['PIN'],
                'name': row['Name'],
                'contract': None # type: ignore
            }
            employees.append(emp)
    return employees

def load_contracts(path: str) -> Dict[str, Contract]:
    """Loads contracts keyed by PIN."""
    contracts = {}
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        for row in reader:
            contract: Contract = {
                'pay_basis': row['pay_basis'],
                'base_salary': Decimal(row['base_salary']),
                'std_weekly_hours': int(row['std_weekly_hours']),
                'nssf_tier': row['nssf_tier'],
                'housing_type': row['housing_type'],
                'housing_value': Decimal(row['housing_value'])
            }
            contracts[row['PIN']] = contract
    return contracts

def load_timesheet(path: str) -> Dict[str, Timesheet]:
    """Loads timesheets keyed by PIN."""
    timesheets = {}
    with open(path, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        
        for row in reader:
            ts: Timesheet = {
                'hours_normal': Decimal(row['hours_normal']),
                'hours_ot_1_5': Decimal(row['hours_ot_1.5']),
                'hours_ot_2_0': Decimal(row['hours_ot_2.0']),
                'total_hours': Decimal(0)
            }
            # Auto-calculate total? Or read it? specs say read 2026_01.tsv which implies logic.
            # But featurelist says "read monthly logs".
            # Let's sum it for now or read 'total_hours' if present?
            # Test data has 'total_hours'.
            if 'total_hours' in row:
                ts['total_hours'] = Decimal(row['total_hours'])
            
            timesheets[row['PIN']] = ts
            
            # Casual Monitor Logic (TBD Phase 2)
            
    return timesheets
