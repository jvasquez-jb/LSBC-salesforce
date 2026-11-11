#!/usr/bin/env python3
"""Build load/licence_statuses.csv: retired and deceased licensees' licences.

Usage: LSBC_MIGRATION_DIR=<working folder> python3 -I build_licence_statuses.py <lsbc_deid.sqlite>

CLOSE marks these with open stop codes 25 Licensee Retired and 26 Licensee
Deceased, and with the applicant's DECEASED flag. In Salesforce they are
licence statuses, not holds. Every migrated licence of such a holder is set to
Retired or Deceased (Deceased wins). Keyed on BusinessLicense.LegacyKey__c, which
starts with the holder's key.
"""
import csv, os, sqlite3, sys

root = os.environ["LSBC_MIGRATION_DIR"]
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
xs = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SHOP")}
xc = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SCHOOL")}

status = {}
for code, app, sc, sq, hc, hq in db.execute("""
        SELECT CAST(SC_STOP_CODE AS INTEGER), APP_APPLICANT_ID, SHO_CERT_NBR_NUM, SHO_SEQ_NUM, SCH_CERT_NBR_NUM, SCH_SEQ_NUM
        FROM STOP_CODE_DETAILS WHERE CAST(SC_STOP_CODE AS INTEGER) IN (25, 26) AND (END_DATE IS NULL OR END_DATE = '')"""):
    k = xp.get(app) if app else xs.get((sc, int(float(sq)))) if sc else xc.get((hc, int(float(hq)))) if hc else None
    if k:
        status[k] = "Deceased" if code == 26 or status.get(k) == "Deceased" else "Retired"
for (app,) in db.execute("SELECT APPLICANT_ID FROM APPLICANTS WHERE DECEASED = 'Y'"):
    if app in xp:
        status[xp[app]] = "Deceased"

licences = [r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(root, "sf", "licence_keys.csv")))]
n = 0
with open(os.path.join(root, "load", "licence_statuses.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "Status"])
    for lk in licences:
        holder = lk.rsplit("-", 1)[0]
        if holder in status:
            w.writerow([lk, status[holder]])
            n += 1
print(f"{len(status)} retired or deceased holders in CLOSE, {n} migrated licences to update")
