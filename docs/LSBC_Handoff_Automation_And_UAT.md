# Hand-off: automation changes and UAT on migrated data

Start a new chat in this repo and give it this file. It covers two jobs:

1. The flow and rule changes still owed after the CLOSE migration (part A).
2. Running every script in the UAT doc against the real CLOSE data now in LSBC-Partial (part B).

CLAUDE.md applies throughout: list every proposed label and API name to Jonathan before creating it,
no requirement IDs in metadata, update the Deployment Manifest, `manifest/package.xml`, the Data
Model and the design doc change log with every deployable change.

## Ground rules for the migrated data

- The data is real licensee data (names, addresses, dates of birth, licences, holds, exams, fees,
  payments) from CLOSE, the Board's legacy system, loaded on 10–11 Nov 2026. It is in the sandbox
  only.
- Never read or load real social security numbers: Shield isn't on yet. People carry a made-up
  number starting `000` in the sandbox-only field Mock Social Security Number. The raw CLOSE export
  in `~/Downloads/9-10 ETL` must not be opened. Migration scripts and their README are in
  `scripts/migration`; they read only `../LSBC-Migration/extract/lsbc_deid.sqlite`.
- Migrated people have no email addresses, so nothing a test does can email them. Don't add real
  email addresses to migrated records, and don't create portal logins for migrated people. Portal
  scripts use the existing `StopCodeTest` registrants and their logins (see CLAUDE.md).
- Migrated records are found by `LegacyKey__c` (`LSBC-P-…` people, `LSBC-S-…` salons,
  `LSBC-SC-…` schools). Test records created during UAT should be easy to find and delete: put
  `UAT` in a name or comment field. Never delete migrated records.
- Every save of a licence, relationship, bond, exam, fee or payment re-runs the stop code sync for
  that holder. That is expected; note any hold that looks wrong as a defect.

What is loaded (sandbox, 11 Nov 2026):

| Data | Count |
|---|---|
| People (licensees, salon owners and managers, enrolled students, applicants) | 35,678 |
| Salons and schools | 7,385 and 58 |
| Licences, all current at load | 40,234 (6 Deceased, 2 Retired) |
| Owner, manager, assistant manager and booth renter relationships | 11,347 |
| School surety bonds | 477 |
| Exam attempts (graded) | 98,539 on 22 Examinations |
| Fees still owed (due date blank, so no Non Payment hold) | 13,210, $487,657.05 |
| Fees paid by payments since 11 Nov 2023 | 167,244 |
| Payments since 11 Nov 2023, with 173,806 allocations | 120,554 |
| Students: course offerings and monthly hours rows | 111 and 32,801 |
| Reciprocity applications still in progress | 27 |
| Open stop codes | 2,602 (see the Record Alert list views) |
| Fee codes, citations, violation types | 621, 123, 38 |

Not loaded: CE seminars (see A6), inspections (Phase 2). Not loaded for data reasons: 21 months of
hours over the 192-hour monthly limit, no-show and ungraded exam attempts, enrolments at closed
schools. Open fee balances total $25 less than CLOSE's figure for the same charges: one charge not
yet traced.

## Part A: automation changes

Each item says what to change, why, and where. Propose names first; build only after Jonathan
approves. Rule changes to an expression set go into the existing version: this org rejects a new
expression set version (see CLAUDE.md, "BRE in this org"). Decision matrices take new versions.

### A1. Fees by licence type beyond renewal

Renewals and late fees are priced per licence type (Fee Schedule V3, rows `<Licence type> Renewal`
and `<Licence type> Late Fee`). The other fees still use one generic row with no fee code, so
revenue can't be reported by code for them. CLOSE has a code per licence type for each:

| Fee | Generic row today | Flows that read it | CLOSE codes |
|---|---|---|---|
| Initial licence or permit | Individual License, Permit, Temporary Permit | Reciprocity, Threading Permit, Temporary Permit, Account New Application | AA cosmetologist, AI manicurist, AP esthetician, AW/BO/BF instructors, CA alternative hair design, CC microdermabrasion, CE shampoo assistant, CG make-up, DA booth renter, QG threading |
| Duplicate licence | Duplicate License | Renewal (duplicate path) | AG, AN, AU, BD/BV/BM (active instructors), B1/B2/B3 (inactive), CU, CY, CZ, DC, DN, EJ |
| Affidavit | Affidavit ($15) | Affidavit | PA cosmetology $15, PG, PH, PI; code 87 is a $25 affidavit |
| Violation | Violation ($25) | Record-Trigger: Regulatory Code Violation After Save | PP operator, PN shop, PO school, PS instructor, ZZ special permit (amounts blank in CLOSE) |
| No-show, restoration exam | No Show, Restoration Examination | Retake, Renewal assessment | many per exam and city, all $25 |
| Establishment | Establishment License, Manager License | Shop and Facility applications | DG cosmetology salon initial, EK/EH manager |

Recommended approach: the same pattern as renewals. Add rows named `<Licence type> <Fee>` to a new
Fee Schedule version, and change each flow's fee name to the licence type's name plus the fee, with
the generic row as the fallback when a type has no row. For violations the name is
`Violation <cited party>`. Amounts: keep today's; CLOSE's amounts are in
`../LSBC-Migration/extract/lsbc_deid.sqlite` (`FEE_SCHEDULES`, row with no `END_DATE`).

### A2. Instructor status in fees

`BusinessLicense.InstructorStatus__c` (Active, Inactive) is loaded from CLOSE. CLOSE charges active
and inactive instructors under different renewal and duplicate codes (for example AX is
"Cosmetology Instructor – Renewal – Active"). Once LSBC answers the client question on statuses N
and X, add inactive rows and have the renewal assessment pick the row by status.

### A3. Booth renter rule (stop code 6)

Code 6 needs a current cosmetologist licence, as in CLOSE. 156 booth renters are held; 39 hold an
esthetician licence and 31 a manicurist licence. If LSBC answers DM-03 "any operator licence",
change `StopCodePerson` code 6 to accept a current cosmetologist, esthetician or manicurist licence
(new inputs from Subflow: Stop Code Sync), then re-sync the held booth renters.

### A4. Manager hold (stop code 16)

Code 16 now clears with a licensed owner or manager relationship, or a current Manager licence on
the shop: 530 open against CLOSE's 50. Managers come only from inspections since 2021, so many are
stale. Ask whether staff set code 16 by hand in CLOSE; if so, make it a manual code (move it out of
`StopCodeEstablishment`, end the automatic holds) rather than tune the rule.

### A5. Open balances and Non Payment (stop code 21)

The 13,098 migrated balances have no due date, so they raise no Non Payment hold. When finance says
which balances to collect, set their due dates (a data update, not automation) and the nightly
schedule opens the holds. No flow change unless finance wants a different rule for migrated
balances.

### A6. Continuing education, then load the CE seminars

Subflow: Stop Code Sync reads a person's latest Training Course Participant of any kind as their
latest student hours (`GetLatestHoursEntry` filters on the contact only). Continuing-education
attendance stored the same way would count as student hours and wrongly open code 20 (no hours for
six months) on instructors. Before loading CE:

1. Add an entry type for continuing education to `TrainingCourseParticipant.EntryType__c` (propose
   the value name), and make `GetLatestHoursEntry` and `GetHoursEntries` read only Monthly Hours
   and Transfer entries.
2. Then load CLOSE's seminars (58, 1992–2026, mostly 16-hour sessions from the Louisiana State
   Beautician and Barbers Association and an online CEU course) as one Training Course
   "Continuing Education" with a Course Offering per seminar, and the 7,243 attendances of
   migrated people as participants with that entry type. Tables: `SEMINARS`, `SEMINAR_DETAILS`
   in the de-identified copy; follow `scripts/migration/build_students.py` for the shape.
3. Decide with LSBC whether seminar providers become Organization accounts with CE Provider
   Approval accreditations (the design's model for the public CE provider list); CLOSE has only the
   seminar names.

### A7. Smaller items

- Violation Type severity: all 38 loaded as Minor Violation; the chief inspector sets them (data).
- Licence numbers (PT-14): migrated licences have no `Identifier`, so migrated licensees can't use
  portal sign-up or public search until LSBC answers how numbers are assigned.
- E-check payments load as Check (9 in three years); add a method only if finance asks.

## Part B: run every UAT script on the migrated data

The UAT doc is [LSBC UAT Scripts](https://claude.ai/artifact/Pv2nDG8sGtdwZsnnQTQgAG). Each script
has an ID, steps on named test records, an expected result, a Result dropdown and a Defect log.

1. Read the whole UAT doc first and list the scripts.
2. For each script, keep the steps and the expected result, and swap the named test record for a
   real migrated record that meets the same starting condition. Find it with SOQL, for example:
   - a licensee with a current cosmetologist licence and no hold:
     `SELECT Account.Name, Account.LegacyKey__c FROM BusinessLicense WHERE RegulatoryAuthorizationType.Name = 'Cosmetologist' AND PeriodEnd > TODAY AND AccountId NOT IN (SELECT WhatId FROM RecordAlert WHERE IsActive = true) LIMIT 5`
   - a holder with an open hold of a given code: `RecordAlert` where `RecordAlertCategory.DeveloperName = 'StopCode12'` and `IsActive = true`
   - a fee still owed: `RegulatoryTrxnFee` where `Status = 'DUE'`
   - a payment with money left unapplied: `Payment__c` where `UnappliedAmount__c > 0`
   - an instructor of each kind: `BusinessLicense` where `RegulatoryAuthorizationType.Name = 'Esthetician Instructor'`
   - a person who failed an exam: `PersonExamination` where `Result = 'Fail'`
   Portal scripts keep the `StopCodeTest` registrants and logins. CE scripts keep the `StopCodeTest`
   records until the CE load is done (A6). Real students (code 20, hours) are now loaded.
3. Run the steps as the script says: through the real screen (the portal, the LSBC Licensing app)
   where the script names one, by flow or API only where it says so. Check the published portal
   with headless Chrome as CLAUDE.md describes.
4. Record each run: set the Result dropdown, and in the script's notes name the real record used
   (its `LegacyKey__c`, never a social security number). Log every failure in the Defect log with
   the record, the step, what happened and what was expected.
5. Clean up what a script created (applications, payments, letters) unless the script says to keep
   it. Undo changes to migrated records where the script changed a status or a date, and note it.
6. Finish with a summary for Jonathan: scripts run, passed, failed, blocked (and why), and the
   defects, most serious first. Anything that needs a flow or rule change goes to part A's list,
   not into a fix during the UAT run.
