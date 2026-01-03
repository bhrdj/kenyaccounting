# Development Strategy

This document captures strategic decisions and rationale as the project evolves.

---

## Prototyping Philosophy

**Readability over robustness during prototyping.**

- No try-except blocks unless absolutely necessary for flow control
- No input validation beyond what breaks the logic
- No logging framework - use print() for debugging
- No type hints initially
- No docstrings - code should be self-explanatory
- No helper functions for one-off operations
- No abstract base classes or interfaces
- Direct attribute access, no getters/setters

We can add robustness, validation, and polish later. Right now we need to verify the calculations are correct.

---

## Data Storage Strategy

### Phase 1: TSV Files (Current)

For prototyping, use TSV files for all data:

**Advantages:**
- Human-readable, easy to inspect and debug
- Git-friendly (meaningful diffs, version history)
- No setup or dependencies required
- Good for validating calculations are correct
- Easy to hand-edit test cases

**Files:**
- `test_employees.tsv` - employee master data
- `test_contracts.tsv` - contract parameters
- `test_leave_stocks.tsv` - leave balances at a point in time
- `test_timesheets/YYYY_MM.tsv` - daily work records per month

### Phase 2: SQLite (Future)

Add SQLite when we need persistence features:

**Triggers to add SQLite:**
1. Need to persist payroll results month-over-month
2. Need to track leave balance history (stocks/flows over time)
3. Need to query historical data ("what did we pay employee X in March?")
4. Need audit trail for compliance

**What SQLite would store:**
- Completed payroll runs (immutable records)
- Leave balance transactions (debits/credits over time)
- Employee/contract change history

**What stays in TSV:**
- Current month's timesheet input (before processing)
- Test fixtures

The leave stocks file is the first sign we need state that persists between runs - when manual updates to that file become unwieldy, it's time for SQLite.

---

## Testing Strategy

### Expected Values

Don't calculate expected values upfront. Instead:
1. Run the system with test fixtures
2. Verify outputs externally (KRA calculator, accountant review)
3. Once verified, lock in as expected values for regression tests

This avoids duplicating calculation logic in test setup.

### Test Fixtures

10 employees covering key scenarios:
- Hourly contracts (52hr and 45hr weeks)
- Fixed monthly salary
- Prorated minimum wage
- Overtime (1.5x and 2.0x)
- Sick leave (full pay and half pay)
- Annual leave usage
- Housing quarters (taxable benefit)
- High earner (32.5% tax bracket)

See `specs/unit_test_spec.md` for full details.

---

## Git Workflow

- `main` branch for stable, reviewed code
- `feature/*` branches for new work
- Merge via PR when feasible
- Test fixtures can go directly to main (they're data, not logic)

---

## Data Flow: TSV ↔ Objects

Clear separation between storage and logic layers.

**TSV = Storage/Transport layer**
- Human-editable input
- Export formats (bank uploads, statutory returns)
- Never used directly in calculations

**Objects = Logic layer**
- All business logic operates on objects
- Calculators take objects, return objects
- Never parse TSV mid-calculation

**Flow:**
```
INPUT:   TSV files → load_*() functions → Objects
PROCESS: Objects → Calculators → Result Objects (PaySlip, etc.)
OUTPUT:  Result Objects → Renderers → CSV/TSV/PDF
         Updated Objects (LeaveStock) → save_*() functions → TSV (or SQLite later)
```

**Key rule:** Boundary crossing (TSV ↔ Object) happens only at the edges - load at start, save at end. Everything in between is pure object manipulation.

**Loader functions** (thin, dumb):
```
load_employees(path) → list[Employee]
load_contracts(path) → dict[employee_id, Contract]
load_leave_stocks(path) → dict[employee_id, LeaveStock]
load_timesheet(path) → dict[employee_id, list[TimesheetDay]]
```

**Saver functions** (thin, dumb):
```
save_leave_stocks(stocks, path)  # after payroll updates balances
save_payroll_results(payslips, path)  # optional archive
```

When SQLite is added, the load/save functions change internally but the object interface stays the same. Calculators never know or care where data came from.

---

## Future Considerations

*Add strategic decisions here as they arise.*
