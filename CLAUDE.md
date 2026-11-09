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
  - Flow elements use the article's prefixes, the one sanctioned underscore: `varB_`, `varT_`,
    `varR_`, `forD_`, `textT_`, `choice_`, screen-initial components (`ASC_Category`). Elements read
    `Get <Object>`, `Set <Field> to value`, `Loop Through <Objects>`; decisions are questions.
  - BRE decision matrices and expression sets: area + purpose, `FeeLateCalculation` (label
    Fee Late Calculation).
  - Validation rules: `<Field><Rule><Dependency>` in PascalCase, e.g. `TotalHoursMax192MonthlyHours`;
    plain-language error message.
  - Standard objects and fields keep Salesforce's spelling.
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
| 4 | Cases and violations (section 4) | |
| 5 | Portal (section 3) | |
| 6 | Staff tools, reports, cutover (PT-15–17, DM-18c, section 5) | |

### Phase 2 carry-over

Raised by later phases while Phase 2 is paused. Pick these up when it resumes.

1. Staff permission sets need Run Flow and BRE runtime access for the rule flows. Confirm whether
   the Public Sector licence includes internal BRE runtime.
2. Who can add and end manual stop codes: `RecordAlert` create/edit, its org-wide default, and the
   Add Stop Code action.
3. Field history on `RecordAlert` `ValidUntilDate` and `IsActive` (`SEC-05`).
4. BRE Designer for LSBC's long-term admin (5 seats in the org).
5. Confirm system-context rule flows are acceptable under the private-by-default model.
6. Portal users need `BRECmtyRuntime` (Phase 5).
7. History on `RegulatoryTrxnFeeItem` is not enabled, so Change Year notes the change in the item's
   Comments. Enable field history on `ForYear__c` if the object supports it (`SEC-05`).

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
- Reference data (fee codes, stop-code files, violations list, programme hours) not yet received.
  Use placeholders and flag them; don't invent values.
- BRE in this org:
  - Test an expression set through `POST /services/data/v66.0/actions/custom/runExpressionSet/<Name>`
    with `{"inputs":[{...}]}` (the same action Flow uses). The Connect `business-rules` endpoint rejects the name.
  - An active version can't be redeployed. Set `ExpressionSetVersion.IsActive` false with
    `sf data update record`, deploy, and the file's `<status>Active</status>` reactivates it. Once
    rules are in use, make a new version instead.
  - Every expression set variable must be an input, an output or a constant. A working variable
    that is neither breaks the Flow action ("type mapping … is not a supported type"), though the
    REST test passes. Fold working values into the output formulas.
  - No `ADDDAYS`; add days with `Date + Number`. `DATE`, `YEAR`, `MIN`, `IF` work.
  - `ISBLANK` never matches a blank Text input. Compare against the expected values instead
    (`Result != "Pass" && Result != "Fail"`). `ISBLANK` works on Date and Number. `ADDMONTHS` works.
- Decision matrix rows are data, not metadata. Deploy the definition as Draft, load rows with
  `POST /services/data/v66.0/connect/omnistudio/decision-matrices/<matrixId>/versions/<versionId>/rows`
  and body `{"rows":[{"rowData":{...}}]}` (a direct `CalculationMatrixRow` insert skips the hash key),
  then redeploy as Active. Row sources live in `data/decisionMatrices/*.csv`. Test with
  `POST /services/data/v66.0/actions/custom/runDecisionMatrix/<Name>`. An unmatched input returns blank outputs.
- Flow: an empty Text variable is null, and `CONTAINS(null, …)` is null, not false, so it fails an
  "equals false" check. Prefix the haystack: `CONTAINS(";" & {!varT_List}, …)`.
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
- Stop code test records in LSBC-Partial are named `StopCodeTest …` (a person, a salon, a school, and
  four Cosmetologist exams: national, practical, state and restoration).
  Reuse them; delete them before UAT data goes in.
- `force-app` holds only metadata this project owns. A full org retrieve sits in `reference/`
  (ignored by git) for lookups. Copy a file into `force-app` only when we change it.
