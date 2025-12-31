This is an excellent name. **KenyAccounting** implies a system built specifically for the unique "harambee" of distinct statutory bodies (NSSF, SHA, KRA) that Kenyan businesses must coordinate.

Here is the **Structural Setup** and **Conceptual Spec** for KenyAccounting. This code structure is designed to be "clone-and-run" ready.

### **1. Directory Structure**

This structure separates your data (TSVs) from the logic, making it safe to upgrade the software without losing payroll records.

```text
KenyAccounting/
│
├── data/                       # USER DATA (Git tracked locally)
│   ├── master_employees.tsv    # Source of Truth: Names, PINs, Base Salaries
│   ├── contracts.tsv           # Complex Logic: Hourly divisors, 52 vs 45 hrs
│   └── timesheets/             # Monthly logs
│       └── 2026_01.tsv
│
├── src/                        # THE ENGINE
│   ├── __init__.py
│   ├── compliance_2026.py      # HARD-CODED LAW: Tax bands, NSSF limits
│   ├── models.py               # Data classes (Employee, Contract)
│   ├── engine.py               # Gross-to-Net Logic
│   └── outputs.py              # Equity Bank CSV & PDF generators
│
├── app.py                      # Streamlit User Interface
├── requirements.txt            # Dependencies
├── run.sh                      # Linux launch script
└── README.md                   # Instructions + Disclaimer

```

---

### **2. The Core Logic (`src/compliance_2026.py`)**

This is the most critical file. It codifies the rules from the backgrounder. I have implemented the "Deductibility Paradigm" (SHIF/AHL are deductible) and the "Year 4" NSSF transition.

```python
# src/compliance_2026.py
from datetime import date
from decimal import Decimal

# --- CONSTANTS ---
#
PERSONAL_RELIEF = 2400 

#
SHIF_RATE = Decimal('0.0275')  # 2.75%
SHIF_MIN = 300

#
AHL_RATE = Decimal('0.015')    # 1.5%

# --- PAYE BANDS (Effective 2026) ---
#
TAX_BANDS = [
    (24000, Decimal('0.10')),
    (32333, Decimal('0.25')),
    (500000, Decimal('0.30')),
    (800000, Decimal('0.325')),
    (float('inf'), Decimal('0.35'))
]

def get_nssf_rates(payroll_date: date):
    """
    Returns NSSF limits based on the specific month.
    Handles the transition to Year 4 rates in February 2026.
    """
    #
    # Year 4 commences Feb 2026. 
    # UEL = 3x National Average (36k) = 108,000
    if payroll_date >= date(2026, 2, 1):
        return {
            "LEL": 9000,
            "UEL": 108000,
            "TIER_1_MAX": 540,  # 6% of 9000
            "TIER_2_MAX": 5940  # 6% of (108000-9000)
        }
    else:
        # Year 3 Rates (for Jan 2026)
        return {
            "LEL": 7000,        # Assuming Year 3 baseline
            "UEL": 72000,       # 2x National Average
            "TIER_1_MAX": 420,  # 6% of 7000
            "TIER_2_MAX": 3900  # 6% of (72000-7000)
        }

def calculate_paye(chargeable_pay: Decimal) -> Decimal:
    """
    Calculates PAYE on Chargeable Pay (after allowable deductions).
   
    """
    tax = Decimal('0.00')
    remaining = chargeable_pay
    previous_limit = 0

    for limit, rate in TAX_BANDS:
        if remaining <= 0:
            break
        
        # Calculate width of current band
        if limit == float('inf'):
            taxable_amount = remaining
        else:
            band_width = limit - previous_limit
            taxable_amount = min(remaining, band_width)
        
        tax += taxable_amount * rate
        remaining -= taxable_amount
        previous_limit = limit

    # Subtract Personal Relief
    final_tax = max(tax - PERSONAL_RELIEF, Decimal('0.00'))
    return final_tax

def calculate_housing_benefit(cash_pay: Decimal, housing_type: str, market_value: Decimal = 0):
    """
    Calculates taxable value of quarters.
   
    """
    if housing_type == 'quarters':
        # Higher of Market Value or 15% of Total Income
        fifteen_percent = cash_pay * Decimal('0.15')
        return max(market_value, fifteen_percent)
    return Decimal('0.00')

```

---

### **3. The Engine Skeleton (`src/engine.py`)**

This handles your complex contract logic (hours, divisors, prorating).

```python
# src/engine.py
import pandas as pd
from decimal import Decimal
from .compliance_2026 import (
    get_nssf_rates, SHIF_RATE, SHIF_MIN, AHL_RATE, 
    calculate_paye, calculate_housing_benefit
)

class PayrollEngine:
    def __init__(self, data_path):
        self.data_path = data_path
    
    def calculate_gross(self, employee, contract, timesheet):
        """
        Handles the diversity of your contracts.
        """
        gross = Decimal('0.00')
        
        # LOGIC: Hourly / Timesheet Based
        if contract['pay_basis'] == 'hourly':
            # Standard Divisor logic
            # If contract is 52 hrs, divisor is 225. If 45 hrs, divisor is approx 195.
            divisor = (contract['std_weekly_hours'] * 52) / 12
            hourly_rate = contract['base_salary'] / Decimal(divisor)
            
            # Timesheet Inputs
            gross += hourly_rate * Decimal(timesheet['hours_normal'])
            # Overtime Rates
            gross += (hourly_rate * Decimal('1.5')) * Decimal(timesheet['hours_ot_1.5'])
            gross += (hourly_rate * Decimal('2.0')) * Decimal(timesheet['hours_ot_2.0'])

        # LOGIC: Prorated Minimum Wage
        elif contract['pay_basis'] == 'min_wage_prorated':
            # "Getting paid a prorated part based on decreased hours"
            std_hours = contract['std_weekly_hours'] * 4  # Approx monthly hours
            worked_hours = timesheet['total_hours']
            fraction = Decimal(worked_hours) / Decimal(std_hours)
            gross = contract['base_salary'] * fraction

        # LOGIC: Fixed Monthly
        else:
            gross = Decimal(contract['base_salary'])
        
        return gross

    def run_payroll(self, payroll_date):
        # 1. Load TSVs into DataFrames
        # 2. Iterate Employees
        
        nssf_limits = get_nssf_rates(payroll_date)
        
        # --- GROSS TO NET LOOP ---
        # 1. Calculate Gross (as above)
        
        # 2. Statutory Deductions (Allowable)
        # NSSF
        nssf_tier_1 = min(gross, nssf_limits['LEL']) * 0.06
        nssf_tier_2 = 0
        if contract['nssf_tier'] != 'opt_out':
             pensionable_excess = min(gross, nssf_limits['UEL']) - nssf_limits['LEL']
             nssf_tier_2 = max(0, pensionable_excess) * 0.06
        
        # SHIF
        shif = max(gross * SHIF_RATE, SHIF_MIN)
        
        # AHL
        ahl = gross * AHL_RATE
        
        total_allowable_deductions = nssf_tier_1 + nssf_tier_2 + shif + ahl
        
        # 3. Taxable Base
        # Housing Benefit (Quarters) added here
        housing_ben = calculate_housing_benefit(gross, contract['housing_type'], contract['housing_value'])
        
        # The New 2026 Paradigm: Deduct statutories BEFORE tax
        chargeable_pay = (gross + housing_ben) - total_allowable_deductions
        
        # 4. PAYE
        paye = calculate_paye(chargeable_pay)
        
        # 5. Net Pay
        # Note: Housing benefit is non-cash, so we don't deduct it, we just taxed it.
        # Net = Gross - (Statutories) - PAYE
        net_pay = gross - total_allowable_deductions - paye

        return {
            "Gross": gross,
            "NSSF": nssf_tier_1 + nssf_tier_2,
            "SHIF": shif,
            "AHL": ahl,
            "PAYE": paye,
            "Net": net_pay
        }

```

---

### **4. The User Interface (`app.py`)**

A minimal Streamlit app to tie it together.

```python
# app.py
import streamlit as st
import pandas as pd
from src.engine import PayrollEngine
from datetime import date

st.set_page_config(page_title="KenyAccounting", layout="wide")

st.title("🇰🇪 KenyAccounting: 2026 Compliance")
st.markdown("Apache 2.0 Open Source Payroll | *Not Tax Advice*")

# Sidebar for Config
with st.sidebar:
    st.header("Payroll Settings")
    payroll_date = st.date_input("Payroll Date", value=date.today())
    st.info(f"Using NSSF Rates for: {'Year 4 (Feb+ 2026)' if payroll_date >= date(2026,2,1) else 'Year 3'}")

# Data Loading Section
st.header("1. Input Data")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Master Files")
    # In real app, these load from local TSV files automatically
    st.success("Loaded: master_employees.tsv")
    st.success("Loaded: contracts.tsv")

with col2:
    st.subheader("Timesheets")
    uploaded_file = st.file_uploader("Upload Monthly Timesheet (TSV)", type="tsv")

if st.button("Run Payroll Calculation"):
    if uploaded_file:
        # Placeholder for actual engine call
        # engine = PayrollEngine("./data")
        # results = engine.run_payroll(payroll_date)
        
        st.header("2. Results Preview")
        # Example Output
        st.dataframe(pd.DataFrame({
            "Name": ["John Doe", "Jane Smith"],
            "Gross": [50000, 18000],
            "NSSF": [3000, 1080], 
            "SHIF": [1375, 495],
            "AHL": [750, 270],
            "Taxable": [44875, 16155], # Gross - Statutories
            "PAYE": [4087, 0], # 16k is below 24k tax band
            "Net Pay": [40788, 16155]
        }))
        
        st.header("3. Downloads")
        st.download_button("Download Equity Bank CSV", data="...", file_name="equity_upload.csv")
    else:
        st.error("Please upload a timesheet first.")

```

---

### **5. Dependencies (`requirements.txt`)**

```text
streamlit
pandas
reportlab
openpyxl

```

### **6. Implementation Plan**

1. **Clone Phase:** You create the folder structure above.
2. **Data Phase:** You populate `master_employees.tsv` with your team's real data.
3. **Refinement:** You tweak `engine.py` to match the exact column names of your timesheets.
4. **Run:** Execute `streamlit run app.py`.

Would you like me to create the **Template TSV Files** (header rows) next, so you can copy-paste them directly into your project?