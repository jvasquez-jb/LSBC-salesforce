#!/usr/bin/env python3
"""Certification numbers for migrated people, establishments and their licences, keyed on LegacyKey__c.

CLOSE keeps each person's licence number in APPLICANTS.OLD_CERT_NBR_NUM: the next value of a
counter followed by the person's birth month and day (MMDD), shared by every licence they hold.
A salon's number is SHOPS.OLD_SHOP_ID: 77 followed by digits, shared by the shop's licences
(its manager licence too). SHOPS.CERT_NBR_NUM, the shop's key in CLOSE, is usually the owner's
applicant ID or the company's tax ID and is never loaded. Schools have no number here.

load/person_certification_numbers.csv         Account upsert: CertificationNumber__pc
load/establishment_certification_numbers.csv  Account upsert: CertificationNumber__c
load/licence_certification_numbers.csv        BusinessLicense upsert: Identifier, on every migrated
                                              licence of a holder who has a number: the number, a
                                              dash and the licence type code (1536380804-C,
                                              779947960-SH). License Number is unique, so a
                                              holder's licences can't share the bare number

Person licence codes are the CLOSE type codes in the licence keys, the same as each licence type's
Regulatory Auth Code. Shop licence keys carry CLOSE codes that differ (AH for the facility, TM for a
manager), so shop licences take the code of their type in the org: sf/shop_licence_codes.csv, from
  sf data query -q "SELECT LegacyKey__c, RegulatoryAuthorizationType.RegulatoryAuthCode
                    FROM BusinessLicense WHERE LegacyKey__c LIKE 'LSBC-S-%'" --result-format csv

The de-identified copy masks every nine-digit value in a certificate column, so the nine-digit
person numbers and all salon numbers come from table CERTIFICATION_NUMBERS, which
extract_certification_numbers.py writes from the raw export after checking each one is a generated
number and equals no applicant ID, SSN or tax ID. Only person numbers that end in the person's birth
month and day are loaded. The script refuses to write any nine-digit value that is not in
CERTIFICATION_NUMBERS. It prints the highest counter values loaded: the Certification Number Counter
and the Establishment Number Counter must start above them.
"""
import csv, os, re, sqlite3
ROOT = os.environ.get("LSBC_MIGRATION_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("LSBC_DB", "lsbc.sqlite")  # lsbc_deid.sqlite: the de-identified copy
db = sqlite3.connect(os.path.join(ROOT, "extract", DB))
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
loaded = {r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(ROOT, "sf", "account_ids.csv")))}
lic = [r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(ROOT, "sf", "licence_keys.csv")))]
shop_codes = {r["LegacyKey__c"]: r["RegulatoryAuthorizationType.RegulatoryAuthCode"]
              for r in csv.DictReader(open(os.path.join(ROOT, "sf", "shop_licence_codes.csv")))}
extracted = {k: (kind, n) for k, kind, n in db.execute("SELECT legacy_key, kind, number FROM CERTIFICATION_NUMBERS")}
allowed_nine = {n for _, n in extracted.values()}

people, shops = {}, {}
skipped = {"nine_digit_not_extracted": 0, "no_birthday_match": 0, "not_loaded": 0}
for app, num, dob in db.execute("SELECT APPLICANT_ID, OLD_CERT_NBR_NUM, APPLICANT_BIRTHDATE FROM APPLICANTS WHERE OLD_CERT_NBR_NUM <> ''"):
    num = (num or "").strip()
    key = xp.get(app)
    if not re.fullmatch(r"\d{5,12}", num):
        continue
    if len(num) == 9:
        skipped["nine_digit_not_extracted"] += 1  # a mock: the real number, if loadable, is in CERTIFICATION_NUMBERS
    elif not re.match(r"^\d{4}-\d\d-\d\d", dob or "") or num[-4:] != dob[5:7] + dob[8:10]:
        skipped["no_birthday_match"] += 1
    elif key not in loaded:
        skipped["not_loaded"] += 1
    else:
        people[key] = num
for key, (kind, num) in extracted.items():
    if key in loaded:
        (people if kind == "P" else shops)[key] = num

for v in list(people.values()) + list(shops.values()):
    if len(v) == 9 and v not in allowed_nine:
        raise SystemExit("refusing: a nine-digit value not checked by extract_certification_numbers.py reached the load file")

def write(name, header, rows):
    with open(os.path.join(ROOT, "load", name), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)

write("person_certification_numbers.csv", ["LegacyKey__c", "CertificationNumber__pc"], sorted(people.items()))
write("establishment_certification_numbers.csv", ["LegacyKey__c", "CertificationNumber__c"], sorted(shops.items()))
rows = []
for k in sorted(lic):
    holder, code = k.rsplit("-", 1)
    if holder in people:
        rows.append([k, f"{people[holder]}-{code}"])
    elif holder in shops and shop_codes.get(k):
        rows.append([k, f"{shops[holder]}-{shop_codes[k]}"])
write("licence_certification_numbers.csv", ["LegacyKey__c", "Identifier"], rows)
print("people with a certification number", len(people), "skipped", skipped)
print("establishments with a certification number", len(shops))
print("licences given their holder's number", len(rows))
print("highest person counter value loaded", max(int(v[:-4]) for v in people.values()))
print("highest establishment number loaded", max(int(v) for v in shops.values()))
