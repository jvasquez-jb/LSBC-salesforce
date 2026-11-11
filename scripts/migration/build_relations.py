#!/usr/bin/env python3
"""Build salon and school relationships (AccountContactRelation).

Sources:
  Owner              SHOPS.APP_APPLICANT_ID / SCHOOLS.APP_APPLICANT_ID
  Manager            MANAGER_LICENSE_NUM on the salon's latest inspection since 2021
  Assistant Manager  ASST_MANAGER_LICENSE_NUM on that same inspection
  Booth Renter       BOOTHS rows backed by a current booth licence

Phase "ids": writes extract/extra_person_ids.txt, the related people who are
not yet loaded (the file holds legacy IDs, so it stays under extract/).
Phase "csv": writes load/account_contact_relations.csv using Salesforce IDs
from sf/account_ids.csv. One row per salon and person; roles are combined.
"""
import csv, os, sqlite3, sys, collections

ROOT = os.environ.get("LSBC_MIGRATION_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("LSBC_DB", "lsbc.sqlite")  # lsbc_deid.sqlite: the de-identified copy
AS_OF = "2026-11-09"
phase = sys.argv[1]
db = sqlite3.connect(os.path.join(ROOT, "extract", DB))
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
xs = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SHOP")}
xc = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SCHOOL")}
ids = {r["LegacyKey__c"]: r for r in csv.DictReader(open(os.path.join(ROOT, "sf", "account_ids.csv")))}

day = lambda s: (s or "")[:10] if "1950" <= (s or "")[:4] <= "2026" else ""
rel = {}  # (business key, applicant id) -> {roles, start}
def add(bk, app, role, start=""):
    if bk in ids and app in xp:
        r = rel.setdefault((bk, app), dict(roles=[], start=""))
        if role not in r["roles"]:
            r["roles"].append(role)
        if start and (not r["start"] or start < r["start"]):
            r["start"] = start

for c, q, a, opened in db.execute("SELECT CERT_NBR_NUM, SEQ_NUM, APP_APPLICANT_ID, OPEN_DATE FROM SHOPS WHERE APP_APPLICANT_ID <> ''"):
    add(xs.get((c, int(q))), a, "Owner", day(opened))
for c, q, a, opened in db.execute("SELECT CERT_NBR_NUM, SEQ_NUM, APP_APPLICANT_ID, OPEN_DATE FROM SCHOOLS WHERE APP_APPLICANT_ID <> ''"):
    add(xc.get((c, int(q))), a, "Owner", day(opened))

latest = {}
for c, q, d, m, am in db.execute("""
    SELECT SHO_CERT_NBR_NUM, SHO_SEQ_NUM, INSPECTION_DATE, MANAGER_LICENSE_NUM, ASST_MANAGER_LICENSE_NUM
    FROM INSPECTIONS WHERE SHO_CERT_NBR_NUM <> '' AND INSPECTION_DATE >= '2021-01-01'
      AND INSPECTION_DATE < '2026-11-11' AND MANAGER_LICENSE_NUM <> ''
    ORDER BY INSPECTION_DATE"""):
    latest[(c, int(float(q)))] = (d, m, am)
txt = lambda v: "" if v is None else str(v).strip()
for key, (d, m, am) in latest.items():
    add(xs.get(key), txt(m), "Manager")
    if txt(am) and txt(am) != txt(m):
        add(xs.get(key), txt(am), "Assistant Manager")

for c, q, a, rented in db.execute(f"""
    SELECT b.SHO_CERT_NBR_NUM, b.SHO_SEQ_NUM, b.APP_APPLICANT_ID, b.DATE_RENTED FROM BOOTHS b
    WHERE EXISTS (SELECT 1 FROM LICENSES l WHERE l.BOO_SEQ_NUM = b.SEQ_NUM
        AND l.APP_APPLICANT_ID = b.APP_APPLICANT_ID AND l.EXPIRATION_DATE >= '{AS_OF}'
        AND l.EXPIRATION_DATE < '2030-01-01')"""):
    add(xs.get((c, int(float(q)))), a, "Booth Renter", day(rented))

roles = collections.Counter(r for v in rel.values() for r in v["roles"])
missing = sorted({a for (_, a) in rel if xp[a] not in ids})
print("relationships", len(rel), dict(roles), "people not yet loaded", len(missing))
if phase == "ids":
    with open(os.path.join(ROOT, "extract", "extra_person_ids.txt"), "w") as fh:
        fh.write("\n".join(missing) + "\n")
else:
    n = 0
    with open(os.path.join(ROOT, "load", "account_contact_relations.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["AccountId", "ContactId", "Roles", "IsActive", "StartDate"])
        for (bk, a), v in sorted(rel.items(), key=lambda kv: (kv[0][0], xp[kv[0][1]])):
            p = ids.get(xp[a])
            if not p or not p["PersonContactId"]:
                continue
            w.writerow([ids[bk]["Id"], p["PersonContactId"], ";".join(v["roles"]), "true", v["start"]])
            n += 1
    print("rows written", n)
