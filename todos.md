# Todos

## Done this session
- Added Mary Wanjiku Wainaina (ID 27) to master_employees.tsv and contracts.tsv
- Added shif_no column to master_employees.tsv (all employees populated from IDs-Certs)
- Created leave_stocks.tsv from monthly attendance sheet (Dec 2025 end-of-month balances)
- OCR'd 5 contracts and saved to data_gitignored/ocr_contracts/ (.txt):
  - 01 Beth: fixed_monthly, 52hr/wk, base 73,000 + 3,000 BF, housing=(base+BF)*0.15
  - 02 Ann Ndegwa: fixed_monthly, 52hr/wk, base 18,900
  - 05 Jared: consolidated_leave, 52hr/wk, base 23,500, works 3 wks/mo
  - 23 Naomi: fixed_monthly, hours at discretion, base 101,050 + 9,064/6mo + 3,000 BF
  - 25 Ian: fixed_monthly, **45hr/wk**, base 35,000
- OCR'd remaining 14 contracts and saved as markdown (.md):
  - 03 Penina: **PDF only has Code of Conduct signature page — no employment contract found**
  - 04 Mary Njeri: V2, probation 4mo + term 6mo, contract wrote 15,205
  - 06 Wincrease: V3, contract base 16,500, 8mo term
  - 07 Pheris: V3, contract wrote 15,205, 12mo term
  - 08 Faith: V3, contract wrote 15,205, 8mo term
  - 10 Muthoni: V2, probation 4mo + term 6mo, contract wrote 15,205
  - 11 Egrah: V3, contract wrote 15,205, 8mo term
  - 12 Wambui: V3, contract wrote 15,205, 8mo term
  - 13 Agnes: V2, probation 4mo + term 6mo, contract wrote 15,205
  - 14 Wanjiru: V2, probation 4mo, contract wrote 15,205 (was ???, now resolved)
  - 15 Rosemary: V2, probation 4mo + term 6mo, contract wrote 15,205
  - 16 Betty: V2, probation 4mo + term to Jul25, contract wrote 15,205
  - 17 Purity: V2 (not V3), probation + 12mo term, contract wrote 15,205
  - 19 Sharon: V5, short-term probation 2026-01-05 to 2026-02-20, base 16,114
  - 20 Esther: V5, short-term probation 2026-01-05 to 2026-02-20, base 16,114
- Updated contracts.tsv with OCR findings:
  - All base_salary of 15,205 → 16,114 (current minimum wage floor)
  - Wincrease base_salary → 16,500 (OCR confirmed contract amount)
  - Wanjiru (14) base_salary ??? → 16,114, start_date ??? → 2024-09-01
  - Fixed version numbers: Purity V3→V2, Sharon/Esther V2→V5
  - Notes updated with "OCR'd" confirmation on all processed contracts

No contracts on file: 03 Penina (only CoC), 18 Damaris, 21 Martin, 22 Jennifer, 27 Mary Wainaina

## Done: contracts.tsv contract types & consolidated_leave
- Changed Beth (1) and Naomi (23): monthly → fixed_monthly
- Changed Jared (5): hourly → consolidated_leave (works 3 wks/mo, leave in 4th week)
- Changed Wambui (12) and Agnes (13): hourly → prorated_min_wage
- Changed Martin (21): 52hr/wk → 45hr/wk (Mon-Fri)
- Verified Ian (25): already 45hr/wk in contracts.tsv (confirmed by OCR contract)
- Added consolidated_leave to Contract model contract_type options
- Moved Penina (3) missing contract to Later/deferred

## Done: Leave tracking — accrued in days, used in hours
- LeaveStock fields already Decimal (done earlier) — stays in days per Employment Act
- LeaveAllocation fields changed from int to Decimal hours; unpaid_days → unpaid_hours
- LeaveCalculator now accepts Contract, derives daily_hours (52hr/wk→8.667, 45hr/wk→9, None→8)
- Each absent day: deducts 1 day from stock, adds daily_hours to usage
- _apply_leave_adjustments uses hourly rate (base_pay / monthly_hours)
- Payslip output shows "hrs" instead of "days" for leave usage
- All 42 tests pass

## Fix loader for real data
- Handle/skip rows with ??? values (IDs 9, 18, 21, 22, 24, 27)
- Read current_base_salary instead of (or in addition to) base_salary
- Filter by status=active, skip duplicate/terminated

## Scrap src/converters.py
- Remove `src/converters.py` (AttendanceConverter) — no longer needed
- Remove any imports/references to it elsewhere

## Input: folder-based file discovery
- Program receives a folder path as input
- Recursively scan all filenames in that folder and subfolders
- Check filenames against the required set (master_employees.tsv, contracts.tsv, timesheets, leave_stocks, etc.)
- If perfect match: continue with payroll processing
- If missing files: report which required filenames are absent
- If duplicate filenames (same name in multiple subfolders): report the duplicates
- No processing until the file set is validated

## Later
- Naomi's leave: "at her discretion" — need to decide how to model (probably just exempt from leave tracking)
- Beth/Naomi Benefits Fund (3,000 KSh): model as taxable/non-taxable depending on utility receipts
- Penina (3): need to locate actual employment contract or set base_salary to 16,114 minimum
- Expired contracts (IDs 4, 6, 10, 11, 12, 13, 15, 16): confirm renewal status
