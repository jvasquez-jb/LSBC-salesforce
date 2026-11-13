#!/usr/bin/env python3
"""Small follow-up updates for loaded records, keyed on LegacyKey__c.

load/licence_last_duplicates.csv  last duplicate date per licence (legacy LICENSES rows of
                                  type D; the fee code says which licence was duplicated)
load/person_close_affidavits.csv  people whose CLOSE comments record an affidavit, so their
                                  free first affidavit is used
load/instructor_ceu.csv           last CEU date on Instructor licences
                                  (APPLICANTS.CEU_LAST_DATE)
"""
import csv, os, re, sqlite3
ROOT = os.environ.get("LSBC_MIGRATION_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("LSBC_DB", "lsbc.sqlite")  # lsbc_deid.sqlite: the de-identified copy
db = sqlite3.connect(os.path.join(ROOT, "extract", DB))
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
loaded = {r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(ROOT, "sf", "account_ids.csv")))}
lic = {r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(ROOT, "sf", "licence_keys.csv")))}  # every migrated licence
day = lambda s: (s or "")[:10] if "1990" <= (s or "")[:4] <= "2026" else ""
# A duplicate's fee code names the licence it duplicated. Code 91 is the generic
# duplicate fee used before 2001: too old to fall in any current renewal period.
DUP_TYPE = {"AG": "C", "AN": "M", "AU": "E", "BD": "CI", "BV": "EI", "BM": "MI",
            "CU": "MB", "CY": "MU", "CZ": "AH", "DC": "B"}
last_dup = {}
for app, fee, created in db.execute("""
    SELECT APP_APPLICANT_ID, FC_FEE_ID, DATE_CREATED FROM LICENSES
    WHERE LT_LICENSE_TYPE = 'D' AND APP_APPLICANT_ID <> '' AND (VOID_LICENSE IS NULL OR VOID_LICENSE <> 'Y')"""):
    key = f"{xp.get(app)}-{DUP_TYPE.get(fee, '')}"
    d = day(created)
    if fee in DUP_TYPE and key in lic and d > last_dup.get(key, ""):
        last_dup[key] = d
with open(os.path.join(ROOT, "load", "licence_last_duplicates.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "LastDuplicateDate__c"])
    for k in sorted(last_dup):
        w.writerow([k, last_dup[k]])
print("licences with a duplicate in CLOSE", len(last_dup))

# CLOSE kept no affidavit count: staff noted each one in the applicant's comments
# ("Cert mailed to TX 01/01/23", older "Aff mailed" or "Affidavit mailed" with a date
# and initials). Notes about marriage certificates are not affidavits.
AFF = re.compile(r"(?i)\baff(id|\.|\b)|\bcert(ification)?(\s+letter)?\.?\s*(mailed|mail|faxed|sent|emailed)\b|\bmailed\s+(cert|aff)")
n = 0
with open(os.path.join(ROOT, "load", "person_close_affidavits.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "HasCloseAffidavit__pc"])
    for app, text in db.execute("SELECT APPLICANT_ID, COMMENTS FROM APPLICANTS WHERE COMMENTS <> ''"):
        k = xp.get(app)
        if k in loaded and AFF.search(re.sub(r"(?i)marriage cert\w*", "", text)):
            w.writerow([k, "true"])
            n += 1
print("people with an affidavit in CLOSE", n)
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
