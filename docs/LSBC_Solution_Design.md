# LSBC Salesforce Public Service Platform — Solution Design

**Client:** Louisiana State Board of Cosmetology
**Engagement:** Phase 1 Foundation, Carahsoft SOW 66003598, NASPO LA 4400010663
**Status:** Discovery complete and the scope readout accepted. Build is under way.
**Last updated:** 6 November 2026

---

## How to use this file

Sections are ordered by delivery milestone so they can be split into separate files on
those boundaries. Every requirement carries a stable ID (`DM-01`, `BR-04`, …) — use these
in Jira stories and commit messages rather than quoting the text, so the two stay linked
when the wording changes.

Each requirement is tagged:

| Tag | Meaning |
|---|---|
| `[SETTLED]` | Decided. Do not reopen without a reason. |
| `[PROPOSED]` | Our recommendation. Needs LSBC confirmation. |
| `[OPEN]` | No answer yet. Tracked in section 8. |

### Naming convention

Names follow the [CFPB Salesforce Naming Conventions](https://github.com/cfpb/salesforce-docs/blob/master/_pages/Salesforce-Naming-Conventions.md),
and flows follow [Automation Champion's flow conventions](https://automationchampion.com/2021/11/09/naming-conventions-for-salesforce-flow/).
Whole words, singular, and **no spaces or underscores in an API name**. The suffix Salesforce
adds is not part of the readable name. The one exception is the type prefix on flow elements.

| Thing | Form | Example |
|---|---|---|
| Custom field | `ReadablePart__c` | `ForYear__c`, `OriginatingState__c`, `ApplicationPath__c` |
| Custom object, if one proves unavoidable | `ReadablePart__c` | `PaymentAllocation__c` |
| Record type developer name | `ReadablePart` | `NewLicensure`, `Reciprocity`, `NewSchool` |
| Flow label | Automation Champion pattern by flow type | `Record-Trigger: Business License After Save`, `Screen Flow: Account Add Stop Code`, `Subflow: Stop Code Sync`, `Business License Schedule: Expired And Lapsed Licenses` |
| Flow API name | The label with spaces and punctuation removed | `RecordTriggerBusinessLicenseAfterSave`, `SubflowStopCodeSync` |
| Flow element | Type prefix and underscore, then PascalCase | `varB_IsEligible`, `varR_Licenses`, `forD_NewPeriodEnd`; `Get Business License`, `Loop Through Licenses` |
| Decision matrix / expression set | `AreaReadablePart` | `FeeSchedule`, `FeeLateCalculation`, `StopCodePerson` |
| Validation rule | `FieldRuleDependency` | `TotalHoursMax192MonthlyHours` |
| Permission set / custom permission | `ReadablePart` | `SchoolAdministrator`, `BoothRenterAccess` |

There is one record-triggered flow per object per context (before save, after save). Later work
adds to that flow rather than creating another.

Standard object and field names are used exactly as Salesforce spells them — `Account`,
`BusinessLicense`, `PersonContactId`, `RegulatoryTrxnFeeItem` — because this file has to work as a
build reference. The convention applies only to what we create.

Requirement IDs in this document (`DM-01`, `BR-02`) are a document device, not metadata, and keep
their existing form.

Suggested split:

```
00-overview.md        Section 0
01-data-model.md      Section 1
02-business-rules.md  Section 2
03-portal.md          Section 3
04-cases.md           Section 4
05-cutover.md         Section 5
06-back-office.md     Section 6   (reference — informs 1 to 5)
07-out-of-scope.md    Section 7
08-open-items.md      Section 8
```

---

## 0. Overview

### 0.1 What is being built

Salesforce Public Sector Solutions replaces CLOSE as the system of record for licensees,
schools, shops, booths and instructors.

| Capability | Delivered by |
|---|---|
| Record of licensure | Person Accounts, business Accounts, `BusinessLicense` |
| Applications | Individual Application, Business Licence Application, Experience Cloud |
| Business rules | Business Rules Engine, called from Flow |
| Evidence | Document Checklist Item, Person Examination, Training Course Participant |
| Money owed | Product, Regulatory Transaction Fee, Fee Item |
| Money received | A thin payment and allocation ledger for every fee: violations, applications and renewals. See `DM-18` |
| Violations | Regulatory Code, Violation Type, Regulatory Code Violation |
| Complaints | Case, Email-to-Case, Web-to-Case |
| Public service | Licence search, school directory, CE provider list |

### 0.2 Design principles

- `PR-01` Standard objects throughout. One exception is made, in `DM-18`, on licensing grounds
  rather than capability grounds. Anything else that does not fit is recorded as an open item
  rather than resolved by inventing an object.
- `PR-02` Declarative first. Screen Flows and BRE carry the logic. LWCs only where Flow
  cannot do the job, each listed individually in section 3.5.
- `PR-03` Maintainable by one administrator. LSBC designates a single long-term System
  Administrator. Configuration a trained admin can read beats a more elegant solution they
  cannot.
- `PR-04` Configuration over code paths. Variation between licence types lives on
  configuration records, not in branching logic.
- `PR-05` Business logic never moves into a component. Stop codes, fee allocation and
  eligibility stay in BRE.

### 0.3 Milestone map

| Milestone | Week | Sections |
|---|---|---|
| Discovery complete | 3 | — |
| Core data model and security | 6 | 1, 2 |
| Experience Cloud portal — built and tested, not published | 9 | 3 |
| Case management and violations | 10 | 4 |
| UAT, training, staff go-live | 12 | 5 |
| Public portal published | March or April 2027 | 3 |

---

## 1. Data model — Week 6

> **Object naming, confirmed in the client org.** There is no `Authorization` object in Public
> Sector Solutions. The issued licence or permit is **`BusinessLicense`**, and it carries both
> individuals and establishments — the holder is `AccountId`, which with Person Accounts covers
> both. `ContactId` also exists but is not used. Every Authorization* object in the org belongs to Consent Management and is unrelated.
> Note that `AuthApplicationPlace` still labels its lookup to `BusinessLicense` as "Authorization",
> so the older name survives in relationship labels.

### 1.1 People and organisations

`DM-01` `[SETTLED]` **Person Accounts are enabled.** A licensee is their own Account, not a
Contact filed under an employer. A cosmetology licence is personal and portable; a change of
salon must not reparent the record or imply the salon owns the licence. This also removes the
placeholder-employer problem for self-employed and mobile operators.

`DM-02` `[SETTLED]` **Students are Person Accounts at registration**, not Contacts under the
school. Converting a Contact to a Person Account later is not feasible.

`DM-01a` `[SETTLED]` **Business Account record types.** `Establishment` (salons and shops) is the
default business record type, required before Person Accounts can be enabled. `School` is
separate because bonds, programmes, hours and DOE status apply only to schools. `Organization`
holds unlicensed businesses — parent companies, CE providers, foreign credential evaluation
agencies — so they never appear in licence search or carry licensing layouts. Person Accounts use
the standard `PersonAccount` record type, relabelled **Person** to sit alongside the three business
record types.

| Object | Purpose | Key content |
|---|---|---|
| Account (person) | Licensees, instructors, students, booth renters | Identity, photo, maiden name, legacy certification number, duplicate count |
| Account (business) | Schools, salons, shops | Record types `Establishment` (salons, shops), `School`, and `Organization` (unlicensed businesses: parent companies, CE providers, evaluation agencies). See `DM-01a`. Validated address with geocoding, parish |
| Contact | Non-licensees only | Public complainants, school administrators, unlicensed owners. Plus the person contact behind each Person Account |
| `BusinessProfile` | Regulatory detail on an establishment | Nine fields only: operating name, business structure, tax identifier |
| `Accreditation` | School approval status | `AccreditingBody`, `Status`, `AccreditationRating`, `EffectiveFrom` and `EffectiveTo`, `LastOnsiteSurveyDate`. This is where DOE status lives |
| Account Contact Relation | Person-to-establishment affiliation | Roles, start and end dates. Booth renter to host salon, school administrator to school, employment |
| Account Account Relation | Business-to-business only | Parent companies, franchises, multi-campus schools |

`DM-03` `[SETTLED]` **Booth renters hold a permit on their own Person Account** and rent space
inside a licensed salon. The link to the host salon is an ACR with role Booth Renter. There is
no separate business Account and no business licence. Booth renters must appear in the public
licence search; today they do not.

A booth renter permit **expires on January 31**, aligned to the salon licence, not on the holder's
birthday. It requires a current operator licence **and** a current salon licence, plus a $5
board-provided contract.

The **initial** permit requires an inspector visit: signatures from both the salon owner and the
booth renter, and verification that the salon licence is current. **Renewal** follows the ordinary
renewal path with no inspector. Inspectors currently issue initial booth permits against salons
with expired licences because nothing checks — see `BR-02`, codes 6 and 16.

`DM-04` `[SETTLED]` **DOE status is a rules input, not a label.** Values: Seeking approval,
Not seeking approval, Rogue. A student from a rogue school cannot be registered at all.

`DM-05` `[PROPOSED]` **Maiden name is stored** and used as a secondary match key at portal
registration. A licensee who married since their last renewal is the classic duplicate case.

`DM-06` `[PROPOSED]` **Legacy certification number is stored** as a second match key for any
later migration. CLOSE carries `Old Certification#` predating current numbering.

`DM-07` `[OPEN]` CLOSE stores **race and sex** on the applicant record. Confirm whether race
is still collected and what for. If it migrates it needs field-level restriction from day one,
and there is no encryption at rest behind it in Phase 1. See `OPEN-13`.

### 1.2 Applications and licensure

| Object | Purpose | Key content |
|---|---|---|
| Draft Application | Part-finished portal submissions | Save-and-resume payload |
| Individual Application | Person-side requests | Record types: New licensure, Renewal, Reciprocity. Originating state, application path, certification block |
| Business Licence Application | Establishment requests | Record types: New establishment, Renewal, New school |
| `BusinessLicense` | The licence or permit, for individuals **and** establishments | `Identifier`, `AccountId` as holder (a Person Account for individuals, a business Account for establishments; `ContactId` is left unused), `RegulatoryAuthorizationType`, `PeriodStart` / `PeriodEnd`, `Status`, `IsActive`, `BusinessType`, `VerificationStatus` / `VerifiedDate`, and the jurisdiction and issuer fields for out-of-state credentials |
| `AuthApplicationPlace` | The place recorded against a licence at issue | Application, licence, and `Place` as a lookup to `Location` or `Address` |
| `RegulatoryAuthorizationType` | Configuration per licence or permit type | Fourteen fields, and sparse: `DurationType`, `RegulatoryAuthCategory`, `RegulatoryAuthCode`, `ProcessingDuration`, `ApplicationUrl`, `IssuingDepartment`. The fee, term length, renewal cycle, continuing-education requirement, hour thresholds and required examinations are all **custom fields**. `BusinessLicense` looks up to this object for both individual and establishment credentials |
| `BusRegAuthorizationType` | Present, but not referenced by `BusinessLicense` | Confirm whether it is used at all before building against it |
| `DocumentChecklistItem` | Outstanding requirements | `IsRequired`, `IsAccepted`, `Status`, `Instruction`, with `DocumentType` and `DocumentCategory` lookups. `ParentRecordId` reaches both application objects, `RegulatoryCodeViolation`, `PersonExamination`, `CourseOffering`, `PersonDisability` and `PreliminaryApplicationRef` — so a violation's payment receipt has a home without touching the ledger |
| `RecordAlert` | Surfaces a hold to staff | `EffectiveDate`, `ValidUntilDate`, `IsActive`, `Severity`, and a `RecordAlertCategory` lookup — so the thirty-one stop codes become category records rather than a picklist, maintainable by an administrator |

`DM-08` `[SETTLED]` **`BusinessLicense.Status` carries terminal states.** Revoked, Retired and
Deceased are not holds — they never clear and never receive an end date. CLOSE already has a
separate Deceased flag on the applicant, which supports this. See `BR-04`.

`DM-08a` `[SETTLED]` **One `BusinessLicense` per credential, kept for life.** A renewal moves
`PeriodEnd` forward on the same record; it does not create a new one. `Identifier` therefore stays
the single public lookup key, and stop-code and prerequisite rules never have to find "the current
one". Year-by-year history comes from renewal applications, fee items carrying `ForYear__c`, and
field history. Credential-level facts — `LastCEUDate__c`, `ConsecutiveCEUCycles__c`,
`IsMasterInstructor__c`, `RenewalCount__c` — live on the licence.

> `BusinessLicenseStatus` in the org ships with Inactive (default), Revoked, Draft and Verified.
> Phase 1 added Active, Retired and Deceased.

`DM-09` `[SETTLED]` **Originating state is captured on reciprocity applications.** Not captured
today. It is the only way interstate routing becomes visible — applicants licence in an
intermediate state to bypass exclusions.

`DM-10` `[SETTLED]` **The place at issue is a standard junction.** `AuthApplicationPlace` links an
application, a licence and a `Place` — itself a lookup to `Location` or `Address`. That is exactly
the distinction needed: "where they work now" is an Account Contact Relation, "what was recorded
against the licence" is this junction.

> The capability exists in the platform today and costs nothing to populate. The Board has routed
> printing the place of business on a licence to its legislative package, so the constraint here is
> legal rather than technical.

### 1.3 Training, exams and fees

| Object | Purpose | Key content |
|---|---|---|
| Training Course (`TrnCourse`) | Catalogue of programmes and CE courses | `TotalHours`, `TotalCredits`, `Status`. The API name is abbreviated: `TrnCourse`, not `TrainingCourse` |
| Course Offering | A school's approved offering of a programme | That school's approved hours (`ApprovedHours__c`). The standard object has no link to an Account, so `School__c` is a custom lookup limited to School Accounts |
| `TrainingCourseParticipant` | Student enrolment and hours | `TotalHours`, `TotalCredits`, `StartDate` and `EndDate` are native. One record per student per month, bounded by the dates, so history is preserved rather than overwritten |
| Person Education | Schooling history | Used in reciprocity review |
| `Examination` | The catalogue | Eight fields — name, description, status. Light enough that one record per timed station costs nothing. Custom `ExamType__c` (National, Practical, State, Restoration) and `LicenseType__c` (lookup to `RegulatoryAuthorizationType`), added in Phase 3 so stop codes and eligibility can tell exams apart |
| `PersonExamination` | One attempt at one station | `ExaminationDate`, `Score` as an integer, `Result`, and a verification block. Several rows per sitting give per-area scoring. Attempt number is custom |
| Product | Fee codes as catalogue entries | Two-letter CLOSE code as external ID |
| `RegulatoryTrxnFee` | What is owed | `ParentRecordId` is polymorphic across both application objects, `BusinessLicense`, `RegulatoryCodeViolation` and `Case`, so a fee attaches directly to a violation. `TotalFeeAmount` rolls up from the items; `Status` and `DueDate` are native |
| `RegulatoryTrxnFeeItem` | The breakdown | Amount, description, calculation info, master-detail to the fee. **No Product lookup and no year** — the fee code link and `ForYear__c` are both custom |
| Regulatory Code | Statute cited | Reference data LSBC loads |
| Violation Type | Categorised picklist | With an Other-with-explanation path |
| Regulatory Code Violation | The violation | Related to establishment and practitioner |
| `PublicComplaint` | The complaint itself | Complainant captured inline — name, email, mobile, address, organisation, `ReporterCategory` — so a member of the public needs no Contact record. Four levels of categorisation, `SourceType` for intake channel, `IsReporterConfidential` for anonymous reports, and `ShouldInclInRegulatoryRpt` for board reporting |
| `ComplaintCase` | A junction, not a record type | Links a `PublicComplaint` to the `Case` that carries the work |
| `ComplaintParticipant` | Who a complaint names | `ParticipantId` is polymorphic to Account, Contact, User or Group, with a `Role` — so one complaint names both a salon and a practitioner |
| `Case` | The work on a complaint or inquiry | Routing, assignment, status and resolution |

`DM-11` `[SETTLED]` **Approved hours sit on Course Offering; the statutory minimum drives
eligibility.** Instructor programmes require 500 state hours but schools commonly submit 600+
to qualify for federal Title IV aid. Exam eligibility sums against the statutory minimum, not
the school's figure.

`DM-12` `[SETTLED]` **School hour requirements are per school, per programme**, across nine
programmes: cosmetology, manicurist, shampoo assistant, manicurist/esthetician,
microdermabrasion, teacher, esthetician, alternative hair design, advanced training.

`DM-12a` `[SETTLED]` **The student registration licence is also the testing voucher.** It is
printed perforated with a top and a bottom portion: the top accompanies the national
examination application, the bottom the practical and state examination application. Replacing
it digitally removes a physical control the testing desk currently relies on, so the portal needs
an equivalent — an eligibility check at the point of booking rather than a piece of paper.

`DM-13` `[SETTLED]` **Hours live apart from the registration record.** Editing the student
screen in CLOSE wipes accumulated hours. Training Course Participant carries them.

`DM-14` `[SETTLED]` **Fee Item carries a "For Year" field.** Every payment in CLOSE applies to
a named licence year. A restoration applies several in one transaction — exam fee for the
current year, late fees for each delinquent year, the renewal itself. Without this field there
is no back-fee calculation, no restoration, and no revenue reporting by licence year.

`DM-15` `[SETTLED]` **Several reference lists are maintained records**, not hard-coded values.
LSBC's compliance officer owns most of them, and each changes on its own cycle.

| List | Note |
|---|---|
| Continuing-education providers | Four approved per year; the public page carries current and prior years |
| Foreign credential evaluation agencies | Changed recently after approximately 30 licences were issued on flawed verifications |
| Non-acceptable high school diploma mills | The list behind the Registration SOP's "unclear, unverifiable or suspicious" branch |
| State reciprocity exceptions | Florida excluded; others carry their own examination requirements |
| Violation types and regulatory codes | Owned by the chief inspector; the checklist was last revised April 2026 |

Where they live, decided in Phase 1: CE providers, credential evaluation agencies and unacceptable
diploma sources are `Organization` Accounts, told apart by `Account.Type`. A provider's or agency's
approval for a given year is an `Accreditation` record (Type CE Provider Approval or Credential
Evaluator Approval) with `EffectiveFrom` and `EffectiveTo`, so current and prior years sit side by
side. State reciprocity exceptions are the `ReciprocityStateRule` decision matrix (settled in Phase 3).
Violation types and regulatory codes are Phase 4 reference data.

`DM-16` `[OPEN]` CLOSE has a **Seminar module** — Maintain Seminar Details and Maintain Seminar
Codes — which may be where approved CE providers and courses actually live. Confirm before
assuming Training Course and Course Offering cover it. See `OPEN-14`.

`DM-17` `[SETTLED]` **School bonds are tracked with effective and end dates and an underwriter.**
A $30,000 insurance bond must be current for a school to renew, and the bond check is a hard
gate in the print path.

A bond is an `Accreditation` record on the School Account: Type Surety Bond, `EffectiveFrom` and
`EffectiveTo`, the bond number in `SourceSystemIdentifier`, plus custom `Underwriter__c` and
`BondAmount__c`. Not a `BusinessLicense`, so it never appears in licence search or the print run.

> **Migration warning.** Bond records in CLOSE repeat the same bond number with appended
> characters (`$$**`, `***`, `///`, `>>>>`) to force uniqueness across renewal years. Any
> migration keyed on bond number will collide.

### 1.4 Money received

`DM-18` `[SETTLED]` **A payment-and-allocation model is required, and no standard object in
scope provides one.** CLOSE's Maintain Financial Transactions screen carries Unapplied Amount,
Applied Previously, Applied and Amt Left, with line items of Code, Description, For Year, Fee and
Amount. A receipt is not tied to one fee: money sits unapplied and is allocated across several
fees and several licence years.

Evidence from three independent desks:

- A school sends one cheque for twenty students; one bad application should not reject the batch.
- Partial payments are applied to late fees, with the renewal slip held until the balance clears.
- Overpayments produce a refund: requested by any department, verified and entered by the front desk, audited through two reports.
- Reversals re-apply a different code and year.

#### What the platform does and does not provide

| Option | Why it does not fit |
|---|---|
| `RegulatoryTrxnFee` / `RegulatoryTrxnFeeItem` | States what is **owed**. The item carries no Product lookup, no year, and no applied-versus-outstanding concept |
| `Payment` (core) | Order Management and Salesforce Payments. Represents a gateway capture or sale, parented to an order payment summary. Commerce semantics, and nothing that points at a regulatory fee item |
| `PaymentCart` / `PaymentCartItem` (PSS) | A checkout basket, not a ledger. `PaymentCartItem` has four meaningful fields — Amount, Description, `InvoiceId` and the parent cart. It references **Invoice**, which is a Billing object. API 66.0 and later |
| `PaymentRequest` / `PaymentRequestLine` (PSS) | Disbursements. Money paid **out** on claims and benefits — the wrong direction |
| Inbound Payments (Winter '27, GA) | Does exactly what is needed, including real-time payment status and compliance before approval. Requires Billing Advanced, Billing and Public Sector Payments Integration permission set licences, none of which are on the Carahsoft quote |

#### The Phase 1 decision

Two thin custom objects, scoped to the violation path only.

| Object | Purpose |
|---|---|
| `Payment__c` | One receipt. Date, amount, method, check or transaction number, check date, payer name, unapplied balance |
| `PaymentAllocation__c` | The junction. Which payment, which `RegulatoryTrxnFeeItem`, how much, and `ForYear__c` |

This closes the violation loop inside Phase 1: a citation raises a $25 fee with a 15-day clock,
a partial or full payment is recorded against it, and the outstanding balance drives the print
hold at day 16.

> **The custom objects exist because of licensing, not because PSS lacks payment objects.** That
> distinction matters at handover and in any Phase 2 conversation.

`DM-18b` `[SETTLED]` **A refund is a status transition with three actors, not a second record.**

| Step | Who | What happens |
|---|---|---|
| Request | Any department | The `PB` code is entered against any piece of money, with a form carrying everything except the fiscal detail |
| Verify | Front desk | Checks and signs the form, then returns it |
| Enter | Front desk | Once the cheque is in hand, enters the refund with the cheque number. Status moves from Completed to **Refunded** |

`Payment__c` therefore carries a refund status — requested, verified, refunded — and a cheque
number, rather than a second record. `PaymentAllocation__c` is unchanged: a refund allocates
against the fee item it reverses, in the licence year it was originally applied to.

The accounting entry is a fourth step, performed in QuickBooks, and sits outside this platform.

As built (Phase 6): staff run **Refund** on the payment, which shows the step the refund has reached. A
request takes the amount, up to what is not applied to fees, and the requesting department. The
front desk then verifies or cancels it, and finally enters the refund check number and date, which
sets the payment's Status to Refunded. Once refunded, the refund comes off the payment's Unapplied
Amount. Two validation rules hold this outside the action: the refund can't be more than the
unapplied money, and a Refunded refund needs its check number and date. Refunding money already
applied to a fee is a client question.

`DM-18c` `[SETTLED]` **Two reports audit refunds**, and the Board has adopted them as the audit
method: an overpayment report and a refund reconciliation report, both drawing on the refund and
the refund request. Both are Phase 1 deliverables.

As built (Phase 6): the LSBC Finance report folder holds **Overpayments** (payments with money not
applied to a fee, or a refund requested or verified but not sent; returned payments left out) and
**Refund Reconciliation** (every refund by status, with requester, verifier, check number and
date). Two more support the ledger: **Payments by Received Date** (daily totals by method, in place
of deposit totals, since there are no deposit numbers) and **Payments Applied by License Year**.
They use two report types, Payments (one row per payment) and Payments with Allocations.

`DM-18a` `[SETTLED]` **Built to be retired, now covering every fee** (revised 10 Nov 2026). The
ledger was first scoped to violations. Phase 6 extends it to all money LSBC receives, because staff
have no other way to record a mailed renewal check. Nothing in the objects changed: an allocation
already pointed at any fee item. Two paths write to it:

| Path | How the payment is created |
|---|---|
| Mailed or counter payment (check, money order, cashier's check, card) | Staff run **Record Payment** on the Person or business Account. They enter the payment, then go through the account's open fee items, oldest first; each offers what it still owes after earlier payments that were not returned. Anything not applied stays unapplied |
| Online (PayStar) | The applicant uploads the receipt to the application's Payment Receipt checklist item. When staff set that item to **Accepted**, a Card payment is created for the application's fees that are still Due, one allocation per fee item. One receipt creates one payment: `Payment__c.ChecklistItem__c` is unique |

LSBC takes no cash. If Inbound Payments arrives through a change order, these objects still map
across: one payment, its allocations to fee items, and a year on each.

`DM-19` `[OPEN]` **The deposit is also the unit of work for printing.** The CLOSE Licenses menu
is deposit-driven — Shop by Deposit, Renewals by Deposit, Print All by Deposit #, Manager by
Deposit Number. A deposit is not only a finance artifact.

Phase 6 note: LSBC confirmed no deposit number is needed on a payment (10 Nov 2026), so `Payment__c`
has none and printing is not batched by deposit. The print queue (Phase 6) works from the licence
instead.

---

## 2. Business rules — Week 6

BRE carries the decision logic; Flow carries orchestration. Rules expressed as decision matrices
are readable and versioned, and the administrator can change a threshold without touching a flow.

**As built (Phase 3).** Flows gather facts and write records; rules never query and never carry a
price. Thresholds are named constants inside each expression set, amounts and lookup tables are
decision matrices, and every rule was tested at its boundaries before any flow called it.

| Kind | Name | Covers |
|---|---|---|
| Decision matrix | `FeeSchedule` | Fee amounts and codes (`BR-07`) |
| Decision matrix | `ReciprocityStateRule` | States not accepted for reciprocity (`BR-16`, `DM-15`) |
| Decision matrix | `ApplicationPathExams` | Exams and Board approval per reciprocity path (`BR-19`, `BR-23`) |
| Expression set | `StopCodePerson`, `StopCodeSchool`, `StopCodeEstablishment` | The fourteen derived stop codes (`BR-02`) |
| Expression set | `FeeLateCalculation`, `FeeDuplicateLicense`, `LicenseExpirationDate` | Late and restoration fees, duplicates, expiry (`BR-08`, `BR-18`, `DM-08a`) |
| Expression set | `EligibilityStudentRegistration`, `EligibilityExamination`, `EligibilityReciprocity`, `EligibilityPermit`, `EligibilityInstructorCE` | Section 2.3 and 2.4 eligibility |
| Flow | Subflow: Stop Code Sync, Subflow: Stop Code Print Check, Subflow: Fee Renewal Assessment | Orchestration the portal and staff tools call |
| Flow | Eight record-triggered flows, four nightly schedules | Keep stop codes current |
| Flow | Screen Flow: Account Add Stop Code, Screen Flow: Regulatory Transaction Fee Item Change Year | Staff actions Add Stop Code and Change Year |

The eligibility rules are built but not yet called: the Phase 5 portal flows and Phase 6 staff
intake call them. Inputs that need a decision before then: a state with no `ReciprocityStateRule`
row is treated as accepted, and its own examination requirements are not yet recorded; the Regular
and International reciprocity paths use the license type's exams until those requirements arrive.
An existing master instructor keeps the status only while CE stays compliant (`BR-17a`, `OPEN-23`).

### 2.1 Stop codes

`BR-01` `[SETTLED]` **A stop code is a numbered hold with a description, effective date and end
date.** Active while the end date is blank; resolved once a date is entered. The licence stays
valid and renewable throughout — only printing and mailing are withheld. The print routine
checks that every stop code on a record carries an end date before producing a licence.

> **How "no end date" is stored.** `RecordAlert.ValidUntilDate` is required, so an alert cannot be
> saved with a blank end date. An open hold carries `ValidUntilDate` of 31 December 4000 (the
> platform maximum) with `IsActive` true; ending it sets `ValidUntilDate` to the moment it ended and
> `IsActive` false. A hold is live when `IsActive` is true and `ValidUntilDate` is in the future.
> Staff are trained that 12/31/4000 means "no end date".

> **A hold attaches to the holder, not the credential.** `RecordAlert` reaches Account, Contact,
> `Case` and `IndividualApplication`, but not `BusinessLicense`. With Person Accounts that works —
> the alert sits on the person or the establishment. The consequence is that a licensee holding
> three credentials gets one alert rather than one per licence, so the print routine checks alerts
> on the holder rather than on the thing being printed. Accepted; see `OPEN-37`.

`BR-02` `[SETTLED]` **Fourteen codes are derivable by the rules engine.** Each is checked by eye
today.

| Code | Description | Derived from |
|---|---|---|
| 1 | NSF | A returned payment reversing a fee |
| 3 | No active bond | School bond end date |
| 4 | Student Hours Incomplete | Accrued hours against programme minimum |
| 5 | Expired Cos License | `PeriodEnd` on the licence |
| 6 | No current cos lic for boothrenter | A held cosmetology licence (prerequisite) |
| 7 | No current cos lic for instructor | A held cosmetology licence (prerequisite) |
| 8 | Exam not passed | Person Examination result |
| 9 | No Esthetician License for Instructor | A held esthetician licence (prerequisite) |
| 15 | Restoration Exam | Lapse beyond three years |
| 16 | No Mgr License on Shop | Manager relationship on the establishment |
| 17 | Exam has not been taken | Absence of a Person Examination record |
| 20 | Needs re-registration | Six months without submitted hours |
| 21 | Non Payment | Outstanding fee balance |
| 31 | Restoration Exam Not Passed | Person Examination result |

**When each derived code opens and ends** (settled in Phase 3 build):

| Code | Opens when | Ends when |
|---|---|---|
| 1 | A `Payment__c` on the holder is marked Returned | Staff end it after verifying the repayment. The repaid fees are covered by code 21 |
| 3 | A School has no Surety Bond `Accreditation` covering today | A covering bond is recorded |
| 4 | A student has an open New Licensure application and approved hours are below the completion threshold | Hours reach the threshold |
| 5 | The holder's Cosmetologist licence `PeriodEnd` is past (status not Revoked, Retired or Deceased) | `PeriodEnd` moves forward |
| 6 | A Booth Rental Permit holder, or a person with an active Booth Renter ACR, holds no current Cosmetologist licence | A current licence exists |
| 7 | An Instructor licence holder holds no current Cosmetologist licence | A current licence exists |
| 8 | The latest attempt at an exam the licence type requires is a Fail | A Pass is recorded |
| 9 | An Instructor licence holder holds no current Esthetician licence | A current licence exists |
| 15 | A licence `PeriodEnd` is more than three years past | The licence is restored |
| 16 | A Salon has no active Owner or Manager ACR whose person holds a current operator licence (`BR-22a`) | One is recorded |
| 17 | An open licensure application needs an exam with no attempt on record | An attempt is recorded |
| 20 | A student's most recent hours ended more than six months ago | New hours arrive |
| 21 | A fee on the holder is Due or Partially Paid past its `DueDate` | It is Paid |
| 31 | The latest Restoration exam attempt is a Fail | A Pass is recorded |

Codes 7 and 9 follow this document: an instructor needs both licences. Whether that holds for every
instructor discipline should be confirmed with LSBC.

> The five prerequisite codes are the quiet win. A booth renter must hold a current cosmetology
> licence, an instructor must hold both cosmetology and esthetician, a shop must have a licensed
> manager. As rules these fire the moment a prerequisite lapses.

`BR-03a` `[SETTLED]` **Certification of contractual fees is a notarised statutory form.** Signed by
the school owner or authorised personnel under Louisiana R.S. 37:508.B, certifying the student has
paid all contractual fees and is therefore eligible to be **scheduled for examination or
transferred**. It gates scheduling, not only transfer.

`BR-03` `[SETTLED]` **Fourteen codes stay manual.** They need the code list, a reason, and the
ability for staff to set and clear a hold — not automation.

| Code | Description | Note |
|---|---|---|
| 2 | Student Loan Default | Originates outside the Board; notification route unknown |
| 10 | Inspection Report not received | Inspections are Phase 2; code exists for history and manual use |
| 11 | Incomplete Transaction | Applied at the counter |
| 12 | Violation | Set from violation capture (in Phase 1) |
| 13 | Proof of Education | Awaiting evidence |
| 14 | Fraudulent License | Pending revocation |
| 18 | Incorrect Address | Set on returned mail |
| 19 | No Termination Papers Received | School-related; student dropout |
| 22 | No social security card | Awaiting evidence |
| 24 | LIC OBTAINED BY FRAUD IN TX | Specific out-of-state finding |
| 27 | No Child Support | Originates outside the Board; notification route unknown |
| 28 | BOARD ORDER/Fee not paid | Follows a board decision |
| 29 | CAUGHT CHEATING DURING EXAM | Examination misconduct |
| 30 | Admin Violation | Administrative hearing pending |

`BR-04` `[PROPOSED]` **Three codes are not holds.** 23 Licence Revoked, 25 Licensee Retired,
26 Licensee Deceased never clear and never receive an end date. They belong as `BusinessLicense.Status`
values. If confirmed, the alert list drops to 28 codes.

`BR-05` `[SETTLED]` **Stop-code inputs are extensible to an inspection-violation source** so a
later phase needs no redesign.

`BR-06` `[OPEN]` CLOSE has **two stop-code buttons** — "Stop Codes" and "Stop Codes (revised)".
Two structures coexist. Which is authoritative affects both the rules design and any migration.
See `OPEN-15`.

### 2.2 Fees

`BR-07` `[SETTLED]` Fee codes are two-letter CLOSE codes and become external IDs on Product.
Confirmed so far: `FD` school renewal, `FH` late fees, `PO` failure to timely renew,
`PB` overpayment and refund request, `BY` miscellaneous, `PE` list, `AC` renewal. Full table from the code-table export.

| Rule | Code | Behaviour |
|---|---|---|
| Individual licence fee | — | $35 annually, due on the licensee's date of birth. Annual by legislative requirement; a three-year lapse triggers a restoration examination |
| Permit fee | — | $50 annually — threading, alternative hair design, shampoo technician, booth rental |
| Booth renter contract | — | $5, board-provided |
| Practical examination | — | $25 |
| State examination | — | $25 |
| School initial inspection | — | $100 |
| School final inspection | — | $300 |
| Violation | — | $25 per violation. A delinquent operator or salon licence is cited as a doubled licensing fee |
| Cleanup order | — | $100, issued in place of multiple citations when a facility reaches five sanitation violations. Seven days to correct, then a return visit |
| Late school registration | — | $2,500 per student where a school misses the 45-day window. Ten to twenty issued a year; one school once settled $120,000 |
| Records list request | — | A paid request handled by IT. Fee not yet known |
| Late penalty | `FH` | $35 per delinquent year on top of the standard $35, with late fees capped at **$465** |
| Duplicate licence | — | First free; $25 thereafter, one per year, paper request only, no digital copy |
| Affidavit | — | First free; $15 thereafter **per licence**, not per request |
| School renewal | `FD` | $190 a year, due before January 31 |
| School late renewal | `FH` + `PO` | $380 doubled renewal plus $175 failure to timely renew — $555 total |
| School bond | — | $30,000 bond must be current; checked in the print routine |
| Restoration | — | $25 examination plus renewal and late fees for every delinquent year. $25 retake. Money order or cashier's cheque only |
| Business renewal | — | Due by **January 31**. Peak intake December through February |
| Violation penalty | — | $25, payable within 15 days, then referral to the prosecutor |
| Student registration | — | $10, submitted by the school with the registration |

`BR-08` `[SETTLED]` **A full restoration totals $525**, made up of a $25 testing fee, a $35
renewal fee and $465 in late fees. The $465 is the cap on late fees. A card payment at the counter
reaches roughly $540 once the terminal's service charge is added, which is why two figures
circulate.

| Component | Amount |
|---|---|
| Testing fee | $25 |
| Renewal fee | $35 |
| Late fees, capped | $465 |
| **Restoration total** | **$525** |
| Same, paid by card at the counter | about $540 |

`BR-08a` `[OPEN]` **A service charge applies to card payments.** Whether it applies to all card
payments or only at the counter is unconfirmed, and it changes what the portal tells someone they
owe against what they are charged. See `OPEN-33`.

**As built (Phase 3).** Amounts live in the `FeeSchedule` decision matrix, keyed by fee name, with
the fee code beside each where it is confirmed (`FH`, `FD`, `PO`); its rows are kept in
`data/decisionMatrices/FeeSchedule.csv`. A price change is a new matrix version with a later start
date. The rules never carry a price: `FeeLateCalculation` holds only the $465 cap and the 36-month
restoration limit. Placeholders and gaps:

| Item | State |
|---|---|
| Fee codes for every fee except `FH`, `FD`, `PO` | Blank until the code-table export arrives. `AC` is not mapped: whether it is the individual $35 renewal is unconfirmed |
| Salon (business) renewal amount | Not stated. Renewal assessment stops with a message for a salon until a `Salon Renewal` row is added |
| Records list request | No amount (`OPEN-30`), so no row |
| Affidavit "first free, then $15 per licence" (`BR-26`) | No counter of prior affidavits in the model. Decide before the affidavit flow is built |
| Duplicate licence once a year (`BR-18`) | Enforced over a rolling twelve months from `LastDuplicateLicenseDate__pc` |
| Late years | Each passed anniversary of the paid-through date is one delinquent year; the renewal pays the current year, and each missed year carries a late fee until the cap |
| `LicenseExpirationDate` output | Returns midnight UTC. Whoever writes it to `PeriodEnd` should set a Louisiana-local time so the date does not show as the evening before |

`BR-09` `[SETTLED]` **A dedicated change-payment-year function is required.** CLOSE has one, with
a warning not to use the reversal screen for it — the year gets corrected often enough to warrant
its own path.

### 2.3 Eligibility

`BR-10` `[SETTLED]` Student registration requires DOE status of Seeking approval or Not seeking
approval. Rogue is rejected.

`BR-11` `[SETTLED]` Students may register from age 16.

`BR-11c` `[SETTLED]` **Hours are capped at 192 a month, from a maximum of 48 a week.** A
validation rule, and the ceiling any import must enforce.

`BR-11d` `[SETTLED]` **Hours match on identifier, dates and student ID — never on name.** The
legacy load inserts straight into tables on those three keys, and name matching is deliberately
avoided because names change and are mistyped. The platform load follows the same rule.

> Schools have a real incentive to keep hours current: a student cannot be registered for a
> written examination without them, and missing hours attract a penalty. That is what makes
> school-entered hours viable rather than wishful.

`BR-11a` `[SETTLED]` **Students have a 45-day window to register**, and commonly begin accruing
hours before the registration is entered. This is the root cause of the name and identifier
mismatches handled by the problem desk each month.

`BR-11b` `[PROPOSED]` **Schools register students immediately on enrolment, before hours accrue.**
Aligned in session. If the platform enforces this it is a process change for schools, not only a
validation rule, and should be presented as such.

`BR-12` `[SETTLED]` **A copy of the social security card is mandatory** and tracked as a Yes/No
field. EIN and TIN are refused. A foreign student must obtain a physical card before registering,
accruing hours, or being licensed. No exception path.

`BR-13` `[SETTLED]` **Two stages govern a student, and the hour figure behind each varies by
licence type.** The pattern is constant: a student tests before completing, and the licence issues
on completion. The thresholds are not.

| Stage | What it unlocks | Evidence required |
|---|---|---|
| Testing threshold | Application for practical and state examinations, $50 | Student licence, certification of contractual fees, a recent colour photo, cumulative hours report |
| Completion threshold | Completion and initial licensure, $35 | School certifies hours completed and the student contractually cleared, cumulative hours report attached |

For cosmetology those thresholds are 1,400 and 1,500. Other disciplines carry their own figures —
the Maintain School record holds a separate hour requirement for each of nine programmes, and the
testing application itself is used across cosmetology, manicurist, alternative hair design,
instructor and esthetician despite being titled with the cosmetology number.

Eligibility therefore sums approved hours against **the statutory minimum for that programme**,
read from configuration, never a hard-coded figure.

`BR-13a` `[SETTLED]` **Hours can be relinquished.** A notarised letter allows a student to give up
a stated number of hours in a named curriculum. Hours are therefore reducible by an attested
event, not only accrued.

`BR-14` `[SETTLED]` Reciprocity exam thresholds: **1,000 accrued hours** for the national
examination, **1,500** for the practical.

`BR-15` `[SETTLED]` **Licence-for-licence reciprocity on an active out-of-state licence overrides
an hour shortfall**, following board approval. The hour rule needs a documented exception path,
not a hard block.

`BR-16` `[SETTLED]` State exceptions are reference data LSBC maintains, not logic. Florida is
excluded because it issues 40-hour permits rather than licences.

`BR-17` `[SETTLED]` Instructors require practical, written and state examinations, and **16
continuing-education hours every other year** from a provider approved for that year.
`Last CEU Date` drives compliance.

`BR-17b` `[SETTLED]` **CEUs apply only to instructors.** No other licence type requires them.
Many people hold an instructor licence without teaching; the requirement applies to keeping it
active, not to holding it.

`BR-17a` `[SETTLED]` **Master instructor status requires five consecutive CEU cycles**, and a
missed cycle restarts the count. Tracking
broke when a prior system crashed and staff overrode dates manually with no history, so anyone
currently holding master status has an unverifiable gap behind them. The platform should track
cycles year over year from go-live rather than attempt to reconstruct.

`BR-18` `[SETTLED]` Duplicate licences are limited to one per person per year.

`BR-18a` `[SETTLED]` **A no-show carries a $25 administrative fee** on reapplication, unless the
candidate gives seven days' notice or 24 hours in an emergency. A separate no-show application
exists for rebooking. The mechanism to address the Board's no-show problem therefore already
exists in policy; it is not enforced systematically.

`BR-19` `[SETTLED]` Welcome Home Act applicants licensed one year in another state require the
state examination only.

`BR-20` `[SETTLED]` **Ability to Benefit is not built.** CLOSE carries ATB with separate Vocab and
Quant scores alongside Type of Diploma, as an alternative to a high school diploma, but it has not
been accepted for over a decade. See `OPEN-17`.

### 2.4 Application paths

`BR-21` `[SETTLED]` **Record types carry the process path; fields carry everything else.** A
record type is justified when the applicant sees a different form, a different person reviews it,
and it needs its own layout. Three yeses means a record type.

| Object | Record types | Fields |
|---|---|---|
| `IndividualApplication` | New licensure, Renewal, Reciprocity | Application path (Regular, Military, Foreign, Welcome Home Act); licence type sought as a lookup to `RegulatoryAuthorizationType` |
| `BusinessLicenseApplication` | New establishment, Renewal, New school | `BusinessType` for the establishment; licence or permit type sought as a lookup to `RegulatoryAuthorizationType` |

`BR-21a` `[SETTLED]` **`ApplicationForm` stays secondary.** It is available and supports multi-licence submissions through `ApplicationFormRelation`, but it is shaped for grants and benefits: Lead, Opportunity, Budget, Benefit and Program lookups, a scoring model of `Score`, `ScoreType` and `ScoreReason`, and no lookup to a licence type or to `BusinessLicense`. Adopting it as primary would mean taking on an evaluation model we do not need and losing the native licence links.

Four cases still need multi-licence behaviour: shop and manager renewing together, threading and
alternative hair design as paired facility and individual permits, booth renter permits dependent
on a current operator licence, and fees captured per credential. `ApplicationFormRelation` can
serve these without `ApplicationForm` becoming the primary object.

`BR-22` `[SETTLED]` **School is its own record type**, justified by the bond and by the opening
process. A new school submits a letter of intent, a two-year business plan, bank financial
statements, scaled floor plans, fire marshal reports, proposed curriculums, notarised teacher
statements and a $30,000 surety bond. An initial inspection at $100 and a final inspection at
$300 both require board approval before opening authorisation.

`BR-22a` `[SETTLED]` **A salon owner must hold the licence for the salon type, or employ a
licensed manager.** An owner present less than 80 per cent of the time must have a manager.
Enforcement is on the honour system today. Stop code 16 is the platform equivalent.

`BR-23` `[SETTLED]` **Reciprocity paths** — four under one record type:

| Path | Requirements |
|---|---|
| Regular | Verification of the current out-of-state licence. Examinations follow the originating state's requirements |
| Military | Application plus orders. $25 state laws and rules examination only; national waived |
| International | Foreign education, licences and language documents evaluated and translated by a board-approved third party, then board approval, before any examination |
| Welcome Home Act | One year licensed in another state. State examination only |

`BR-24` `[SETTLED]` **Threading and alternative hair design are different permits with different
paths.** They are commonly conflated; they are not the same.

| Permit | Path |
|---|---|
| Threading | Paper application plus a 15-question multiple-choice test, graded by hand by the programme manager. No schooling requirement. A cultural craft, commonly brought from India |
| Alternative hair design | 500 hours of schooling, registration as a regular student, then testing out. Covers natural hair care, braiding, weaving and wigry, without chemicals |

Both cost $50 and expire on the holder's birthday.

`BR-24a` `[SETTLED]` **A threading permit is only for people who hold no other licensure.** A
cosmetologist or esthetician may thread under their existing licence and does not need the
permit. Eligibility therefore checks for the absence of a held licence, not the presence
of one — the inverse of the prerequisite codes in `BR-02`.

`BR-25` `[SETTLED]` The **retake form is re-examination**, not an application. It belongs on
Person Examination.

`BR-26` `[SETTLED]` **An affidavit is both.** Requested on an application — first free, $15
thereafter — and produces a certification of licensure. Three variants:

| Variant | Content |
|---|---|
| Licensure | Initial and expiration dates, schools, hours attained, practical results (70% pass) and national results (averaged across passing attempts) |
| Reciprocity | Initial and expiration dates and the national score only |
| Student | Whichever results exist, plus whether licensure comes by examination or reciprocity |

Where grades or school information are missing, restoration research is required first.

`BR-27` `[SETTLED]` **Reciprocity licences renew identically to regular licences** after initial
testing. No separate renewal path.

`BR-28` `[SETTLED]` **A temporary permit is an event permit for an out-of-state licensee**, and a
bridge into reciprocity. The applicant holds a current licence in another state and needs to work
at a named event: hair show, beauty pageant, demonstration, movie set, reciprocity, or other.

- $50, applied for at least 30 days in advance, with a copy of the current out-of-state licence
  and the event dates
- Valid for **30 days from issue**, and renewable **once** before completion of testing
- Governed by Administrative Rule 1113.A and B
- Money order or cashier's cheque only

It belongs on the reciprocity path rather than as a standalone record type, and needs an expiry
clock plus a single-renewal rule. Owned by the problem desk, not the reciprocity desk.

---

## 3. Experience Cloud portal — Week 9

**As built (Phase 5).** The site is LSBC LPI at `/LPI` (Aura, Licenses & Permits template), in a
help-centre layout in LSBC's colours. Guests get licence search, the school directory, CE providers,
the complaint form, Forms & Resources and Sign Up; everything else needs a login. Every form is a
Screen Flow that follows its paper PDF section by section, built from shared subflows.

| Piece | How it works |
|---|---|
| Sign up | Two paths: a licensee matches licence number, last or maiden name and ZIP; someone new to the Board gives name, date of birth and contact details, and a person account is created unless the same name and date of birth is on file. Apex `PortalUserRegistration` creates the login; `RecordTriggerUserAfterSave` assigns the licences and the `PortalLicenseeAccess` group a minute later |
| Drafts | A form writes nothing to the application objects until Certify. It keeps a draft on `PreliminaryApplicationRef` (the standard object, used in place of the "Draft Application" in 1.2), with its documents on checklist items under the draft. Save for later is flow pause; My Applications lists saved forms with Continue, and the Aura `flowResume` component resumes them. Drafts untouched for 30 days are deleted nightly |
| Documents | Checklist rows come from `ApplicationDocumentRequirement__mdt`; each item is filed under a document category. The `documentChecklistUpload` LWC shows the checklist as rows with one upload each (`PT-18`). Items the form says are mailed, or sent by another state or company, are Sent to the Board: the applicant submits without them and staff upload them. Upload Documents on My Applications takes later uploads |
| Certification | Every form ends with the checkbox, typed name and timestamp (`PT-19`), showing the form's printed attestation |
| Payment | Fees come from the Fee Schedule; the pay step links to PayStar and takes the receipt as a checklist upload. Shop and facility fees are paid to the inspector as printed; when nothing is due the empty receipt item is removed |
| Rules called | Reciprocity exams from the `ReciprocityStateExams` matrix and `EligibilityReciprocity` version 2; temporary and threading permits from `EligibilityPermit`; duplicate and renewal fees from the Phase 3 rules |
| Access | Guest profile LSBC LPI Profile, member profile LSBC Portal User, sharing set on the user's own records. School Administrator and Business Owner access over Account Contact Relations waits for Phase 2 (`PT-02`) |

| Form (PDF) | Flow | Creates on Certify |
|---|---|---|
| License Renewal | `ScreenFlowIndividualApplicationRenewal` | One Renewal application per licence, a Duplicate application per duplicate, fees; a name change sets the Name Change Proof Pending hold |
| Reciprocity (Cosmetology, Esthetician, Manicurist, Instructor), Military, Foreign | `ScreenFlowIndividualApplicationReciprocity` | Reciprocity application with path, exams and answers; Person Language for the national exam; fees by path |
| Reciprocity Retake | `ScreenFlowIndividualApplicationRetake` | Retake application and a new Person Examination attempt (`BR-25`) |
| Temporary Permit | `ScreenFlowIndividualApplicationTemporaryPermit` | Reciprocity application, licence type Temporary Permit, with the event and its dates |
| Threading | `ScreenFlowIndividualApplicationThreadingPermit` | New Licensure application, Threading Permit; holders of a licence are told they don't need one |
| Affidavit | `ScreenFlowIndividualApplicationAffidavit` | Affidavit application (Renewal record type); first free, then $15 |
| Shop | `ScreenFlowBusinessLicenseApplicationShop` | The establishment (or the existing one), Owner and Manager relations, New Establishment application, fees |
| Threading / AHD Facility | `ScreenFlowBusinessLicenseApplicationFacility` | The establishment with its tax ID, Owner relation, New Establishment application, fees |
| New School Check List | `ScreenFlowBusinessLicenseApplicationSchool` | The school with its capacity, School Administrator relation, New School application, $100 fee; later items uploaded afterwards |

The 17 School Forms wait for the School Administrator audience (Phase 2).

### 3.1 Audiences

`PT-01` `[SETTLED]` **Four audiences driven by custom permissions, not profiles.** One person
commonly holds several roles — a salon owner is usually a licensed cosmetologist, a school owner
often a licensed instructor. One person, one portal user, with navigation and permission sets
turning on according to the roles they hold.

| Audience | Sees |
|---|---|
| Guest | Licence search, school directory, CE provider list, links to the agency site, complaint form if permitted |
| Licensee / Applicant | Base layer for every authenticated user: my licences, apply, renew, documents, fees |
| School Administrator | Student registration, rosters, hours reporting, school forms, the school's own licence |
| Business Owner / Manager | The establishment's licence, renewals and violations |

`PT-02` `[OPEN]` Access to a business account that is not the user's own depends on sharing
following an Account Contact Relation. **Unconfirmed — needs a sandbox spike before the portal
design is locked.** Fallback is share groups or Apex managed sharing. See `OPEN-11`.

### 3.2 Completeness before payment

`PT-03` `[SETTLED]` **An application cannot be paid for, or submitted, until every required
checklist item is satisfied.** Payment comes after completeness, not alongside it.

The reason is operational. Incomplete paperwork is returned by post with a letter listing what is
missing, at the Board's expense, and the same file commonly goes back more than once. A complete
application takes three to four weeks to reach a test date; an incomplete one restarts.

| Step | Behaviour |
|---|---|
| Build | Applicant completes the form, uploads documents against the checklist generated from the licence type |
| Evaluate | Submission stays closed until every required item is present. Missing items named on screen |
| Pay | Payment link becomes available only once the checklist is satisfied |
| Receipt | Captured as a checklist item in its own right |
| Review | Staff verify evidence and receipt against what is owed, then decide |

`PT-03a` `[SETTLED]` **Much of this is native.** Both application objects carry `AmountPaid`,
`PaymentDate`, `RequirementsCompleteDate` and `WasReturned`, so the completeness gate and the
return cycle are configuration rather than custom fields. `WasReturned` is a checkbox with nowhere
to record why, so a return reason is the one field worth adding — `ApplicationForm` has one and the
licensing objects do not.

`PT-04` `[SETTLED]` Common return reasons become checklist items with their own rules: missing
certification, expired licence, wrong fee, missing identity document or identifier, missing
testing evidence, missing signatures (school owner **or** student), unselected courses, incomplete
addresses, illegible handwriting.

`PT-05` `[SETTLED]` **Student registration checklist:** two passport photos, proof of birth
(birth certificate, state ID or driver's licence), copy of the social security card, proof of
education (diploma, transcript, GED or HiSET).

`PT-06` `[SETTLED]` **One photo replaces two.** Two are required today because one goes in the
paper folder and one travels with testing paperwork. One upload serves both.

`PT-07` `[OPEN]` **Bulk payment allocation.** Schools send one cheque for many students. Today
one bad application rejects the whole stack and costs nearly a month. Partial application requires
a deposit line to attach to several registrations and settle independently. The Phase 1 ledger in
`DM-18` is deliberately not extended to cover this; it depends on the decision about cheques in `OPEN-02`.

### 3.3 Registration and identity

`PT-08` `[SETTLED]` **Applicants create an account before applying.** Removes the need for guest
users to create application records, is required for status tracking, and avoids exposing
system-context code to anonymous traffic on an org holding PII.

`PT-09` `[SETTLED]` **Registration is licence-number lookup with secondary matching.** A portal
user must already hold an active licence; the portal does not create profiles for people the Board
does not already know.

| Step | Behaviour |
|---|---|
| Look up | The applicant enters their licence or certification number |
| Confirm | Secondary match questions on name and address, never the social security number |
| No match | The applicant is directed to contact the Board rather than allowed to create a record |

The social security number may be stored in Salesforce, encrypted and hidden, but is never used
as an external lookup key. That distinction is the whole point of the design: the identifier the
public types is a licence number, not a personal identifier.

`PT-09a` `[SETTLED]` **Capture a mobile number at registration**, to support text messaging in a
later phase.

`PT-09b` `[SETTLED]` **A rejection sends an automated email** explaining the reason.

`PT-22` `[SETTLED]` **Search is standard Salesforce search.** The Board has decided to use what
the platform provides rather than build around it.

Staff search the legacy system with a leading wildcard — the last four of an identifier as
`%0224`, or a date of birth as `04/24/%`. Standard search supports trailing wildcards, not leading
ones, so a fragment from the middle or end of a value will not match in the same way. What it does
instead is search names, identifiers, phone numbers and addresses together in one box, which
covers most of what staff currently do with several targeted queries.

> Worth knowing for migration and for access: the last four digits of an applicant's L number are
> their birth month and day. The identifier therefore encodes date-of-birth information, which is
> why staff can search either way.

This is a deliberate decision to accept standard behaviour. If it proves insufficient once staff
use it, the remedy is a short formula field holding the last four digits of each identifier so the
fragment matches as a whole value — but that is a later response to evidence, not a Phase 1 build.

`PT-10` `[SETTLED]` Public licence search, school directory and CE provider list follow one
pattern: a guest-accessible screen flow with Get Records in system context, results in a standard
data table. Guest access must be granted to each flow explicitly.

`PT-11` `[SETTLED]` Licence search covers individuals, establishments **and booth renters**, with
filters for organisation, city and licence type. School directory is searchable by programme and
city.

`PT-12` `[SETTLED]` **Accessibility is WCAG 2.1 AA.** Acceptance criteria cite that standard
rather than referring to state guidance generally. It applies to our components and to every PDF
LSBC moves across, which remains LSBC's content to remediate.

`PT-13` `[OPEN]` **The public search is empty at go-live.** The CLOSE-backed search at
lsbc.louisiana.gov stops working when CLOSE retires. With migration out of scope the Salesforce
search returns nothing for anyone licensed before go-live — which reads to the public as
unlicensed. Three options: run both searches in parallel, LSBC loads a minimal snapshot from our
template, or a small change order for a one-time load. See `OPEN-05`.

`PT-14` `[PROPOSED]` **Salon licence numbers begin with 777.** Staff manually switch modes today
rather than the system recognising the prefix. Derive it.

### 3.4 Staff-facing

`PT-15` `[SETTLED]` **Staff need an internal path** to enter an application on an applicant's
behalf, record a deposit, and attach a scanned document to the right record. The mailroom
continues to receive payments, address changes, returns and paper forms after go-live.

`PT-16` `[SETTLED]` **A standardised letter template with fillable fields** for dates and amounts.
The current character limit produces letters the Executive Director has called unprofessional.
Named sponsor on the renewal desk.

`PT-17` `[SETTLED]` **Name change at renewal sets a stop code** requiring proof before printing —
deliberately, so the licensee is not charged a $25 duplicate fee later. Preserve as designed.

### 3.5 Where components are used

`PT-18` `[SETTLED]` Flow carries the forms. LWCs only where Flow cannot do the job:

- Photo capture and crop, for the printed licence and field verification
- Document checklist upload, where an applicant attaches several documents on a phone with
  per-item status
- The licence type picker, if the combined list across both type objects needs search or grouping
- Public search results, only if the standard data table proves unusable in guest context

`PT-20` `[SETTLED]` **The form inventory, from LSBC's own register.** Fourteen numbered documents
with a named owner against each, plus four process areas without forms.

| Ref | Form | Owner |
|---|---|---|
| LSBC-001 | Threading / alternative hair design facility application | Programme manager |
| LSBC-002 | Affidavit — request for certification of Louisiana licensure | Problem desk |
| LSBC-003 | Reciprocity, in five variants: cosmetology, esthetician, manicurist, instructor, retake | Reciprocity desk |
| LSBC-004 | Reciprocity — military | Reciprocity desk |
| LSBC-005 | Threading application | Programme manager |
| LSBC-006 | Foreign reciprocity | Reciprocity desk |
| LSBC-007 | Florida transfer requirements | Reference, no owner |
| LSBC-008 | Cosmetology laws and rules | Reference, no owner |
| LSBC-009 | New shop / salon application | Shops and booth rental |
| LSBC-010 | New school checklist | Shops and booth rental, with the programme manager |
| LSBC-011 | Licence renewal application | Renewal desk |
| LSBC-012 | Booth renters information | **Not an application.** Five pages of federal independent-contractor guidance on worker classification. Reference only |
| LSBC-013 | Temporary permit application | Problem desk |
| LSBC-014 | School reference forms | Programme manager |

`PT-21` `[SETTLED]` **LSBC-014 is eleven forms in one document**, none of them published
individually. The portal has to account for all of them.

| Form | Note |
|---|---|
| Student enrolment application | The form already specified in `PT-05` |
| Certification of contractual fees | Notarised, statutory, gates scheduling and transfer |
| Notice of termination | Student dropout |
| Student registration transfer | Moving between schools |
| Notarised letter to relinquish hours | Hours given up from a named curriculum |
| Application for national exam | |
| Application for national retake exam | |
| Application for alternative hair design practical and state exam | |
| Application for practical and state exam | |
| 1,400 hour application for practical and state examinations | $50 |
| 1,500 hour completion form | $35 initial licence fee |
| Application for retake exam | |
| Application for no-show exam | $25 administrative fee |
| Accommodation request form, with a separate disability documentation form | |
| Student field trips, workshops and shows | |

`PT-19` `[SETTLED]` **Every application carries a certification block** — checkbox, timestamp,
typed name — built once as a reusable screen. No electronic signature product.

> **Confirmed by LSBC, November 2026:** a certification checkbox that the applicant has checked
> the information is correct, in place of DocuSign or any other e-signature. Every signature line
> on the paper forms becomes this step, showing the form's own attestation wording. Forms with no
> signature line get it too. A notarised form is still uploaded, unless the Board accepts the
> certification step in its place (client question).

`PT-23` `[SETTLED]` **Portal forms match LSBC's paper PDFs** (in `docs/`): the same sections in
the same order, labels and choices as printed, attestations verbatim, enclosures as checklist
items worded as printed. Details the Board already holds are filled in from the person's record,
not retyped. Every PDF field and where it is stored is in the "LSBC Application Form Field
Mapping" doc, which the Board approves before new fields are built. Forms are Screen Flows, not
OmniScripts (`PR-02`, `PR-03`).

`PT-24` `[SETTLED]` **Portal look.** The layout follows the help.hulu.com help centre (dark hero
with one large search, popular tasks, a topic tile grid, a "Need more help?" band, a dark footer)
in LSBC's colours and imagery: the wordmark navy, the seal's blue and gold, the Facebook cover
banner and the seal. Reference images are in `docs/branding/`.

---

## 4. Case management and violations — Week 10

**As built (Phase 4).** A violation raises its own fee and, through the Phase 3 stop code rules,
its own hold; payments clear it. Complaints arrive as Cases and become `PublicComplaint` records
when staff triage them.

| Kind | Name | Covers |
|---|---|---|
| Fields | `RegulatoryCodeViolation`: `Establishment__c`, `Practitioner__c`, `CitedParty__c`, `Case__c`; `RegulatoryTrxnFee.AmountPaid__c` | Who is cited and billed; how much of a fee is paid (`CM-02`, `CM-03`) |
| Validation rules | `EstablishmentOrPractitionerRequired`, `CitedPartyMatchesAccount`, `DescriptionRequiredOtherViolationType` | A violation names a party, bills a named party, and explains an Other |
| Reference data | Louisiana State Board of Cosmetology authority; placeholder `RegulatoryCode` and `ViolationType` records plus Other | Replaced when the violations list arrives |
| Flow | Record-Trigger: Regulatory Code Violation After Save | On create: the `Violation` fee from `FeeSchedule`, billed to the cited party, due 15 days after the violation date; sets Compliance Due Date. Stops the save if the fee is missing from the schedule |
| Flow | Subflow: Fee Amount Paid Sync; Record-Trigger: Payment Allocation After Save and Before Delete; Record-Trigger: Payment After Save (extended) | Totals allocations into Amount Paid and sets the fee Due, Partially Paid or Paid. Returned payments do not count |
| Hold | Existing code 21 (Non Payment) | Opens when the violation fee passes its due date unpaid, ends when it is paid. Code 12 stays a manual hold |
| Actions | New Violation on Case, business Account and Person Account; Record Complaint on Case | Staff capture; the Account actions pre-fill the party and Cited Party |
| Flow | Screen Flow: Case Record Complaint | Creates the `PublicComplaint`, the `ComplaintCase` link and participants, sets Case Type Complaint and moves the Case to Complaint Intake |
| Case setup | Queues Complaint Intake and General Inquiries; assignment rule `CaseRouting`; auto-response rule `CaseAcknowledgement` with two templates; Email-to-Case | Intake and routing (`CM-01`) |

Known limits: deleting several payment allocations on one fee at once leaves its Amount Paid too
high (delete them one at a time); a complainant becomes a participant only when the Case is linked
to a Contact. The sandbox Email-to-Case address and acknowledgement sender are JourneyBlazers addresses; production
needs LSBC mailboxes, forwarding and a verified LSBC sender (client questions).

`CM-01` `[SETTLED]` Email-to-Case intake, routing, assignment, prioritisation and status tracking.
The public complaint form is a guest screen flow on the portal (Phase 5) that creates a Case with
Origin Web, in place of Web-to-Case. The legacy CLOSE Complaints workflow is retired.

`CM-02` `[SETTLED]` **Violations are captured in Phase 1** against the establishment Account and
the practitioner. Regulatory Code carries the statute, the standard Violation Type object the
category (its records, not a picklist, with an Other record that requires an explanation),
Regulatory Code Violation the violation itself. Staff choose the cited party on each violation;
the fee and any hold go to that party.

`CM-03` `[SETTLED]` **The violation loop closes inside Phase 1.** A violation creates a $25
Regulatory Transaction Fee with a 15-day clock; unpaid past 15 days raises a Record Alert (stop
code 21, Non Payment); the hold blocks licence printing and ends when the fee is paid.

`CM-04` `[SETTLED]` **Everything downstream of a violation is Phase 2** — inspection visits,
enforcement actions, administrative hearings as records, facility grading.

`CM-05` `[PROPOSED]` **Administrative violations involve an external party.** Board staff log the
violation and set the hold, then send a file — names, addresses, licensing history, stop codes —
to the contracted prosecuting attorney, who drafts the hearing notice and any consent agreement.
Notices go by certified **and** regular post. Appeals go to the 19th Judicial District Court, rarely.

`CM-06` `[SETTLED]` **Consent-agreement penalties are not a fee until the board votes.** Funds are
entered only after board approval.

`CM-07` `[OPEN]` **Roughly 50 open administrative violation cases exist**, with active stop codes
holding licences from printing. With migration out of scope those holds do not exist in Salesforce
at go-live, and an affected licensee's licence will print. See `OPEN-03`.

---

## 5. Security, cutover and training — Weeks 11 to 12

### 5.1 Security model

`SEC-01a` `[SETTLED]` **Private by default, with sharing opened deliberately.** Of the three
options — public read/write, public read-only, and private with sharing rules — the Board chose
private. Front desk staff and other groups must not be able to see or change every record. Users
are segmented into named groups such as front desk and reviewer, and access is granted outward
from there rather than restricted inward from open.

`SEC-01b` `[SETTLED]` **The org is dedicated to the Board.** It is not shared with other
Louisiana boards such as pharmacy or home inspectors. No cross-board data separation is required.

`SEC-01` `[SETTLED]` Government Cloud Plus provides CONUS hosting aligned to OTS and FedRAMP
requirements. Core security model covers profiles, roles, permission sets and sharing for front
desk, finance, inspectors and leadership. An Inspector permission set group and role slot are
reserved now.

`SEC-01c` `[PROPOSED]` **The access matrix is kept in
[LSBC_Access_Matrix.xlsx](LSBC_Access_Matrix.xlsx)**, not in this document. It is the working copy
the Board reviews and the source the permission sets, groups and sharing rules are built from. In
outline:

| Layer | Shape |
|---|---|
| Profile | One profile, `LSBC Standard User`, cloned from Minimum Access. It grants nothing |
| Role | One per desk (section 6), for record visibility up the hierarchy. `SystemAdministrator` for admins and IT, who also own portal accounts |
| Permission sets | Small building blocks (`LicensingRead`, `PaymentEntry`, `AccommodationAccess`, …). Any that touch a Public Sector object is cloned from `PublicSectorAccessPSL`, so it carries the Public Sector Access licence |
| Permission set groups | One per desk, combining building blocks. A person covering two desks gets two groups |
| Sharing | Private by default. Sharing rules open records outward to a public group per desk |

`SEC-02` `[SETTLED]` **Person Accounts constrain the sharing design.** Org-wide default for
Contacts must be Controlled by Parent, or both Account and Contact set to Private.

`SEC-03` `[SETTLED]` **Shield is in Phase 1.** Confirmed by email in October 2026, reversing the
deferral recorded in the signed Statement of Work. Platform encryption, event monitoring and
Field Audit Trail are all in scope.

The signed SOW still carries the deferral assumption, and no re-signature is planned — the email
confirmation stands as the record. Note that the SOW's Scope section and Week 6 milestone row
always committed to Shield, so the executed document now describes the correct outcome in two
places and the superseded one in a third.

`SEC-03a` `[SETTLED]` **Shield is provisioned on January 15**, which is Week 10 — after the core
data model milestone at Week 6, and before UAT opens in Week 11 (`CUT-02`).

| Consequence | Response |
|---|---|
| Fields are built in December and encrypted in January | The encrypted field list is agreed as part of the Week 6 deliverable, so January applies a decision rather than making one |
| Encrypted fields cannot be used in some filters, formulas and list views | Anything built in December that depends on a field later encrypted breaks when encryption is switched on. The field list has to be known before those are built |
| Field Audit Trail is not retroactive | History starts on enablement. UAT history has no value, so this is accepted. The exception is any administrative violation hold hand-entered before cutover, which will carry no creation record |

`SEC-04` `[SETTLED]` The encrypted field list is a **Week 6 deliverable**, drafted by the build team
with no separate Board approval. Fields are built now and encrypted when Shield is provisioned. Dependencies on those
fields in formulas, filters and list views are avoided from the start.

**The encrypted field list** (Phase 1, November 2026):

| Field | Scheme | Why |
|---|---|---|
| `Contact.SocialSecurityNumber__c` (`SocialSecurityNumber__pc` on the Person Account) | Probabilistic | Identity. Never filtered or matched on (`OPEN-09`) |
| `PersonDisability.AccommodationDetails__c` | Probabilistic | Health information (`SEC-08`) |
| Person birthdate (`Contact.Birthdate`) | Confirm it is encryptable at enablement | Identity; the L number already encodes part of it |

Considered and **not** encrypted:

| Field | Reason |
|---|---|
| `MaidenName__c`, email, mobile | Used for secondary matching at portal registration |
| `BusinessLicense.Identifier` | The public lookup key for search and registration |
| `PersonDisability.Accommodations__c` | Picklists cannot be encrypted. Protected by field access to testing and reciprocity roles |

From now on, no formula, filter, list view, lookup filter or decision-matrix input may reference a
field on the encrypted list.

Rules that need the birthdate (birthday expiry, the age-16 check) never receive it. The calling flow
reads `Birthdate` and passes only a birth month and day, or an age in whole years. Reading the field
in Flow works under probabilistic encryption; filtering on it would not.

`SEC-05` `[SETTLED]` **Standard field history tracking enabled deliberately** on licence status,
exam results and hold status. Also on comment fields — CLOSE comment boxes have no edit lock and
no history, and anyone can change anyone's comment with no record.

`SEC-06` `[SETTLED]` The commitment made in session — that the new system will encrypt sensitive
files — is now accurate. No correction is owed. Social security cards currently sit in unlocked
filing cabinets without cameras; the platform replaces that with encryption at rest, access
control and an audit trail.

`SEC-07` `[OPEN]` If guest complaints are permitted, the guest flow pattern **creates** records
rather than only reading them. That is a materially larger security review than a read-only search.

`SEC-08` `[SETTLED]` **Accommodation data is health information**, and the Board has already made
a written confidentiality commitment on the form: the information and any supporting documentation
will not be shared with any outside source without the applicant's express written permission.

A dedicated accommodation request form exists, with a separate disability documentation form. The options are wider than extended time and a reader:

- Accessible testing site
- Braille, requiring one month's notice
- Reader for visual impairment, and separately for learning disability
- Sign language interpreter
- Extended time, at time-and-a-half or double
- Separate testing area

Accommodations surface at testing, not at registration. Access is restricted to the testing and
reciprocity roles, with encryption at rest and Field Audit Trail behind it from Shield enablement.
These fields belong on the Week 6 encrypted field list.

`SEC-09` `[SETTLED]` **Employee data is out of scope.** Onboarding, I-9, drug tests and civil
service records are excluded from the build.

### 5.2 Cutover

`CUT-01` `[SETTLED]` **Cutover is phased.** Staff go live on January 27, four days before the
January 31 business deadline, at peak volume, with back-office process owners on parental leave.
Mail volume rises from two or three deposits a day to five or six, at up to 40 items each. The
portal is built and tested to the Week 9 milestone but **published in March or April**, after
renewal season closes. See `OPEN-01`.

`CUT-02` `[SETTLED]` **UAT is conducted by LSBC staff** in a pre-production environment during
Weeks 11 and 12, using representative data. Written sign-off is required before production go-live.

`CUT-03` `[SETTLED]` Two train-the-trainer sessions: administrator and end user. Training guides,
Trailhead links, quick-reference guides.

---

## 6. Back-office processes — reference

Informs sections 1 to 5. Neither process disappears at go-live.

### 6.1 The mailroom

All incoming paper and money is triaged at one desk. Mail sorts into regulars at $35, mixed items
and violations; walk-ins cover registration, examinations, retakes and reciprocity.

| Step | Today |
|---|---|
| Create a deposit | In CLOSE: deposit number, date, department breakdown, payer name, amount, instrument type, date on instrument, batch number, system-generated tracking number |
| Scan cheques | Onsite scanner at end of day. Failed scans keyed into JP Morgan by hand |
| Reconcile cards | Walk-in receipts matched to authorization codes in Insider. Physical and card totals kept separate |
| Online payments | PayStar reports pulled by date and category each morning, entered into CLOSE as a card deposit |
| Track | Every deposit logged in Excel. At month end Excel must match the cash edit paperwork |
| Return | Incomplete submissions, incorrect amounts, unsigned instruments, temporary cheques and out-of-date instruments returned in full. Cash not accepted |

Volume: two to three deposits a day of up to 40 items, rising to five or six December through
February. Cheques retained about three years, then destroyed by an external vendor.

**Tracking numbers can be deleted by other users**, which is a cause of month-end reconciliation
failures.

### 6.2 The problem desk

Affidavits, school bonds, stop-code release, clerical corrections, address and name changes,
returned mail, frontline call triage.

- Affidavit requests processed and the certification auto-generated, then printed, signed,
  stamped, scanned, filed and mailed. Prior requests tracked in free-text comments.
- Weekly deposits cover returned-payment repayments, paid affidavits and school renewals with bonds.
- Stop codes released by verifying payment and setting the end date.
- Address and name changes require documentary proof.
- Returned mail marked undeliverable, address updated on proof, licence re-mailed.
- Entering a zip code auto-generates the parish.

**Returned payments, reversals and refunds:**

| Workflow | What happens |
|---|---|
| Returned payment | Stop code 1 applied with today's date, $25 fee added, three-part letter with return label. Repayment entered as a deposit line, stop code ended, case logged in a quarterly spreadsheet to the accountant |
| Reversal | Dedicated screen marks a payment for reversal; the correct fee code, year and amount re-applied, cash edit printed |
| Overpayment and refund | Any department requests a refund by entering the `PB` code against a payment, with a form carrying everything but the fiscal detail. The front desk verifies and signs it, then enters the refund with the cheque number once the cheque arrives. Status moves from Completed to Refunded. The accounting entry happens in QuickBooks, outside this platform |

All three turn on the fee code, the For Year and the tracking number.

### 6.3 The renewal desk

- The licence is a three-part form; the top portion is the renewal slip. Licensees frequently do
  not return it, instead writing their identifier on a cheque memo.
- About **half of all renewals arrive late**.
- Partial payments are applied to late fees, the renewal slip held, a dual-copy letter sent, and
  the file kept until the balance clears.
- Printing requires saving multiple times then opening Adobe separately.
- Monthly archiving produces up to 24 banker boxes, described by staff as a trip and fire hazard.

> **Policy tension, for LSBC leadership rather than the project.** Automated renewal reminders
> are supported by the renewal desk, but late fees are revenue and half of renewals are late.
> Building reminders reduces the Board's income. This should be an explicit decision, recorded.

### 6.4 Student hours

A bulk import, not a portal upload.

- Schools submit a spreadsheet to a dedicated mailbox by the tenth of each month, in a fixed
  eight-column format: first name, last name, identifier, month covered, hours earned that month,
  school identifier, sequence number, total hours.
- IT processes the file; exceptions return as a problem sheet marked NR for not registered.
- Flagged records are matched by hand on name and school identifier.
- **60-day grace period** after the tenth. Beyond that, hours must arrive with testing paperwork.
- A student with no hours for six months must re-enrol.
- Corrections arrive on a form and are recorded with old value, new value, date and initials —
  an audit trail the platform should keep natively rather than in free text.

### 6.5 The testing desk

A separate role owns examinations: scheduling, grade entry, and the letters that follow a failure.
Reciprocity hands completed paperwork across once payment has been processed and the deposit
balances. Practical and state examinations are administered on site; the national examination is
run by a third-party vendor. Grade entry is manual, and it is what exam-gated stop codes read.

**Official certifications arrive from other state boards in sealed envelopes.** A digital-first
design does not remove this, and whether a scanned certification is acceptable has not been answered.

### 6.6 Board governance

Board meeting agendas and minutes are managed entirely outside CLOSE, in Word. Preliminary agendas
posted three to five days before a meeting, final at least 24 hours before. Minutes approved at
the following meeting, then uploaded to the website and emailed to the state library. A reasonable
candidate for leaving exactly where it is.

### 6.7 Archives

Paper records sit in filing cabinets across the office. Microfilm runs from 1986 to 2025. Both are
excluded by the SOW; adding them was raised in session.

---

## 7. Out of scope

| Area | Note |
|---|---|
| Data migration from CLOSE | Platform configured to receive it. See `OPEN-03`, `OPEN-05` |
| Paper and microfilm digitisation | Raised in session as in scope; excluded by the SOW |
| Inspections and enforcement | Beyond violation capture. Phase 1 prepares the ground only |
| Payment integration | PayStar and Elavon. Phase 1 links out and records the receipt. Integration only under a signed change order |
| Knowledge base and public AI | Roadmap |
| Employee and civil service data | Explicitly excluded |
| lsbc.louisiana.gov replacement | Extent of any content move still being agreed |

### 7.1 Preparing for inspections

None of this builds inspections.

- `PRE-01` Validated physical addresses with geocoding on every business Account, plus parish for
  territory assignment
- `PRE-02` Stop-code inputs extensible to an inspection-violation source
- `PRE-03` Fee codes extensible so fines sit alongside application and renewal fees
- `PRE-04` Regulatory Code records usable as stop-code reasons now and inspection checklist
  references later
- `PRE-05` Inspector permission set group and role slot reserved

`PRE-06` `[OPEN]` Which inspection product Phase 2 uses. PSS includes Inspection Management with a
mobile app on the existing stack. Field Service is a separate managed package with its own licences
and data model, justified by scheduling optimisation across many inspectors or strong offline
needs. The Carahsoft quote carries eleven Field Service licences. See `OPEN-10`.

### 7.2 Interfaces not in scope

| System | State |
|---|---|
| PayStar | Web payments. Link out only |
| Elavon | Counter terminal payments |
| Converge | **Field payments taken by inspectors** on credit or debit, alongside money orders and cheques, documented on pink slips and funds-collected forms. A third channel, and the only one where money originates away from the office |
| National examination vendor | Scores keyed by hand. Three different vendor names given across three sessions |
| Encore | Field violations re-keyed manually. Does not talk to CLOSE |
| Foreign credential verification | Third-party agencies, recently changed after approximately 30 incorrectly issued licences |

### 7.3 Phase 2 requirements log

Captured during discovery, confirmed out of scope for Phase 1, logged so the Phase 1 build does
not have to be unpicked later. Each entry names what Phase 1 must do — which is usually nothing
more than leaving a door open.

#### Inspections

| Ref | Requirement | What Phase 1 does |
|---|---|---|
| `P2-01` | **Nine inspectors and one vacancy**, assigned by parish, living in the parishes they serve and starting from home. Workload balanced on salon count, so rural parishes clear quickly and dense ones like Baton Rouge absorb most effort | Parish on every business Account, derived from the postcode. See `PRE-01` |
| `P2-01a` | Routine inspection of every salon **twice a year**; complaint inspections within **14 days**, against a written fact-based complaint from a patron | Nothing. The cadence defines Phase 2 scheduling |
| `P2-01b` | Inspectors must be licensed cosmetologists with two years' chair experience, and their **own licence must be current** within a 30-day grace to issue delinquency violations | The prerequisite pattern in `BR-02` already covers this shape |
| `P2-01c` | A $100 cleanup order replaces multiple citations at five sanitation violations, with seven days to correct and a return visit. Discretionary today; the chief inspector wants it automated to standardise inspector behaviour | Nothing. Recorded in meeting notes as an aligned decision despite being out of scope — see `OPEN-28` |
| `P2-01d` | Field reports in use: inspection, booth rental, violation, pink slips for the money trail, school reports, and failure-to-inspect notices | Nothing |
| `P2-02` | Inspectors work on iPads using a third-party system, capturing paperwork and taking payment on site by cheque, money order or card | Nothing. Noted because on-site payment interacts with the money model in `DM-18` |
| `P2-03` | Initial shops, new locations and ownership changes require an on-site visit before opening. A shop may open immediately on passing; the office mails the licence within one to two weeks | Business Licence Application carries the approval, so an inspection outcome can gate it later |
| `P2-03a` | A failed inspection sets the establishment to **pending open**, with a list of required corrections emailed to the owner | Application status values should allow a pending-correction state from Phase 1 |
| `P2-03b` | Initial booth renter permits also require an inspector visit; renewals do not | Application record type already distinguishes new from renewal |
| `P2-04` | A violation fee schedule exists, maintained by the chief inspector, charging $25 per violation | Product records are extensible. See `PRE-03` |
| `P2-05` | An inspection checklist exists in current use | Regulatory Code records are usable as checklist references. See `PRE-04` |
| `P2-06` | Categorised violations should support reporting by county, city, facility and individual, and public-service messaging on common issues | Violation Type is a maintained picklist from Phase 1, so the categories accrue from day one |
| `P2-07` | Inspectors have no real-time access to licensing data in the field | Nothing. The licence search and record structure make this straightforward later |
| `P2-08` | A–F facility grading, modelled on food establishments | Nothing until violations have history to grade from |

#### Examinations and scheduling

| Ref | Requirement | What Phase 1 does |
|---|---|---|
| `P2-09` | Scheduling runs on an external national testing platform, navigated manually by date | Person Examination holds the result, not the booking |
| `P2-10` | Daily capacity is capped — roughly 30 cosmetologists, 16 estheticians (eight beds across two sessions), 15 manicurists. Historically 80 a day across morning and afternoon sessions; nobody recalls why it changed | Nothing. Capacity management is a scheduling concern |
| `P2-10a` | A roster must be run before each scheduling session to count remaining capacity by hand | Nothing |
| `P2-11` | No-shows waste booked slots at a significant rate | Nothing in Phase 1. A reminder capability would address it |
| `P2-11a` | Clearance letters carrying the arrival time are sent to schools, which distribute them to students. Students commonly say they never received theirs | A student portal login would let them retrieve it directly — raised by the testing desk as a wanted outcome |
| `P2-12` | Reciprocity applicants are not differentiated from new licensees and are scheduled by hand, by experience | Application path on the record makes the distinction available when scheduling arrives |
| `P2-13` | Accommodations — extended time and readers — are flagged through the national council's website | Captured on the examination path per `SEC-08`, not sent anywhere |
| `P2-14` | Written examinations are offered in English, Spanish and Vietnamese, without formal translation policy | Nothing. Noted as a policy gap the Board may want to close |
| `P2-15` | Failed candidates face no lockout and no mandatory additional hours; they pay and retest indefinitely | Person Examination carries attempt number, so a policy could be applied later without redesign |

#### Website and data

| Ref | Requirement | What Phase 1 does |
|---|---|---|
| `P2-16` | Public-facing data should come from the platform directly, rather than staff creating and uploading PDFs | The licence search and school directory establish the pattern. Extent of the wider content move is `OPEN-06` |
| `P2-16a` | Route optimisation and territory planning as the inspector team grows | Noted for a later phase; Salesforce Maps is the likely route |
| `P2-16b` | Consolidating the inspection report and the violation form into one workflow, ending duplicate entry | Nothing. A Phase 2 design principle |

#### Data validation raised in session

| Ref | Requirement | What Phase 1 does |
|---|---|---|
| `P2-17` | Shop numbers are entered with six or seven digits where nine are required | Validation on the Account identifier — **in Phase 1**, cheap and worth doing |
| `P2-18` | Physical and mailing addresses are confused | Address type is standard. **In Phase 1** |
| `P2-19` | Expired licences are not flagged where they should block something | Prerequisite stop codes cover this. **In Phase 1**, see `BR-02` |

> `P2-17` to `P2-19` were raised as Phase 2 pain but are Phase 1 work. They cost almost nothing
> and each was named unprompted by the staff who hit them.

---

## 8. Open decisions

| # | Item | Why it matters | Needed by |
|---|---|---|---|
| `OPEN-02` | Cheques and money orders after cutover | The Board must keep accepting them for now — card payment is recent and older licensees rely on paper. Phasing them out goes to the December board meeting. Until then the manual lane is built | December board meeting |
| `OPEN-38` | Freelance and mobile operators | Mobile salons, disability permits and 30-day temporary permits must file monthly itineraries or client rosters. Freelance operators without a fixed salon are a tracking gap the rules do not close. Needs board rules or legislation | Board, later phase |
| `OPEN-03` | Open stop codes at go-live | Around fifty live administrative violation holds. Without them, licences will print that should not | Immediate |
| `OPEN-05` | The migration volume | Licence records are in scope up to an agreed volume. The figure has not been set | Immediate |
| `OPEN-06` | Extent of the website content move | Agendas, minutes, directories, the rules book and FAQs all go past what has been confirmed | Immediate |
| `OPEN-11` | Sharing across Account Contact Relation | Decides whether school administrators and salon owners can be served declaratively | Sandbox spike |
| `OPEN-13` | Race and sex on the applicant record | A protected category. Still collected? Migrating? What access model? | Erin |
| `OPEN-14` | The Seminar module | May be where approved continuing-education providers and courses actually live | William |
| `OPEN-15` | Two stop-code files | Partial files received. A regular and a revised version exist — which is authoritative? | William |
| `OPEN-19` | Sealed certifications | Whether a scanned certification is acceptable, or the sealed original must be kept | Stephanie |
| `OPEN-20` | Renewal reminders | Half of renewals arrive late and late fees are income. A policy decision for the Board | Before backlog lock |
| `OPEN-21` | Remaining retention periods | Deposits three years. Cheques are given as one year here but about three years in section 6.1 — confirm which. Other document types sit with compliance | Compliance |
| `OPEN-22` | Knowledge base in or out | Half of all calls are students asking about scores — the largest single deflection target | Before backlog lock |
| `OPEN-24` | Enforcing registration on enrolment | Aligned in session. Enforcing it is a process change for schools, not only a validation rule | Before Week 7 |
| `OPEN-25` | Which exam forms consolidate | The Board wants all of them digitised. Several of the eleven overlap and should merge | Deborah |
| `OPEN-26` | The no-show fee | A $25 fee exists in policy but is not systematically enforced. Should the platform apply it? | Deborah |
| `OPEN-28` | Automatic cleanup orders | Recorded in distributed notes as agreed. It is inspections functionality and out of scope | Immediate |
| `OPEN-29` | The $55 renewal amount | The mailroom sorts renewal payments by amount. Nobody has explained $55 | Kiwan |
| `OPEN-30` | The records list request | A paid request for lists, fulfilled by IT. A product with a fee that appears nowhere in the design | Kiwan |
| `OPEN-31` | The staff wish list | Submitted previously and not located. May carry expectations not captured anywhere | The group |
| `OPEN-33` | The card service charge | Applies to card payments, raising a $525 restoration to roughly $540. All card payments, or only at the counter? | Carnita or the front desk |

### Settled

| # | Item | Where it landed |
|---|---|---|
| `OPEN-01` | Cutover shape | Phased. Staff in January. The portal is built on the original schedule but published in March or April after renewal season closes |
| `OPEN-04` | Temporary permits | A $50 event permit for an out-of-state licensee, valid 30 days, renewable once before testing |
| `OPEN-08` | OTS security posture | Shield is in Phase 1, so the posture the Board expected is the posture delivered |
| `OPEN-10` | Inspector headcount | Nine inspectors and one vacancy, connected iPads, no offline requirement. The native inspections framework is already provisioned |
| `OPEN-12` | The encryption commitment | Accurate, since Shield is in Phase 1 |
| `OPEN-16` | Late fees | $465 cap on late fees. A full restoration totals $525, or roughly $540 paid by card |
| `OPEN-17` | Ability to Benefit | No longer accepted and has not been for over a decade. Not a path we build |
| `OPEN-18` | Place of business and facility grading | Both to a later phase. The Board is taking each to counsel for the spring legislative package |
| `OPEN-23` | Master instructor history | Existing master instructors accepted as they stand at go-live; tracking starts fresh |
| `OPEN-07` | The paper and microfilm archive | The archive is sized: millions of records, billions of pages, hundreds of filing cabinets, 104 years. Enough to brief vendors |
| `OPEN-09` | Identity matching at registration | Registration is licence-number lookup with secondary matching on name and address. A portal user must already hold an active licence. The social security number may be stored encrypted but is never a lookup key |
| `OPEN-34` | Who sees what | Private by default. Users are segmented into named groups and access is granted outward, not restricted inward |
| `OPEN-35` | One platform, or several | One platform. The org is dedicated to the Board, not shared with other Louisiana boards |
| `OPEN-36` | Portal sign-up | Settled with `OPEN-09` — licence number, then name and address |
| `OPEN-27` | Operator licence renewal cycle | Annual, by legislative requirement. A three-year lapse triggers a restoration examination |
| `OPEN-32` | `ApplicationForm` as primary or secondary | Secondary. It is grant-and-benefit shaped — Lead, Opportunity, Budget and Program lookups, a scoring model, no licence type or licence link. The two application objects stay primary |
| `OPEN-37` | Holds attach to the holder, not the licence | Accepted. One `RecordAlert` per person or establishment, checked by the print routine. To be shown to the Board for feedback; a change would mean a custom lookup from `RecordAlert` to `BusinessLicense` |
| `OPEN-39` | Complaint intake | `PublicComplaint` carries the complaint, `Case` carries the work, `ComplaintCase` joins them. It beats `Case` with record types on anonymity, categorisation, intake channel and board reporting |

**The shape of what remains.** Twenty-one open, and the build is under way.

**One holds up the Week 6 data model and is ours to settle:** `OPEN-11`, the sharing spike
against Account Contact Relation.

**Two are with the Board and have dates:** `OPEN-02`, cheques and money orders, at the December
board meeting; and freelance operators without a fixed salon, which needs board rules or
legislation and is marked as such.

**Three affect what the public sees on day one:** `OPEN-05` the migration volume, `OPEN-06`
website scope, and `OPEN-03` the live administrative holds.

**The rest are configuration detail**, each with a named owner who has already been asked.

---

## 9. Source materials

Everything in this document traces to a document, a screen or a session. When building a flow,
a rule or a form, read the source rather than the summary — the detail below is where field
inventories, exact wording and edge cases live.

### Forms and procedures from LSBC

| Source | What it contains | What it drives |
|---|---|---|
| Applications inventory (spreadsheet) | Fourteen numbered documents with a named owner against each, plus four process areas without forms | `PT-20`. Note the register has at least one error: temporary permits are assigned to the problem desk, which disclaims them |
| Student enrolment application | The full field inventory in two blocks: applicant details, education history, prior-enrolment questions, school details, course selection, and **hours attending each day of the week** | `PT-05`, the student registration flow. The weekday hours fields are not modelled anywhere else |
| School reference pack (19 pages) | Eleven further forms, none published separately: certification of contractual fees, notice of termination, registration transfer, notarised relinquishment of hours, national and retake exam applications, practical and state applications, the 1,400-hour and 1,500-hour forms, no-show application, accommodation request and disability documentation, field trips | `PT-21`, `BR-13`, `BR-18a`, `SEC-08`. The accommodation form carries the Board's written confidentiality commitment |
| Registration procedures (SOP suite) | `REG-DP-001` application review and approval, `REG-DP-002` student registration, plus deposit preparation, mailing, and return and transfer processing. Effective 1 June 2026 | The three-pile sort (return, re-registration, initial processing), duplicate detection by identifier, and the education verification decision table — `BR-10`, `PT-03`, `PT-04` |
| Problem desk procedures (21 pages, with screenshots) | Affidavits, bonds, stop-code release, NSF handling, reversals, overpayments, clerical corrections, returned mail | Section 6.2, `BR-01`, `BR-26`, and the three money workflows |
| Mailroom procedures (21 pages) | Ten desks with their inputs and deposits, payment validation rules, sorting by amount, retention periods | Section 6.1, `DM-18`, `DM-19`, `OPEN-21`, `OPEN-29` |
| Reciprocity applications (five variants, plus military and foreign) | Field inventories per discipline, including gender, maiden name, originating state and school | `BR-23`, `DM-09` |
| Temporary permit application | Event types, the 30-day validity, the single renewal, Administrative Rule 1113.A and B | `BR-28` |
| Affidavit application | Request for certification of Louisiana licensure, including "name you were initially licensed under" | `BR-26`, `DM-05` |
| New shop or salon application, new school checklist | Establishment requirements, bond, inspections | `BR-22` |
| Licence renewal application | What a renewal actually asks for | `BR-21` and the renewal path |
| Booth renters information | **Not a form.** Five pages of federal independent-contractor guidance on worker classification | Reference only — do not build an application from it |
| Inspection checklist (revised April 2026) | Seven sections by facility type: paperwork, school facility, alternative hair design, nails, cosmetology, esthetics, facility maintenance, and first aid and sanitation across all types | `PRE-04`, `P2-05`. Six paperwork items are answerable from Phase 1 data |
| Violations list | Thirty-four findings as cited at inspection | `CM-02`, Violation Type reference data |
| Late school registration sanction letter | The graduated fine schedule with suspended amounts, the calculation from class start to receipt, and four cited rules including the one-instructor-per-twenty ratio | `BR-11a`, `BR-11b`, and the sanction calculation |
| Compliance desk procedure | Scope of the compliance role, and what sits outside the build | `SEC-09` |
| Test times | Practical examination durations broken down by station, per discipline | The segment-level examination model and `P2-10` |
| Cosmetology laws and rules | The statute book. Scanned, 62 pages | Regulatory Code reference data |
| State web accessibility policy and roadmap | PPM 74, effective February 2025, implementing the DOJ Title II rule. Compliance date 24 April 2026, with exemptions for pre-dating documents and archived content | `PT-12` and the website scope question |

### Legacy system screens

| Source | What it shows | What it drives |
|---|---|---|
| Stop code list (F9 lookup) | All thirty-one codes with descriptions | `BR-02`, `BR-03`, `BR-04` |
| Stop code maintenance | Code, description, effective date, end date | `BR-01` — a hold clears by end date, not status |
| Maintain financial transactions | Unapplied amount, applied previously, applied, amount left; line items of code, description, for year, fee, amount | `DM-14`, `DM-18` |
| Reverse transactions | Fee codes in use, the for-year field, the separate change-payment-year function | `BR-07`, `BR-09` |
| Maintain applicant | Record type, old certification number, maiden name, deceased flag, social security card received, instructor status, last CEU date, two stop-code buttons | `DM-05`, `DM-06`, `DM-08`, `BR-12`, `BR-17`, `BR-06` |
| View licence information | Licence history as a stack with tracking numbers, place of employment, manager and assistant manager designations | `DM-10`, `BR-22a`. Shop and manager licences renew as a pair |
| Maintain schools, and the bond screens | Hour requirements per programme across nine programmes; bond number, effective and end dates, underwriter | `DM-12`, `DM-17`. Bond numbers repeat with appended characters to force uniqueness — a migration collision risk |
| Student registration and hours | Transfer-hours flag per month, time since last completed | `DM-13`, `BR-11a` |
| Licenses menu and print screens | Printing batched by deposit number; the printed status flag | `DM-19`, and the print-status gap the front desk raised |
| Financial reports menu | Cash edit, overpayments, batch total, NSF | Section 6.2 |
| Front desk annotations | Balance owed not visible at payment entry; applicant, school and shop mode selection; comments editable with no record of who changed them | `SEC-05`, and three quick wins |

### What the client org actually provisions

Confirmed by export from the LSBC org, November 2026. Read this before building anything.

| Finding | Consequence |
|---|---|
| No `Authorization` object. The issued credential is `BusinessLicense`, holding individuals and establishments alike | Global naming change. Structure is unaffected |
| No payment objects — no `PaymentCart`, `PaymentCartItem`, `Invoice`, `PaymentInstruction` | Confirms `DM-18`. The ledger is custom because the platform objects are not provisioned, not because they do not exist |
| `PersonDisability` (17 fields) is standard | Accommodation data belongs here rather than on custom fields. See `SEC-08` |
| `PersonLanguage` (11 fields) is standard | Examination language — English, Spanish, Vietnamese |
| `Accreditation` (21 fields) is standard | The home for school DOE status. See the `DM` table in 1.1 and `DM-04` |
| `PersonEmployment` (15 fields) is standard | Compare against Account Contact Relation. ACR carries roles and dates and handles booth renters, so it remains the likely choice |
| `PublicComplaint` (40 fields), `ComplaintCase`, `ComplaintParticipant` are standard | Chosen over `Case` with record types. See `OPEN-39` |
| The full inspections framework is provisioned: `Visit`, `InspectionType`, `InspectionAssessmentInd`, `RegulatoryCodeAssessmentInd`, `ViolationTypeAssessmentInd`, `AssessmentIndicatorDefinition`, `AssessmentTask`, `ViolationEnforcementAction`, `Location`, `Polygon` | Phase 2 needs no additional product. The eleven Field Service licences on the quote should be re-examined |
| `ApplicationForm`, `ApplicationFormRelation`, `ApplicationFormEvaluation` are provisioned | The multi-licence schema exists. Only the agentic intake needs Agentforce. A sandbox spike can settle whether a Screen Flow can write to it |
| `Employee` and `Employee2` are set to No Access | Matches the scope boundary confirmed with compliance |

### Platform sources

| Source | Relevance |
|---|---|
| Winter '27 release notes | Inbound Payments reaching general availability behind Billing licences; agentic application intake requiring Agentforce and Data 360; Workforce Scheduling; the location address picker; removal of `ApplicationFormTemplateId` from `IndividualApplication` |
| `PaymentCartItem` object reference | Four meaningful fields, referencing `Invoice`. Evidence for the `DM-18` decision |
| `Payment` object reference (core) | Order Management semantics, parented to an order payment summary. Also evidence for `DM-18` |

### Sessions

Eleven working sessions, recorded and transcribed: initial discovery and a follow-up with the
Executive Director; the mailroom; affidavits and the problem desk; reciprocity; student
registration; renewals; board governance; threading, school enrolment and testing; compliance;
inspections; and the front desk. Where this document states what a desk does, the transcript is
the source.

---

## 10. Change log

| Date | Change |
|---|---|
| 6 Nov 2026 | Shield removed from out of scope; it is in Phase 1 (`SEC-03`). |
| 6 Nov 2026 | Portal built to the Week 9 milestone, published March or April. `CUT-01` settled, milestone map and `OPEN-01` updated. |
| 6 Nov 2026 | `SEC-03a` aligned with `CUT-02`: Shield on January 15 comes before UAT opens in Week 11. |
| 6 Nov 2026 | Duplicate `OPEN-25` resolved: complaint intake renumbered `OPEN-39`. |
| 6 Nov 2026 | `BR-20` settled per `OPEN-17`. Stale `OPEN-16` reference removed from `BR-08a`. |
| 6 Nov 2026 | `OPEN-21` flags the conflicting cheque retention figures (one year vs about three in 6.1). |
| 6 Nov 2026 | Open count corrected to twenty-two. Sections 3.5 and 3.6 renumbered 3.4 and 3.5; 7.2 moved before 7.3. |
| 6 Nov 2026 | Section 9 org findings updated for the settled `Accreditation` and `PublicComplaint` decisions. |
| 6 Nov 2026 | `BusinessLicense` holder corrected to `AccountId`. `DM-01a` adds business Account record types `Establishment`, `School`, `Organization`. |
| 6 Nov 2026 | Training Course API name recorded as `TrnCourse`. |
| 6 Nov 2026 | `OPEN-37` settled: holds attach to the holder. `SEC-04`: encrypted field list needs no Board approval; encrypt after build. |
| 6 Nov 2026 | Phase 1 data model built. `DM-08a` added: one `BusinessLicense` per credential, renewals extend `PeriodEnd`. |
| 6 Nov 2026 | `DM-17`: school bonds are `Accreditation` records (Type Surety Bond), not licences. |
| 6 Nov 2026 | `DM-15`: reference lists placed — Organization Accounts by `Account.Type`, yearly approvals as `Accreditation` records. |
| 6 Nov 2026 | Course Offering gains a `School__c` lookup; the standard object has none. |
| 6 Nov 2026 | `SEC-04` encrypted field list drafted in 5.1. |
| 6 Nov 2026 | `DM-05`, `DM-06`, `BR-04` built ahead of LSBC confirmation; still marked PROPOSED. |
| 6 Nov 2026 | Person-level fields (maiden name, legacy certification number, social security number and card, duplicate licence count) live on **Contact** and surface on the Person Account as `__pc`. Account custom fields are for business accounts. |
| 6 Nov 2026 | Parish is one global value set, `Parish` (64 parishes plus Out of state), used by `Account.Parish__c` for business addresses and `Contact.HomeParish__c` for home addresses. |
| 6 Nov 2026 | `BusinessLicenseStatus` gains Active alongside Retired and Deceased. |
| 6 Nov 2026 | Parish is the global value set `Parish` (64 parishes plus Out of state), used by `Account.Parish__c` for business addresses and `Contact.HomeParish__c` for home addresses. Picklists shared across objects are global value sets. |
| 6 Nov 2026 | `BusinessLicenseStatus` gains Active alongside Retired and Deceased. |
| 6 Nov 2026 | Person Account record type relabelled **Person** and given a description; developer name `PersonAccount` unchanged. |
| 6 Nov 2026 | Metadata labels and API names use US spelling (License, Program, Check) to match the platform; this document keeps its own spelling. |
| 6 Nov 2026 | `SEC-01c` added: the access matrix lives in `LSBC_Access_Matrix.xlsx`, first draft proposed. `ProgrammeManager` role renamed `ProgramManager`. |
| 6 Nov 2026 | Naming convention adopts the CFPB conventions and Automation Champion's flow conventions. Flow labels carry the flow type; API names drop the punctuation; one record-triggered flow per object per context. |
| 6 Nov 2026 | Phase 2 (security) paused pending Board feedback on the access matrix. Phase 3 (business rules) proceeds; rule flows run in system context so they do not depend on the access model. |
| 6 Nov 2026 | `BR-01`: `RecordAlert.ValidUntilDate` is required, so an open hold carries 31 December 4000 with `IsActive` true; ending it sets the date to now and `IsActive` false. |
| 6 Nov 2026 | `BR-02`: opening and ending conditions settled for the fourteen derived codes. Code 1 opens automatically and is ended by staff; code 4 opens only against an open licensure application; codes 7 and 9 both apply to every instructor, pending LSBC confirmation. |
| 6 Nov 2026 | `Examination` gains `ExamType__c` and `LicenseType__c`; the standard object cannot otherwise tell a national exam from a practical, or one licence's exam from another's. |
| 6 Nov 2026 | `BR-01`–`BR-03` built: Subflow: Stop Code Sync reconciles holds from the Stop Code rules; six after-save flows and four nightly schedules call it; Subflow: Stop Code Print Check answers whether a holder may print; staff add manual holds with the Add Stop Code action on Account. |
| 6 Nov 2026 | Stop code sync also runs when an application opens or closes and when a fee's status changes. Add Stop Code placed on the business and Person Account layouts. |
| 6 Nov 2026 | `BR-07`–`BR-09`, `BR-18` built: `FeeSchedule` decision matrix, `FeeLateCalculation`, `LicenseExpirationDate`, `FeeDuplicateLicense`, Subflow: Fee Renewal Assessment, and the Change Year action on fee items. `Contact.LastDuplicateLicenseDate__c` added. Placeholders and gaps listed under 2.2. |
| 6 Nov 2026 | `DM-15` settled: state reciprocity exceptions are the `ReciprocityStateRule` decision matrix. Section 2 eligibility built: hours validation (`BR-11c`, `BR-13a`), `ApplicationPathExams`, and five eligibility expression sets. 5.1 notes how rules avoid the birthdate. Phase 3 complete; section 2 opens with an as-built summary. |
| 9 Nov 2026 | Defect fixed: batched flow runs opened duplicate stop code holds (code 21 six times on one test holder). Each trigger and schedule now syncs once per holder per batch, and the sync ends duplicates, keeping the oldest. Schedules moved to 00:30–01:00 org time; the org runs on Pacific time, not Central. |
| 9 Nov 2026 | `CM-02`: Violation Type uses the standard `ViolationType` object, not a picklist; an Other record requires an explanation. Staff choose the cited party (establishment or practitioner) per violation; the fee and hold go to that party. |
| 9 Nov 2026 | `CM-03`: an unpaid violation fee opens the existing code 21 (Non Payment). Code 12 stays a manual hold. Payments set the fee's Amount Paid and Status through payment allocations; returned payments stop counting, and deleting an allocation re-totals the fee. |
| 9 Nov 2026 | `CM-01`: Web-to-Case dropped; the public complaint form is a portal guest screen flow in Phase 5. Complaints become `PublicComplaint` records through the Record Complaint triage action on the Case. |
| 9 Nov 2026 | Phase 4 built: violation capture and loop, payment allocation sync, Case queues, routing, acknowledgements, Email-to-Case and complaint triage. Section 4 opens with an as-built summary. |
| 9 Nov 2026 | `PT-19` confirmed by LSBC: a certification checkbox, typed name and timestamp in place of DocuSign or any e-signature. Notarised forms are still uploaded unless the Board decides otherwise. |
| 9 Nov 2026 | `PT-23` added: portal forms match LSBC's 15 application PDFs section by section, as Screen Flows. The "LSBC Application Form Field Mapping" doc maps every PDF field; 20 new fields are proposed there for Board approval. The School Forms packet (17 forms) is mapped and built with the school portal. |
| 9 Nov 2026 | `PT-24` added: the portal follows the help.hulu.com help-centre layout in LSBC's branding (Facebook cover banner and seal, in `docs/branding/`). |
| 10 Nov 2026 | Phase 5 built: the portal site, sign-up, guest pages and the application forms. Section 3 opens with an as-built summary. |
| 10 Nov 2026 | Portal drafts use the standard `PreliminaryApplicationRef` in place of a custom Draft Application object; nothing is written to the application objects until the applicant certifies. Save for later is flow pause (enabled for the org); drafts are deleted after 30 days untouched. |
| 10 Nov 2026 | `PT-09` extended: sign-up has a second path for people new to the Board, who have no licence number to match. |
| 10 Nov 2026 | `PT-18`: the document checklist upload LWC is built, with document categories. Documents that reach the Board by mail or from a third party are marked Sent to the Board and don't stop the applicant submitting. |
| 10 Nov 2026 | `BR-19`: the reciprocity state tables (06/2024) are a new decision matrix, `ReciprocityStateExams`, read by `EligibilityReciprocity` version 2; `ReciprocityStateRule` is retired. The original licence is the out-of-state licence with the earliest initial date. |
| 10 Nov 2026 | `BR-25`: a retake is both an application (for certification, checklist and fee) and a new Person Examination attempt. |
| 10 Nov 2026 | Facility tax ID stored on a new `Account.TaxIdentificationNumber__c`: `BusinessProfile` has no tax field in this org. |
| 10 Nov 2026 | Portal screen flows carry plain labels (shown to applicants in the Save for later dialog); their API names follow the naming convention. |
| 10 Nov 2026 | `DM-18a` revised: the payment ledger covers every fee. Staff record mailed payments with Record Payment on the Account; accepting a PayStar receipt creates the payment. No cash, no deposit number (`DM-19` note). |
| 10 Nov 2026 | `DM-18b` as built: a Refund action on the payment steps through request, verify and refund. Unapplied Amount now subtracts a completed refund. Refunds of applied money raised as a client question. |
| 10 Nov 2026 | `DM-18c` as built: LSBC Finance reports Overpayments, Refund Reconciliation, Payments by Received Date and Payments Applied by License Year. |
