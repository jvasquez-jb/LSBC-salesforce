#!/usr/bin/env python3
"""Build load/mock_ssn.csv: each migrated person's mock social security number.

Usage: LSBC_MIGRATION_DIR=<working folder> python3 -I build_mock_ssn.py <lsbc_deid.sqlite>

Reads only the de-identified copy, where every applicant ID is already a
made-up number starting 000. Writes it as 000-12-3456 to the sandbox-only field
MockSocialSecurityNumber__pc, keyed on the person's LegacyKey__c. Refuses to
write any number that doesn't start 000. Sandbox only: in production the real
number goes in SocialSecurityNumber__pc once Shield is on.
"""
import csv, os, re, sqlite3, sys

root = os.environ["LSBC_MIGRATION_DIR"]
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
loaded = {r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(root, "sf", "account_ids.csv")))
          if r["PersonContactId"]}
n = 0
with open(os.path.join(root, "load", "mock_ssn.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "MockSocialSecurityNumber__pc"])
    for mock, key in db.execute("SELECT src1, legacy_key FROM XW_PERSON"):
        if key not in loaded:
            continue
        if not re.fullmatch(r"000\d{6}", mock or ""):
            sys.exit(f"{key}: not a mock number; stopping")
        w.writerow([key, f"{mock[:3]}-{mock[3:5]}-{mock[5:]}"])
        n += 1
print(f"{n} people")
