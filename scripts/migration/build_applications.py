#!/usr/bin/env python3
"""Build the in-progress application load from CLOSE.

Usage (LSBC_MIGRATION_DIR=<folder>):
  python3 -I build_applications.py <deid> people        -> extract/application_ids.txt (people to load first)
  python3 -I build_applications.py <deid> applications  -> load/applications.csv (insert once)

CLOSE's APPLICATIONS table holds reciprocity and transfer applicants' details
(states licensed, hours, school, out-of-state licence number) with no status and
no licence type. An application dated on or after SINCE whose applicant holds no
current Louisiana licence is treated as still in progress; the rest became
licences. Each becomes a Reciprocity Individual Application, Submitted, with the
licence type read from the type of hours (cosmetology, manicuring, esthetics).
"""
import csv, os, re, sqlite3, sys

SINCE = "2025-11-11"
AS_OF = "2026-11-11"  # a licence expiring on or after this is current
root = os.environ["LSBC_MIGRATION_DIR"]
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
mode = sys.argv[2]
RECIPROCITY_RT = "012cp00000MfSuzAAF"  # LSBC-Partial; look it up in another org
STATES = {"AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California", "CO": "Colorado",
          "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia", "FL": "Florida", "GA": "Georgia",
          "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
          "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
          "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
          "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
          "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
          "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
          "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
          "WI": "Wisconsin", "WY": "Wyoming"}
TYPE = {"MAN": "Manicurist", "M": "Manicurist", "COS": "Cosmetologist", "C": "Cosmetologist",
        "EST": "Esthetician", "E": "Esthetician"}
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
rows = db.execute("""SELECT a.APP_APPLICANT_ID, a.APPLICATION_DATE, a.STATE_CURRENTLY_LICENSED, a.STATE_ORIGINALLY_LICENSED,
        a.TYPE_OF_HOURS_COMPLETED FROM APPLICATIONS a WHERE a.APPLICATION_DATE >= ? AND a.APPLICATION_DATE < '2027'
        AND NOT EXISTS (SELECT 1 FROM LICENSES l WHERE l.APP_APPLICANT_ID = a.APP_APPLICANT_ID
            AND l.EXPIRATION_DATE >= ? AND l.LT_LICENSE_TYPE NOT IN ('S', 'D'))""", (SINCE, AS_OF)).fetchall()
rows = [r for r in rows if r[0] in xp]

if mode == "people":
    with open(os.path.join(root, "extract", "application_ids.txt"), "w") as fh:  # mock IDs only
        fh.write("\n".join(sorted({r[0] for r in rows})) + "\n")
    print(f"{len(rows)} applications in progress")
else:
    ids = {r["LegacyKey__c"]: r["Id"] for r in csv.DictReader(open(os.path.join(root, "sf", "account_ids.csv")))}
    import json
    types = json.load(open(os.path.join(root, "sf", "auth_types.json")))
    with open(os.path.join(root, "load", "applications.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["RecordTypeId", "AccountId", "Category", "ApplicationType", "ApplicationPath__c", "Status",
                    "AppliedDate", "LicenseTypeId", "OriginatingState__c"])
        n = 0
        for a, d, cur, orig, hrs in rows:
            acct = ids.get(xp[a])
            if not acct:
                continue
            st = STATES.get((orig or cur or "").strip().upper(), "")
            w.writerow([RECIPROCITY_RT, acct, "License", "New", "Regular", "Submitted", f"{d[:10]}T17:00:00.000Z",
                        types[TYPE.get((hrs or "").strip().upper(), "Cosmetologist")], st])
            n += 1
    print(f"{n} applications")
