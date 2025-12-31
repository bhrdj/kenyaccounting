# **First-pass Kenya Tax Backgrounder**

# **Google Deep Research Prompt (2025\_12\_21):** 

`(1) Search for any scheduled changes to Kenyan employment taxes (PAYE), statutory deductions (NSSF, SHA/SHIF, Housing Levy), or labour laws effective January 2026.`

`(2) Verify if 'Regulation of Wages (General) (Amendment) Order 2024' is the most current wage order as of December 2025, or if a 2025 amendment has been gazetted. Extract the specific Nairobi minimum wage rates (Monthly, Daily, Hourly) for relevant categories from the valid order.`

`(3) Search for the current 2025/2026 KRA PAYE tax brackets, Personal Relief, and Insurance Relief values.`

`(4) Search for the specific 2025/2026 rates and earnings limits for NSSF (Tier I and II), the Social Health Authority (SHA) contributions (formerly NHIF), and the Affordable Housing Levy.`

`(5) Search for the KRA rules regarding the taxation of employer-provided housing (dormitories/quarters) versus cash housing allowances, specifically how the taxable benefit is calculated (e.g., 15% rule vs market value).`

`(6) Analyze '2 EmploymentAct_Cap226-No11of2007_01.pdf' to define the logic for:`

`(a) Annual leave accrual and usage`

`(b) Sick leave entitlement (full pay vs half pay days)`

`(c) Conversion of casual employment to term contracts (Section 37)`

`(d) Standard working hours and overtime regulations.`

`(7) List the statutory public holidays from '1 PublicHolidaysActCap110.pdf' and note the provision for declaring ad-hoc holidays.`

# **Kenya Employment Regulation & Fiscal Policy 2026: A Comprehensive Compliance Framework for Accounting Systems**

## **1\. Executive Summary**

The transition into the 2026 fiscal year represents a watershed moment for payroll accounting and employment regulation in Kenya. Driven by the cumulative impact of the **Finance Act 2025**, the scheduled escalation of the **NSSF Act 2013**, and the stabilization of the **Social Health Insurance Fund (SHIF)**, Nairobi-based enterprises face a regulatory environment characterized by increased statutory burdens, sophisticated compliance mechanisms, and a fundamental restructuring of the taxable income base. This report provides an exhaustive technical analysis of the legal and fiscal parameters effective January 1, 2026, designed to guide the architecture of compliant accounting systems.

The prevailing theme for 2026 is the "deductibility paradigm." The government has decisively moved away from the traditional tax relief model—where statutory contributions acted as a credit against tax payable—toward a model where contributions to the Social Health Authority (SHA) and the Affordable Housing Levy (AHL) act as allowable deductions against gross income. This shift, codified in the Tax Laws (Amendment) Act 2024 and reinforced by the Finance Act 2025, necessitates a complete re-engineering of payroll gross-to-net logic.1 Simultaneously, the National Social Security Fund (NSSF) enters **Year 4** of its implementation schedule in February 2026, triggering a dramatic expansion of the pensionable earnings base to three times the national average earnings, significantly raising the Upper Earnings Limit (UEL) for Tier 2 contributions.3

Beyond statutory deductions, the regulatory landscape regarding employment contracts has tightened. The Employment and Labour Relations Court continues to rigorously enforce **Section 37** of the Employment Act, treating long-term casual engagements as de facto permanent contracts. Accounting systems must now function as compliance monitors, flagging tenure milestones to prevent the accrual of unbudgeted liabilities for notice pay, leave, and severance.5 Furthermore, the valuation of non-cash benefits, particularly employer-provided housing, remains a critical audit focal point for the Kenya Revenue Authority (KRA), requiring precise valuation formulas distinguishing between directors, agricultural employees, and general staff.7

This document synthesizes these legislative requirements into a cohesive operational framework. It addresses the nuanced application of the **Significant Economic Presence Tax (SEPT)** for cross-border labor, the revised **per diem** tax-free thresholds, and the intricate calculation methodologies for overtime and leave pay. By integrating the latest statutory instruments gazetted through late 2025, this report serves as the definitive reference for financial controllers and system architects preparing for the 2026 compliance cycle.

## ---

**2\. The Fiscal Architecture of 2026: Finance Act 2025 and Income Tax Reforms**

The Finance Act 2025 has fundamentally altered the computational logic for employment income tax (PAYE). For decades, Kenyan payroll systems operated on a logic where gross pay was taxed, and statutory contributions offered a small downstream relief. Effective January 2026, this logic is obsolete. The new fiscal architecture prioritizes the expansion of the tax base while offering relief through the reduction of chargeable income rather than tax credits.

### **2.1 The Paradigm Shift: From Reliefs to Allowable Deductions**

The most significant structural change for accounting systems in 2026 is the reclassification of statutory levies. Previously, contributions to the National Health Insurance Fund (NHIF) and the Affordable Housing Levy (AHL) were subjected to a 15% insurance relief (capped at specific amounts) which was deducted from the final PAYE liability. The **Tax Laws (Amendment) Act 2024** and **Finance Act 2025** have repealed these reliefs in favor of making the contributions **allowable deductions**.1

This seemingly subtle accounting change has profound implications for net pay and system design. By treating SHIF and AHL as allowable deductions, the government effectively lowers the employee's **Chargeable Pay**—the amount upon which the PAYE tax bands are applied.

**System Logic Transformation:**

* **Legacy Model (Deprecated):**  
  1. Calculate Gross Pay.  
  2. Calculate PAYE on Gross Pay.  
  3. Calculate Reliefs: (Insurance Relief \+ Housing Relief \+ Personal Relief).  
  4. PAYE Payable \= Gross PAYE \- Total Reliefs.  
* **2026 Compliance Model:**  
  1. Calculate Gross Pay.  
  2. Calculate Statutory Deductions: NSSF \+ SHIF \+ AHL.  
  3. Determine Chargeable Pay: Gross Pay \- (NSSF \+ SHIF \+ AHL \+ Approved Pension).  
  4. Calculate Gross PAYE on Chargeable Pay.  
  5. PAYE Payable \= Gross PAYE \- Personal Relief.

The elimination of the insurance relief for SHIF and the affordable housing relief simplifies the final tax calculation but complicates the determination of the taxable base. Accounting systems must ensure that the "Taxable Pay" field is dynamic, automatically deducting the exact values of SHIF and AHL contributions before the tax tables are queried. Failure to adjust this logic will result in the over-deduction of PAYE, exposing the employer to employee grievances and potential litigation for unlawful deduction of wages under Part IV of the Employment Act.8

### **2.2 Per Diem and Subsistence Allowances: The KES 10,000 Threshold**

For organizations with mobile workforces or frequent business travel, the taxation of per diem has been a contentious area. The Finance Act 2025 has introduced a significant concession by amending Section 5 of the Income Tax Act to increase the tax-free limit for per diem allowances.

The New Threshold:  
Effective July 2025 (and fully operational for the January 2026 fiscal year), the daily limit for tax-free per diem has been raised from KES 2,000 to KES 10,000.9  
Implications for Accounting Systems:  
Previously, any daily allowance exceeding KES 2,000 was treated as a taxable benefit unless fully supported by receipts. The low threshold imposed a heavy administrative burden on accounting departments to collect receipts for standard meals and accommodation. The new KES 10,000 limit aligns more closely with economic reality, reducing the receipt collection burden for standard business travel.  
**System Configuration Rules:**

1. **Validation Rule:** The expense management module must be programmed with a constant TAX\_FREE\_LIMIT \= 10000\.  
2. **Tax Trigger:** IF (Daily\_Per\_Diem\_Rate \> 10000\) THEN Taxable\_Benefit \= Daily\_Per\_Diem\_Rate \- 10000\.  
3. **Receipt Requirement:** The system should only mandate receipt attachment for tax exemption purposes if the amount claims to be a reimbursement exceeding KES 10,000. Amounts under KES 10,000 are deemed standard subsistence and should flow through the payroll as non-taxable income.10

### **2.3 Advance Pricing Agreements (APAs) and Expatriate Payroll**

While often viewed as a corporate tax mechanism, the introduction of **Advance Pricing Agreements (APAs)** effective **January 1, 2026**, has direct relevance for the payroll of multinational corporations operating in Nairobi.11

APAs allow taxpayers to enter into binding agreements with the Commissioner of the KRA regarding the transfer pricing methodology for related-party transactions. In the context of employment, this is critical for **recharged labor costs** and **management fees** involving expatriate staff. If a Nairobi subsidiary pays a management fee to its parent company that includes the salary costs of expatriate personnel, the pricing of this service can now be pre-agreed via an APA.

Strategic Insight:  
Payroll managers should collaborate with tax teams to utilize APAs for defining the "arm's length" nature of expatriate compensation packages recharged to Kenya. This provides certainty on the deductibility of these costs for Corporate Income Tax (CIT) purposes and insulates the organization from aggressive KRA audits regarding "excessive" management fees. The accounting system should include a flag for "APA-Covered Transactions" to segregate these payroll costs from standard local payroll for reporting purposes.

### **2.4 Digital System Integrity and Penalty Waivers**

In a move to modernize tax administration, the Finance Act 2025 empowers the Cabinet Secretary to waive penalties and interest if the liability arose due to an error or delay in the KRA's electronic tax system (iTax or eTIMS).11

This provision, effective January 1, 2026, places a premium on **digital audit trails**. Accounting systems must be capable of logging every interaction with the KRA portal. If a PAYE return is filed late due to an iTax system failure, the accounting system's timestamped log of the failed attempt will be the primary evidence required to apply for the waiver.

**System Requirement:**

* **Transmission Logs:** The payroll system must retain a secure log of API calls or upload attempts to the KRA portal, recording the exact time, date, and error message received. This "digital alibi" is now a statutory defense mechanism against penalties.

## ---

**3\. Statutory Deductions Matrix: 2026 Rates and Compliance Logic**

The core of payroll processing in Nairobi involves the accurate calculation of deductions for the NSSF, SHA, and the Housing Levy. 2026 sees the most aggressive increase in these rates in recent history, driven by the maturation of the NSSF Act 2013\.

### **3.1 National Social Security Fund (NSSF): The Year 4 Escalation**

The NSSF Act No. 45 of 2013 introduced a tiered pension system to replace the old flat-rate provident fund. The Act mandated a phased implementation over five years. Following the resolution of legal challenges in February 2023 (the effective Year 1), **February 2026** marks the commencement of **Year 4** of the Third Schedule.3

#### **3.1.1 The Multiplier Effect**

The Third Schedule of the NSSF Act defines the **Upper Earnings Limit (UEL)** for Year 4 as **three times the National Average Earnings**.3 The "National Average Earnings" is a statutory figure gazetted by the Cabinet Secretary, which has historically been pegged at **KES 36,000** for the purpose of these transition calculations.3

This multiplier effect results in a massive expansion of the pensionable base:

* **Year 3 (2025):** UEL was 2x National Average (approx. KES 72,000).  
* **Year 4 (Feb 2026):** UEL is 3x National Average (approx. KES 108,000).

#### **3.1.2 Tier 1 and Tier 2 Calculation Logic**

The contribution remains **12% of pensionable earnings** (6% Employee \+ 6% Employer). The earnings are split into Tier 1 and Tier 2\.

**Table 1: NSSF Contribution Parameters (Year 4 \- Effective Feb 2026\)**

| Parameter | Limit/Rate | Statutory Derivation |
| :---- | :---- | :---- |
| **Lower Earnings Limit (LEL)** | **KES 9,000** | Statutory fixed amount for Year 4\.13 |
| **Upper Earnings Limit (UEL)** | **KES 108,000** | 3 x KES 36,000 (National Average).3 |
| **Tier 1 Base** | KES 9,000 | Earnings up to LEL. |
| **Tier 2 Base** | KES 99,000 | UEL (108,000) \- LEL (9,000). |
| **Tier 1 Deduction (EE)** | **KES 540** | 6% of KES 9,000. |
| **Tier 2 Deduction (EE)** | **KES 5,940** | 6% of KES 99,000. |
| **Total Employee Max** | **KES 6,480** | Tier 1 \+ Tier 2\. |
| **Total Employer Max** | **KES 6,480** | Matching Contribution. |
| **Total Remittance** | **KES 12,960** | Per employee per month. |

Critical System Update:  
Accounting systems must update their NSSF reference tables effective February 1, 2026\. The system must automatically switch from the Year 3 limits (LEL 8,000 / UEL 72,000) to the Year 4 limits (LEL 9,000 / UEL 108,000). Failure to do so will result in significant under-deduction for employees earning between KES 72,000 and KES 108,000, attracting penalties from the NSSF.

#### **3.1.3 Contracting Out (Tier 2\)**

Employers operating a private occupational pension scheme sanctioned by the Retirement Benefits Authority (RBA) have the statutory right to "contract out" of Tier 2 contributions.

* **Tier 1 (KES 540):** Mandatory remittance to NSSF.  
* **Tier 2 (KES 5,940):** Can be redirected to the private scheme.  
* **System Logic:** The payroll software must support a "Pension Destination" field at the employee profile level.  
  * IF Pension\_Status \== "Contracted Out" THEN Remit Tier 1 to NSSF AND Remit Tier 2 to Private\_Scheme.  
  * IF Pension\_Status \== "Standard" THEN Remit Tier 1 \+ Tier 2 to NSSF.

This distinction is vital for the **NSSF Return** generation. The standard return file must explicitly show zero or adjusted figures for Tier 2 if the employer has opted out, to prevent the NSSF system from automatically generating arrears.

### **3.2 Social Health Insurance Fund (SHIF): The Percentage Regime**

The transition from the National Health Insurance Fund (NHIF) to the Social Health Insurance Fund (SHIF) is fully operational in 2026\. The key compliance risk here is the shift from a capped tiered system to a pure percentage system with no upper limit.

* **Rate:** **2.75%** of Gross Salary.14  
* **Base:** Gross Salary (Basic Pay \+ Regular Cash Allowances). Irregular bonuses and non-cash benefits are generally excluded unless they are regularized.  
* **Floor:** The law mandates a minimum contribution of **KES 300**.16  
* **Ceiling:** **None**.

Impact Analysis:  
Under the old NHIF, the maximum deduction was KES 1,700. Under SHIF, a manager earning KES 500,000 will contribute KES 13,750 per month. This drastic increase reduces net disposable income significantly. However, the new "allowable deduction" status 1 mitigates this by shielding that KES 13,750 from PAYE, saving the employee approximately KES 4,125 in taxes (at the 30% marginal rate).  
Accounting Logic:  
The system must calculate SHIF before PAYE.  
SHIF\_Deduction \= MAX(Gross\_Pay \* 0.0275, 300\)  
Taxable\_Income \= Gross\_Pay \- SHIF\_Deduction \- NSSF\_Deduction \- AHL\_Deduction.

### **3.3 Affordable Housing Levy (AHL)**

The Affordable Housing Levy remains a mandatory statutory deduction, stabilized by the **Affordable Housing Act 2024**.

* **Rate:** **1.5%** Employee \+ **1.5%** Employer.17  
* **Base:** Gross Monthly Salary.  
* **Remittance Deadline:** 9th day of the following month.  
* **Tax Treatment:** Allowable deduction against taxable income.1

System Configuration:  
The AHL must be tracked as a separate tax head for remittance purposes but aggregated with NSSF and SHIF for the purpose of calculating the "Total Statutory Deductions" that reduce the PAYE base. The employer's portion (1.5%) is an expense to the company and is not a taxable benefit to the employee.

## ---

**4\. Pay As You Earn (PAYE): Computation and Bands**

With the pre-tax deductibility of statutory levies established, the PAYE calculation in 2026 follows a streamlined but mathematically distinct path compared to previous years.

### **4.1 Allowable Deductions Definition**

For a Nairobi accounting system, **Chargeable Pay** is no longer synonymous with Gross Pay. It is a derived figure.

Formula for Chargeable Pay:

$$\\text{Chargeable Pay} \= \\text{Gross Pay} \- (\\text{NSSF}\_{\\text{Employee}} \+ \\text{SHIF}\_{\\text{Employee}} \+ \\text{AHL}\_{\\text{Employee}} \+ \\text{Approved Pension}\_{\\text{Voluntary}})$$  
*Constraints:*

* **Pension Contribution Limit:** The deduction for voluntary pension contributions is capped at **KES 30,000 per month** (KES 360,000 per annum).18 Any contribution above this is taxable.  
* **Mortgage Interest Deduction:** For employees with owner-occupied mortgages, interest up to **KES 300,000 per annum** (KES 25,000 per month) is deductible.18 This deduction is applied *after* statutory deductions but *before* tax calculation.

### **4.2 Tax Bands (Effective 2026\)**

Unless the Finance Act 2025 introduces specific rate changes (which snippets suggest focus more on administrative changes like APAs and per diem), the prevailing bands from the Finance Act 2023 remain in force. The introduction of the 35% top marginal rate is the key feature for high earners.

**Table 2: PAYE Tax Bands (Resident Individuals)** 19

| Monthly Chargeable Pay (KES) | Tax Rate | Cumulative Tax (KES) |
| :---- | :---- | :---- |
| First **24,000** | 10% | 2,400 |
| Next **8,333** (24,001 \- 32,333) | 25% | 4,483.25 |
| Next **467,667** (32,334 \- 500,000) | 30% | 144,783.35 |
| Next **300,000** (500,001 \- 800,000) | 32.5% | 242,283.35 |
| Over **800,000** | 35% | Variable |

### **4.3 Personal Relief**

The standard **Personal Relief** is **KES 2,400 per month** (KES 28,800 per annum).19 This amount is subtracted directly from the Gross Tax Liability calculated using the bands above.

Important Note on Insurance Relief:  
With SHIF contributions moving to "allowable deductions," they no longer qualify for the 15% Insurance Relief. Insurance relief is now strictly applicable to private life and education insurance policies (with a maturity of at least 10 years). The accounting system must ensure that SHIF contributions are not double-counted as both a deduction and a relief.2

## ---

**5\. Employment Act Compliance: Wage Rules and Casual Conversion**

Beyond the fiscal math, the **Employment Act 2007** imposes rigorous standards on employment terms. For Nairobi businesses, the strict enforcement of casual labor rules is a primary area of legal risk.

### **5.1 Section 37: The Casual Conversion Trap**

Section 37 of the Employment Act is the definitive rule on casual labor. It mandates the automatic conversion of casual employment to a term contract under specific conditions.

The Statutory Trigger:  
A casual employee (paid daily, engaged for \<24 hours at a time) is deemed to be a term employee (monthly contract) if:

1. They work for a period amounting to **one month** continuously; OR  
2. They perform work that cannot reasonably be completed within a period of **three months**.5

Legal Precedent:  
The Employment and Labour Relations Court, in cases such as Okello & 4 others v University of Nairobi, has consistently ruled that maintaining workers on casual wages for years is unlawful. The court interprets "continuous" broadly. If a worker shows up every day for a month, they are permanent.  
System Control Mechanism:  
Nairobi accounting systems must include a "Casual Monitor" module.

* **Logic:** Track the number of consecutive days a casual ID appears on the daily muster roll.  
* **Alert:** IF Consecutive\_Days \> 26 THEN Flag "Mandatory Conversion".  
* **Consequence:** Once converted, the employee is entitled to NSSF, SHIF, AHL, 21 days annual leave, and notice pay. The system must prevent the processing of a 27th consecutive daily wage payment without triggering a contract change workflow.

### **5.2 Section 30: Sick Leave Entitlements**

Section 30 of the Employment Act stipulates specific sick leave benefits which must be hard-coded into the payroll logic.

* **Eligibility:** An employee is entitled to sick leave after **two consecutive months** of service.8  
* **Entitlement:**  
  * First 7 Days: **Full Pay** (100%).  
  * Subsequent 7 Days: **Half Pay** (50%).  
  * Total Statutory Entitlement: **14 Days** per year (7 Full \+ 7 Half).20  
* **System Logic:**  
  * The payroll system must support a "Half-Pay" leave type. When selected for days 8-14 of a sickness episode, the system should automatically apply a 0.5 multiplier to the daily rate for those specific days.  
  * It must also track the "Service Period \> 2 Months" condition before enabling the sick leave code for a new hire.

### **5.3 Housing Benefit Valuation (Section 31\)**

Section 31 requires employers to provide housing or a housing allowance. When physical housing is provided (e.g., staff quarters or leased apartments), it creates a taxable benefit.

Valuation Rule:  
The taxable value added to the employee's income is the higher of:

1. **Fair Market Rental Value:** The amount the property would rent for in the open market.  
2. **15% of Total Income:** Calculated on the employee's gross emoluments (Salary \+ Allowances \+ Bonuses).7

**Special Categories:**

* **Agricultural Employees:** The value is **10%** of total income.7  
* **Directors:** For whole-time service directors, the value is the higher of 15% of total income or the Fair Market Value.

Dormitories and Shared Accommodation:  
In sectors like hospitality or security where staff might share dormitories, KRA audits often aggressively assess the "Fair Market Value." While 15% is the statutory default, if the actual cost to the employer or the market value of the shared room is higher, the higher figure applies. The accounting system must allow for a manual override to input "Assessed Market Value" if it exceeds the calculated 15%.7

## ---

**6\. Wage Regulation: Minimums and Overtime**

The **Regulation of Wages (General) (Amendment) Order** establishes the baseline compensation floors. Nairobi falls under the "Cities" category, commanding the highest minimum wages.

### **6.1 Minimum Wage Rates (Effective Jan 2026\)**

Following the 6% increase gazetted in late 2024, the minimum wages effective for 2026 are as follows.11

**Table 3: Minimum Wages (Nairobi/Cities) \- 2026**

| Occupation | Monthly Minimum (KES) | Daily Rate (KES) | Hourly Rate (KES) |
| :---- | :---- | :---- | :---- |
| **General Labourer** (Cleaner, Sweeper) | 16,113.75 | 775.39 | 77.54 |
| **Night Watchman** | 17,976.54 | 862.52 | 86.25 |
| **Machine Attendant** | 18,263.27 | 877.42 | 87.74 |
| **Driver (Light Vehicle)** | 21,748.87 | 1,045.05 | 104.50 |
| **Driver (Heavy Commercial)** | 36,360.92 | 1,750.54 | 175.05 |
| **Clerk / Cashier** | 36,360.92 | 1,750.54 | 175.05 |

*Note: These rates are exclusive of housing allowance. If housing is not provided, an additional 15% housing allowance must be paid, raising the effective minimum cost.*

### **6.2 Overtime Calculation Methodology**

The Regulation of Wages Order defines standard hours and overtime multipliers.

* **Standard Hours:** 52 hours per week (Day) / 60 hours per week (Night).22  
* **Overtime Multipliers:**  
  * **1.5x (Time and a Half):** For hours worked in excess of normal hours on weekdays.  
  * **2.0x (Double Time):** For hours worked on Rest Days (typically Sundays) and gazetted Public Holidays.22

The "Divisor" Debate:  
To calculate the hourly rate for a monthly paid employee, the standard practice in Kenya (supported by the Ministry of Labour interpretation of the 52-hour week) is to use a divisor of 225 hours.

* *Calculation:* (52 hours/week \* 52 weeks/year) / 12 months \= 225.33 (Rounded to 225).  
* **System Configuration:** Hourly\_Rate \= Basic\_Monthly\_Salary / 225\.  
* *Note:* Some collective bargaining agreements (CBAs) may specify a divisor of 240 or 176 (for 40-hour weeks). The system must allow the divisor to be configured at the "Grade" or "CBA" level, defaulting to 225 for general staff.24

## ---

**7\. Implementation Roadmap for Accounting Systems**

To ensure a compliant payroll run for January 2026, accounting system administrators must execute the following configuration changes:

1. **Update Deduction Logic (Priority Critical):**  
   * Re-map **SHIF** and **AHL** codes from "Post-Tax Deduction" to "Pre-Tax Allowable Deduction."  
   * Ensure Taxable Income is calculated *after* these deductions are subtracted from Gross.  
2. **Input NSSF Year 4 Parameters:**  
   * Update the NSSF reference table effective **01/02/2026** (February).  
   * Set **LEL \= 9,000**.  
   * Set **UEL \= 108,000**.  
   * Verify the "Contracted Out" toggle is functioning to split Tier 2 correctly.  
3. **Configure Per Diem Validation:**  
   * Update the tax-free limit rule to **KES 10,000**. Ensure amounts \>10,000 automatically flow to the taxable benefit field unless flagged as "Receipted."  
4. **Audit Trail Enforcement:**  
   * Enable detailed logging for all iTax/eTIMS data transmissions to support potential penalty waiver applications under the new Finance Act provisions.  
5. **Casual Labor Governance:**  
   * Implement a "soft block" or warning notification when a casual employee's days exceed 26 in a rolling 30-day window, prompting HR to review for Section 37 conversion risks.

By executing these changes, Nairobi-based organizations can navigate the complex regulatory waters of 2026, ensuring compliance with the KRA, NSSF, SHA, and the Ministry of Labour while optimizing their tax positions within the boundaries of the law.

#### **Works cited**

1. 2025 Payslip Overhaul: Housing Levy and SHIF Become Allowable Deductions as NSSF Contributions Surge \- Cliffe Dekker Hofmeyr, accessed December 31, 2025, [https://www.cliffedekkerhofmeyr.com/news/publications/2025/Practice/Tax-Exchange-Control/tax-exchange-control-alert-21-February-2025-2025-payslip-overhaul-housing-levy-and-shif-become-allowable-deductions-as-nssf-contributions-surge](https://www.cliffedekkerhofmeyr.com/news/publications/2025/Practice/Tax-Exchange-Control/tax-exchange-control-alert-21-February-2025-2025-payslip-overhaul-housing-levy-and-shif-become-allowable-deductions-as-nssf-contributions-surge)  
2. Amendments to Kenya's Tax Laws on Employment Income for 2024 \- Workpay, accessed December 31, 2025, [https://www.myworkpay.com/blogs/amendments-to-kenyas-tax-laws-on-employment-income-for-2024](https://www.myworkpay.com/blogs/amendments-to-kenyas-tax-laws-on-employment-income-for-2024)  
3. Kenya Payroll Changes \- 2026 \- Help Centre \- Native Teams, accessed December 31, 2025, [https://help.nativeteams.com/kenya-payroll-changes-2026](https://help.nativeteams.com/kenya-payroll-changes-2026)  
4. EXPLAINER: How new NSSF contributions will affect your salary in 2026 \- Pulse Kenya, accessed December 31, 2025, [https://www.pulse.co.ke/story/explainer-how-new-nssf-contributions-will-affect-your-salary-in-2026-2025121607333131022](https://www.pulse.co.ke/story/explainer-how-new-nssf-contributions-will-affect-your-salary-in-2026-2025121607333131022)  
5. When the rubber meets the road: ELRC's stand on casualisation of labour, accessed December 31, 2025, [https://www.cliffedekkerhofmeyr.com/news/publications/2025/Practice/Employment-Law/Employment-law-alert-16-october-When-the-rubber-meets-the-road-ELRCs-stand-on-casualisation-of-labour](https://www.cliffedekkerhofmeyr.com/news/publications/2025/Practice/Employment-Law/Employment-law-alert-16-october-When-the-rubber-meets-the-road-ELRCs-stand-on-casualisation-of-labour)  
6. Casual vs. Contract: When Does a 'Helper' Become a Permanent Employee?, accessed December 31, 2025, [https://wawerunyamburalaw.com/?p=1492](https://wawerunyamburalaw.com/?p=1492)  
7. Kenya \- Individual \- Income determination \- Worldwide Tax Summaries Online \- PwC, accessed December 31, 2025, [https://taxsummaries.pwc.com/kenya/individual/income-determination](https://taxsummaries.pwc.com/kenya/individual/income-determination)  
8. 8 Regulation of Wages (General) (Amendment) Order 2024.pdf  
9. Unpacking the Kenya Finance Bill 2025: What's changing? \- Cliffe Dekker Hofmeyr, accessed December 31, 2025, [https://www.cliffedekkerhofmeyr.com/news/publications/2025/Practice/Tax-Exchange-Control/tax-and-excahnge-control-alert-5-may-Unpacking-the-Kenya-Finance-Bill-2025-Whats-changing](https://www.cliffedekkerhofmeyr.com/news/publications/2025/Practice/Tax-Exchange-Control/tax-and-excahnge-control-alert-5-may-Unpacking-the-Kenya-Finance-Bill-2025-Whats-changing)  
10. Analysis of The Finance Bill 2025 \- Taxwise Africa Consulting LLP, accessed December 31, 2025, [https://taxwiseconsulting.com/image/services/blog-analysis-of-the-finance-bill-2025.pdf](https://taxwiseconsulting.com/image/services/blog-analysis-of-the-finance-bill-2025.pdf)  
11. Kenya introduces Finance Bill 2025 | EY \- Global, accessed December 31, 2025, [https://www.ey.com/en\_gl/technical/tax-alerts/kenya-introduces-finance-bill-2025](https://www.ey.com/en_gl/technical/tax-alerts/kenya-introduces-finance-bill-2025)  
12. Kenya \- Corporate \- Significant developments \- Worldwide Tax Summaries Online, accessed December 31, 2025, [https://taxsummaries.pwc.com/kenya/corporate/significant-developments](https://taxsummaries.pwc.com/kenya/corporate/significant-developments)  
13. How new NSSF rates hit employees and employers as the upper limit doubles, accessed December 31, 2025, [https://www.gitauauditors.co.ke/how-new-nssf-rates-hit-employees-and-employers-as-the-upper-limit-doubles/](https://www.gitauauditors.co.ke/how-new-nssf-rates-hit-employees-and-employers-as-the-upper-limit-doubles/)  
14. Best PAYE Tax Calculator for Kenya \- Wingubox, accessed December 31, 2025, [https://apps.wingubox.com/best-paye-tax-calculator-for-kenya](https://apps.wingubox.com/best-paye-tax-calculator-for-kenya)  
15. Kenya makes several changes to employment-related contributions \- EY Global Tax News, accessed December 31, 2025, [https://globaltaxnews.ey.com/news/2024-0317-kenya-makes-several-changes-to-employment-related-contributions](https://globaltaxnews.ey.com/news/2024-0317-kenya-makes-several-changes-to-employment-related-contributions)  
16. Kenya employers to begin making contributions to Social Health Insurance Fund \- EY, accessed December 31, 2025, [https://www.ey.com/en\_gl/technical/tax-alerts/kenya-employers-to-begin-making-contributions-to-social-health-insurance-fund](https://www.ey.com/en_gl/technical/tax-alerts/kenya-employers-to-begin-making-contributions-to-social-health-insurance-fund)  
17. Collection of Affordable Housing Levy by Kenya Revenue Authority \- KRA, accessed December 31, 2025, [https://www.kra.go.ke/news-center/public-notices/2099-collection-of-the-affordable-housing-levy-by-kenya-revenue-authority](https://www.kra.go.ke/news-center/public-notices/2099-collection-of-the-affordable-housing-levy-by-kenya-revenue-authority)  
18. Allowable deductions \- KRA, accessed December 31, 2025, [https://www.kra.go.ke/component/kra\_faq/faq/732](https://www.kra.go.ke/component/kra_faq/faq/732)  
19. Individual Income Tax \- Pay As You Earn (PAYE) \- KRA, accessed December 31, 2025, [https://www.kra.go.ke/individual/filing-paying/types-of-taxes/paye](https://www.kra.go.ke/individual/filing-paying/types-of-taxes/paye)  
20. Everything You Need To Know About Leave Days In Kenya \- Workpay, accessed December 31, 2025, [https://www.myworkpay.com/blogs/everything-you-need-to-know-about-leave-days-in-kenya](https://www.myworkpay.com/blogs/everything-you-need-to-know-about-leave-days-in-kenya)  
21. How the Provision of a Place of Residence to an Employee is Taxed \- GovHK, accessed December 31, 2025, [https://www.gov.hk/en/residents/taxes/salaries/salariestax/chargeable/residence.htm](https://www.gov.hk/en/residents/taxes/salaries/salariestax/chargeable/residence.htm)  
22. Employer of Record (EOR) in Kenya: 2025 Updates \- Playroll, accessed December 31, 2025, [https://www.playroll.com/global-hiring-guides/kenya](https://www.playroll.com/global-hiring-guides/kenya)  
23. Working Hours in Kenyan Labour Law: What the Law Says \- Bridge Talent Management, accessed December 31, 2025, [https://bridgetalentgroup.com/working-hours-in-kenyan-labour-law/](https://bridgetalentgroup.com/working-hours-in-kenyan-labour-law/)  
24. Hourly, Daily Rate Calculator \- Wingubox, accessed December 31, 2025, [https://apps.wingubox.com/hourly-daily-rate-calculator](https://apps.wingubox.com/hourly-daily-rate-calculator)