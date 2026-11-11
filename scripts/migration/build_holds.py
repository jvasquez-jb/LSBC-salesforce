#!/usr/bin/env python3
"""Build load/open_holds.csv: open legacy stop codes as RecordAlert rows.

Only codes whose category in the sandbox is described as "Set and ended by
staff" are written. The other codes are opened and ended by the sandbox's own
automation from the underlying data, so loading them would fight it. Open
codes with no category in the sandbox go to load/held_stop_codes.csv.
"""
import csv, json, os, sqlite3, collections
ROOT = os.environ.get("LSBC_MIGRATION_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("LSBC_DB", "lsbc.sqlite")  # lsbc_deid.sqlite: the de-identified copy
db = sqlite3.connect(os.path.join(ROOT, "extract", DB))
cats = json.load(open(os.path.join(ROOT, "sf", "alert_categories.json")))
ids = {r["LegacyKey__c"]: r["Id"] for r in csv.DictReader(open(os.path.join(ROOT, "sf", "account_ids.csv")))}
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
xs = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SHOP")}
xc = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SCHOOL")}
day = lambda s: (s or "")[:10] if "1990" <= (s or "")[:4] <= "2026" else ""
st, seen = collections.Counter(), set()
with open(os.path.join(ROOT, "load", "open_holds.csv"), "w", newline="") as fh, \
     open(os.path.join(ROOT, "load", "held_stop_codes.csv"), "w", newline="") as hh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["SourceSystemIdentifier", "WhatId", "RecordAlertCategoryId", "Subject", "Description",
                "Severity", "IsActive", "EffectiveDate", "ValidUntilDate"])
    hw = csv.writer(hh, lineterminator="\n")
    hw.writerow(["holder_key", "stop_code", "effective_date", "reason"])
    for seq, code, eff, created, app, sc, sq, hc, hq in db.execute("""
        SELECT SEQ_NUM, SC_STOP_CODE, EFFECTIVE_DATE, DATE_CREATED, APP_APPLICANT_ID,
               SHO_CERT_NBR_NUM, SHO_SEQ_NUM, SCH_CERT_NBR_NUM, SCH_SEQ_NUM
        FROM STOP_CODE_DETAILS WHERE END_DATE IS NULL OR END_DATE = '' ORDER BY SEQ_NUM"""):
        k = xp.get(app) if app else xs.get((sc, int(float(sq)))) if sc else xc.get((hc, int(float(hq)))) if hc else None
        if k not in ids:
            st["holder not loaded"] += 1
            continue
        code = int(float(code))
        cat = cats.get(f"StopCode{code:02d}")
        start = day(eff) or day(created)
        if not cat:
            hw.writerow([k, code, start, "no category in sandbox"])
            st[f"no category ({code})"] += 1
            continue
        if not (cat["desc"] or "").startswith("Set and ended by staff"):
            st["automatic code, left to the sandbox"] += 1
            continue
        key = f"{k}-SC{code:02d}-{int(float(seq))}"
        if key in seen or not start:
            st["skipped: duplicate key or no date"] += 1
            continue
        seen.add(key)
        w.writerow([key, ids[k], cat["id"], cat["label"], (cat["desc"] or "")[:255], "Error", "true",
                    f"{start}T12:00:00.000Z", "4000-12-31T00:00:00.000Z"])
        st[cat["label"]] += 1
for k, v in st.most_common():
    print(v, k)
