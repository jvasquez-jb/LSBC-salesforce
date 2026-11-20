# LSBC Salesforce Public Service Platform — Solution Design

**Client:** Louisiana State Board of Cosmetology
**Engagement:** Phase 1 Foundation, Carahsoft SOW 66003598, NASPO LA 4400010663
**Status:** Built in the LSBC-Partial sandbox except security (section 5.1), which is paused for
the Board's feedback on the access matrix. The portal is built and stays unpublished until March or April 2027.
CLOSE data is loaded into the sandbox (section 7).
**Last updated:** 12 November 2026

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

**Code in the build.** `PR-02` keeps code to what Flow cannot do. Everything below is code the
administrator should know exists; each piece only moves data or lays out a screen, and none holds a
business rule. Payments, refunds, the print queue, stop codes and every form are Flow.

| Component | Kind | Why it is code |
|---|---|---|
| `PortalUserRegistration` | Apex, called from the sign-up flow | Creates the portal login. A flow run by a guest cannot create a user |
| `LetterPdfController`, `LetterPdfSaveAction`, page `LetterPdf` | Apex and Visualforce, called from Generate Letter | Renders a letter as a PDF and saves it to the record. The org has no internal Document Generation runtime. Wording is in Letter Template custom metadata |
| `DocumentChecklistUploadController` and the `documentChecklistUpload` component | Apex (read-only) and LWC | The document upload screen: lists an application's checklist items and their files |
| `flowResume` | Aura component | Resumes a saved portal form from My Applications |

Each Apex class has a test class. There are no Apex triggers.

### 0.3 Milestone map

| Milestone | Week | Sections | Build status (12 Nov 2026) |
|---|---|---|---|
| Discovery complete | 3 | — | Done |
| Core data model and security | 6 | 1, 2 | Data model and business rules built. Security paused for the Board's access-matrix feedback |
| Experience Cloud portal — built and tested, not published | 9 | 3 | Built, except the School Administrator and Business Owner audiences and the 17 School Forms, which wait for security |
| Case management and violations | 10 | 4 | Built |
| UAT, training, staff go-live | 12 | 5 | Staff tools, reports and training guides built. Staff access waits for security. The build team has run the UAT scripts on the migrated data and fixed what they found (12 Nov); the Board's UAT has not started |
| Public portal published | March or April 2027 | 3 | Not published |

---

## 1. Data model — Week 6

> **Object naming, confirmed in the client org.** There is no `Authorization` object in Public
> Sector Solutions. The issued licence or permit is **`BusinessLicense`**, and it carries both
> individuals and establishments — the holder is `AccountId`, which with Person Accounts covers
> both. `ContactId` also exists but is not used. Every Authorization* object in the org belongs to Consent Management and is unrelated.
> Note that `AuthApplicationPlace` still labels its lookup to `BusinessLicense` as "Authorization",
> so the older name survives in relationship labels.

> **Every field goes on a layout and gets admin access.** Each custom field the build creates is,
> in the same change, added to its object's page layout (read-only when a flow or the applicant sets
> it) and given field access in `PublicSectorAccessAdminPSL`. Staff and testers can only check what
> they can see; a field missing from the layout hides an applicant's answer or a rule's input.
> `scripts/checks/field_coverage.py` lists any field that breaks this and is run before each commit.
> The only field kept off every layout is the social security number. Staff field access for each
> role is decided with the access matrix (5.1).

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
| Account (person) | Licensees, instructors, students, booth renters | Identity, photo, maiden name, legacy certification number, earlier affidavit in CLOSE |
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
birthday. It requires a current operator licence (cosmetologist, esthetician or manicurist; LSBC
confirmed any operator licence on 12 Nov 2026) **and** a current salon licence, plus a $5
board-provided contract.

The **initial** permit requires an inspector visit: signatures from both the salon owner and the
booth renter, and verification that the salon licence is current. **Renewal** follows the ordinary
renewal path with no inspector. Inspectors currently issue initial booth permits against salons
with expired licences because nothing checks — see `BR-02`, code 6.

`DM-04` `[SETTLED]` **DOE status is a rules input, not a label.** Values: Seeking approval,
Not seeking approval, Rogue. A student from a rogue school cannot be registered at all.

`DM-05` `[PROPOSED]` **Maiden name is stored** and used as a secondary match key at portal
registration. A licensee who married since their last renewal is the classic duplicate case.

`DM-06` `[PROPOSED]` **Legacy certification number is stored** as a second match key for any
later migration. CLOSE carries `Old Certification#` predating current numbering.

`DM-07` `[OPEN]` CLOSE stores **race and sex** on the applicant record. Confirm whether race
is still collected and what for. If it migrates it needs field-level restriction from day one.
Shield is in Phase 1 (`SEC-03`) but is not provisioned until January 15 (`SEC-03a`), and a picklist
cannot be encrypted, so field access is its main protection either way. See `OPEN-13`.

### 1.2 Applications and licensure

| Object | Purpose | Key content |
|---|---|---|
| Draft Application | Part-finished portal submissions | Save-and-resume payload |
| Individual Application | Person-side requests | Record types: New licensure, Renewal, Reciprocity. Originating state, application path, certification block |
| Business Licence Application | Establishment requests | Record types: New establishment, Renewal, New school |
| `BusinessLicense` | The licence or permit, for individuals **and** establishments | `Identifier`, `AccountId` as holder (a Person Account for individuals, a business Account for establishments; on a person's licence `ContactId` holds the person's Contact as well, filled by `Record-Trigger: Business License Before Save` and backfilled on every migrated person licence), `RegulatoryAuthorizationType`, `PeriodStart` / `PeriodEnd`, `Status`, `IsActive`, `BusinessType`, `VerificationStatus` / `VerifiedDate`, and the jurisdiction and issuer fields for out-of-state credentials |
| `AuthApplicationPlace` | The place recorded against a licence at issue | Application, licence, and `Place` as a lookup to `Location` or `Address` |
| `RegulatoryAuthorizationType` | Configuration per licence or permit type | Fourteen fields, and sparse: `DurationType`, `RegulatoryAuthCategory`, `RegulatoryAuthCode`, `ProcessingDuration`, `ApplicationUrl`, `IssuingDepartment`. The fee, term length, renewal cycle, continuing-education requirement, hour thresholds and required examinations are all **custom fields**. `BusinessLicense` looks up to this object for both individual and establishment credentials |
| `BusRegAuthorizationType` | Unused. Comes with Public Sector Solutions; links a business type to the licence types it needs | Left empty: LSBC applicants choose their form, and each `BusinessLicense` points straight at its `RegulatoryAuthorizationType`. Salesforce confirmed on 19 Nov 2026 that no standard feature needs it filled in |
| `DocumentChecklistItem` | Outstanding requirements | `IsRequired`, `IsAccepted`, `Status`, `Instruction`, with `DocumentType` and `DocumentCategory` lookups. `ParentRecordId` reaches both application objects, `RegulatoryCodeViolation`, `PersonExamination`, `CourseOffering`, `PersonDisability` and `PreliminaryApplicationRef` — so a violation's payment receipt has a home without touching the ledger |
| `RecordAlert` | Surfaces a hold to staff | `EffectiveDate`, `ValidUntilDate`, `IsActive`, `Severity`, and a `RecordAlertCategory` lookup — so CLOSE's thirty-two stop codes (code 32 was added in October 2026) become category records rather than a picklist, maintainable by an administrator. Twenty-nine are built, because `BR-04` makes three of them licence statuses, plus a Name Change Proof Pending hold |

`DM-08` `[SETTLED]` **`BusinessLicense.Status` carries terminal states.** Revoked, Retired and
Deceased are not holds — they never clear and never receive an end date. CLOSE already has a
separate Deceased flag on the applicant, which supports this. See `BR-04`.

`DM-08a` `[SETTLED]` **One `BusinessLicense` per credential, kept for life.** A renewal moves
`PeriodEnd` forward on the same record; it does not create a new one. `Identifier` therefore stays
the single public lookup key, and stop-code and prerequisite rules never have to find "the current
one". Year-by-year history comes from renewal applications, fee items carrying `ForYear__c`, and
field history. Credential-level facts — `LastCEUDate__c`, `ConsecutiveCEUCycles__c`,
`IsMasterInstructor__c`, `InstructorStatus__c` (Active or Inactive, from CLOSE; a master instructor is also active or inactive; it does not change the fees), `RenewalCount__c` — live on the licence.

> `BusinessLicenseStatus` in the org ships with Inactive (default), Revoked, Draft and Verified.
> Phase 1 added Active, Retired and Deceased. 16 Nov 2026 added Expired.

As built (16 Nov 2026): staff can set Expired on New License, and Decide's renewal approval sets an
Expired licence back to Active. The public search shows a licence past its end date as "Expired on
<date>", and sign-up and the threading permit accept an Active or Expired licence. The nightly change
that sets a licence past its `PeriodEnd` to Expired (version 3 of the business licence schedule) is
built and tested but **held**: version 2 stays active until Jonathan approves it, so until then a
lapsed licence keeps its status. The change is kept in `docs/held-changes/nightly-license-expiry.patch`.

As built (16 Nov 2026), renewals: a renewal's fee is filed under the renewal application, not the
licence (`SubflowFeeRenewalAssessment` takes the application), with items named for the licence type
("Cosmetologist renewal", "Cosmetologist late fee"). A licence with a renewal waiting is not offered
for renewal again. A multi-licence renewal has one Payment Receipt item, on its first application.

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
side. State reciprocity exceptions are the `ReciprocityStateExams` decision matrix, built from the June 2024
state tables (`BR-19`). It replaced `ReciprocityStateRule` on 10 Nov 2026.
Each date in the tables is when a state started or stopped giving the NIC theory or practical exam (the Board built them from NIC's State Education and Licensing Guide): on a start date the later period applies, on a stop date the earlier one (Board, 19 Nov 2026). Version 2 of the matrix sets Utah to the state exam only and moves Indiana's cut-off to 1 Jan 2007. Licences earned by apprenticeship, experience or online training, and the types the Board doesn't accept from any state (Hairdressing, Hairstyling, Hair Design, Hairdresser, Hairdresser/Cosmetologist, Hairdressing and Manicuring, Cosmetician, Class CA, Class CH, Florida specialists), are applicant answers that `EligibilityReciprocity` turns into Cannot Transfer. Military applicants pay $25 for the state exam and $50 for a military permit. The Board issues them only the Military Permit, never a regular licence; it renews yearly for $50, with a $50 late fee once it is more than 30 days expired (the licence type's Late Fee Grace Days).
Violation types and regulatory codes are Phase 4 reference data.

`DM-16` `[OPEN]` CLOSE has a **Seminar module** — Maintain Seminar Details and Maintain Seminar
Codes — which may be where approved CE providers and courses actually live. Confirm before
assuming Training Course and Course Offering cover it. See `OPEN-14`.

**As built (11 Nov 2026).** CLOSE's seminar module holds seminar names, dates and attendance, not providers. The 58 seminars (1992–2026) load as Course Offerings under one Training Course, Continuing Education, and each attendance of a migrated person as a Training Course Participant with Entry Type Continuing Education (3,899 rows). Stop codes read only student hours: the sync, the six-month schedule and the hours trigger skip that entry type. Whether seminar providers become Organization accounts with CE Provider Approval accreditations is a client question.

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

Two thin custom objects. They were first scoped to the violation path only, and on 10 Nov 2026
widened to every fee LSBC receives (`DM-18a`).

| Object | Purpose |
|---|---|
| `Payment__c` | One receipt. Date, amount, method, check or transaction number, check date, payer name, unapplied balance |
| `PaymentAllocation__c` | The junction. Which payment, which `RegulatoryTrxnFeeItem`, how much, and `ForYear__c` |

This closes the violation loop inside Phase 1: a citation raises a $25 fee with a 15-day clock,
a partial or full payment is recorded against it, and the outstanding balance drives the print
hold at day 16.

> **The custom objects exist because of licensing, not because PSS lacks payment objects.** That
> distinction matters at handover and in any Phase 2 conversation.

> **Scope.** Recording staff-entered payments for all of LSBC's revenue is wider than the original
> violation exception. It is still not payment integration (no gateway and no card data), but it is
> real scope beyond what was first agreed. See `OPEN-53`.

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
instead, in batches by approval date (Print Requested Date), which LSBC confirmed on 17 Nov 2026.

---

## 2. Business rules — Week 6

BRE carries the decision logic; Flow carries orchestration. Rules are readable, and the
administrator can change a threshold without touching a flow.

> **Versions and history.** Decision matrices keep versions: a price change is a new version with a
> later start date, and the old one stays. Expression sets do too: a rule change is a new version,
> deployed on its own (metadata type `ExpressionSetDefinitionVersion`) with the next rank and active
> from the day it deploys, while the old version stays in the org and keeps running until then.
> Redeploying the whole expression set file, active version included, is what fails
> ("LatestVersionSnapshotId not found"); Salesforce says production must never have an active version
> edited in place (`OPEN-52`, settled 19 Nov 2026).

**As built (Phase 3).** Flows gather facts and write records; rules never query and never carry a
price. Thresholds are named constants inside each expression set, amounts and lookup tables are
decision matrices, and every rule was tested at its boundaries before any flow called it.

| Kind | Name | Covers |
|---|---|---|
| Decision matrix | `FeeSchedule` | Fee amounts and codes (`BR-07`) |
| Decision matrix | `ReciprocityStateExams` | The exams each state's licensees take, from the June 2024 state tables (`BR-19`, `DM-15`). Replaced `ReciprocityStateRule`, which is still deployed but read by nothing |
| Decision matrix | `ApplicationPathExams` | Exams and Board approval per reciprocity path (`BR-19`, `BR-23`) |
| Expression set | `StopCodePerson`, `StopCodeSchool`, `StopCodeEstablishment` | The fourteen derived stop codes (`BR-02`) |
| Expression set | `FeeLateCalculation`, `FeeDuplicateLicense`, `LicenseExpirationDate` | Late and restoration fees, duplicates, expiry (`BR-08`, `BR-18`, `DM-08a`) |
| Expression set | `EligibilityStudentRegistration`, `EligibilityExamination`, `EligibilityReciprocity`, `EligibilityPermit`, `EligibilityInstructorCE` | Section 2.3 and 2.4 eligibility |
| Flow | Subflow: Stop Code Sync, Subflow: Stop Code Print Check, Subflow: Fee Renewal Assessment | Orchestration the portal and staff tools call |
| Flow | Eight record-triggered flows, four nightly schedules | Keep stop codes current |
| Flow | Screen Flow: Account Add Stop Code, Screen Flow: Regulatory Transaction Fee Item Change Year | Staff actions Add Stop Code and Change Year |

The eligibility rules are called by the Phase 5 portal forms and the Phase 6 staff intake. Inputs
still awaiting a decision: state-table cells that are ambiguous or undated are client questions
(under `DM-15`), and the Regular and International reciprocity paths use the license type's exams
until their own requirements arrive.
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

> **When holds are re-checked.** Saving a licence, relationship, bond, exam attempt, application,
> fee, payment or hours entry, or deleting a licence, queues a re-check of the holder's automatic
> stop codes. It runs in the background a few seconds after the save, once per holder however many
> records the save touched, so a portal form that saves several records stays within platform
> limits. Nightly schedules re-check holders whose dates passed.

`BR-02` `[SETTLED]` **Thirteen codes are derivable by the rules engine.** Each is checked by eye
today.

| Code | Description | Derived from |
|---|---|---|
| 1 | NSF | A returned payment reversing a fee |
| 3 | No active bond | School bond end date |
| 4 | Student Hours Incomplete | Accrued hours against programme minimum |
| 5 | Expired Cos License | `PeriodEnd` on the licence |
| 6 | No current cos lic for boothrenter | A held operator licence: cosmetologist, esthetician or manicurist (prerequisite) |
| 7 | No current cos lic for instructor | A held cosmetology licence (prerequisite) |
| 8 | Exam not passed | Person Examination result |
| 9 | No Esthetician License for Instructor | A held esthetician licence (prerequisite) |
| 15 | Restoration Exam | Lapse beyond three years |
| 17 | Exam has not been taken | Absence of a Person Examination record |
| 20 | Needs re-registration | 180 days without hours received |
| 21 | Non Payment | Outstanding fee balance |
| 31 | Restoration Exam Not Passed | Person Examination result |

**When each derived code opens and ends** (settled in Phase 3 build):

| Code | Opens when | Ends when |
|---|---|---|
| 1 | A `Payment__c` on the holder is marked Returned | Staff end it after verifying the repayment. The repaid fees are covered by code 21 |
| 3 | A School has no Surety Bond `Accreditation` covering today | A covering bond is recorded |
| 4 | A student has an open New Licensure application and approved hours are below the completion threshold | Hours reach the threshold |
| 5 | The holder's Cosmetologist licence `PeriodEnd` is past (status not Revoked, Retired or Deceased) | `PeriodEnd` moves forward |
| 6 | A Booth Rental Permit holder, or a person with an active Booth Renter ACR, holds no current cosmetologist, esthetician or manicurist licence. Wider than CLOSE, which needs a cosmetology licence: LSBC confirmed any operator licence (12 Nov 2026) | A current licence exists |
| 7 | A Cosmetology Instructor licence holder holds no current Cosmetologist licence | A current licence exists |
| 8 | The latest attempt at an exam the licence type requires is a Fail | A Pass is recorded |
| 9 | An Esthetician Instructor licence holder holds no current Esthetician licence | A current licence exists |
| 15 | A licence `PeriodEnd` is more than three years past and the holder has no current licence of that type (status not Revoked, Retired, Deceased or Draft). An old lapsed record does not open it while the person holds a current licence of the same type (decided 16 Nov 2026) | The licence is restored |
| 17 | An open licensure application needs an exam with no attempt on record | An attempt is recorded |
| 20 | The Board last received hours for a student more than 180 days ago, by the hours entry's Received Date (LSBC confirmed 180 days from the last hours received, 12 Nov 2026; until then six calendar months from the end of the last hours period) | New hours arrive |
| 21 | A fee on the holder is Due or Partially Paid past its `DueDate` | It is Paid |
| 31 | The latest Restoration exam attempt is a Fail | A Pass is recorded |

Codes 7 and 9 follow CLOSE, which ties code 7 to the Cosmetology Instructor licence and code 9 to
the Esthetician Instructor licence. A Manicurist Instructor gets no automatic hold: CLOSE has no code
for it. (Built 11 Nov 2026; the first build applied both codes to every instructor.)

Code 16 (no manager on a shop) is set and ended by staff (12 Nov 2026). Managers are recorded only
when an inspector visits, so the automatic rule held 535 shops against CLOSE's 50, and LSBC confirmed
staff keep the designation by hand. A manager must also hold a current operator licence. CLOSE files
the Manager licence under the shop with no person named, so no hold can check it; the shop form checks
it instead: the manager's licence number must be a current cosmetologist, esthetician or manicurist
licence, or the application carries a note for staff.

> The prerequisite codes are the quiet win. A booth renter must hold a current operator licence and
> an instructor a current licence in their own discipline. As rules these fire the moment a
> prerequisite lapses.

`BR-03a` `[SETTLED]` **Certification of contractual fees is a notarised statutory form.** Signed by
the school owner or authorised personnel under Louisiana R.S. 37:508.B, certifying the student has
paid all contractual fees and is therefore eligible to be **scheduled for examination or
transferred**. It gates scheduling, not only transfer.

`BR-03` `[SETTLED]` **Sixteen codes stay manual.** They need the code list, a reason, and the
ability for staff to set and clear a hold — not automation.

| Code | Description | Note |
|---|---|---|
| 2 | Student Loan Default | Originates outside the Board; notification route unknown |
| 10 | Inspection Report not received | Inspections are Phase 2; code exists for history and manual use |
| 11 | Incomplete Transaction | Applied at the counter |
| 12 | Violation | Set from violation capture (in Phase 1) |
| 13 | Proof of Education | Awaiting evidence |
| 14 | Fraudulent License | Pending revocation |
| 16 | No Mgr License on Shop | Staff decide: managers are recorded only on inspection visits. Automatic until 12 Nov 2026 |
| 18 | Incorrect Address | Set on returned mail |
| 19 | No Termination Papers Received | School-related; student dropout |
| 22 | No social security card | Awaiting evidence |
| 24 | LIC OBTAINED BY FRAUD IN TX | Specific out-of-state finding |
| 27 | No Child Support | Originates outside the Board; notification route unknown |
| 28 | BOARD ORDER/Fee not paid | Follows a board decision |
| 29 | CAUGHT CHEATING DURING EXAM | Examination misconduct |
| 30 | Admin Violation | Administrative hearing pending |
| 32 | NSF Late Fees | The late fee on a returned payment is unpaid (added in CLOSE in October 2026) |

`BR-04` `[PROPOSED]` **Three codes are not holds.** 23 Licence Revoked, 25 Licensee Retired,
26 Licensee Deceased never clear and never receive an end date. They belong as `BusinessLicense.Status`
values. With code 32, CLOSE has thirty-two codes; without these three the alert list is twenty-nine,
which is what is built (ahead of confirmation).

`BR-05` `[SETTLED]` **Stop-code inputs are extensible to an inspection-violation source** so a
later phase needs no redesign.

`BR-06` `[OPEN]` CLOSE has **two stop-code buttons** — "Stop Codes" and "Stop Codes (revised)".
Two structures coexist. Which is authoritative affects both the rules design and any migration.
See `OPEN-15`.

### 2.2 Fees

`BR-07` `[SETTLED]` Fee codes are CLOSE codes (mostly two letters, six are three digits) and become
external IDs on Product. All 621 are loaded from the CLOSE extract, 563 active, with their revenue code.
Each licence type has its own renewal and late fee code: `AC` and `AH` for a cosmetologist, `AJ` and
`AO` manicurist, `AQ` and `AV` esthetician, `AX`/`BP`/`BG` and `BX` for the three instructors, `DB` and
`DF` booth renter, `DI` and `DL` salon, `EH` and `EI` manager, `FD` school renewal. `FH` is the school
late fee, charged as failure to timely renew. `PO` is not a renewal fee: it is the violation fine for a
school (`PP` operator, `PN` shop, `PS` instructor). `PB` overpayment, `BY` miscellaneous, `PE` list.

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
| Late penalty | Per licence type: `AH`, `AO`, `AV`, `BX`, `DF`, `DL`, `EI` | $35 per delinquent year on top of the standard $35, with late fees capped at **$465** (`BR-07`) |
| Duplicate licence | — | $25 every time, the first included; one per licence per renewal period, requested at any point in the period; paper request only, no digital copy |
| Affidavit | — | The first ever free; $15 for every licence after that, **per licence**, not per request. Two licences on a first request: one free, one $15 |
| School renewal | `FD` | $190 a year, due before January 31 |
| School late renewal | `FD` + `FH` | $380 doubled renewal (`FD`) plus $175 failure to timely renew (`FH`) — $555 total. `PO` is the school violation fine, not part of this |
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
the CLOSE fee code beside each; its rows are kept in
`data/decisionMatrices/FeeSchedule.csv`. A price change is a new matrix version with a later start
date. Version 4 (11 Nov 2026) prices initial licences, duplicates, affidavits and violations per licence type with CLOSE's codes and current amounts, the same way version 3 prices renewals: a flow looks up `<License type> Initial`, `<License type> Duplicate License` or `<License type> Affidavit` and falls back to the generic row when the type has none. A violation looks up `Violation Shop`, `Violation School`, `Violation Operator`, `Violation Instructor` (a practitioner cited at a school who holds an instructor licence) or `Violation Special Permit`. Each fee item links to its fee code Product. Temporary permits, threading facilities, no-shows and exam retakes keep one generic row: CLOSE has no per-type code for them. The rules never carry a price: `FeeLateCalculation` holds only the $465 cap and the 36-month
restoration limit. Placeholders and gaps:

| Item | State |
|---|---|
| Fee codes | All 621 CLOSE codes are loaded as Products (11 Nov 2026) and each fee item links to its code. `AC` is the cosmetologist renewal. Temporary permits, threading facilities, no-shows and retakes have no per-type code in CLOSE |
| Salon (business) renewal amount | $55, code `DI` (version 3) |
| Records list request | No amount (`OPEN-30`), so no row |
| Affidavit "first free, then $15 per licence" (`BR-26`) | The affidavit form counts the applicant's earlier affidavit requests: the first is free. LSBC confirmed (12 Nov 2026) the first ever is free and $15 is per licence. One request covers one licence and produces its own certification letter, as built. Built 12 Nov 2026: Earlier Affidavit In CLOSE (`Contact.HasCloseAffidavit__c`) marks the 2,853 migrated people whose CLOSE comments record an affidavit (CLOSE keeps no count), and the form treats it as the free one used; the applicant types Initially Licensed Name. CLOSE's $25 code 87 is discontinued |
| Duplicate licence once per renewal period (`BR-18`) | LSBC confirmed (12 Nov 2026) one duplicate per licence per renewal period, any time in the period, $25 every time. Built 12 Nov 2026: `FeeDuplicateLicense` allows a duplicate when the licence's Last Duplicate Date (`BusinessLicense.LastDuplicateDate__c`) falls before its current period (the twelve months before its expiration, or the next period when renewed on the same request), and always charges the Fee Schedule amount. Approving a duplicate in Decide sets the date; 2,507 licences carry their last CLOSE duplicate |
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

`BR-18` `[SETTLED]` Duplicate licences are limited to **one per licence per renewal period**, requested
at any point in the period (some licensees post their licence at several salons; the limit guards
against fraud). Every duplicate costs $25, the first included.

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
thereafter — and produces a certification of licensure. The first affidavit ever is free and each
further licence certified costs $15. Each licence is its own request with its own certification
letter, so a first-time applicant for two licences pays $15 in all. CLOSE records earlier affidavits,
including those from before CLOSE, only as a comment on the applicant ("Cert mailed to TX 01/01/23",
"Aff mailed" with a date and initials); any such comment means the free one is used. "Name you were initially licensed under" is any
name since school registration (a legal name change or maiden name), so the applicant types it. Three variants:

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
at an event. The paper form lists event types and asks for the event dates 30 days in advance, but
reciprocity says (12 and 16 Nov 2026) neither matters: the permit runs 30 days from issue whatever the
event. The portal form asks neither and has no advance-notice check.

- $50, with a copy of the current out-of-state licence
- Valid for **30 days from issue**, and renewable **once** before completion of testing. Approving
  it in Decide sets the expiration **33 days** after approval (Temporary Permit's Term Length): 30 days
  plus about 3 for the post, as reciprocity does by hand today. Staff can change it before mailing
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
| Documents | Each form's checklist is a document checklist template (an Action Plan template, Setup > Action Plan Templates) that the admin edits without a deploy; `Subflow: Document Checklist Generate` creates the items from the latest published version of the template whose Unique Name matches the application (record type with licence type, path or application type), and no Action Plan records are created, so applicants and desk staff need no Action Plans licence (only template editors do). Each item is filed under its document type's category. The `documentChecklistUpload` LWC shows the checklist as rows with one upload each (`PT-18`). Items the form says are mailed, or sent by another state or company, are Sent to the Board (the template puts them in the Sent to the Board category): the applicant submits without them and staff upload them. Upload Documents on My Applications takes later uploads. Every document a form asks for is a checklist item, the accommodation documentation included (16 Nov 2026) |
| Certification | Every form ends with the checkbox, typed name and timestamp (`PT-19`), showing the form's printed attestation |
| Payment | Fees come from the Fee Schedule; the pay step links to PayStar and takes the receipt as a checklist upload. Shop and facility fees are paid to the inspector as printed; when nothing is due the empty receipt item is removed. The portal books no inspection: inspectors set their own schedule (LSBC, 12 Nov 2026). Whether the $105 moves online, and whether PayStar takes e-checks, is with LSBC |
| Rules called | Reciprocity exams from the `ReciprocityStateExams` matrix and `EligibilityReciprocity` version 2; threading permits from `EligibilityPermit` (it also limits a temporary permit to one renewal, for staff); duplicate and renewal fees from the Phase 3 rules |
| Access | Guest profile LSBC LPI Profile, member profile LSBC Portal User, sharing set on the user's own records. Owners, Managers and School Administrators read their businesses through share records kept by `Subflow: Portal Business Access Sync` (`PT-02`) |

| Form (PDF) | Flow | Creates on Certify |
|---|---|---|
| License Renewal | `ScreenFlowIndividualApplicationRenewal` | One Renewal application per licence, a Duplicate application per duplicate, fees; a name change sets the Name Change Proof Pending hold |
| Reciprocity (Cosmetology, Esthetician, Manicurist, Instructor), Military, Foreign | `ScreenFlowIndividualApplicationReciprocity` | Reciprocity application with path, exams and answers; Person Language for the national exam; fees by path |
| Reciprocity Retake | `ScreenFlowIndividualApplicationRetake` | Retake application and a new Person Examination attempt (`BR-25`) |
| Temporary Permit | `ScreenFlowIndividualApplicationTemporaryPermit` | Reciprocity application, licence type Temporary Permit, with the out-of-state licence; no event questions |
| Threading | `ScreenFlowIndividualApplicationThreadingPermit` | New Licensure application, Threading Permit; holders of a licence are told they don't need one |
| Affidavit | `ScreenFlowIndividualApplicationAffidavit` | Affidavit application (Renewal record type); first free, then $15 |
| Shop | `ScreenFlowBusinessLicenseApplicationShop` | A new establishment for a new shop or a new location; the existing one for a reopening or new ownership (LSBC, 12 Nov 2026). Owner and Manager relations (the manager's number must be a current operator licence), New Establishment application, fees |
| Threading / AHD Facility | `ScreenFlowBusinessLicenseApplicationFacility` | The establishment with its tax ID, Owner relation, New Establishment application, fees |
| New School Check List | `ScreenFlowBusinessLicenseApplicationSchool` | The school with its capacity, School Administrator relation, New School application, $100 fee paid to the inspector at the premises inspection, with no online pay step; the $300 final inspection and $340 application fees are collected by the inspector at the final inspection, and staff add them then (LSBC, 12 Nov 2026); later items uploaded afterwards |

The 17 School Forms wait for the School Administrator audience (Phase 2).

**As updated 19 Nov 2026 (demo feedback, 18 Nov).** The portal takes an editorial look the Board asked
for (Vogue, Cosmopolitan, Architectural Digest): a centred masthead with the navy pelican logo, Playfair
Display headlines and Montserrat text, a black hero with the 2026 seal, round topic links, a promo strip,
story-style cards and a black footer, on the Board's pale cool blue-grey (`#D3DCE8`) with slate blue
(`#4A4D78`) icons and no gold. It is generated by `scripts/generators/portaltheme.py` from
`scripts/generators/portal/`; edits made in Experience Builder are copied back there. Two additions:

| Piece | How it works |
|---|---|
| Change My Address | Individual licensees only (person accounts). The form (`ScreenFlowCaseAddressChangeRequest`, `/change-address`, linked from My Applications) takes the new mailing address, a Proof of Address checklist upload and the certification, and opens a Case (Type Address Change, General Inquiries) holding the requested address. Staff check the proof and run Apply Address Change on the Case. Which other addresses portal users may change is with LSBC |
| Board Documents and Publications | Salesforce CMS: workspace LSBC Portal Content with the LPI site as channel; Board agendas, minutes and school publications are CMS Documents (PDFs) in the manual collection Board Documents and Publications, shown as a carousel on the home page. Documents, not News, because an Aura site's CMS detail page takes only Document or Image content. Guests can see published CMS content (the site's guest CMS access setting, 19 Nov 2026). Six marked samples stand in until LSBC sends real papers |

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

`PT-02` `[SETTLED]` Access to a business account that is not the user's own follows the person's Account
Contact Relation. The `OPEN-11` spike (19 Nov 2026) found that a sharing set can map a portal user to their
related accounts (`Contact.RelatedAccount`) without code, but can't filter by the relation's role: a Booth
Renter would see the salon, and an instructor a school's students. So `Subflow: Portal Business Access Sync`
keeps manual share records instead: the portal logins of a business's Owners, Managers and School
Administrators read the business, its licences, business applications, violations and fees, and lose that
access when the relation ends or its role changes. The relation, portal user, licence, business application,
violation and fee triggers tick `Account.PortalAccessSyncPending__c`, and `Record-Trigger: Account After Save`
runs the sync in the background, once per business per save, as it does the stop code sync. Students' records
are never shared to a school: the school forms read them in screens filtered by the school's relation.

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
a deposit line to attach to several registrations and settle independently. `DM-18a` has since
extended the ledger to every fee, but bulk allocation is still not built: Record Payment applies a
payment to one account's fees, and a school's cheque covers twenty students' accounts. It still
depends on the decision about cheques in `OPEN-02`.

### 3.3 Registration and identity

`PT-08` `[SETTLED]` **Applicants create an account before applying.** Removes the need for guest
users to create application records, is required for status tracking, and avoids exposing
system-context code to anonymous traffic on an org holding PII.

`PT-09` `[SETTLED]` **Registration is licence-number lookup with secondary matching.** A licensee
signs up by matching a licence they already hold.

| Step | Behaviour |
|---|---|
| Look up | The applicant enters their licence or certification number |
| Confirm | Secondary match questions on last or maiden name and ZIP, never the social security number |
| No match | The applicant is directed to contact the Board rather than allowed to create a record |

Extended in Phase 5: **someone new to the Board** (a reciprocity, permit or first-time applicant
with no licence number) signs up on a second path with name, date of birth and contact details. A
person account is created unless one with the same name and date of birth already exists. The
duplicate check queries on first and last name only and compares the date of birth after the query,
so it keeps working once the date of birth is encrypted with probabilistic encryption, which cannot be
filtered on (`SEC-04`). The date of birth lives in the custom field `Contact.DateOfBirth__c`
(`DateOfBirth__pc`), because Shield cannot encrypt the standard `Birthdate` (`OPEN-51`).

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

`PT-13` `[OPEN]` **What the public search holds at go-live depends on the production load.** The
CLOSE-backed search at lsbc.louisiana.gov stops working when CLOSE retires. The build team has
loaded CLOSE's current licences into the sandbox (section 7), so a production load would fill the
search. Two things stand in the way. Whether that load is in scope, and at what volume, is not agreed
(`OPEN-05`, `OPEN-53`). Migrated licences now carry their holder's number where CLOSE has one that
can be used (`OPEN-40`, below); search by name works for everyone.

`PT-14` `[SETTLED]` **Licence numbers belong to the person** (William, 18 Nov 2026). CLOSE gives each
person one number, `APPLICANTS.OLD_CERT_NBR_NUM`: the next value of a counter followed by the birth
month and day (MMDD), shared by every licence they hold. Salesforce keeps it on the person as
**Certification Number** (`Contact.CertificationNumber__c`, unique). Decide issues it on a person's
first licence: it creates a **Certification Number Counter** record, whose auto-number is the counter
(an auto-number can't hand the same value out twice), and adds the birth month and day; a person who
already has a number keeps it. Because `BusinessLicense.Identifier` is unique in the org, each licence's
License Number is the certification number, a dash and the licence type's code (`1846410407-C`, the
CLOSE code, held in the type's standard `RegulatoryAuthCode`). The printed licence shows the
certification number with an L in front (L1846410407), as CLOSE printed it so licensees know it is their
licence number. Sign-up, public search and the shop form's manager check match the number typed, with or
without the L, or any licence starting with it and a dash. Establishments have their own counter (William,
19 Nov 2026): a salon, threading facility or alternative hair design facility gets **Certification Number**
on the business account (`Account.CertificationNumber__c`) from the **Establishment Number Counter**, 77
followed by the counter, on its first licence; all its licences, the manager licence included, carry it
(`779947961-SH`). CLOSE's salon numbers (`SHOPS.OLD_SHOP_ID`) have two digits after the 77 that are not
part of the counter; new numbers start above the highest CLOSE number, so none collide (`OPEN-40`).
Schools are numbered by staff. Permits use the holder's number, as any person licence does.

### 3.4 Staff-facing

`PT-15` `[SETTLED]` **Staff need an internal path** to enter an application on an applicant's
behalf, record a deposit, and attach a scanned document to the right record. The mailroom
continues to receive payments, address changes, returns and paper forms after go-live.

As built (Phase 6): **New Application** on a Person Account opens any of the nine portal forms with
that person as the applicant (the forms take a `recordId` input; blank on the portal, where the
applicant is the signed-in user). The form saves the application, checklist and fees exactly as on
the portal. Staff tick the certification and type the name as the applicant signed the paper form.
At the pay step they see the fees and record the payment afterwards with **Record Payment**
(`DM-18a`). Shop, facility and school forms are entered on the owner's or director's person
account. **Upload Documents** on an application opens its checklist for scanned and mailed
documents, including those marked Sent to the Board, which the portal does not let applicants
upload. Deposits are recorded per payment; there is no deposit number (`DM-19` note).

Added 16 Nov 2026: **Completion and Initial License (school completion form)**, a staff-only form
under New Application (`Screen Flow: Individual Application New Licensure`). Staff copy the school's
1,500 hour completion form: licence sought, school, Date Enrolled, Date Completed and Total Completed
Hours (`EnrolledDate__c`, `CompletedDate__c`, `TotalCompletedHours__c` on the application). A
second screen sets the certified hours beside the hours on the Training tab and the licence type's
completion hours and flags any gap. The Cumulative Hours Report is a required checklist item, the
school representative's name goes on the certification step, and certifying creates a New Licensure
application (path Regular, linked to the school's course offering) with the licence type's Initial
fee. The Student License (L) number is not stored until student registration is built (client
question). Staff entries on every form end with a staff message, and a school's fee is recorded with
Record Payment on the school.

`PT-16` `[SETTLED]` **A standardised letter template with fillable fields** for dates and amounts.
The current character limit produces letters the Executive Director has called unprofessional.
Named sponsor on the renewal desk.

As built (Phase 6): **Generate Letter** on an Account, Individual Application or Business License
Application lets staff pick a letter and type any details, then saves a PDF on LSBC letterhead in
the record's Files. The wording lives in Letter Template custom metadata, which an admin edits in
Setup without a deployment: a heading, a body with merge fields (`{{Name}}`, `{{Date}}`,
`{{ApplicationNumber}}`, `{{MissingItems}}`, `{{BalanceDue}}`, `{{Details}}`) and the objects it
applies to. There is no character limit. A Visualforce page renders the PDF because the org has no
internal Document Generation runtime; its Apex only lays the letter out. Four starter letters (return,
balance due, returned payment, affidavit certification) carry placeholder wording, and the
letterhead's address, phone and website are placeholders, both until LSBC supplies them.

`PT-17` `[SETTLED]` **Name change at renewal sets a stop code** requiring proof before printing —
deliberately, so the licensee is not charged a $25 duplicate fee later. Preserve as designed.

As built (Phase 6): **End Stop Code** on the stop code shows the new name the licensee reported (read
from the stop code's description) as first and last name. Staff check it against the proof, and the
person's name is changed as the stop code ends. Any other stop code is simply ended; the screen warns
that one the system set comes back at the next check unless its cause is fixed.

**Review and decide (Phase 6).** **Decide** on an Individual Application or Business License
Application shows what stands in the way: required documents not yet accepted, fees not fully paid,
and the holder's active stop codes. Staff then approve, return or refuse:

- **Approve** is allowed only when the application is certified (a staff entry counts as
  certified), every required document is accepted and the fees are paid. For a renewal entered
  before its fee moved to the application, unpaid fees on the licence also count.
  A new application creates the licence with the number staff enter (numbering is a client
  question). A renewal moves the licence's expiration on from its current date, or from today if it
  has passed, and adds one to Renewal Count. The expiration comes from `LicenseExpirationDate`; a
  licence that expires on the holder's birthday needs a date of birth first. Approval marks the
  licence ready to print (Print Requested Date, clearing any Printed Date), sets an Expired licence
  back to Active, and marks the application Approved with its Approved Date. Eligibility rules are
  not run again: the portal forms run them before an applicant can submit.
- **Return** records the return reason and the note (Decision Reason), ticks Was Returned, and can
  create the return letter at once.
- **Refuse** sets an individual application to Denied. Business License Application Status has no
  Denied value, so a refused business application is Canceled, with the reason saved. Either way
  the application's Due and Partially Paid fees are canceled (17 Nov 2026).

Licences and applications are never deleted by staff: a licence entered in error is set to Revoked,
an application is closed with Decide (Jonathan, 16 Nov 2026).

**Print queue (Phase 6).** Approval, renewal and a duplicate set the licence's Print Requested Date.
The **Licenses Ready to Print** list view shows every licence with Ready to Print ticked (requested
and not printed since; a formula, because a list view cannot compare two dates). Staff print, tick
the licences and click **Mark Printed**: each holder is checked with `SubflowStopCodePrintCheck`, a
licence whose holder has an active stop code is skipped and stays in the list, and the rest get
today's Printed Date. The **Licenses Ready to Print** report groups the queue by Print Requested Date
(the approval day, oldest first), then licence type, so staff print one day's batch at a time.
**Print Licenses** on the list view opens the ticked licences as a PDF laid out on LSBC's three-part
stock (form LBC-19, 8.5 x 11 in: a wall certificate, the renewal stub, and a second wall certificate),
one sheet per licence (`LicensePdf`, `LicensePdfController`). The stub's 3.5 x 2 in wallet card is left
blank (William, 18 Nov 2026); Erin is proposing to the Board that a wallet card be sold as a $25 duplicate. It leaves
out licences not waiting to print and holders with an active stop code, the same check as Mark Printed,
and marks nothing printed. Positions were measured from LSBC's scan of a blank sheet; they are checked on
blank stock LSBC is mailing, and the page takes `dx` and `dy` (inches) to nudge a printer's offset. The
governor's name is the custom label License Governor Name.

### 3.5 Where components are used

`PT-18` `[SETTLED]` Flow carries the forms. LWCs only where Flow cannot do the job:

- Photo capture and crop, for the printed licence and field verification
- Document checklist upload, where an applicant attaches several documents on a phone with
  per-item status
- The licence type picker, if the combined list across both type objects needs search or grouping
- Public search results, only if the standard data table proves unusable in guest context

Every document a form asks for is a checklist item uploaded through the `documentChecklistUpload`
component; no form attaches files any other way (16 Nov 2026). The accommodation documentation
became one: a required Documentation for Disability Related Needs item (document type
`DisabilityDocumentation`, category Exam Accommodations) on the form's draft, added by
`Subflow: Accommodation Request` when an accommodation is requested. It moves to the application at
Certify with the other documents, staff accept or return it, and Decide waits for it. Applicants
must upload it; staff entering a paper application can leave it for later.

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
| Reference data | Louisiana State Board of Cosmetology authority; from CLOSE, 123 `RegulatoryCode` citations with their rule text and 38 `ViolationType` records in CLOSE's four categories (Unlicensed Operator, Salon, School, Administrative Rules), plus Other | The chief inspector confirms which are current and sets severity (loaded as Minor) |
| Flow | Record-Trigger: Regulatory Code Violation After Save | On create: the `Violation` fee from `FeeSchedule`, billed to the cited party, due 15 days after the violation date; sets Compliance Due Date. Stops the save if the fee is missing from the schedule |
| Flow | Subflow: Fee Amount Paid Sync; Record-Trigger: Payment Allocation After Save and Before Delete; Record-Trigger: Payment After Save (extended) | Totals allocations into Amount Paid and sets the fee Due, Partially Paid or Paid. Returned payments do not count |
| Hold | Existing code 21 (Non Payment) | Opens when the violation fee passes its due date unpaid, ends when it is paid. Code 12 stays a manual hold |
| Actions | New Violation on Case, business Account and Person Account; Record Complaint on Case | Staff capture; the Account actions pre-fill the party and Cited Party |
| Flow | Screen Flow: Case Record Complaint | Creates the `PublicComplaint`, the `ComplaintCase` link and participants, sets Case Type Complaint and moves the Case to Complaint Intake. Since 16 Nov 2026 it defaults the complaint type and incident date from the Case (the public complaint form stores them in `Case.ComplaintType__c` and `Case.IncidentDate__c`) and sets the Case's Account to the establishment complained about, else the practitioner; New Violation from that Case pre-fills the party from the Account |
| Case setup | Queues Complaint Intake and General Inquiries; assignment rule `CaseRouting`; auto-response rule `CaseAcknowledgement` with two templates; Email-to-Case | Intake and routing (`CM-01`) |

**Address changes (19 Nov 2026).** A portal Change My Address request is a Case with Type Address
Change and the requested address in `RequestedStreet__c`, `RequestedCity__c`, `RequestedState__c`,
`RequestedPostalCode__c`, `RequestedCountry__c`, plus a Proof of Address checklist item. Screen Flow: Case
Apply Address Change (the Apply Address Change action; People Maintenance desks and admins) shows current
and requested addresses, requires staff to confirm they checked the proof, updates the person's mailing
address, stamps `AddressChangeAppliedDate__c` and closes the Case. Account field history records who made
the change. Person accounts only: salons, schools and manager licences are out of scope (Board, 18 Nov 2026).

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
holding licences from printing. The sandbox load brought CLOSE's open staff-set holds across as stop
codes (1,555 of them), so these holds exist in Salesforce if the production load repeats it. They
reach production only if that load goes ahead (`OPEN-05`). The cases themselves are not migrated. See
`OPEN-03`.

---

## 5. Security, cutover and training — Weeks 11 to 12

### 5.1 Security model

**Build status: built 19 Nov 2026; `OPEN-11` access built the same day, the school forms follow.** The Board went through the access matrix desk by
desk on 18 Nov 2026 (`SEC-01c`) and agreed its Sharing Settings. For the rest, Erin Marceaux asked the build team
to go with its recommendations, which follow that tab. `scripts/generators/security.py` builds everything from
the workbook: 18 permission sets, a permission set group per desk with a muting set that caps it at its Sharing
Settings column, and 142 sharing rules. The staff action flows (Decide, Record Payment, Refund, Generate Letter,
Add and End Stop Code, Mark Printed, New Application, Record Complaint, Change Year) run in system context
**with sharing**: the user acts only on records shared with them, and the flow makes the writes a desk's own
permissions wouldn't (a licence created by Decide at Front Desk). Each runs only for the desks whose permission
sets grant it. The refund verifier rule and the confidential complainant rule followed the same day. Staff licences (Public Sector Access and
Document Checklist for every staff user and the Default Workflow User) and real desk users move to Phase 7, in
January 2027 (Jonathan, 19 Nov 2026); until then the desks are tested by moving one test user through them.
What the later phases left for security is now decided:

| Area | Decision |
|---|---|
| Staff tools | Every staff desk sees the LSBC Licensing app, its record pages and Home. Each action goes to the desks that can edit what it changes: Record Payment to the Payment-edit desks; Refund to the refund desks; Decide and Generate Letter to the application-edit desks; End Stop Code and Add Stop Code to the Hold-edit desks; Print Licenses and Mark Printed to the License-edit desks; New Application and Upload Documents to the application desks. Decide also needs read and create on Certification Number Counter; printing needs the license page and class, letters the letter page and classes. Letter Templates are admin-only |
| Rules | Run Flow and the core Public Sector licence, which includes rule runtime (confirmed by the Account Executive on 19 Nov 2026), for every staff user and for the Default Workflow User that scheduled flows run as, which in production must be an LSBC user. Production checks it on the running user even in system context; sandboxes don't. `BRECmtyRuntime` for portal users. System-context rule flows are accepted: they read reference data and write only what the screen submits. The Business Rules Engine Designer seat goes to LSBC's named admin at handover |
| Stop codes and violations | The Hold-edit desks (Compliance Officer, Front Desk Supervisor, Front Desk, Problem Desk, Program Manager) add and end manual stop codes. Inspector, Compliance Officer and Program Manager create violations; the Complaint-edit desks run Record Complaint. Amount Paid stays read-only (set by flow) |
| Complaints | `PublicComplaint` is Private. A confidential complainant is seen only by Compliance Officer and the roles above it (Executive Director), plus Program Manager, who edits complaints; the licensee and the portal never see the reporter. Queue members are desk groups, not named people: Complaint Intake gets the Complaint-edit desks, General Inquiries gets Front Desk Supervisor, Front Desk and Problem Desk |
| Portal | Owners, Managers and School Administrators reach their businesses through their Account Contact Relations, as share records kept by a flow (`PT-02`). Staff reach establishments the portal creates through the Account sharing rules, whoever owns them. An account can't be owned by a queue, so on approval Decide passes a portal-created business to the staff member approving it; the applicant keeps access through their relation |
| Notes and activities | No one edits or deletes a note or activity they didn't write (Erin Marceaux, 18 Nov 2026). Notes open view-only to everyone but their author because the file setting "Set by record" stays off. Tasks and events: only the creator may change the subject or comments (validation rule `SubjectDescriptionEditOnlyByCreator`) or delete them (`Record-Trigger: Task Before Delete`, `Event Before Delete`); whoever a task is assigned to can still close it. Administrators included |
| Admin and portal content | William is LSBC's long-term admin: the Business Rules Engine Designer seat and Letter Templates. Only admins publish Board documents on the portal |
| Field history (`SEC-05`) | `RecordAlert` Valid Until and Active, violation Status, `PublicComplaint` reporter confidentiality, and the fee item's year if the object supports it |
| Reports | LSBC Finance: Executive Director, Finance and Program Manager. LSBC Operations: all staff. The dashboard runs as the viewer, so Home shows report charts rather than a link |
| Refunds | The verifier must be a different person from the requester, enforced by a validation rule. The refund desks verify: Finance, Front Desk Supervisor and Front Desk |
| Accommodation documents | Checklist items in the Exam Accommodations category are open only to the desks that see Accommodation: Reciprocity Desk, Testing Desk and Program Manager |

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

`SEC-01c` `[SETTLED]` **The access matrix is kept in
[LSBC Access Matrix.xlsx](<LSBC Access Matrix.xlsx>)**, not in this document. It is the working copy
the Board reviews and the source the permission sets, groups and sharing rules are built from. The
Board agreed its Sharing Settings tab on 18 Nov 2026; the other tabs follow from it. In outline:

| Layer | Shape |
|---|---|
| Profile | One profile, `LSBC Standard User`, cloned from Minimum Access. It grants nothing |
| Role | One per desk (section 6), for record visibility up the hierarchy. Program Manager sits over Reciprocity Desk, Student Registration, Testing Desk and Inspection Supervisor (Erin Marceaux, 18 Nov 2026); the other desks report to Executive Director. `SystemAdministrator` for admins and IT, who also own portal accounts |
| Permission sets | Small building blocks (`LicensingRead`, `PaymentEntry`, `AccommodationAccess`, …). Any that touch a Public Sector object is cloned from `PublicSectorAccessPSL`, so it carries the Public Sector Access licence |
| Permission set groups | One per desk, combining building blocks, with a muting permission set that removes whatever the desk's Sharing Settings column doesn't give it. A person covering two desks gets two groups |
| Sharing | Private by default; License Type, Training Course and Course Offering are Public Read Only. Sharing rules open records outward to a public group per desk, or to AllStaff for reading. Account rules are split by record type, because one Account permission covers all four |

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
| `Contact.DateOfBirth__c` (`DateOfBirth__pc` on the Person Account) | Probabilistic. Custom Date fields take only probabilistic; the standard `Birthdate` can't be encrypted, so it is left empty (`OPEN-51`) | Identity; the L number already encodes part of it. Never filtered on: sign-up compares it after a name query (`PT-09`) |

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

Built 19 Nov 2026: history is on for every object staff use that supports it, up to Salesforce's 20
fields each (`scripts/generators/history.py`), and each record page's History tab shows it. The social
security number and date of birth are never tracked. Three person fields (Home Parish, Certification
Number, Maiden Name) are ticked by hand in Account Set History Tracking, since metadata can't set person
field history.

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
reciprocity desks and the Program Manager, who covers testing (Board, 18 Nov 2026), with encryption at rest and Field Audit Trail behind it from Shield enablement.
These fields belong on the Week 6 encrypted field list.

As built (16 Nov 2026): the request is one `PersonDisability` per form, updated when the applicant
comes back to the step and removed with its documentation if the answer becomes No. The supporting
documentation is not a file on the Person Disability: it is a checklist item on the application in
the Exam Accommodations category (`PT-18`). Only the desks that see Accommodation (Reciprocity Desk,
Testing Desk, Program Manager) may open items in that category (Phase 2, 19 Nov 2026).

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

As built (Phase 6): one training guide per desk, written step by step on the LSBC Licensing app's
screens: [Mailroom and Front Desk](https://claude.ai/artifact/NwTZF552EehJzUo4AgeaEQ),
[Renewal Desk](https://claude.ai/artifact/Je9toe5RXaKKY132MGs2R1),
[Reciprocity and Testing](https://claude.ai/artifact/QR3YD7EVusSLPCQXJy4vvL),
[Problem Desk](https://claude.ai/artifact/5XDCeaK9KrJhNhwx9SCtek) and
[Complaints](https://claude.ai/artifact/SqDtAjsJFBtEqUxCKEwSZw). The administrator material is the
LSBC Salesforce Admin Guide. For the January 27 staff go-live with the portal unpublished, staff
enter paper applications with New Application and record mailed payments with Record Payment
(`PT-15`). Data load templates and a separate cutover runbook were left out of Phase 6 by
decision; the Deployment Manifest is the deployment runbook.

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
- A student with no hours for 180 days must re-enrol.
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
| Data migration from CLOSE | Listed as out of scope, but the build team has loaded CLOSE data into the sandbox (below). Whether that work and a production load are covered by the SOW, and at what volume, is not agreed: see `OPEN-05`, `OPEN-53` |
| Paper and microfilm digitisation | Raised in session as in scope; excluded by the SOW |
| Inspections and enforcement | Beyond violation capture. Phase 1 prepares the ground only |
| Payment integration | PayStar and Elavon. Phase 1 links out and records the receipt. Integration only under a signed change order |
| Knowledge base and public AI | Roadmap |
| Employee and civil service data | Explicitly excluded |
| lsbc.louisiana.gov replacement | Extent of any content move still being agreed |

**First CLOSE load (sandbox, 10 Nov 2026).** LSBC supplied CLOSE data and a first load went into
LSBC-Partial: 31,166 people with a current licence, 7,385 salons, 58 schools and 38,978 licences (one
per holder and licence type, renewals rolled into Renewal Count). Records match on abstracted keys in
`LegacyKey__c` on Account, `BusinessLicense` and `Accreditation`, never on the SSN, which was not
loaded. It raised four gaps:

- **Licence number.** Settled 19 Nov 2026 (`PT-14`): `build_certification_numbers.py` loads each
  person's CLOSE number as their Certification Number where it ends in their birth month and day
  (21,191 people) and sets their licences' License Number to it plus the type code (18,371 licences).
  The nine-digit numbers are generated numbers, not social security numbers (William, 19 Nov 2026): the
  de-identified copy masked them, so `extract_certification_numbers.py` read them from the raw export once,
  keeping only those that end in the birth month and day and match no applicant ID, SSN or tax ID. With
  them, 35,451 people are numbered. 7,385 salons and facilities are loaded with their CLOSE salon number
  (`SHOPS.OLD_SHOP_ID`), and 39,963 licences carry their holder's number.
- **Instructor types.** CLOSE has three; the build has one, which codes 7 and 9 treat as needing both a
  cosmetologist and an esthetician licence. About 600 instructors were held on load.
- **Booth renters.** Code 6 needs a cosmetologist licence; `DM-03` says any operator licence. Settled
  12 Nov 2026: any operator licence, which ended 69 of the 158 code 6 holds.
- **Licence types not built:** Manager (1,194 current), Make-up (38), Microdermabrasion (24). Duplicate
  licences (267) are reprints, not a licence type. Make-up is renewal only: no new permits are issued
  (LSBC, 12 Nov 2026), and no form offers one.

Loading licences opened 6,889 stop codes, mostly code 16 (no licensed manager), because owner and
manager relationships load next.

**Second round (11 Nov 2026).** Owner, manager and booth renter relationships (11,347), 477 school
bonds and 1,555 staff-set stop codes followed, cutting code 16 to 767. Later on 11 Nov a shop's own
current Manager licence began to clear code 16 too (`BR-22a`), which brought it to about 530. The build then took over the
load. A de-identified copy of the CLOSE extract replaces every SSN-shaped applicant ID and
certificate number with a made-up number starting 000, so nothing after that reads a real SSN before
Shield. The 10 Nov load was made before that copy existed. The sandbox carries those numbers in a sandbox-only Mock Social Security Number field that is
never deployed. Two of the gaps above are closed in the build: three instructor licence types, Manager,
Microdermabrasion and Make-up Application, every CLOSE fee code, and renewals and late fees priced per
licence type in `FeeSchedule` version 3. Version 4 adds initial, duplicate, affidavit and violation fees per licence type or cited party, and the continuing-education seminars load as course offerings and attendances (see `DM-16`).
Licence numbers are loaded for people and establishments (`PT-14`); the booth renter base licence (`OPEN-50`) was settled on 12 Nov 2026.

**What is loaded (sandbox, 11 Nov 2026).**

| Data | Count |
|---|---|
| People (licensees, owners and managers, enrolled students, applicants) | 35,678 |
| Salons and schools | 7,385 and 58 |
| Licences, all current at load | 40,234 |
| Owner, manager, assistant manager and booth renter relationships | 11,347 |
| School surety bonds | 477 |
| Exam attempts | 98,539 |
| Fees still owed, with no due date | 13,212 ($487,682.05, matching CLOSE) |
| Payments since 11 Nov 2023, with 173,806 allocations | 120,554 |
| Students: course offerings and monthly hours rows | 111 and 32,801 |
| Reciprocity applications in progress | 27 |
| Continuing-education seminars and attendances | 58 and 3,899 |
| Fee codes | 621 |
| Open stop codes after the automatic rules ran | 2,602 |

Some loaded data raised holds CLOSE does not have: code 16 (no manager) and code 20 (no hours for six
months) (`OPEN-55`). Code 16 is now set by staff: the 535 automatic holds were ended on 12 Nov 2026 and
CLOSE's open code 16 holds loaded, 3 of its 50 (the other 47 are on shops not migrated). Code 20 stays
automatic: LSBC confirmed a student with no activity for 180 days must re-enroll. The reverse also happens: the old unpaid balances have no due date, so they raise
no Non Payment hold where CLOSE has one (`OPEN-56`).

**Real data in a sandbox without security.** Real names, addresses, dates of birth, licences, exams,
fees and payments have been in LSBC-Partial since 10 Nov 2026. Social security numbers were never
loaded. The security model is not built (5.1) and Shield arrives in January. On 12 Nov the sandbox had
five active internal users, all System Administrators. Who may log in, and that the project's rule
keeping offshore resources away from agency data holds, need confirming (`OPEN-54`).

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
| `OPEN-05` | The migration volume | Licence records are in scope up to an agreed volume. The figure has not been set. The sandbox now holds 40,234 licences and much more besides (section 7) | Immediate |
| `OPEN-06` | Extent of the website content move | Agendas, minutes, directories, the rules book and FAQs all go past what has been confirmed | Immediate |
| `OPEN-11` | Sharing across Account Contact Relation | Settled 19 Nov 2026: a sharing set can't filter by role, so a flow keeps share records (`PT-02`) | Closed |
| `OPEN-13` | Race and sex on the applicant record | A protected category. Still collected? Migrating? What access model? | Erin |
| `OPEN-15` | Two stop-code files | Partial files received. A regular and a revised version exist — which is authoritative? | William |
| `OPEN-19` | Sealed certifications | Whether a scanned certification is acceptable, or the sealed original must be kept | Stephanie |
| `OPEN-20` | Renewal reminders | Half of renewals arrive late and late fees are income. A policy decision for the Board | Before backlog lock |
| `OPEN-21` | Remaining retention periods | Deposits three years. Cheques are given as one year here but about three years in section 6.1 — confirm which. Other document types sit with compliance | Compliance |
| `OPEN-22` | Knowledge base in or out | Half of all calls are students asking about scores — the largest single deflection target | Before backlog lock |
| `OPEN-24` | Enforcing registration on enrolment | Aligned in session. Enforcing it is a process change for schools, not only a validation rule | Before Week 7 |
| `OPEN-26` | The no-show fee | A $25 fee exists in policy but is not systematically enforced. Should the platform apply it? | Deborah |
| `OPEN-28` | Automatic cleanup orders | Recorded in distributed notes as agreed. It is inspections functionality and out of scope | Immediate |
| `OPEN-29` | The $55 renewal amount | The mailroom sorts renewal payments by amount. Nobody has explained $55 | Kiwan |
| `OPEN-30` | The records list request | A paid request for lists, fulfilled by IT. A product with a fee that appears nowhere in the design | Kiwan |
| `OPEN-31` | The staff wish list | Submitted previously and not located. May carry expectations not captured anywhere | The group |
| `OPEN-33` | The card service charge | Applies to card payments, raising a $525 restoration to roughly $540. All card payments, or only at the counter? | Carnita or the front desk |
| `OPEN-40` | The rest of the licence numbers | Settled 19 Nov 2026 with `PT-14` except one point: people's and establishments' CLOSE numbers are loaded, the nine-digit ones included (generated, not SSNs, William). Still asked of William: what the two digits after 77 in CLOSE's salon numbers are (new numbers use a plain counter above the highest CLOSE number), and the last values of both CLOSE counters at cutover | Before the production load |
| `OPEN-41` | Numbering new licences | Settled with `PT-14`: Decide numbers a person's licences from the Certification Number Counter and a salon's or facility's from the Establishment Number Counter; staff type a school's number |
| `OPEN-43` | Refunding money already applied to a fee | Refund covers only money not applied to a fee. Staff would take money off a fee by hand first, with no record of why (`DM-18b`) | Staff go-live |
| `OPEN-44` | Notarised forms and the certification step | Will the Board accept the portal's certification (checkbox, typed name, time) in place of notarisation, for example the contractual fees certificate (`BR-03a`, `PT-19`)? | Portal publish |
| `OPEN-45` | LSBC mailboxes and sending addresses | Email-to-Case needs LSBC's complaint and inquiry mailboxes forwarded by OTS, and acknowledgements and portal emails need a verified LSBC sender, with DKIM and SPF (`CM-01`, `PT-09b`) | Staff go-live |
| `OPEN-46` | Letter wording and letterhead | The four letters use placeholder wording and a placeholder letterhead (`PT-16`) | Staff go-live |
| `OPEN-47` | Counting affidavits | Answered 12 Nov 2026: the first affidavit ever is free, $15 per licence after that, and CLOSE comments mark earlier ones. Code 87 is discontinued (`BR-26`, `BR-07`) | Closed |
| `OPEN-48` | The printed licence layout | Built from LSBC's scan (17 Nov 2026); alignment is confirmed only by printing on blank stock, which LSBC is mailing (`PT-16`) | Staff go-live |
| `OPEN-57` | Rule-call allowance and portal seats | The org allows 2,500 rule calls a month; about 2,600 licence expiries a month each run the hold check, and renewals add roughly 10,000 to 16,000. Portal users each hold two per-user licences with 100 seats against about 40,000 licensees. Decided 19 Nov 2026: the portal stays as built and LSBC trues up logins at renewal; moving rules out of the rules engine is on hold. Still to confirm before the portal is published: the per-user licences block sign-up at the 100th user (not billed later), and whether going over the call limit stops rules or is billed | Account Executive, before the portal is published |
| `OPEN-53` | Scope: migration and the payment ledger | Migration is listed out of scope, but the build team has loaded CLOSE data (section 7). That load is more than licence records: it includes three years of finance history, 120,554 payments with 173,806 allocations, in the custom ledger. The ledger itself grew from violations to every fee (`DM-18a`). Both need a change order or an agreed reading of the SOW | Project manager, before this document goes to LSBC |
| `OPEN-54` | Real data in the sandbox | Real CLOSE data has been in LSBC-Partial since 10 Nov with security unbuilt and Shield in January. Confirm who may log in, and that offshore resources have no access to agency data | Project manager, immediate |
| `OPEN-56` | Unpaid CLOSE balances and printing | Non Payment needs a due date, and the 13,212 migrated balances ($487,682) have none, so they hold nothing at go-live. CLOSE has 63 Non Payment holds open; Salesforce has 2, so licences CLOSE holds for non-payment will print. A policy choice for LSBC and finance, not a data fix: which balances, if any, should hold printing, and from what due date (`DM-18`, `BR-02`) | Staff go-live |

### Settled

| # | Item | Where it landed |
|---|---|---|
| `OPEN-01` | Cutover shape | Phased. Staff in January. The portal is built on the original schedule but published in March or April after renewal season closes |
| `OPEN-04` | Temporary permits | A $50 event permit for an out-of-state licensee, valid 30 days, renewable once before testing |
| `OPEN-52` | History of rule changes | A rule change is a new expression set version, deployed on its own with the next rank; the old version stays, so LSBC's administrator sees the history in Expression Set Builder (Salesforce Support and a sandbox test, 19 Nov 2026) |
| `OPEN-51` | Encrypting the date of birth | Salesforce confirmed on 19 Nov 2026 that Shield can't encrypt the standard `Birthdate`. The date of birth moved to the custom `Contact.DateOfBirth__c`, encrypted probabilistically; the standard field is emptied and off the layouts |
| `OPEN-08` | OTS security posture | Shield is in Phase 1, so the posture the Board expected is the posture delivered |
| `OPEN-10` | Inspector headcount | Nine inspectors and one vacancy, connected iPads, no offline requirement. The native inspections framework is already provisioned |
| `OPEN-12` | The encryption commitment | Accurate, since Shield is in Phase 1 |
| `OPEN-16` | Late fees | $465 cap on late fees. A full restoration totals $525, or roughly $540 paid by card |
| `OPEN-17` | Ability to Benefit | No longer accepted and has not been for over a decade. Not a path we build |
| `OPEN-18` | Place of business and facility grading | Both to a later phase. The Board is taking each to counsel for the spring legislative package |
| `OPEN-23` | Master instructor history | Existing master instructors accepted as they stand at go-live; tracking starts fresh |
| `OPEN-07` | The paper and microfilm archive | The archive is sized: millions of records, billions of pages, hundreds of filing cabinets, 104 years. Enough to brief vendors |
| `OPEN-09` | Identity matching at registration | Registration is licence-number lookup with secondary matching on name and address. The social security number may be stored encrypted but is never a lookup key. Extended in Phase 5 with a second path for people new to the Board (`PT-09`) |
| `OPEN-34` | Who sees what | Private by default. Users are segmented into named groups and access is granted outward, not restricted inward |
| `OPEN-35` | One platform, or several | One platform. The org is dedicated to the Board, not shared with other Louisiana boards |
| `OPEN-36` | Portal sign-up | Settled with `OPEN-09` — licence number, then name and ZIP; people new to the Board sign up with name, date of birth and contact details |
| `OPEN-27` | Operator licence renewal cycle | Annual, by legislative requirement. A three-year lapse triggers a restoration examination |
| `OPEN-32` | `ApplicationForm` as primary or secondary | Secondary. It is grant-and-benefit shaped — Lead, Opportunity, Budget and Program lookups, a scoring model, no licence type or licence link. The two application objects stay primary |
| `OPEN-37` | Holds attach to the holder, not the licence | Accepted. One `RecordAlert` per person or establishment, checked by the print routine. To be shown to the Board for feedback; a change would mean a custom lookup from `RecordAlert` to `BusinessLicense` |
| `OPEN-03` | Open stop codes at go-live | Answered by the load: CLOSE's open staff-set holds, the live administrative holds among them, came across as stop codes in the sandbox (1,555). They reach production with the production load (`OPEN-05`) |
| `OPEN-14` | The Seminar module | It holds seminar names, dates and attendance, not providers. The 58 seminars and 3,899 attendances are loaded as continuing education (`DM-16`). Providers are `OPEN-49` |
| `OPEN-50` | Booth renter base licence | Any current operator licence: cosmetologist, esthetician or manicurist (LSBC, 12 Nov 2026). Code 6 follows it (`BR-02`, `DM-03`) |
| `OPEN-25` | Which exam forms consolidate | One exam application with an exam type choice (Deborah, 12 Nov 2026). Built with the school portal |
| `OPEN-49` | Seminar providers | Milady, Pivot Point and Rocketcert (Deborah, 12 Nov 2026), created as Organization accounts, each with a 2026 CE Provider Approval (1 Jan to 31 Dec). The Board approves providers each year; staff add each year's approval (`DM-16`) |
| `OPEN-55` | Holds raised by migrated data | Code 16 is set by staff (`BR-03`); code 20 stays automatic at 180 days (`BR-11`). Both confirmed by LSBC, 12 Nov 2026 |
| `OPEN-42` | Instructor status N and X | N is Master-Inactive, X is not applicable (William, 12 Nov 2026). Masters load with Active or Inactive and Master Instructor ticked; X stays blank. Status does not change the fees (`BR-07`) |
| `OPEN-39` | Complaint intake | `PublicComplaint` carries the complaint, `Case` carries the work, `ComplaintCase` joins them. It beats `Case` with record types on anonymity, categorisation, intake channel and board reporting |

**The shape of what remains.** Thirty-one open. The LSBC Client Questions document tracks over a
hundred smaller configuration questions; those that change scope, go-live or the data are listed here.

**Two are for the project manager before this document goes to LSBC:** `OPEN-53`, migration and the
payment ledger as scope, and `OPEN-54`, real data in a sandbox without security. `OPEN-05`, the
migration volume, goes with them.

`OPEN-11`, the sharing spike against Account Contact Relation, was settled on 19 Nov 2026 (`PT-02`).

**Two are with the Board and have dates:** `OPEN-02`, cheques and money orders, at the December
board meeting; and `OPEN-38`, freelance operators without a fixed salon, which needs board rules or
legislation.

**Several decide the production load and what the public sees:** `OPEN-56` unpaid CLOSE balances that hold nothing, and `OPEN-06` website scope.

**Several are needed for staff go-live on January 27:** `OPEN-43`, and `OPEN-45` to `OPEN-48`.

**The rest are configuration detail**, each with a named owner who has already been asked.

---

## 9. Source materials

Everything in this document traces to a document, a screen or a session. When building a flow,
a rule or a form, read the source rather than the summary — the detail below is where field
inventories, exact wording and edge cases live.

### Forms and procedures from LSBC

| Source | What it contains | What it drives |
|---|---|---|
| Applications inventory (spreadsheet) | Fourteen numbered documents with a named owner against each, plus four process areas without forms | `PT-20`. Note the register has at least one error: temporary permits are assigned to the problem desk, which disclaims them; they belong to reciprocity |
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
| Stop code list (F9 lookup) | All thirty-one codes with descriptions (code 32 was added in October 2026) | `BR-02`, `BR-03`, `BR-04` |
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
| 6 Nov 2026 | Person-level fields (maiden name, legacy certification number, social security number and card, duplicate licence count, since moved to the licence) live on **Contact** and surface on the Person Account as `__pc`. Account custom fields are for business accounts. |
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
| 10 Nov 2026 | `PT-16` as built: Generate Letter with Letter Template custom metadata and a Visualforce PDF on letterhead; four starter letters with placeholder wording. |
| 10 Nov 2026 | Review and decide built: Decide on both application objects; End Stop Code with the name change. Eligibility rules are not re-run at Decide. A refused business application is Canceled until a Denied status is added. |
| 10 Nov 2026 | Print queue built: Ready to Print formula, Licenses Ready to Print list view and Mark Printed list button, which skips licences whose holder has an active stop code. |
| 10 Nov 2026 | `PT-15` as built: New Application runs the portal forms for a person as staff; Upload Documents on applications, including documents sent to the Board. |
| 10 Nov 2026 | Staff work queues: list views Applications Awaiting Review (both application objects), Open Stop Codes, Payments Received This Week (in place of Payments by Deposit) and the LSBC Licensing Home page that shows them with Licenses Ready to Print. |
| 10 Nov 2026 | Staff reports built: LSBC Operations folder (seven reports on six new report types) and the LSBC Operations dashboard, shown to each viewer with their own access and placed on the LSBC Licensing Home page. |
| 10 Nov 2026 | `CUT-03` as built: five desk training guides; Phase 6 closed. Staff access to the Phase 6 tools is on the Phase 2 list. |
| 10 Nov 2026 | Status brought current after Phase 6: header, milestone build status, a 5.1 note listing what paused security still owes the later phases, `PT-09` and `OPEN-09`/`OPEN-36` describe the new-to-the-Board sign-up path, and `OPEN-11` now holds up security rather than the data model. Duplicate change log rows removed. |
| 11 Nov 2026 | `DM-07` no longer says Phase 1 has no encryption at rest: Shield is in Phase 1 (`SEC-03`), from January 15. |
| 10 Nov 2026 | First CLOSE load in the sandbox (section 7): Legacy Key fields on Account, `BusinessLicense` and `Accreditation` and the `LSBCDataMigration` permission set brought into the build. Licence numbers, instructor types, booth renter licences and three missing licence types raised as client questions. |
| 11 Nov 2026 | CLOSE migration build: Instructor split into Cosmetology, Esthetician and Manicurist Instructor, each needing its own discipline's licence for codes 7 and 9 (`BR-02`); the reciprocity, retake and temporary permit forms ask which instructor licence. Manager, Microdermabrasion and Make-up Application licence types (`BR-22a`, `DM-12`). Code 32 NSF Late Fees is manual (`BR-03`). All CLOSE fee codes on Product; renewal and late fees per licence type, `FH` failure to renew, `PO` is a school fine (`BR-07`). CLOSE's violations and citations replace the placeholders (`CM-02`). A rule change now edits the existing expression set version: new versions can't be deployed in this org. |
| 11 Nov 2026 | `FeeSchedule` version 4: initial, duplicate, affidavit and violation fees per licence type or cited party, with CLOSE codes and amounts and the generic row as fallback; fee items link to their fee code Product (`BR-07`). Continuing Education entry type on hours entries, ignored by stop codes; CLOSE seminars and attendances loaded (`DM-16`, `OPEN-14`). |
| 11 Nov 2026 | Code 16 also clears when the shop holds a current Manager licence: CLOSE keeps the Manager licence on the shop (`BR-22a`). New `BusinessLicense.InstructorStatus__c` (Active, Inactive) from CLOSE's instructor status; N and X are a client question. |
| 12 Nov 2026 | UAT on migrated data, fixes (`BR-01`, `BR-11`, `BR-07`, `PT-10`, `PT-15`): the stop code re-check runs in the background, once per holder per save (new Account field Stop Code Sync Pending; Record-Trigger: Account After Save), and deleting a licence re-checks too. Non Payment ignores fees with no due date. A payment applied to fees can't be deleted. Staff paper intake asks no email and leaves no receipt item. The Standard Account Duplicate Rule reports only, so establishment forms always save. A returned checklist item's file moves to the application (one file per item is a platform rule); accommodation documents reach the Person Disability through the person account. Person Account layout rebuilt; the Home dashboard stays a link until Phase 2 sharing decides how it runs. |
| 12 Nov 2026 | Brought in line with the build after review. Section 7 records that the build team loaded CLOSE data, with what is loaded and the real-data exposure; `PT-13` and `CM-07` no longer assume no migration. `DM-18` says the ledger now covers every fee. Fee table: late fees are per licence type, school late renewal is `FD` + `FH`, every code is loaded. `ReciprocityStateExams` replaces `ReciprocityStateRule` in sections 1 and 2. Code 6 notes its conflict with `DM-03`; stop codes are 32 in CLOSE, 29 built. `PT-07` and `PT-09` updated; section 2 states that expression set rule changes keep no history; 0.2 lists the code in the build. Section 8: `OPEN-03` and `OPEN-14` settled with notes; `OPEN-40` to `OPEN-55` added from the client questions and this review; thirty-five open. |
| 12 Nov 2026 | Section 7 explains why code 16 fell from 767 to about 530. `OPEN-53` names the three years of payments and allocations in the load. Unpaid CLOSE balances split from `OPEN-55` into `OPEN-56`, a policy choice: they raise no Non Payment hold, so licences CLOSE holds will print. Thirty-six open. |
| 12 Nov 2026 | LSBC answers (Tywanda): code 6 accepts any current operator licence, `OPEN-50` settled (`BR-02`, `DM-03`). Code 16 is set and ended by staff: the automatic rule is removed from `StopCodeEstablishment` and the sync, 535 automatic holds ended and CLOSE's 3 live code 16 holds loaded (`BR-03`, `OPEN-55` now code 20 only). A manager's operator licence is checked on the shop form, since CLOSE files the Manager licence under the shop. The shop form treats a new location as a new establishment. The portal books no inspection; online payment of the $105 and e-checks are with LSBC (`PT-20`). Thirty-five open. |
| 12 Nov 2026 | LSBC answers (Deborah): code 20 at 180 days instead of six months (`BR-11`), `OPEN-55` settled. The new school form takes no online payment: the inspector collects inspection fees at the visits (`BR-22`); the inspector collects the $300 and $340 at the final inspection. CE providers Milady, Pivot Point and Rocketcert created, `OPEN-49` settled pending approval dates. `OPEN-25` settled (one exam application). Make-up is renewal only. Instructor status N and X go to William (`OPEN-42`). Thirty-two open. |
| 12 Nov 2026 | Deborah's follow-up: CE providers are approved by the Board each year, so each has a 2026 approval (1 Jan to 31 Dec) and staff add the next. The inspector collects all new school fees at the inspections, the $300 and $340 at the final one. Code 20 counts from the last hours received; the build counts from the end date of the last hours entry. |
| 12 Nov 2026 | Code 20 counts from the date the Board received the last hours, as Deborah described: new field Received Date on Training Course Participant (defaults to the day the entry is made), backfilled on the 32,804 migrated hours entries from CLOSE's entry date (a median 16 days after the month's end). `StopCodePerson` input `LatestHoursReceivedDate` replaces `LatestHoursEndDate`; the nightly schedule watches the received date (`BR-11`, `DM-16`). |
| 12 Nov 2026 | Every custom field goes on its layout and gets admin field access in the same change; `scripts/checks/field_coverage.py` enforces it (section 1). Layouts brought in line: the record type, applicant answers, certification and location on both applications, fee year and product, Legacy Key, Parish, Tax ID, Entry Type, Attempt Number, bond and CE fields, Fee Code; the Examination, Person Disability, Person Education and licence type (Regulatory Authorization Type) layouts added to the repo with their fields. Compact layouts on nine objects. The person account shows relationships, exams, accommodation requests and languages. |
| 12 Nov 2026 | Cory's answers (problem desk): the first affidavit ever is free and $15 is charged per licence certified; CLOSE records earlier affidavits only as an applicant comment; "name you were initially licensed under" is any earlier name, typed by the applicant (`BR-26`). Duplicates are one per renewal period, not per year (`BR-18`). Temporary permits belong to reciprocity (Stephanie). Parish stays blank where the ZIP spans parishes (`PRE-01`). Build changes made the same day (see the next row) |
| 12 Nov 2026 | Follow-ups from Cory and Stephanie: a duplicate is one per licence per renewal period, any time in it, $25 every time with no free first (`BR-18`). Two licences are two affidavit requests with a letter each; CLOSE comments ("Cert mailed", "Aff mailed") mark earlier affidavits, before CLOSE included; code 87 is discontinued (`BR-26`, `OPEN-47` closed). The temporary permit's event type comes off; the permit runs 30 days from issue plus mail time, set by hand (`BR-28`). Built the same day: Last Duplicate Date on the licence replaces the person's duplicate count and date; Earlier Affidavit In CLOSE and Initially Licensed Name added; event type removed from the temporary permit form. Event dates and the 30-day advance check wait on reciprocity |
| 12 Nov 2026 | LSBC answers (William): instructor status N is Master-Inactive and X is not applicable; the status does not change the fees, so `InstructorStatus__c` no longer claims it does. The 26 N instructors reload as Inactive masters, the 28 M as Active masters (`BR-07`), `OPEN-42` settled. The portal's Forms and Resources page links the School Forms packet and the Threading and Alternative Hair Design Facility Application on the Board's website; the copies mapped in `docs/` are the same forms. Thirty-one open. |
| 16 Nov 2026 | Stephanie (reciprocity): the events and dates section can go and the system should set the expiration (`BR-28`). The temporary permit form no longer asks event dates or checks 30 days' notice; Event Start Date, Event End Date and the optional Event Information document are removed; `EligibilityPermit` drops the advance-notice step. Temporary Permit's Term Length is 33 days, so Decide sets the expiration 30 days plus mail time after approval |
| 16 Nov 2026 | Stop code 15 (restoration exam) counts only licence types the holder no longer holds: a lapsed licence of a type they hold currently no longer opens it (`BR-04`). A licence saved with a person Contact but no Organization now gets the Organization filled from the person (`Record-Trigger: Business License Before Save`): licences, the Licenses tab and every stop code check are keyed on Organization, and one created with only the Contact was missed by all three (`DM-01`). |
| 16 Nov 2026 | Every document a form asks for is a checklist item (`PT-03`, `PT-18`). The accommodation documentation became a required Documentation for Disability Related Needs item (category Exam Accommodations) on the form's draft, moved to the application at Certify; one Person Disability per form (`SEC-08`). Who sees Exam Accommodations documents is a Phase 2 question. |
| 16 Nov 2026 | Licence status Expired added to `BusinessLicenseStatus` (`DM-08`): settable on New License, reset to Active by a renewal approval, shown as "Expired on <date>" in the public search. The nightly expiry (schedule version 3) is held until Jonathan approves it; version 2 stays active. |
| 16 Nov 2026 | Renewals (`DM-08a`): the renewal fee is filed under the renewal application, not the licence; the nine submitted renewals' fees were moved. A licence with a renewal waiting is not offered for renewal again. |
| 16 Nov 2026 | `BusinessLicense.ContactId` is filled on person licences (`DM-01`): `Record-Trigger: Business License Before Save` fills whichever of Organization and Contact is missing; 32,998 existing person licences backfilled. |
| 16 Nov 2026 | Staff form Completion and Initial License for the 1,500 hour completion form (`PT-15`), with new fields Total Completed Hours, Date Enrolled and Date Completed on Individual Application and document type Cumulative Hours Report. The Student License (L) number waits for student registration. |
| 16 Nov 2026 | Decide (`PT-15`): approval needs certification (staff entry counts), sets Approved Date, clears Printed Date and sets an Expired licence back to Active; older renewals count unpaid fees on the licence. Licences and applications are never deleted by staff. |
| 16 Nov 2026 | Record Complaint (`CM-01`): new Case fields Complaint Type and Incident Date from the public complaint form; Record Complaint carries them over and sets the Case's Account to the business, else the practitioner. |
| 17 Nov 2026 | Decide's Deny and Refuse cancel the application's unpaid fees (`PT-15`). The latest exam attempt for stop codes is chosen by the new formula Attempt Order on Person Examination (date, attempt number, created time), so a same-day fail and pass are ordered correctly (`BR-02`, code 08). |
| 19 Nov 2026 | Reciprocity answers from the Board (`BR-19`, `BR-23`, `DM-15`, `PT-20`): a licence not earned at a licensed or certified school, or of a type the Board doesn't accept from any state, can't transfer (new field Non-Transferable License Type; `EligibilityReciprocity` inputs). Utah takes the state exam only and Indiana's cut-off moves (`ReciprocityStateExams` V2). Military applications charge $25 plus a $50 military permit (`FeeSchedule` V5); the permit's licence type and renewal fee wait on the Board. Military ID or orders. Documents sent to the Board take an optional copy on the portal. Portal forms discard at most three abandoned drafts per start (the form faulted for an applicant with 14). |
| 19 Nov 2026 | Military Permit (`BR-23`, `BR-07`): a military reciprocity application is for the new licence type Military Permit (category Permit), so Decide issues only the permit. Renewal $50 and late fee $50 (`FeeSchedule` V6); new field `RegulatoryAuthorizationType.LateFeeGraceDays__c` (30 on the permit) delays the late fee in `Subflow: Fee Renewal Assessment`. The permit expires on the holder's birthday, like the other permits (confirmed 19 Nov 2026). |
| 19 Nov 2026 | `BusRegAuthorizationType` stays empty: Salesforce confirmed it comes with Public Sector Solutions and no standard feature needs it. |
| 19 Nov 2026 | Business Rules Engine licensing confirmed by Salesforce: rule runtime for staff comes with the core Public Sector licence, checked on the running user even in system context, including the Default Workflow User for scheduled flows. 5 Designer seats are included. Sandboxes don't enforce the licence, so this can't be tested before production. |
| 19 Nov 2026 | Date of birth moved to the new custom field `Contact.DateOfBirth__c` (`OPEN-51`, `SEC-04`): Shield can't encrypt the standard `Birthdate`. Sign Up, Applicant Details, both Decide flows, Threading Permit, the Person Account layouts and the CLOSE load use it; the 35,589 migrated dates were copied and the standard field emptied. |
| 19 Nov 2026 | Rule changes are new expression set versions (`OPEN-52`): a version deploys on its own as `ExpressionSetDefinitionVersion` with the next rank while the old one stays active, tested on `EligibilityInstructorCE` (V2 deployed as Draft, then Active beside V1, then removed). Editing an active version in place is retired. |
| 19 Nov 2026 | Licence numbers (`PT-14`, `OPEN-40`, `PT-16`, `DM-19`): a person's Certification Number (`Contact.CertificationNumber__c`) is issued by Decide from the new Certification Number Counter plus the birth month and day, as CLOSE does; each licence's License Number is that number, a dash and the type code (`RegulatoryAuthCode`), because `Identifier` is unique. Sign-up, public search and the manager check match a number with or without the code. 21,191 people and 18,371 licences loaded from CLOSE. Licenses Ready to Print groups by approval date; Print Licenses prints onto the three-part stock (LBC-19). The Print Name on License flag is not used (William) and isn't migrated. |
| 19 Nov 2026 | `OPEN-57` opened: the org allows 2,500 rule calls a month and 100 portal users' licences, far below the build's volume and the licensee population; sizing is with the Account Executive. |
| 19 Nov 2026 | `OPEN-57`: Jonathan kept the portal as built (logins trued up at LSBC's renewal) and put moving rules out of the rules engine on hold. |
| 19 Nov 2026 | `SEC-01c` settled: the Board agreed the access matrix's Sharing Settings on 18 Nov 2026, and the other tabs were rebuilt to match. Program Manager edits almost everything, accommodations included (`SEC-08`); Executive Director and Program Manager edit Fee Products; Reciprocity Desk, Student Registration, Testing Desk and Inspection Supervisor report to Program Manager. Each desk group gets a muting permission set so it never exceeds its Sharing Settings. The remaining Phase 2 questions (violations, complaint confidentiality, queues, refunds, report folders, portal establishments, accommodation documents, letter templates) follow the build team's recommendations in the Client Questions doc, adjusted to the agreed Sharing Settings, at Erin Marceaux's request. The workbook is now `LSBC Access Matrix.xlsx`. |
| 19 Nov 2026 | Phase 2 security built from the access matrix (`SEC-01c`): permission sets, desk groups with muting sets, sharing rules, org-wide defaults (Account, Case, Opportunity Private; License Type, Training Course, Course Offering Public Read Only), profile LSBC Standard User, report folder sharing, queue members. Staff action flows now run in system context with sharing, restricted to the desks that use them. |
| 19 Nov 2026 | Refund: a new Refund Requested By User field and a validation rule stop the requester verifying their own refund (`DM-18b`). Confidential complainant: the Public Complaint page shows the Complainant section only when the complaint isn't confidential or the user holds View Confidential Complainant (Executive Director, Compliance Officer, Program Manager, admins) (`CM-02`). |
| 19 Nov 2026 | Establishment numbers and the nine-digit person numbers (`PT-14`, `OPEN-40`, `OPEN-41`), from William's answers: salons, threading and alternative hair design facilities get Certification Number on the business account from the new Establishment Number Counter (77 plus a counter), and their licences, manager licence included, carry it with the type code. CLOSE's nine-digit person numbers are generated, not SSNs, so they are loaded (read from the raw export once by `extract_certification_numbers.py`), as are the salon numbers (`SHOPS.OLD_SHOP_ID`): 35,451 people, 7,385 establishments. Printed licences show the number with an L in front, and sign-up, public search and the manager check accept it typed with the L. |
| 19 Nov 2026 | Demo feedback (18 Nov): staff Home shows Open Stop Codes in the right-hand column (`PT-15`); the printed licence leaves the wallet card blank, a $25 wallet duplicate waits for the Board (`PT-16`); field history on every staff object with the History tab showing it (`SEC-05`). |
| 19 Nov 2026 | Portal address change for individual licensees: Change My Address request Case and staff Apply Address Change, proof of address checked first (`PT-15`, `CM-02`). |
| 19 Nov 2026 | Portal redesigned in an editorial style with Erin Marceaux's 2026 logos and seal, then the Board's colours (pale cool blue-grey, slate blue, no gold) (`PT-01`, `PT-02`). Staff app takes the 2026 seal and logo navy. |
| 19 Nov 2026 | Board Documents and Publications on the portal home from Salesforce CMS, as Documents because Aura detail pages take only Document or Image content; guests may view published CMS content (`PT-01`). |
| 19 Nov 2026 | `OPEN-11` settled (`PT-02`): portal Owners, Managers and School Administrators read their businesses through share records kept by `Subflow: Portal Business Access Sync`, since a sharing set can't filter by relation role; Decide passes a portal-created business to the approving staff member. No one edits or deletes notes or activities they didn't write. William is LSBC's long-term admin; only admins publish Board documents. Staff licences move to Phase 7, January 2027 (5.1). |
| 19 Nov 2026 | Document checklists move from the Application Document Requirement settings (retired) to Action Plan templates, one per form, so LSBC's admin maintains them in Setup (`PT-18`, `PR-01`). Templates only: the subflow builds the checklist items itself, because a draft can't take an application's template and template metadata carries org-specific Ids; templates are loaded per org by `scripts/actionplans/load_templates.py`. |
