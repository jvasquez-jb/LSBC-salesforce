# Generators for Phase 6 metadata

These scripts write metadata in `force-app`. Edit the script, run it, then deploy the output, so the
generated files stay consistent. Run with `python3 -I` from the repo root.

| Script | Writes | Run |
|---|---|---|
| `pagegen.py` | The 17 LSBC record pages (`flexipages/*RecordPage`), all in the Account Record Page format. The `PAGES` table lists each page's actions and tabs | `python3 -I scripts/generators/pagegen.py force-app/main/default/flexipages <describe dir>`; the describe dir holds `sf sobject describe -s <Object> --json` output per object, one `<Object>.json` each. An optional third argument limits it to some objects (`Account` or `Account,Case`) |
| `flowlib.py` | Shared helpers for the flow generators below | (imported) |
| `recordpayment.py` | `ScreenFlowAccountRecordPayment` | `python3 -I scripts/generators/recordpayment.py force-app/main/default/flows` |
| `refund.py` | `ScreenFlowPaymentRefund` | as above |
| `letter.py` | `ScreenFlowLetterGenerate` | as above |
| `decide.py` | `ScreenFlowIndividualApplicationDecide` and `ScreenFlowBusinessLicenseApplicationDecide` | as above |
| `endstop.py` | `ScreenFlowRecordAlertEndStopCode` | as above |
| `markprinted.py` | `ScreenFlowBusinessLicenseMarkPrinted` | as above |
| `languages.py` | `ScreenFlowAccountPersonLanguages` (read-only list of a person's languages, on the Account page) | as above |
| `newapp.py` | `ScreenFlowAccountNewApplication` | as above |
| `newlicensure.py` | `ScreenFlowIndividualApplicationNewLicensure` (Completion and Initial License: the school's completion form, entered by staff from New Application) | as above |
| `staffintake.py` | One-off patch that added staff intake (`recordId`, staff flags) to the nine portal forms and three upload and payment flows. Already applied; it skips files it has patched | not needed again |

Portal form flows were written by `flowkit.py`, which is not in this repo.
