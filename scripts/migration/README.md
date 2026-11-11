# CLOSE data migration scripts

Tim Owens's scripts for the first load of CLOSE (the Board's legacy Oracle system) into LSBC-Partial,
10 Nov 2026. They read a local SQLite copy of the CLOSE export and write CSV load files keyed on
`LegacyKey__c`. Load the files with `sf data upsert bulk --external-id LegacyKey__c`.

The CLOSE export and the load files never go in this repo: they hold real licensee data, and the
export holds social security numbers. Keep them outside the repo folder.

## Layout

The scripts expect this working folder, with `scripts/` beside the others:

| Folder | Holds |
|---|---|
| `extract/` | The parsed export (`<SCHEMA>.<TABLE>.csv`, `inventory.json`) and `lsbc.sqlite` |
| `sf/` | Files pulled from the target org: `account_ids.csv` (`LegacyKey__c`, `Id`, `PersonContactId` of every loaded account), `alert_categories.json` (stop code categories by developer name: id, label, description), `auth_types.json` (licence type name to Id), `describe_Account.json` (`sf sobject describe -s Account --json`), `us_states.json` |
| `load/` | The CSV load files the scripts write |

Refresh `sf/account_ids.csv` after every account load: the relationship, hold and enrichment
scripts only write rows for accounts already in the org.

## Order

| Step | Script | Writes | Notes |
|---|---|---|---|
| 1 | `extract_exp.py <dump> extract` | `extract/*.csv`, `inventory.json` | Parses the Oracle 9.2 `exp` dump |
| 2 | `load_sqlite.py` | `extract/lsbc.sqlite` | Run from the working folder. Skips Oracle Enterprise Manager tables |
| 3 | `build_crosswalk.py` | Crosswalk tables in `lsbc.sqlite` | CLOSE applicant, shop and school keys to `LSBC-P-`, `LSBC-S-`, `LSBC-SC-` keys, assigned in random order so they can't be traced back. The crosswalk never goes to Salesforce |
| 4 | `build_person_accounts.py` | `person_accounts.csv` | People with a current licence. Never writes the applicant ID, login, password, sex, race or comments |
| 5 | `build_business_accounts.py` | `establishment_accounts.csv`, `school_accounts.csv` | Active shops and schools, or those with a current licence. Parish from the ZIP code, blank when the ZIP spans parishes |
| 6 | `build_licenses.py` | `business_licenses.csv`, `held_licenses.csv` | One licence per holder and type, renewals rolled up. Types with no licence type in Salesforce go to the held file |
| 7 | `build_relations.py ids`, then `build_person_accounts.py extract/extra_person_ids.txt extra_people.csv`, then `build_relations.py csv` | `account_contact_relations.csv` | Owners from the shop or school, managers from the latest inspection since 2021, booth renters backed by a current booth licence. The `ids` step finds related people not yet loaded; load them before the `csv` step |
| 8 | `build_bonds.py` | `school_bonds.csv` | Every surety bond for a loaded school. End years 3000 to 9999 mean a continuous bond, capped at 4000-12-31 |
| 9 | `build_holds.py` | `open_holds.csv`, `held_stop_codes.csv` | Open CLOSE stop codes, only for categories described "Set and ended by staff". Salesforce raises the other codes itself |
| 10 | `build_enrichment.py` | `person_duplicate_counts.csv`, `instructor_ceu.csv` | Duplicate licence count and last date per person; last CEU date on instructor licences |

`read_office.py` prints the text of a `.pptx` or `.xlsx`, used to read the design files.

## De-identified copy and reference data (from 11 Nov 2026)

Salesforce Shield isn't on yet, so nothing after the swap below reads a real social security
number. Our working folder is `../LSBC-Migration` (beside this repo): `extract/lsbc_deid.sqlite`,
`sf/`, `load/`.

| Script | Writes | Notes |
|---|---|---|
| `deidentify.py <lsbc.sqlite> <lsbc_deid.sqlite>` | The de-identified copy | Run once on the raw export. Every applicant ID, certificate number, SSN and tax ID column, and any nine-digit number in free text, becomes a mock starting `000` (an area the SSA never issues); the same real value always gets the same mock, so joins still work. So do the 25 applicant IDs that are 7, 8 or 10 digits (an SSN that lost a leading zero or gained a digit) wherever a whole value equals one. Receipt, cheque, deposit and phone numbers keep their values unless they match a known ID. Logins and passwords are blanked. The real-to-mock mapping is never written. Prints counts only and fails if any real ID is left |
| `build_fee_products.py <deid> <load dir>` | `fee_products.csv` | All 621 CLOSE fee codes as Products, upserted on `FeeCode__c`. Active when the code has a current amount (563) |
| `build_mock_ssn.py <deid>` | `mock_ssn.csv` | Each migrated person's mock number as 000-12-3456, for the sandbox-only Mock Social Security Number. Upsert on Account `LegacyKey__c`. Needs the sandbox-only permission set Sandbox Mock Data. Refuses any number not starting 000 |
| `refresh_sf_inputs.py <working folder>` | `sf/auth_types.json`, `account_ids.csv`, `alert_categories.json`, `describe_Account.json`, `us_states.json` | Pulls them from the default org. Rerun after every account load and after licence types or stop codes change |
| `build_licence_statuses.py <deid>` | `licence_statuses.csv` | Licences of holders CLOSE marks retired (code 25) or deceased (code 26, or the deceased flag) get that status. Needs `sf/licence_keys.csv` (every migrated licence's `LegacyKey__c`) |
| `build_violations.py <deid> <load dir> <authority Id>` | `regulatory_codes.csv`, `violation_types.csv` | 123 statute citations and 38 violations in CLOSE's 4 categories. Inserts: load once |

Tim's scripts read `extract/$LSBC_DB` under `$LSBC_MIGRATION_DIR`: run them with
`LSBC_MIGRATION_DIR=../LSBC-Migration LSBC_DB=lsbc_deid.sqlite`. `build_licenses.py` also takes
`LSBC_ONLY_TYPES` (licence type names separated by `;`) to write only those types. It maps CLOSE's
three instructor licences to their own types, and Manager (held by the shop in CLOSE),
Microdermabrasion and Make-up Application. The mock IDs replace the real ones in the crosswalk too, so the `LSBC-` keys
already in Salesforce still match.

## Before running against another org

- Record type IDs are hard-coded for LSBC-Partial (`RT` in `build_business_accounts.py`,
  `PERSON_RT` in `build_person_accounts.py`). Look them up in the target org first.
- Rebuild everything in `sf/` from the target org.
