# LSBC Salesforce build

Louisiana State Board of Cosmetology, Phase 1 on Public Sector Solutions. The design is
[docs/LSBC_Solution_Design.md](docs/LSBC_Solution_Design.md). Read the section for the phase
you are working on before building, and section 9 for what the org actually provisions.

## Working rules

- At the end of each phase, update the admin guide, a Claude Doc titled "LSBC Salesforce Admin
  Guide" (<https://claude.ai/artifact/3zfR5LEknYU6f9EebqB3xy>). It is written for a new admin: what
  each object, field, rule and flow does, with a Mermaid diagram for each flow and branching rule,
  and encrypted fields marked. No requirement IDs.
- At the end of each phase, also add scripts to the UAT doc, "LSBC UAT Scripts"
  (<https://claude.ai/artifact/Pv2nDG8sGtdwZsnnQTQgAG>). The build team and the Board run the same
  scripts, so don't split them by tester. Each script has an ID, steps on named test records, the
  expected result and a Result dropdown. Fails go in its Defect log. When the portal or staff tools
  start calling a rule, add scripts that test it through the real screen.
- At the end of each phase, update "LSBC Client Questions"
  (<https://claude.ai/artifact/YatXF6tvuQRESxJ8VaDawj>): every question waiting on LSBC, the Board,
  OTS or Salesforce, with who to ask, when it's needed and a Status dropdown. Add new questions as
  they come up; close answered ones once the build and design reflect them.
- Portal forms match LSBC's paper PDFs in `docs/` section by section. "LSBC Application Form Field
  Mapping" (<https://claude.ai/artifact/6sUaehTcvisoaMyeu822Rf>) maps every PDF field to its
  Salesforce field, for the Board. Update it whenever a form's field or mapping changes; the Board
  approves new form fields from it. Signatures are a certification checkbox, typed name and
  timestamp, never DocuSign or another e-signature product.
- Whenever an object, field or relationship changes, update "LSBC Data Model"
  (<https://claude.ai/artifact/9Jz5Cz3thQrdYjRwFDTCfj>): one Mermaid ER diagram per area, showing
  custom and key standard fields, encrypted fields marked, no requirement IDs. Mark planned fields
  as planned until they deploy.
- With every deployable change (each commit that touches `force-app`, `data/` or `scripts/`), update
  "LSBC Deployment Manifest" (<https://claude.ai/artifact/XfhVuAzpXfoDxYPsR2SU5X>), which Jonathan
  deploys from with Gearset: its metadata-by-phase table, data to load, post-deployment steps and a
  dated change log row. Regenerate `manifest/package.xml`
  (`sf project generate manifest --source-dir force-app --name manifest/package.xml --output-dir .`)
  in the same commit. Any sandbox-specific value added to metadata (a user, an email address, a
  status) goes in its "before deploying to production" list.

- Deploy straight to the `LSBC-Partial` sandbox (default org). No scratch orgs.
- Requirement IDs (`DM-01`, `BR-04`, …) go in commit messages and Jira only. Never put them in
  metadata descriptions, help text, labels or anything an admin sees in Setup: a future admin
  won't know what they mean. Write descriptions in plain language.
- Naming follows the [CFPB Salesforce Naming Conventions](https://github.com/cfpb/salesforce-docs/blob/master/_pages/Salesforce-Naming-Conventions.md)
  and, for flows, [Automation Champion's flow conventions](https://automationchampion.com/2021/11/09/naming-conventions-for-salesforce-flow/).
  **List every proposed label and API name to Jonathan before creating it.**
  - Objects, fields, record types, permission sets: whole words, PascalCase, no spaces or
    underscores. `ForYear__c`, record type `NewLicensure`, permission set `SchoolAdministrator`.
  - Flow label per Automation Champion; API name is the label minus spaces and punctuation.
    `Record-Trigger: Business License After Save` → `RecordTriggerBusinessLicenseAfterSave`;
    `Screen Flow: Account Add Stop Code`, `Subflow: Stop Code Sync`,
    `Business License Schedule: Expired And Lapsed Licenses`.
    One record-triggered flow per object per context; later phases add to it.
    Exception: portal screen flows show their label to applicants (the Save for later dialog, saved
    and error messages), so their label is plain ("License Renewal", "Sign Up") and the convention
    label opens their description; the API name still follows the convention. The map is
    `PORTAL_LABELS` in `flowkit.py`.
  - Flow elements use the article's prefixes, the one sanctioned underscore: `varB_`, `varT_`,
    `varR_`, `forD_`, `textT_`, `choice_`, screen-initial components (`ASC_Category`). Elements read
    `Get <Object>`, `Set <Field> to value`, `Loop Through <Objects>`; decisions are questions.
  - BRE decision matrices and expression sets: area + purpose, `FeeLateCalculation` (label
    Fee Late Calculation).
  - Validation rules: `<Field><Rule><Dependency>` in PascalCase, e.g. `TotalHoursMax192MonthlyHours`;
    plain-language error message.
  - Standard objects and fields keep Salesforce's spelling.
- Every custom field goes on its object's page layout (read-only when a flow or the applicant sets it)
  and gets field access in `PublicSectorAccessAdminPSL`, in the same change that creates it. If the
  object's layout isn't in `force-app`, retrieve it first. Run `python3 -I scripts/checks/field_coverage.py`
  before committing; it must pass. The only field kept off layouts is the social security number
  (`EXCEPTIONS` in the script).
- A picklist whose values are used on more than one object is a global value set, referenced by
  each field. Never copy the same values inline on two fields. Example: `Parish`, used by
  `Account.Parish__c` and `Contact.HomeParish__c`.
- Person-level fields go on Contact (they surface on the Person Account as `__pc`). Account custom
  fields are for business accounts.
- Standard objects first (`PR-01`). Declarative first: Flow + Business Rules Engine; LWCs only for
  the cases listed in `PT-18`. Business logic never lives in a component (`PR-05`).
- Shield is in scope. Avoid formula, filter and list-view dependencies on fields on the
  encrypted list (`SEC-04`).
- The portal is built now but not published until March or April 2027.
- When a decision changes the design, update the doc and add a row to its section 10 change log.

## Build phases

| Phase | Scope | Status |
|---|---|---|
| 0 | Foundation: Person Accounts, record types, repo, doc corrections | Done |
| 1 | Data model (section 1), encrypted field list | Done |
| 2 | Security (5.1), `OPEN-11` ACR sharing spike | Paused: awaiting Board feedback on `LSBC_Access_Matrix.xlsx` |
| 3 | Business rules (section 2) | Done. Eligibility rules built, called from Phase 5 and 6 |
| 4 | Cases and violations (section 4) | Done |
| 5 | Portal (section 3) | Done. School Administrator and Business Owner forms wait for Phase 2 |
| 6 | Staff tools, reports, cutover (PT-15–17, DM-18c, section 5) | Done. Staff app LSBC Licensing; access waits for Phase 2 |

### Phase 2 carry-over

Raised by later phases while Phase 2 is paused. Pick these up when it resumes.

1. Staff need Run Flow and the core Public Sector licence, which includes rule runtime (Account Executive,
   19 Nov 2026; no separate `BRERuntime` licence exists or is needed). Production checks it on the user who
   saves the record, even in system context, and on the Default Workflow User (Process Automation Settings) that
   every scheduled flow runs as; in production that must be an LSBC user. System Administrators are not exempt.
   Sandboxes don't enforce it (Erin Marceaux, with none, runs the nightly stop code schedule), so it can't be
   tested here. The org has 5 Public Sector Access seats today; more licences for staff arrive in January 2027.
2. Who can add and end manual stop codes: `RecordAlert` create/edit, its org-wide default, and the
   Add Stop Code action.
3. Field history on `RecordAlert` `ValidUntilDate` and `IsActive` (`SEC-05`).
4. BRE Designer for LSBC's long-term admin (5 seats, included in the licence; 3 used by the build team).
5. Confirm system-context rule flows are acceptable under the private-by-default model.
6. Portal users need `BRECmtyRuntime` (Phase 5); it comes with the Public Sector community licence
   (Salesforce, 19 Nov 2026). Guests can't hold it and no guest flow calls a rule. Production has only 100
   portal logins, 100 `PublicSectorCmtyAccessPSL` and 100 `BRECmtyRuntime` seats against about 40,000 active
   licences, and `RecordTriggerUserAfterSave` assigns both seats at sign-up: more seats needed before the
   portal is published (Client Questions, with the AE).
7. History on `RegulatoryTrxnFeeItem` is not enabled, so Change Year notes the change in the item's
   Comments. Enable field history on `ForYear__c` if the object supports it (`SEC-05`).
8. Who can create violations (`RegulatoryCodeViolation`) and run Record Complaint, and who can edit
   Amount Paid (flow-set; keep it read-only for staff).
9. `PublicComplaint` confidentiality: who sees the complainant on a complaint with
   `IsReporterConfidential` ticked, and the object's org-wide default.
10. Queue membership for Complaint Intake and General Inquiries (staff, not Jonathan). Members are
    data (`GroupMember`), not in the queue metadata.
11. Field history on violation `Status` and `PublicComplaint.IsReporterConfidential` (`SEC-05`).
12. Establishments created by the portal shop and facility applications are owned by the applicant's
    portal user (that is how the owner sees them). Decide staff access to them, and whether ownership
    moves to an LSBC user or queue once the application is approved.
13. The School Administrator and Business Owner portal audiences (access over Account Contact
    Relations, `OPEN-11`) and the 17 School Forms; staff access to portal submissions.
14. The LSBC Licensing app is visible only to System Administrator (in `profiles/Admin`). Give the
    staff profile or permission sets app visibility, the record pages and the Home page.
15. Staff access to the Phase 6 actions and flows: Record Payment, Refund, Generate Letter, Decide,
    End Stop Code, Mark Printed, New Application, Upload Documents. Decide whether the refund
    verifier must differ from the requester (only a department name is recorded now).
16. Field access for the Phase 6 fields (`Payment__c` CheckDate, PayerName, ChecklistItem;
    DecisionReason on both applications; BusinessLicense PrintRequestedDate, PrintedDate,
    IsReadyToPrint). Refund fields stay read-only on the layout: only the Refund flow sets them.
17. Apex class and Visualforce access for letters: `LetterPdfController`, `LetterPdfSaveAction`,
    page `LetterPdf`. Who may edit Letter Template custom metadata.
18. Sharing for report folders LSBC Finance and LSBC Operations and dashboard folder LSBC
    Operations. The dashboard runs as the viewer, so it follows record access.
19. The Home page shows only a View Dashboard link: Lightning pages can't embed a dashboard that runs as
    the viewer. Decide: run it as a fixed user, or put report charts on Home.
20. Staff who run Decide need create and read on `CertificationNumberCounter__c` (it issues certification
    numbers), and staff who print need the `LicensePdf` page and `LicensePdfController` class.
21. Portal users have no access to `PreliminaryApplicationRef` (drafts). Files can't be attached to a draft
    from the portal; documents go on checklist items, accommodation documents via the person account.

## Org notes

- Business Account record types deployed: `Establishment` (default), `School`, `Organization` (`DM-01a`).
- Person Accounts are enabled. The record type is labelled `Person`; its developer name stays `PersonAccount`.
- Admin access comes from the permission set group `force__Public_Sector_Solutions_Admin`.
  Field access for PSS objects is granted by `PublicSectorAccessAdminPSL` in that group (added to the
  group in Phase 1; after changing it, wait for the group status to return to Updated). Add new
  admin field access there. Don't create separate admin permission sets.
- Training Course's API name is `TrnCourse`, not `TrainingCourse`.
- Holds attach to the holder (Person or business Account), not the licence. Accepted; the Board may
  revisit.
- Encrypted field list: build the fields now, encrypt when Shield arrives. No Board approval needed.
- Date of birth is `Contact.DateOfBirth__c` (`DateOfBirth__pc`), never the standard `Birthdate`/`PersonBirthdate`:
  Shield can't encrypt the standard field, so it stays empty. Never filter, sort or search on the date of birth;
  read it after finding the person another way.
- Reference data (fee codes, stop-code files, violations list, programme hours) not yet received.
  Use placeholders and flag them; don't invent values.
- BRE in this org:
  - Test an expression set through `POST /services/data/v66.0/actions/custom/runExpressionSet/<Name>`
    with `{"inputs":[{...}]}` (the same action Flow uses). The Connect `business-rules` endpoint rejects the name.
  - A rule change is a new version, never an edit to the active one (Salesforce: production rejects
    in-place edits). Put it in its own file,
    `force-app/main/default/expressionSetVersion/<Name>_V<n>.expressionSetVersion-meta.xml` (metadata
    type `ExpressionSetDefinitionVersion`; retrieve the current version with
    `sf project retrieve start --metadata ExpressionSetDefinitionVersion:<Name>_V<n-1>` to start from),
    with the next `rank` and `versionNumber`, `startDate` today and `status` Active, and deploy only
    that file. The old version stays active, so nothing goes offline. Which overlapping active version
    runs was not proven (the test V2 was identical): on the first real change, test through
    `runExpressionSet` that the new logic answers, then deactivate the old version.
    Never redeploy the whole `expressionSetDefinition` file once a version in it is active: that is
    what fails with "LatestVersionSnapshotId not found". Tested 19 Nov 2026 on `EligibilityInstructorCE`.
    Version descriptions max 255 characters. Decision matrices take new versions too (`FeeSchedule` V3).
  - Rule calls are metered: usage entitlement `RulesEngineCallsLimit` is 2,500 a month (sandbox, 19 Nov
    2026). The build uses far more (about 2,600 licence expiries a month each run the hold check, plus
    renewals). Jonathan put moving rules into Flow on hold (19 Nov 2026); LSBC trues up usage at renewal.
    Don't add rule calls per record in schedules or triggers without counting them.
  - Every expression set variable must be an input, an output or a constant. A working variable
    that is neither breaks the Flow action ("type mapping … is not a supported type"), though the
    REST test passes. Fold working values into the output formulas.
  - No `ADDDAYS`; add days with `Date + Number`. `DATE`, `YEAR`, `MIN`, `IF` work.
  - `ISBLANK` never matches a blank Text input. Compare against the expected values instead
    (`Result != "Pass" && Result != "Fail"`). `ISBLANK` works on Date and Number. `ADDMONTHS` works.
  - A Date output comes back as midnight GMT, which Flow reads as the previous day in Pacific. Map it
    to a DateTime variable (`outputParameters`, not stored automatically) and add 17/24 for noon
    Louisiana time, as `ScreenFlowIndividualApplicationDecide` does.
- Decision matrix rows are data, not metadata. Deploy the definition as Draft, load rows with
  `POST /services/data/v66.0/connect/omnistudio/decision-matrices/<matrixId>/versions/<versionId>/rows`
  and body `{"rows":[{"rowData":{...}}]}` (a direct `CalculationMatrixRow` insert skips the hash key),
  then redeploy as Active. Row sources live in `data/decisionMatrices/*.csv`. Test with
  `POST /services/data/v66.0/actions/custom/runDecisionMatrix/<Name>`. An unmatched input returns blank outputs.
- Flow: an empty Text variable is null, and `CONTAINS(null, …)` is null, not false, so it fails an
  "equals false" check. Prefix the haystack: `CONTAINS(";" & {!varT_List}, …)`.
- A screen text input or multi-select left empty after a visit is an empty string, not null: test it
  with Is Blank (or a trimmed formula), never Is Null. Radio buttons reject Is Blank; Is Null works there.
- State and Country picklists are on. Screen addresses use the standard Address component
  (`flowruntime:address`, `required` input for the asterisks), which shows Country and State dropdowns but
  outputs and takes *names* (`Louisiana`, `United States`): write them to the name fields (`PersonMailingState`,
  `ShippingCountry`), never the `…Code` fields (restricted picklist error). Saving a state without a country fails.
  In the browser driver, open its dropdowns with focus + ArrowDown; a click doesn't open State.
- A radio button with a fixed default resets when its screen is reached again through a connector,
  even with "remember values". An error screen that sends the user back uses the real Back button
  (`allowBack` true, `allowFinish` false, `backButtonLabel`).
- Stop code syncs from record triggers run in the background: each trigger ticks
  `Account.StopCodeSyncPending__c` on the holder and `Record-Trigger: Account After Save` (Run
  Asynchronously) unticks it and runs `Subflow: Stop Code Sync`, once per holder per save. New triggers
  that affect holds tick the flag; never call the sync subflow from a record trigger (three syncs in one
  portal save hit the 100-query limit). Schedules still call it directly. Holds appear seconds after a save. Deletes that affect holds tick the flag in a before-delete trigger (`RecordTriggerAccountContactRelationBeforeDelete`); the background sync runs after the record is gone.
- Flow runs interviews for a batch of records together, element by element, so several records for
  the same Account in one save or one scheduled run all read before any writes. Anything that
  creates records per holder needs a gate: the stop code triggers and schedules get the holder's
  first record (same save: same `LastModifiedDate`; schedules: same window), sorted by Id, and only
  that record's run syncs. Flow can't filter `Id` with "less than". The sync subflow also ends
  duplicate open holds, keeping the oldest.
- The org time zone is America/Los_Angeles (Pacific), not Louisiana's Central. A scheduled flow's
  start time is read in org time: the stop code schedules run 00:30–01:00 Pacific (02:30–03:00
  Louisiana), so `TODAY()` is the same date in both zones. Whether to switch the org to
  America/Chicago is Jonathan's call: it changes what "today" means everywhere.
- UAT test data (from the 16–17 Nov 2026 end-to-end run): brand-new records created on screen, named
  `UAT <Area> <Role>` (UAT Stop …, UAT Fees …, UAT Staff …, UAT Signup …, UAT Portal …, UAT Rules …, UAT Page …,
  UAT Completion Student, UATTest New/Second Applicant). The UAT doc's "Test records" and "Set up your test records"
  sections list them and their portal logins. UAT runs on these, never on StopCodeTest records. Staff never delete
  licences or applications: test licences are set to Revoked, applications closed with Decide.
- Never use a delete-by-conditions element in a flow (Delete Records with filters): it faults when nothing matches.
  Look up the records, check the collection isn't empty, then delete the collection.
- Stop code test records in LSBC-Partial are named `StopCodeTest …` (a person, a salon, a school, and
  four Cosmetologist exams: national, practical, state and restoration).
  Reuse them; delete them before UAT data goes in. Phase 5 added `StopCodeTest Registrant`,
  `Registrant Two`/`Three` (signed up, with portal logins), `Registrant Four`/`Five` (left for UAT
  sign-up), `StopCodeTest Registrant Six` (signed up as new to the Board, no license), the establishments `StopCodeTest Portal Salon` and `StopCodeTest Braid Studio` and the school `StopCodeTest Portal Beauty Academy` (from the portal shop, facility and new school applications), `StopCodeTest Trigger`, `StopCodeTest CE Provider Current/Prior/Expired`, `StopCodeTest New Location Salon` (shop form test, BLA-0000000014; BLA-0000000015 is a reopening of StopCodeTest Salon), the school `StopCodeTest Fee Check Academy` (BLA-0000000016) and the Draft
  `StopCodeTest Texas License`. Portal test logins (`stopcodetest.portal@lsbc-partial.test`,
  `stopcodetest.trigger@…`, `jvasquez+lsbcreg*@journeyblazers.com`) can't be deleted: deactivate them.
- Case intake (sandbox): Email-to-Case routing address `jvasquez@journeyblazers.com` (Origin Email);
  test by emailing its Salesforce inbound address from another mailbox. Acknowledgements send from the
  verified org-wide address `jvasquez+lsbc@journeyblazers.com`: Salesforce rejects the routing address
  as a sender. Default Case owner is the General Inquiries queue. These are org settings, kept out of
  `force-app`; production uses LSBC addresses. Deliverability must be All email to test acknowledgements.
- Manager licences belong to the shop, as in CLOSE (no person holds one), so no hold checks a manager's own
  operator licence; the shop form checks the manager's licence number instead. Code 16 (no manager) is
  staff-set, not automatic: managers are recorded only on inspection visits.
- Violations: the `FeeSchedule` `Violation` row must exist or a violation can't be saved. Violation
  and complaint test records sit on the `StopCodeTest` accounts and Cases `RoutingTest …`,
  `ComplaintTest …`, `E2CTest …`; delete them with the stop code test data.
- Portal (site LSBC LPI, `/LPI`, Licenses & Permits theme): every flow a guest runs is set to
  "Override default behavior and restrict access to enabled profiles or permission sets"
  (`isAdditionalPermissionRequiredToRun`) and then granted to the guest profile `LSBC LPI Profile`
  in its flow access. Images in HTML blocks use `/sfsites/c/resource/<StaticResourceName>`, one
  static resource per image: the block prefixes the page path (`/LPI/s`), so `/LPI/...` doubles.
  Check the published site with headless Chrome (`--dump-dom`, `--screenshot`) after publishing.
  To drive forms as a portal user, open the org's frontdoor URL, then
  `/servlet/servlet.su?oid=<org>&sunetworkid=<network>&sunetworkuserid=<user>` (Log in as). Screen inputs carry
  the flow field's API name in `name`. A local HTTP control server is blocked; use one-shot puppeteer scripts.
- Sign up has two paths: a licensee (license number, last name, ZIP) or someone new to the Board
  (name, date of birth, contact details; a person account is created unless one with the same name and
  date of birth exists). Guest-created accounts belong to the site's guest record default owner, who must
  have a role for the portal login to be created: in production that has to be an LSBC user with a role.
- Portal users get the permission set group `PortalLicenseeAccess` (`PortalLicensee` +
  managed `force__DocumentChecklist`), assigned by `RecordTriggerUserAfterSave`. Without
  Document Checklist, a portal file upload to a checklist item fails ("insufficient access rights
  on entity") even with full record access.
- Every document a form asks for is a document checklist item (with its own document type and category),
  uploaded through `Subflow: Document Checklist Upload` / the `documentChecklistUpload` LWC. Never a plain file
  upload on a screen, and never files attached to another record by the flow (Jonathan, 16 Nov 2026).
- Document checklist items: `IsRequired` can only be set on create (replace the item to change it),
  and `AccountId` can't be set at all. Each item is filed under its document type's
  `DocumentCategory` (links in `documentCategoryDocumentTypes/`). Portal uploads go through the
  `documentChecklistUpload` LWC in `Subflow: Document Checklist Upload`. Documents that reach the Board by mail
  or straight from another state or company are flagged `IsSentToBoard__c` (on the requirement settings, copied
  to the item): the portal shows them without an upload and doesn't wait for them; staff upload them on arrival. A file can't be deleted while
  it is linked to a checklist item, nor the item while it has a file: delete the
  `ContentDocumentLink` first (`scripts/apex/DeleteRegistrantThreeTestApplications.apex`).
  A checklist item holds one file (platform rule, admin included): when staff return an item the checklist
  trigger moves its file to the application, and the upload component hides the box once an item has a file.
  Portal users can't attach files to `PersonDisability`, even as owner.
- Portal forms write nothing to the application objects until the applicant certifies. Each form
  creates a draft (`PreliminaryApplicationRef`, Application Type = target object) at the start; its
  documents sit on checklist items under the draft, and `SavedApplicationUrl` holds
  `/LPI/s/continue-application?guid=<$Flow.InterviewGuid>` to find the paused form again. On
  Certify the form creates the real records and `Subflow: Preliminary Application Transfer` moves
  the checklist items and marks the draft submitted; the form deletes the draft after payment.
  Save for later is flow pause (org setting `enableFlowPauseEnabled`, in `settings/Flow`); screens
  that allow it get the 30-day message from `flowkit.PAUSED_TEXT`. My Applications lists saved forms
  (`ScreenFlowIndividualApplicationResume`); Continue opens `/continue-application?interviewId=`,
  where the Aura `flowResume` component resumes it. `Subflow: Preliminary Application Discard`
  deletes a draft; the nightly `PreliminaryApplicationReferenceScheduleExpiredDrafts` (01:15) runs it
  after 30 days untouched. A form start discards at most three abandoned drafts (`IsTheDiscardLimitReached`): discarding
  14 in one go passed the 100-query limit. New forms follow the same pattern.
- CLOSE migration (the Board's legacy system): load scripts in `scripts/migration` (see its README).
  Work only from the de-identified copy `../LSBC-Migration/extract/lsbc_deid.sqlite`, where every
  SSN-shaped applicant ID and certificate number is a mock starting `000`; never open the raw export
  (Shield isn't on yet). The sandbox-only field `Contact.MockSocialSecurityNumber__c` lives in
  `sandbox-only/`, outside `force-app` and `package.xml`: never deploy it to production. Load files
  go in `../LSBC-Migration/load`; refuse any with a nine-digit value outside the `000` range.
- `force-app` holds only metadata this project owns. A full org retrieve sits in `reference/`
  (ignored by git) for lookups. Copy a file into `force-app` only when we change it.
- Phase 6 staff tools (app LSBC Licensing, console): the record pages and the Phase 6 screen flows are
  generated by the scripts in `scripts/generators` (see its README): edit the script, rerun, deploy. Pages share one format; a standard related list shows only if it is on the page layout, a dynamic one (`DYN` in `PAGES`, lookup columns without `Id`) doesn't need it. Person Examinations and Person Disabilities can't be added to the Person Account layout, so they are dynamic lists. A dynamic list shows no New button unless the page sets it (a fifth item in the `DYN` tuple, `['New']`, written as `actionNames`). Salesforce never shows New on a person account's Licenses (`BusinessLicenses`, Organization) list, even when set, so licences are added with the `Account.NewLicense` header action (person and business). Person Language can't be a related list anywhere (layout or page, Account or Individual), so `Screen Flow: Account Person Languages` (`scripts/generators/languages.py`) shows languages on the same tab (`('FLOW', name)` in `PAGES`; deploy the flow before the page). `pagegen.py` takes an optional object list (`… <out> <describe dir> Account`). Compact layouts are each object's default; a Person Account compact layout lives under `objects/PersonAccount`, not Account. Flow
  status picklists use API values (`RegulatoryTrxnFee.Status` is `DUE`, `PARTIALLY_PAID`, `PAID`).
  Reports created through the Analytics API default to "my records" (`<scope>user</scope>`): set
  `organization` before deploying. Business License Application Status has no Denied value, so
  Decide sets a refused business application to Canceled.
- Fee Schedule rows are `<License type> <Fee>` (Renewal, Late Fee, Initial, Duplicate License, Affidavit) and
  `Violation <Shop|School|Operator|Instructor|Special Permit>`; flows fall back to the generic row and link each
  item to its fee code Product. Continuing-education attendance is a Training Course Participant with Entry Type
  Continuing Education (Training Course `Continuing Education`, one offering per CLOSE seminar): stop codes skip it.
- Payments: Record Payment (Account) for mail and counter; accepting a Payment Receipt checklist item
  creates the Card payment (`SubflowPaymentReceiptPaymentCreate`, one per receipt via the unique
  `ChecklistItem__c`). No cash, no deposit number.
- Phase 6 test records: `IA-0000000033` (approved new licence `TEST-C-1001` for StopCodeTest
  Licensee, which now has a date of birth), `IA-0000000034` (renewal of StopCodeTest Registrant
  Cosmetologist, now to 2028-03-01; StopCodeTest Registrant has a date of birth), `StopCodeTest
  NameChange` (now StopCodeTest / Renamed Smith, ended name change stop code, licence `TEST-C-1002`),
  payments `PAY-000005` to `PAY-000009` (`PAY-000006` refunded), `IA-0000000096` (approved duplicate
  of SCT40003, paid) and `IA-0000000108` (approved temporary permit `TEST-TP-1001` for StopCodeTest
  Registrant Six, paid), and letter PDFs in Files on
  `IA-0000000003`, `StopCodeTest School` and `BLA`/Account test records. Delete them with the other
  StopCodeTest data.
- Licence numbers (William, 18 Nov 2026): a person's number is CLOSE's `APPLICANTS.OLD_CERT_NBR_NUM`, a
  counter plus the birth month and day (MMDD), shared by all their licences. It lives on the person as
  `Contact.CertificationNumber__c`; Decide issues it from `CertificationNumberCounter__c` (auto-number = the
  counter; set its next value at cutover from CLOSE's last). `BusinessLicense.Identifier` is unique, so a person's
  licence's License Number is `<number>-<RegulatoryAuthCode>` (`1846410407-C`); lookups by number match it or
  `<number>-*`. Business licences still take a typed number in Decide (salons 77 + counter, schools staff-set) until
  William answers whether salons share the counter. The 9-digit CLOSE numbers (SSN-shaped) aren't loaded.
  `LegacyCertificationNumber__c` is kept, unused. Test person: `UAT Number Applicant` (1846410407, IA-0000000205/206).
- Licence printing: Print Licenses (list view Licenses Ready to Print) opens `LicensePdf` on the LBC-19 three-part
  stock; positions in inches in the page, nudged with `dx`/`dy`. Governor: custom label `LicenseGovernorName`.
