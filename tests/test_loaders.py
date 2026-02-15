import pytest
from unittest.mock import mock_open, patch
from decimal import Decimal
from datetime import date
from src.loaders import load_employees, load_contracts, load_timesheet
from src.models import Contract, Employee, Timesheet

# --- MOCK DATA ---
VALID_EMPLOYEES_TSV = """PIN\tName\tDepartment
A001\tJohn Doe\tIT
A002\tJane Smith\tHR
"""

VALID_CONTRACTS_TSV = """PIN\tpay_basis\tbase_salary\tstd_weekly_hours\tnssf_tier\thousing_type\thousing_value
A001\thourly\t200.00\t45\tstandard\tnone\t0
A002\tfixed_monthly\t50000.00\t40\tstandard\tquarters\t5000
"""

VALID_TIMESHEET_TSV = """PIN\thours_normal\thours_ot_1.5\thours_ot_2.0\ttotal_hours
A001\t160\t10\t5\t175
A002\t160\t0\t0\t160
"""

CASUAL_WARNING_TSV = """PIN\thours_normal\thours_ot_1.5\thours_ot_2.0\ttotal_days_worked
A003\t8\t0\t0\t27
"""

# --- TESTS ---

def test_load_employees():
    with patch("builtins.open", mock_open(read_data=VALID_EMPLOYEES_TSV)):
        employees = load_employees("dummy_path.tsv")
        assert len(employees) == 2
        assert employees[0]["name"] == "John Doe"
        assert employees[0]["pin"] == "A001"

def test_load_contracts():
    with patch("builtins.open", mock_open(read_data=VALID_CONTRACTS_TSV)):
        contracts = load_contracts("dummy_path.tsv")
        assert "A001" in contracts
        assert contracts["A001"]["pay_basis"] == "hourly"
        assert contracts["A001"]["base_salary"] == Decimal("200.00")
        assert contracts["A002"]["housing_type"] == "quarters"

def test_load_timesheet():
    with patch("builtins.open", mock_open(read_data=VALID_TIMESHEET_TSV)):
        timesheets = load_timesheet("dummy_path.tsv")
        assert "A001" in timesheets
        assert timesheets["A001"]["hours_normal"] == Decimal("160")
        assert timesheets["A001"]["hours_ot_1_5"] == Decimal("10")
        
def test_missing_column_error():
    """Ensure parser raises error if required column is missing."""
    INVALID_TSV = "PIN\tName\nA001\tJohn" # Missing 'Department'
    with patch("builtins.open", mock_open(read_data=INVALID_TSV)):
        with pytest.raises(ValueError, match="Missing columns"):
            load_employees("dummy.tsv")

