import streamlit as st
from datetime import date
from pathlib import Path

from src.loaders import load_employees, load_contracts, load_leave_stocks, load_timesheet
from src.calculators import PayrollEngine
from src.outputs import (
    PayslipRenderer,
    BankFileGenerator,
    KRAReturnGenerator,
    NSSFReturnGenerator,
    SHAReturnGenerator,
)

st.set_page_config(page_title="KenyAccounting", page_icon="📊", layout="wide")

st.title("KenyAccounting")
st.caption("Kenyan Payroll & Statutory Deductions")


# Sidebar for data paths
st.sidebar.header("Data Files")

data_dir = st.sidebar.text_input("Data directory", value="tests/fixtures")
timesheet_dir = st.sidebar.text_input("Timesheets directory", value="tests/fixtures/test_timesheets")

# Select payroll month
st.sidebar.header("Payroll Period")
year = st.sidebar.selectbox("Year", options=[2025, 2026, 2027], index=1)
month = st.sidebar.selectbox("Month", options=list(range(1, 13)), index=1, format_func=lambda m: date(2000, m, 1).strftime("%B"))

payroll_date = date(year, month, 28)  # Use 28th as safe end-of-month


@st.cache_data
def load_data(data_dir, timesheet_dir, year, month):
    data_path = Path(data_dir)
    ts_path = Path(timesheet_dir)

    employees = {e.employee_id: e for e in load_employees(data_path / "test_employees.tsv")}
    contracts = {c.employee_id: c for c in load_contracts(data_path / "test_contracts.tsv")}
    leave_stocks = {l.employee_id: l for l in load_leave_stocks(data_path / "test_leave_stocks.tsv")}

    # Try to load timesheet for the selected month
    ts_file = ts_path / f"{year}_{month:02d}.tsv"
    if ts_file.exists():
        ts_entries = load_timesheet(ts_file)
        timesheet = {}
        for entry in ts_entries:
            if entry.employee_id not in timesheet:
                timesheet[entry.employee_id] = []
            timesheet[entry.employee_id].append(entry)
    else:
        timesheet = {}

    return employees, contracts, leave_stocks, timesheet, ts_file.exists()


# Load data
try:
    employees, contracts, leave_stocks, timesheet, ts_exists = load_data(data_dir, timesheet_dir, year, month)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()


if not ts_exists:
    st.warning(f"No timesheet found for {payroll_date.strftime('%B %Y')}. Expected file: {timesheet_dir}/{year}_{month:02d}.tsv")
    st.stop()


# Run payroll button
if st.sidebar.button("Run Payroll", type="primary"):
    engine = PayrollEngine(payroll_date)
    payslips = []

    for emp_id in sorted(employees.keys()):
        if emp_id in timesheet:
            payslip = engine.process(
                employees[emp_id],
                contracts[emp_id],
                timesheet[emp_id],
                leave_stocks[emp_id],
            )
            payslips.append(payslip)

    st.session_state["payslips"] = payslips
    st.session_state["payroll_date"] = payroll_date


# Display results if payroll has been run
if "payslips" in st.session_state:
    payslips = st.session_state["payslips"]
    payroll_date = st.session_state["payroll_date"]

    st.header(f"Payroll Results - {payroll_date.strftime('%B %Y')}")

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    total_gross = sum(ps.gross.total_gross for ps in payslips)
    total_net = sum(ps.net_pay for ps in payslips)
    total_paye = sum(ps.deductions.paye for ps in payslips)
    total_nssf = sum(ps.deductions.nssf_tier_1 + ps.deductions.nssf_tier_2 for ps in payslips)

    col1.metric("Total Gross", f"KES {total_gross:,.2f}")
    col2.metric("Total Net", f"KES {total_net:,.2f}")
    col3.metric("Total PAYE", f"KES {total_paye:,.2f}")
    col4.metric("Total NSSF", f"KES {total_nssf:,.2f}")

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["Payslips", "Summary Table", "Downloads"])

    with tab1:
        renderer = PayslipRenderer()
        for ps in payslips:
            with st.expander(f"{ps.employee.name} - Net: KES {ps.net_pay:,.2f}"):
                st.code(renderer.render(ps), language=None)

    with tab2:
        import pandas as pd

        data = []
        for ps in payslips:
            data.append({
                "Name": ps.employee.name,
                "Gross": float(ps.gross.total_gross),
                "NSSF T1": float(ps.deductions.nssf_tier_1),
                "NSSF T2": float(ps.deductions.nssf_tier_2),
                "SHIF": float(ps.deductions.shif),
                "AHL": float(ps.deductions.ahl_employee),
                "PAYE": float(ps.deductions.paye),
                "Net": float(ps.net_pay),
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

    with tab3:
        st.subheader("Download Files")

        col1, col2 = st.columns(2)

        with col1:
            # Bank file
            bank_gen = BankFileGenerator(payslips)
            st.download_button(
                "Download Bank CSV",
                bank_gen.to_equity_csv(),
                file_name=f"equity_salaries_{year}_{month:02d}.csv",
                mime="text/csv",
            )

            # KRA P10
            kra_gen = KRAReturnGenerator(payslips)
            st.download_button(
                "Download KRA P10 CSV",
                kra_gen.to_p10_csv(),
                file_name=f"kra_p10_{year}_{month:02d}.csv",
                mime="text/csv",
            )

        with col2:
            # NSSF
            nssf_gen = NSSFReturnGenerator(payslips)
            st.download_button(
                "Download NSSF Return CSV",
                nssf_gen.to_nssf_csv(),
                file_name=f"nssf_return_{year}_{month:02d}.csv",
                mime="text/csv",
            )

            # SHA
            sha_gen = SHAReturnGenerator(payslips)
            st.download_button(
                "Download SHA/SHIF Return CSV",
                sha_gen.to_sha_csv(),
                file_name=f"sha_shif_{year}_{month:02d}.csv",
                mime="text/csv",
            )

else:
    st.info("Click 'Run Payroll' in the sidebar to generate payslips.")

    # Show loaded employees
    st.subheader("Loaded Employees")
    for emp_id in sorted(employees.keys()):
        emp = employees[emp_id]
        contract = contracts[emp_id]
        has_ts = emp_id in timesheet
        st.write(f"- {emp.name} ({contract.contract_type}) {'✓' if has_ts else '✗ no timesheet'}")
