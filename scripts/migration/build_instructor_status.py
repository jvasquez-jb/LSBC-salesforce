#!/usr/bin/env python3
"""Build load/instructor_status.csv: Instructor Status and Master Instructor on instructor licences.

Usage: LSBC_MIGRATION_DIR=<working folder> python3 -I build_instructor_status.py <lsbc_deid.sqlite>

CLOSE keeps one status per person (APPLICANTS.INSTRUCTOR_STATUS): A active,
I inactive, M master. N and X are not yet explained by LSBC, so those and
blanks are left empty. The status goes on each of the person's migrated
instructor licences (keys ending -CI, -EI or -MI).
"""
import collections, csv, os, sqlite3, sys

root = os.environ["LSBC_MIGRATION_DIR"]
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
status = {xp[a]: (s or "").strip().upper() for a, s in db.execute("SELECT APPLICANT_ID, INSTRUCTOR_STATUS FROM APPLICANTS") if a in xp}
keys = [r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(root, "sf", "licence_keys.csv")))]
stats = collections.Counter()
with open(os.path.join(root, "load", "instructor_status.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "InstructorStatus__c", "IsMasterInstructor__c"])
    for lk in keys:
        holder, code = lk.rsplit("-", 1)
        if code not in ("CI", "EI", "MI"):
            continue
        s = status.get(holder, "")
        stats[s or "blank"] += 1
        if s == "A":
            w.writerow([lk, "Active", "false"])
        elif s == "I":
            w.writerow([lk, "Inactive", "false"])
        elif s == "M":
            w.writerow([lk, "", "true"])
print(dict(stats))
