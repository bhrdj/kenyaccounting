import streamlit as st
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.loaders import (
    load_employees, load_contracts, load_leave_stocks, load_timesheet,
    load_timesheet_folder, validate_input_folder, find_file, find_timesheet_dir,
    find_leave_stocks_for_month,
)
from src.calculators import PayrollEngine
from src.models import LeaveStock
from src.rates import KenyanHolidays
from src.outputs import (
    PayslipRenderer,
    BankFileGenerator,
    KRAReturnGenerator,
    NSSFReturnGenerator,
    SHAReturnGenerator,
    save_payroll_outputs,
    save_leave_stocks,
    upload_leave_stocks_to_gsheet,
)

st.set_page_config(page_title="KenyAccounting", page_icon="📊", layout="wide")

st.title("KenyAccounting")
st.caption("Kenyan Payroll & Statutory Deductions")


# Sidebar: input folder
st.sidebar.header("Input Folder")
input_folder = st.sidebar.text_input(
    "Paste folder path containing payroll files",
    value=st.session_state.get("input_folder", ""),
    help="Folder with master_employees.tsv, contracts.tsv, leave_stocks/ dir, and a year subfolder of timesheets",
)
st.session_state["input_folder"] = input_folder

# Validate folder
folder_valid = False
if input_folder:
    folder_path = Path(input_folder)
    is_valid, messages = validate_input_folder(folder_path)
    for msg in messages:
        if is_valid:
            st.sidebar.success(msg) if msg.startswith("Valid") else st.sidebar.info(msg)
        else:
            st.sidebar.error(msg)
    folder_valid = is_valid
else:
    st.sidebar.info("Enter a folder path to begin")

# Select payroll month
st.sidebar.header("Payroll Period")
year = st.sidebar.selectbox("Year", options=[2025, 2026, 2027], index=1)
month = st.sidebar.selectbox("Month", options=list(range(1, 13)), index=1, format_func=lambda m: date(2000, m, 1).strftime("%B"))

payroll_date = date(year, month, 28)  # Use 28th as safe end-of-month

# Show month info
working_days = KenyanHolidays.count_working_days(year, month)
holidays = KenyanHolidays.get_holidays_for_month(year, month)
st.sidebar.caption(f"Working days: {working_days}")
if holidays:
    holiday_list = ", ".join(h.name + (" *" if h.is_estimated else "") for h in holidays)
    st.sidebar.caption(f"Holidays: {holiday_list}")
    if any(h.is_estimated for h in holidays):
        st.sidebar.caption("* estimated date")


@st.cache_data
def load_data(folder_str, year, month):
    folder = Path(folder_str)

    emp_path = find_file(folder, "master_employees.tsv")
    con_path = find_file(folder, "contracts.tsv")
    leave_path = find_leave_stocks_for_month(folder, year, month)

    employees = {e.employee_id: e for e in load_employees(emp_path)}
    contracts = {c.employee_id: c for c in load_contracts(con_path)}
    leave_stocks = {l.employee_id: l for l in load_leave_stocks(leave_path)} if leave_path else {}

    # Load per-employee timesheets from year subfolder
    ts_dir = find_timesheet_dir(folder, year)
    if ts_dir:
        timesheet = load_timesheet_folder(ts_dir, year, month)
        ts_exists = len(timesheet) > 0
    else:
        timesheet = {}
        ts_exists = False

    # Fill in default leave stocks for employees without records
    for emp_id in contracts:
        if emp_id not in leave_stocks:
            leave_stocks[emp_id] = LeaveStock(
                employee_id=emp_id,
                sick_full_pay=Decimal("7"),
                sick_half_pay=Decimal("7"),
                annual_leave=Decimal("0"),
                as_of_date=date(2025, 12, 31),
            )

    return employees, contracts, leave_stocks, timesheet, ts_exists


if not folder_valid:
    st.info("Enter a valid input folder path in the sidebar to begin.")
    st.stop()

# Load data
try:
    employees, contracts, leave_stocks, timesheet, ts_exists = load_data(input_folder, year, month)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

if not ts_exists:
    st.warning(f"No timesheet data found for {payroll_date.strftime('%B %Y')} in the input folder.")
    st.stop()


# Run payroll button
if st.sidebar.button("Run Payroll", type="primary"):
    engine = PayrollEngine(payroll_date)
    payslips = []

    for emp_id in sorted(contracts.keys()):
        if emp_id in timesheet and emp_id in employees and emp_id in leave_stocks:
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
        renderer = PayslipRenderer(company_name="B'aida Daycare & Learning Centre")
        for ps in payslips:
            with st.expander(f"{ps.employee.name} - Net: KES {ps.net_pay:,.2f}"):
                st.code(renderer.render(ps), language=None)

    with tab2:
        import pandas as pd

        data = []
        for ps in payslips:
            row = {
                "Name": ps.employee.name,
                "Base": float(ps.gross.base_pay),
            }
            if ps.gross.housing_allowance > 0:
                row["Housing"] = float(ps.gross.housing_allowance)
            row.update({
                "Gross": float(ps.gross.total_gross),
                "NSSF T1": float(ps.deductions.nssf_tier_1),
                "NSSF T2": float(ps.deductions.nssf_tier_2),
                "SHIF": float(ps.deductions.shif),
                "AHL": float(ps.deductions.ahl_employee),
                "PAYE": float(ps.deductions.paye),
                "Net": float(ps.net_pay),
            })
            data.append(row)
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)

        # Show warnings if any
        warnings_found = False
        for ps in payslips:
            if ps.warnings:
                if not warnings_found:
                    st.subheader("Warnings")
                    warnings_found = True
                for w in ps.warnings:
                    st.warning(f"{ps.employee.name}: {w}")

    with tab3:
        st.subheader("Download Files")

        col1, col2 = st.columns(2)

        with col1:
            # All payslips PDF
            pdf_renderer = PayslipRenderer(company_name="B'aida Daycare & Learning Centre")
            st.download_button(
                "Download All Payslips (PDF)",
                pdf_renderer.render_all_pdf(payslips),
                file_name=f"payslips_{year}_{month:02d}.pdf",
                mime="application/pdf",
            )

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

        st.divider()

        # Save outputs to a subfolder next to the input folder
        output_dir = Path(input_folder) / "outputs"
        company_name = "B'aida Daycare & Learning Centre"
        if st.button(f"Save to {output_dir}"):
            written = save_payroll_outputs(payslips, year, month, output_dir, company_name)
            st.success(f"Saved {len(written)} files to {output_dir / f'{year}_{month:02d}'}")

        st.divider()

        # Save updated leave stocks for next month's payroll
        st.subheader("Update Leave Stocks")
        from calendar import monthrange
        _, last_day = monthrange(year, month)
        leave_filename = f"leave_stocks_{year}_{month:02d}_{last_day:02d}.tsv"
        tab_name = f"{year}_{month:02d}_{last_day:02d}"
        leave_dest = Path(input_folder) / "leave_stocks" / str(year) / leave_filename
        exists_local = leave_dest.exists()

        col_ls1, col_ls2 = st.columns(2)

        with col_ls1:
            label = f"{'Replace' if exists_local else 'Save'} {leave_filename}"
            if exists_local:
                st.caption(f"Existing file: {leave_dest}")
            if st.button(label):
                dest = save_leave_stocks(payslips, year, month, Path(input_folder))
                st.success(f"{'Replaced' if exists_local else 'Saved'}: {dest}")

        with col_ls2:
            sheet_name = f"leave_stocks_{year}"
            if st.button(f"Upload tab '{tab_name}' to {sheet_name}"):
                try:
                    written_tab = upload_leave_stocks_to_gsheet(payslips, year, month)
                    st.success(f"Uploaded tab '{written_tab}' to {sheet_name}")
                except Exception as e:
                    st.error(f"Google Sheets upload failed: {e}")

else:
    st.info("Click 'Run Payroll' in the sidebar to generate payslips.")

    # Show loaded employees
    st.subheader("Loaded Employees")
    for emp_id in sorted(employees.keys()):
        if emp_id in contracts:
            emp = employees[emp_id]
            contract = contracts[emp_id]
            has_ts = emp_id in timesheet
            st.write(f"- {emp.name} ({contract.contract_type}) {'✓' if has_ts else '✗ no timesheet'}")
