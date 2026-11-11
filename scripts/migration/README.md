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

## Before running against another org

- Record type IDs are hard-coded for LSBC-Partial (`RT` in `build_business_accounts.py`,
  `PERSON_RT` in `build_person_accounts.py`). Look them up in the target org first.
- Rebuild everything in `sf/` from the target org.
