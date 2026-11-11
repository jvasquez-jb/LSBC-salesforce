#!/usr/bin/env python3
"""Small follow-up updates for loaded records, keyed on LegacyKey__c.

load/person_duplicate_counts.csv  duplicate-licence count and last date per person
                                  (legacy LICENSES rows of type D)
load/instructor_ceu.csv           last CEU date on Instructor licences
                                  (APPLICANTS.CEU_LAST_DATE)
"""
import csv, os, sqlite3
ROOT = os.environ.get("LSBC_MIGRATION_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("LSBC_DB", "lsbc.sqlite")  # lsbc_deid.sqlite: the de-identified copy
db = sqlite3.connect(os.path.join(ROOT, "extract", DB))
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
loaded = {r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(ROOT, "sf", "account_ids.csv")))}
lic = {r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(ROOT, "load", "business_licenses.csv")))}
day = lambda s: (s or "")[:10] if "1990" <= (s or "")[:4] <= "2026" else ""
n = 0
with open(os.path.join(ROOT, "load", "person_duplicate_counts.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "DuplicateLicenseCount__pc", "LastDuplicateLicenseDate__pc"])
    for app, cnt, last in db.execute("""
        SELECT APP_APPLICANT_ID, COUNT(*), MAX(COALESCE(NULLIF(DATE_LAST_RENEWED, ''), DATE_CREATED))
        FROM LICENSES WHERE LT_LICENSE_TYPE = 'D' AND APP_APPLICANT_ID <> '' GROUP BY 1"""):
        k = xp.get(app)
        if k in loaded:
            w.writerow([k, cnt, day(last)])
            n += 1
print("people with duplicate-licence history", n)
n = 0
with open(os.path.join(ROOT, "load", "instructor_ceu.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "LastCEUDate__c"])
    for app, ceu in db.execute("SELECT APPLICANT_ID, CEU_LAST_DATE FROM APPLICANTS WHERE CEU_LAST_DATE <> ''"):
        d = day(ceu)
        for t in ("CI", "EI", "MI"):
            key = f"{xp.get(app)}-{t}"
            if d and key in lic:
                w.writerow([key, d])
                n += 1
print("instructor licences with a CEU date", n)
