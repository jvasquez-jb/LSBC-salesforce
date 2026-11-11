# CLOSE data migration scripts

Tim Owens's scripts for the first load of CLOSE (the Board's legacy Oracle system) into LSBC-Partial,
10 Nov 2026. They read a local SQLite copy of the CLOSE export and write CSV load files keyed on
`LegacyKey__c`. Load the files with `sf data upsert bulk --external-id LegacyKey__c`.

The CLOSE export and the load files never go in this repo: they hold real licensee data, and the
export holds social security numbers. Keep them outside the repo folder.

| Script | Writes | Notes |
|---|---|---|
| `build_crosswalk.py` | Crosswalk tables in the local SQLite: CLOSE applicant, shop and school keys to `LSBC-P-`, `LSBC-S-`, `LSBC-SC-` keys | Keys are assigned in random order, so they can't be traced back to the CLOSE value. The crosswalk never goes to Salesforce |
| `build_person_accounts.py` | `person_accounts.csv` | People with a current licence. With an ID file argument, owners and managers of loaded salons who hold no current licence. Never writes the applicant ID, login, password, sex, race or comments |
| `build_business_accounts.py` | `establishment_accounts.csv`, `school_accounts.csv` | Active shops and schools, or those with a current licence. Parish comes from the ZIP code, blank when the ZIP spans parishes |
| `build_licenses.py` | `business_licenses.csv`, `held_licenses.csv` | One licence per holder and type, renewals rolled up. Types with no licence type in Salesforce go to the held file |
| `build_bonds.py` | `school_bonds.csv` | Every surety bond for a loaded school. End years 3000 to 9999 mean a continuous bond, capped at 4000-12-31 |

Before running against another org:

- Record type IDs are hard-coded for LSBC-Partial (`RT` in `build_business_accounts.py`,
  `PERSON_RT` in `build_person_accounts.py`). Look them up in the target org first.
- The scripts expect `extract/lsbc.sqlite`, `sf/` (org describes, `auth_types.json`,
  `us_states.json`) and `load/` next to the `scripts` folder, as in Tim's working folder.

Not here yet: the scripts for the owner, manager and booth renter relationships, the extra
owner and manager person accounts, the staff-set stop codes, duplicate licence counts and last CEU
dates. They are in Tim's working folder and were not in the export shared on 11 Nov.
