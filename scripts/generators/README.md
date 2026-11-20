# Generators for Phase 6 metadata

These scripts write metadata in `force-app`. Edit the script, run it, then deploy the output, so the
generated files stay consistent. Run with `python3 -I` from the repo root.

| Script | Writes | Run |
|---|---|---|
| `pagegen.py` | The 17 LSBC record pages (`flexipages/*RecordPage`), all in the Account Record Page format. The `PAGES` table lists each page's actions and tabs | `python3 -I scripts/generators/pagegen.py force-app/main/default/flexipages <describe dir>`; the describe dir holds `sf sobject describe -s <Object> --json` output per object, one `<Object>.json` each. An optional third argument limits it to some objects (`Account` or `Account,Case`) |
| `addresschange.py` | `ScreenFlowCaseAddressChangeRequest` (portal Change My Address) and `ScreenFlowCaseApplyAddressChange` (staff Apply Address Change on Case) | `python3 -I scripts/generators/addresschange.py force-app/main/default/flows` |
| `history.py` | Field history: `trackHistory` on the fields in its `FIELDS` table (writing a minimal file for standard fields) and `enableHistory` on Account, Contact and the custom objects. At most 20 fields per object; the social security number and date of birth are never tracked. Person custom fields (`__pc`) can't be tracked through metadata: tick them in Setup, Account, Set History Tracking | `python3 -I scripts/generators/history.py`, then deploy the files it lists |
| `portaltheme.py` | The portal's look: the LSBC LPI theme's custom CSS (`portal/theme.css`), the site footer (`portal/footer.html`), the home page body (`portal/home.html`), header, search and hero settings, and the branding set (colours, fonts, logo) | `python3 -I scripts/generators/portaltheme.py`, deploy `experiences/LSBC_LPI1` and the `Portal*` static resources, then `sf community publish --name "LSBC LPI"` |
| `flowlib.py` | Shared helpers for the flow generators below | (imported) |
| `recordpayment.py` | `ScreenFlowAccountRecordPayment` | `python3 -I scripts/generators/recordpayment.py force-app/main/default/flows` |
| `refund.py` | `ScreenFlowPaymentRefund` | as above |
| `letter.py` | `ScreenFlowLetterGenerate` | as above |
| `decide.py` | `ScreenFlowIndividualApplicationDecide` and `ScreenFlowBusinessLicenseApplicationDecide` | as above |
| `endstop.py` | `ScreenFlowRecordAlertEndStopCode` | as above |
| `markprinted.py` | `ScreenFlowBusinessLicenseMarkPrinted` | as above |
| `languages.py` | `ScreenFlowAccountPersonLanguages` (read-only list of a person's languages, on the Account page) | as above |
| `stopcodes.py` | `ScreenFlowAccountStopCodes` (read-only table of an account's stop codes, open first, on the Account page's Stop Codes tab; runs as the user, so a desk without stop code access sees a short message) | as above |
| `newapp.py` | `ScreenFlowAccountNewApplication` | as above |
| `newlicensure.py` | `ScreenFlowIndividualApplicationNewLicensure` (Completion and Initial License: the school's completion form, entered by staff from New Application) | as above |
| `security.py` | Phase 2 staff security from `docs/LSBC Access Matrix.xlsx`: the 18 permission sets, 13 desk permission set groups with their `<Desk>Muting` sets, the sharing rules, and the run mode and run restriction of the staff action flows. Field access comes from `security_fields.json` (every field the admin can be given access to; refresh it when fields are added). Rerun it after any flow generator above | `python3 -I scripts/generators/security.py`, then deploy `permissionsets`, `mutingpermissionsets`, `permissionsetgroups`, `sharingRules` and the staff flows |
| `portalaccess.py` | `SubflowPortalBusinessAccessSync` (portal Owners, Managers and School Administrators read their businesses through share records) and its trigger hooks: patches the relation, licence, fee, violation and user triggers to tick `Account.PortalAccessSyncPending__c`; skips a trigger already patched | `python3 -I scripts/generators/portalaccess.py force-app/main/default/flows` |
| `schoolforms.py` | The school portal forms from the Board's School Forms packet, filed by a School Administrator, and their portal pages (`experiences/LSBC_LPI1` routes and views). Built so far: `ScreenFlowIndividualApplicationStudentEnrollment` (`/student-enrollment`) | `python3 -I scripts/generators/schoolforms.py force-app/main/default/flows`, deploy the flows and `experiences/LSBC_LPI1`, then `sf community publish --name "LSBC LPI"` |
| `checklistgenerate.py` | `SubflowDocumentChecklistGenerate`: builds an application's document checklist from its Action Plan template (templates are loaded by `scripts/actionplans/load_templates.py` from `data/actionPlanTemplates/DocumentChecklists.csv`) | `python3 -I scripts/generators/checklistgenerate.py force-app/main/default/flows` |
| `staffintake.py` | One-off patch that added staff intake (`recordId`, staff flags) to the nine portal forms and three upload and payment flows. Already applied; it skips files it has patched | not needed again |

Portal form flows were written by `flowkit.py`, which is not in this repo.
