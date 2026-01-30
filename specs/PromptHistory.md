# HUMAN-TYPED Prompt History

These are the prompts typed by the human contributor, shown for better understanding of the development process to-date by other contributors. Note that this document doesn't include chatbot-generated prompts in the fashion of Gemini Deep Research etc. Those are included along with the research output. There may have been some human editing of those chatbot-generated prompts as well.

## Initial Gemini Deep Research Prompt

### Prompt Text
I have a Kenyan company (USA c Corp local branch) and I follow all the Kenyan employment act rules. located in Nairobi. but I have diverse contracts with my team.  some of them work three weeks a month, others have half-day saturdays, etc.  some are on 52 hour weeks contractually, others are on 45 hour week contracts, others are on monthly hour contracts, basically 52*3 weeks per month, others are casual paid daily. we follow employment act for sick days, half-pay sick days, annual leave, holidays (including surprise political holidays), etc. I also pay NSSF, sha, kra, housing allowance for most, provide dormitory housing for some. and all the other tax deductions on both sides like affordable housing, etc.

some work 52 hour weeks at minimum wage, some work fewer contract hours at above minimum wage, some work fewer hours "at" minimum wage, but getting pay a prorated part of the monthly minimum wage based on their decreased hours.

before I get into the accounting programming, let's do a thorough compilation of the regulations, *for the purpose of this code*. this isn't a general interest project, I need to get the key info organized to supply to the codebot's context to make the accounting system. including the tax brackets, nssf mandatory systems, etc.

### Attached PDF Files
- Public Holidays Act
- Kenya Employment Act
- Regulation of Wages Amendment 2024

## Gemini - Project Legal Framing and Documentation Prompts

### Prep
- **License Selection** pick a software license for a new accounting open source software in Kenya, in a public repo. want attribution.
- **Copyright Registration Timing Strategy** do I register copyright when the code is complete? when in the dev cycle for a public project
- **Compilation of License Detail** write a LICENSE_EXPLAINER.md including all of this detail, to put in the repo root.  choosing apache.

### Deepening Understanding
- **Understanding of Role of NOTICE File** should I include the NOTICE file in the repo?
- **Crediting Contributors** how to do attribution if there are multiple contributors?  do I just include them in the NOTICE file as they contribute?
- **Crediting Informal Group** Can I include attribution to a informal group of people?  Like "with contributions from members of Effective Altruism Nairobi"?
- **Checking Updated NOTICE File** how is it now
- **Checking File Extension** NOTICE doesn't get a file extension?

## Gemini - Conceptual Design Prompt
I have a Kenyan company (USA c Corp local branch) and I follow all the Kenyan employment act rules. located in Nairobi. but I have diverse contracts with my team. some of them work three weeks a month, others have half-day saturdays, etc. some are on 52 hour weeks contractually, others are on 45 hour week contracts, others are on monthly hour contracts, basically 52*3 weeks per month, others are casual paid daily. we follow employment act for sick days, half-pay sick days, annual leave, holidays (including surprise political holidays), etc. I also pay NSSF, sha, kra/PAYE, housing allowance for most, provide dormitory housing for some. and all the other tax deductions on both sides like affordable housing, etc.

some work 52 hour weeks at minimum wage, some work fewer contract hours at above minimum wage, some work fewer hours "at" minimum wage, but getting pay a prorated part of the monthly minimum wage based on their decreased hours.

I'm making this accounting system as a open source project with apache license.  I included a "this is not tax advice get your own accountant" extended disclaimer in the readme.

Can you do a basic structural setup, scoping conceptual spec?  I'm imagining a simple setup where a user clones the repo, runs installation of the python code via some multiplatform system if installation is necessary (i'm on linux) but the system can just use a local web browser interface.  User will specify the local accounting data file structure local filepath. (Software will be accompanied by a template file structure with template TSVs etc).

List of key input TSVs:
- Master employees input table of names, ID number, base salaries, phone numbers
- Employees contract parameters table, one record for each employee-contract, includes name, ID number, contract status ongoing or terminated/superseded, start date, scheduled end date (if term contract), actual termination date (if terminated), contract type (categories to be developed), and various various other contract provisions.
- Timesheet table with one record for each employee-day, hour ranges worked entered, or alternatively total hours directly entered for that day.

List of output TSVs:
- Output a spreadsheet formatted for uploading to Equity Bank bulk payments.

Other structure:
Code will maintain a local SQLite database, in a local git repo.  Advise people to backup the repo somehow according to their institution's needs.  All inputs and outputs may also be kept in the repo.

Suggestions?

## Claude Code - Project Task Planning

### TODOS.md Creation
no, the TODOS.md should be high level items. just four items:
task create a /logprompt slash command so that Claude appends the current prompt to the PromptList.md file in the current directory (usually a git repo root). the format of the promptlist should be defined within the slash command code, based on the current PromptList.md format.
task add a copy of the code for this slash command to the kenyaccounting repo also, if that isn't the standard place for it.
task add paystub generation to the kenyaccounting software core scope if not there yet
task make a spec for unit tests testing the software's stated goals.

### Prompt Logging Request
add the previous prompt to the PromptHistory.md according to that format. and this one.

### Start Tasks
create a new git feature branch for this list of tasks, then start the tasks. add this prompt to PromptList.md also

### Unit Test Spec Update
now update the unit test spec with pseudocode /logprompt

### Leave Stocks Clarification
note that the input spreadsheet will say if the employee was sick or not, how many days and hours they workds. and the history database will support stocks of different kinds of leave. and they the model determines if they used sick days, what kind of sick days, annual leave days, and/or unpaid leave. that decision isn't specified case by case, it's determined by the stocks and flows. so you need stocks data in the final tests.

## Claude Code - Spec Management

### Spec Update Approach
oh yeah, i need to use the unit test spec to review and comprehensively update the initial spec to a new spec with the new date. should i rename the initial spec to the new date and commit, and then edit it, so it maintains continuity?

## Claude Code - Project Configuration

### Claude Attribution Removal
put a note in CLAUDE.md to stop crediting Claude.

### Prompt Logging
add to promptlog my prompt about renaming the initial spec, and also the one about not crediting claude and that prompt there also

## Claude Code - CLAUDE.md and Technical Spec Session

### CLAUDE.md Creation
/init (create CLAUDE.md for the repo)

### Commit Message Attribution
include in CLAUDE.md to not attribute claude in commit messages

### Statutory Output Formats
also, another output is the documentation for KRA and NSSF and SHA payments. is there an upload format for those?

### Test Fixtures and Technical Spec
we don't need the expected values yet, we can check it externally after we get the test results. let's start with the test fixtures. then a technical spec without code, but including a concept for a healthy and elegant object-oriented structure. use minimal helper functions etc. make a note that in this prototyping phase we want to avoid spamming up the readability of the code with bells and whistles, even if they're good code practice. we can add lots of try-except blocks and robustness later.

### Git Branch Management
can we make this commit you just did on a new branch for feature: technical spec
undo the commit. commit the test fixtures to main. then let's do a new feature branch for the technical spec

### SQLite Question
what's good practice. we were planning on using sqlite right? go ahead and put all the prompts from this convo into the prompthistory btw.

### Dev Strategy Document
make a dev_strategy.md document including this response content. we can bring info from the prompthistory over there and add more as we proceed also.

### TSV ↔ Object Flow
what about the OO and the tsv, which goes in which at which stages. did you come to a best practice conclusion on that?

## Claude Code - Technical Spec Implementation Session

### Full Implementation Run
continue based on TODOS.md

(Claude proceeded to implement all 6 phases from TODOS.md: models, rates, loaders, calculators, tests, outputs, and Streamlit UI)

### Virtual Environment Setup
we should use the git/.venv but make our own requirements.txt

### Documentation Update
update the prompthistory

### Commentary
you were supposed to do a technical spec but you couldn't help coding up the entire app prototype?

(Result: 4 commits, 6 modules, 23 passing tests, working Streamlit app. Phases 1-6 complete.)

## Claude Code - NSSF Year 3 Rate Fix Session

### NSSF Discrepancy Report
The online tax calculator gave me the following after inputting gross pay 57500:
NSSF Tier I: 480.00
NSSF Tier II: 2,970.00

but your kenyaccounting gave:
NSSF Tier 1:               540.00
NSSF Tier 2:             2,910.00

### January 2026 Support Request
can you update the calculator to also be able to handle january 2026?

(Result: Fixed Year 3 NSSF LEL from 7,000 to correct value of 8,000. System was already date-aware with Feb 2026 transition, just had wrong Year 3 rate. Updated src/rates.py, specs/technical_spec.md, and tests/test_payroll.py. All 35 tests passing.)

### Git Workflow
commit
push
merge to main
push

(Result: Committed b77798d to feature/technical-spec, pushed, merged to main via fast-forward, pushed main to origin.)

## Claude Code - Test Fixture Generation Session

### Fixtures Folder Naming Question
why did you call this folder "fixtures" what does that mean

### Reorganize Generated Supplementals
move everything in generated_supplementals to the trash/ folder inside of it

### Generate Complete Test Input Set
ok now use the tests/fixtures/single_source_truth_tests summary info to generate all the inputs that would be relevant. contract types table, daily hours timesheets etc. etc. a complete set of inputs the way they should be goes into the generated_supplementals folder, to use to run tests

### Include Aren Calculator Test Cases
what about the test_cases_aren

### Add Aren as January Employees
add them as january employees

### Adjust Daily Working Hours
for employees 13 to 19 change the daily working hours from 8 to 8.66

### Weekly Schedule Structure
okay we have to adjust this. current instructions for employees 13-19 have weekdays at 9h and saturdays at 9h. so we need a different input structure, because these instructions can change each week.

(Result: Created test_weekly_schedules/ with per-employee per-week schedule TSV. Updated timesheets to 9h weekdays, 7h Saturdays. Updated contracts to 52hr/week.)

### Add Employees 20-26 with Leave Scenarios
add feburary employment for employees 13-19. make employees 20 through 26 for january and february with random sick days, annual leave days, one employee that takes enough sick days to run out and use annual leave, another employee that runs out of annual leave days so has to use unpaid leave.

### Engine-Driven Leave Attribution
the code should shoulder the responsibility of changing the leave attribution category.

(Result: Simplified timesheet columns from hours_sick_full/hours_sick_half/hours_annual/hours_unpaid to hours_sick/hours_annual/hours_unpaid. Engine now responsible for allocating sick hours against sick_full stock first, then sick_half, then overflow to annual. Annual leave overflows to unpaid when stock exhausted.)

### Log Prompts
add all the the user prompts to the user prompt record system /logprompt

### Spec Update Check
did we add the necessary details to the spec?
