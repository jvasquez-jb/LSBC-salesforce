#!/usr/bin/env python3
"""Certification numbers for migrated people and their licences, keyed on LegacyKey__c.

CLOSE keeps each person's licence number in APPLICANTS.OLD_CERT_NBR_NUM: the next value of a
counter followed by the person's birth month and day (MMDD), shared by every licence they hold.

load/person_certification_numbers.csv   Account upsert: CertificationNumber__pc
load/licence_certification_numbers.csv  BusinessLicense upsert: Identifier, on every migrated
                                        licence of a person who has a number: the number, a dash
                                        and the licence type code (1536380804-C). License Number is
                                        unique, so a person's licences can't share the bare number.
                                        The codes are the CLOSE type codes in the licence keys, the
                                        same as each licence type's Regulatory Auth Code

Only numbers that end in the person's birth month and day are loaded. Nine-digit numbers are
left out: they are shaped like Social Security numbers (the de-identified copy holds only mocks
for them), and the Board has not yet said whether they are SSNs. The script refuses to write any
nine-digit value. It prints the highest counter value loaded: the Certification Number Counter
must start above it.
"""
import csv, os, re, sqlite3
ROOT = os.environ.get("LSBC_MIGRATION_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("LSBC_DB", "lsbc.sqlite")  # lsbc_deid.sqlite: the de-identified copy
db = sqlite3.connect(os.path.join(ROOT, "extract", DB))
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
loaded = {r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(ROOT, "sf", "account_ids.csv")))}
lic = [r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(ROOT, "sf", "licence_keys.csv")))]

numbers, skipped = {}, {"nine_digit": 0, "no_birthday_match": 0, "not_loaded": 0}
for app, num, dob in db.execute("SELECT APPLICANT_ID, OLD_CERT_NBR_NUM, APPLICANT_BIRTHDATE FROM APPLICANTS WHERE OLD_CERT_NBR_NUM <> ''"):
    num = (num or "").strip()
    key = xp.get(app)
    if not re.fullmatch(r"\d{5,12}", num):
        continue
    if len(num) == 9:
        skipped["nine_digit"] += 1
    elif not re.match(r"^\d{4}-\d\d-\d\d", dob or "") or num[-4:] != dob[5:7] + dob[8:10]:
        skipped["no_birthday_match"] += 1
    elif key not in loaded:
        skipped["not_loaded"] += 1
    else:
        numbers[key] = num

for v in numbers.values():
    if len(v) == 9:
        raise SystemExit("refusing: a nine-digit value reached the load file")

with open(os.path.join(ROOT, "load", "person_certification_numbers.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "CertificationNumber__pc"])
    for k in sorted(numbers):
        w.writerow([k, numbers[k]])
n = 0
with open(os.path.join(ROOT, "load", "licence_certification_numbers.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "Identifier"])
    for k in sorted(lic):
        person, code = k.rsplit("-", 1)
        if person in numbers:
            w.writerow([k, f"{numbers[person]}-{code}"])
            n += 1
print("people with a certification number", len(numbers), "skipped", skipped)
print("licences given their holder's number", n)
print("highest counter value loaded", max(int(v[:-4]) for v in numbers.values()))
