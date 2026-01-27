# Payroll Calculation Flow

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INPUT DATA                                      │
├──────────────────┬──────────────────┬───────────────────┬───────────────────┤
│  Employee Master │    Contract      │   Leave Stocks    │    Timesheet      │
│  - Name, PIN     │  - Pay basis     │  - Sick (full)    │  - Hours/day      │
│  - Base salary   │  - Weekly hours  │  - Sick (half)    │  - Absent y/n     │
│  - Housing allow │  - Housing type  │  - Annual leave   │  - Sick y/n       │
│    (if cash)     │  - Housing value │                   │  - OT hours       │
└────────┬─────────┴────────┬─────────┴─────────┬─────────┴─────────┬─────────┘
         │                  │                   │                   │
         ▼                  ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LEAVE ALLOCATION ENGINE                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            GROSS PAY ENGINE                                  │
│              (includes cash housing allowance if applicable)                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEDUCTIONS ENGINE                                    │
│                      (NSSF, SHIF, AHL calculated)                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            PAYE ENGINE                                       │
│            (adds non-cash housing benefit to taxable income)                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NET PAY                                         │
│                  (cash only - no non-cash benefits)                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Leave Allocation Engine

Determines how absent days are categorized and paid.

```
                    ┌─────────────────┐
                    │   For each      │
                    │   absent day    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Consolidated   │
                    │  salary?        │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │ YES                         │ NO
              ▼                             ▼
     ┌─────────────────┐           ┌─────────────────┐
     │ Is this         │           │  Was employee   │
     │ rostered        │           │     sick?       │
     │ off-time?       │           └────────┬────────┘
     └────────┬────────┘                    │
              │                  ┌──────────┴──────────┐
       ┌──────┴──────┐           │ YES                 │ NO
       │ YES         │ NO        ▼                     ▼
       ▼             ▼    ┌─────────────┐      ┌─────────────┐
  ┌─────────┐  ┌─────────┐│ Sick full   │      │ Annual leave│
  │ No leave│  │ Sick    ││ stock > 0?  │      │ stock > 0?  │
  │ tracked │  │ during  │└──────┬──────┘      └──────┬──────┘
  │ (built  │  │ duty:   │       │                    │
  │ into    │  │ process │  ┌────┴────┐          ┌────┴────┐
  │ roster) │  │ as sick │  │YES    NO│          │YES    NO│
  └─────────┘  └─────────┘  ▼         ▼          ▼         ▼
                       ┌──────┐ ┌─────────┐ ┌──────┐ ┌──────┐
                       │SICK  │ │Half     │ │ANNUAL│ │UNPAID│
                       │FULL  │ │stock>0? │ │LEAVE │ │LEAVE │
                       └──────┘ └────┬────┘ └──────┘ └──────┘
                                     │
                                ┌────┴────┐
                                │YES    NO│
                                ▼         ▼
                           ┌──────┐ ┌──────┐
                           │SICK  │ │UNPAID│
                           │HALF  │ │LEAVE │
                           └──────┘ └──────┘
```

**Consolidated salary employees:** Annual leave is built into the roster. Rostered off-time (e.g., one week off per month) is not counted as leave usage and no annual leave stock is decremented. Sick leave is only tracked when illness occurs during scheduled active duty periods.

**Outputs:**
- Days at full pay (worked + sick full + annual leave)
- Days at half pay (sick half)
- Days unpaid
- Updated leave stock balances (annual leave not tracked for consolidated salary)

---

## 2. Gross Pay Engine

Calculates total cash earnings before deductions.

```
┌─────────────────┐
│   Contract      │
│   pay basis?    │
└────────┬────────┘
         │
    ┌────┴────┬─────────────────┬─────────────────┬─────────────────┬─────────────────┐
    │         │                 │                 │                 │                 │
    ▼         ▼                 ▼                 ▼                 ▼                 ▼
┌────────┐ ┌────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│CONSOLI-│ │ HOURLY │   │  PRORATED   │   │FIXED MONTHLY│   │FIXED MONTHLY│   │FIXED MONTHLY│
│DATED   │ │        │   │  MIN WAGE   │   │ (no leave)  │   │(with leave) │   │(with sick   │
│SALARY  │ │        │   │             │   │             │   │             │   │ during duty)│
└───┬────┘ └───┬────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
    │          │               │                 │                 │                 │
    ▼          ▼               ▼                 ▼                 ▼                 ▼
┌────────┐ ┌────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│        │ │Divisor │   │ Std hours = │   │             │   │ Daily rate =│   │ Daily rate =│
│Base pay│ │=(wkly× │   │ wkly hrs × 4│   │ Base pay =  │   │ base / work │   │ base / work │
│= base  │ │52)/12  │   │             │   │ base salary │   │ days in mo  │   │ days in mo  │
│salary  │ │        │   │ Fraction =  │   │             │   │             │   │             │
│        │ │Hourly =│   │ worked /    │   │             │   │ Base pay =  │   │ Base pay =  │
│(same   │ │base /  │   │ std hrs     │   │             │   │ (full days ×│   │ (duty days ×│
│every   │ │divisor │   │             │   │             │   │  rate) +    │   │  rate) +    │
│month)  │ │        │   │ Base pay =  │   │             │   │ (half days ×│   │ (sick full ×│
│        │ │Base =  │   │ base ×      │   │             │   │  rate × 0.5)│   │  rate) +    │
│        │ │rate ×  │   │ fraction    │   │             │   │             │   │ (sick half ×│
│        │ │hours   │   │             │   │             │   │             │   │  rate × 0.5)│
└───┬────┘ └───┬────┘   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
         │
         ▼
┌─────────────────┐
│  OVERTIME?      │
└────────┬────────┘
         │
    ┌────┴────┐
    │ YES     │ NO
    ▼         │
┌─────────┐   │
│ Add:    │   │
│ OT 1.5x │   │
│ OT 2.0x │   │
└────┬────┘   │
     │        │
     └────┬───┘
          │
          ▼
┌─────────────────────────────────────┐
│  CASH HOUSING ALLOWANCE?            │
│  (employer does NOT provide housing)│
└────────────────┬────────────────────┘
                 │
            ┌────┴────┐
            │ YES     │ NO
            ▼         │
       ┌─────────┐    │
       │ Add to  │    │
       │ base pay│    │
       └────┬────┘    │
            │         │
            └────┬────┘
                 │
                 ▼
          ┌─────────────┐
          │  GROSS PAY  │
          │  (cash)     │
          └─────────────┘
```

---

## 3. Deductions Engine

Calculates statutory deductions (allowable against tax).

```
              ┌─────────────┐
              │  GROSS PAY  │
              └──────┬──────┘
                     │
     ┌───────────────┼───────────────┬───────────────┐
     │               │               │               │
     ▼               ▼               ▼               ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  NSSF   │    │  NSSF   │    │  SHIF   │    │   AHL   │
│ Tier 1  │    │ Tier 2  │    │         │    │         │
└────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
     │              │              │              │
     ▼              ▼              ▼              ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ 6% of   │    │ 6% of   │    │ 2.75%   │    │ 1.5%    │
│ gross   │    │ (gross  │    │ of      │    │ of      │
│ up to   │    │ - LEL)  │    │ gross   │    │ gross   │
│ LEL     │    │ capped  │    │         │    │         │
│         │    │ at UEL  │    │ Min:    │    │         │
│ Max:    │    │         │    │ 300     │    │         │
│ 540     │    │ Max:    │    │         │    │         │
│         │    │ 5,940   │    │         │    │         │
└────┬────┘    └────┬────┘    └────┬────┘    └────┬────┘
     │              │              │              │
     └──────────────┴──────┬───────┴──────────────┘
                           │
                           ▼
                 ┌───────────────────┐
                 │ TOTAL ALLOWABLE   │
                 │ DEDUCTIONS        │
                 │ = NSSF T1 + T2    │
                 │   + SHIF + AHL    │
                 └───────────────────┘
```

**Year 4 NSSF Limits (Feb 2026+):**
- LEL (Lower Earnings Limit): 9,000
- UEL (Upper Earnings Limit): 108,000

---

## 4. Non-Cash Housing Benefit (Quarters)

Only applies when employer PROVIDES housing. NOT part of gross pay.

```
┌─────────────────┐     ┌─────────────────┐
│   GROSS PAY     │     │  Market rent    │
│   (cash)        │     │  of quarters    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       │
┌─────────────────┐              │
│ 15% of gross    │              │
│ (10% for agri)  │              │
└────────┬────────┘              │
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ HOUSING BENEFIT │
            │ = higher of:    │
            │ - 15% of gross  │
            │ - market rent   │
            └────────┬────────┘
                     │
                     ▼
            ┌─────────────────┐
            │ Added to        │
            │ TAXABLE INCOME  │
            │ (not to gross)  │
            └─────────────────┘
```

---

## 5. PAYE Engine

Calculates income tax.

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────────┐
│  GROSS PAY  │    │ HOUSING BENEFIT │    │ TOTAL ALLOWABLE     │
│  (cash)     │    │ (non-cash, if   │    │ DEDUCTIONS          │
│             │    │  quarters)      │    │                     │
└──────┬──────┘    └────────┬────────┘    └──────────┬──────────┘
       │                    │                        │
       └────────────────────┴────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ CHARGEABLE PAY  │
                   │ = Gross         │
                   │   + Housing     │
                   │     benefit     │
                   │   - Deductions  │
                   └────────┬────────┘
                            │
                            ▼
              ┌──────────────────────────┐
              │     APPLY TAX BANDS      │
              │     (progressive)        │
              ├──────────────────────────┤
              │ First 24,000    → 10%    │
              │ Next 8,333      → 25%    │
              │ Next 467,667    → 30%    │
              │ Next 300,000    → 32.5%  │
              │ Above 800,000   → 35%    │
              └────────────┬─────────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │   GROSS TAX     │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │ PERSONAL RELIEF │
                  │ - 2,400         │
                  └────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │     PAYE        │
                  │ (min zero)      │
                  └─────────────────┘
```

---

## 6. Net Pay Calculation

```
┌─────────────┐
│  GROSS PAY  │
│  (cash)     │
└──────┬──────┘
       │
       │    ┌─────────────┐
       │    │  NSSF T1    │
       │    ├─────────────┤
       ├───▶│  NSSF T2    │
       │    ├─────────────┤
       │    │  SHIF       │
       │    ├─────────────┤
       │    │  AHL        │
       │    ├─────────────┤
       │    │  PAYE       │
       │    └──────┬──────┘
       │           │
       ▼           ▼
┌─────────────────────────┐
│        NET PAY          │
│ = Gross - NSSF T1       │
│        - NSSF T2        │
│        - SHIF           │
│        - AHL            │
│        - PAYE           │
└─────────────────────────┘
```

**Note:** Non-cash housing benefit is NOT in this calculation. It affected PAYE amount but is not deducted from net pay.

---

## Complete Data Flow Summary

```
INPUTS                          PROCESSING                      OUTPUTS
──────                          ──────────                      ───────

Employee Master ─────┐
  (+ cash housing    │
   allowance)        │
                     │
Contract ────────────┼──────▶ Leave Allocation ──▶ Days by pay type
                     │              │
Leave Stocks ────────┤              │
                     │              ▼
Timesheet ───────────┘        Gross Pay Calc ────▶ GROSS PAY (cash)
                                    │                  │
                                    │                  │
                                    ▼                  ▼
                              Deductions Calc ───▶ NSSF, SHIF, AHL
                                    │                  │
                                    │                  │
                    Non-cash ───────┤                  │
                    housing         ▼                  │
                    benefit     PAYE Calc ───────▶ PAYE
                    (quarters)      │                  │
                                    │                  │
                                    ▼                  ▼
                              Net Pay Calc ──────▶ NET PAY (cash)
                                    │
                                    ▼
                              ┌───────────┐
                              │  OUTPUTS  │
                              ├───────────┤
                              │ Paystub   │
                              │ Bank CSV  │
                              │ Reports   │
                              │ Updated   │
                              │ leave     │
                              │ stocks    │
                              └───────────┘
```

---

## Housing Summary

| Scenario | Treatment | In Gross Pay? | In PAYE Calc? | In Net Pay? |
|----------|-----------|---------------|---------------|-------------|
| Cash housing allowance | Part of salary | YES | YES (as part of gross) | YES (as part of gross) |
| Non-cash quarters | Taxable benefit | NO | YES (added to chargeable pay) | NO |
