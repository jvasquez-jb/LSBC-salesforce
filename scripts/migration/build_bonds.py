#!/usr/bin/env python3
"""Build load/school_bonds.csv: surety bonds (Accreditation) for loaded schools.

Every bond on file for a loaded school is written, so the history is kept.
Status is Active when the bond covers AS_OF, otherwise Expired. Far-future end
dates (years 3000 to 9999) are how the source marks a continuous bond; they
are kept, capped at 4000-12-31, because the hold automation treats a blank
end date as no cover. The bond number
is kept in the Name only: it repeats across renewals, and the sandbox requires
SourceSystemIdentifier to be unique.
"""
import csv, os, sqlite3, collections
ROOT = os.environ.get("LSBC_MIGRATION_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("LSBC_DB", "lsbc.sqlite")  # lsbc_deid.sqlite: the de-identified copy
AS_OF = "2026-11-10"
db = sqlite3.connect(os.path.join(ROOT, "extract", DB))
xc = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SCHOOL")}
loaded = {r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(ROOT, "load", "school_accounts.csv")))}
day = lambda s, lo, hi: (s or "")[:10] if lo <= (s or "")[:4] <= hi else ""
seq, st = collections.Counter(), collections.Counter()
with open(os.path.join(ROOT, "load", "school_bonds.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "Name", "Account.LegacyKey__c", "Type", "Status", "AccreditingBody",
                "EffectiveFrom", "EffectiveTo", "Underwriter__c"])
    for num, uw, eff, end, c, q in db.execute("""
        SELECT BOND_NUMBER, UNDERWRITER, EFFECTIVE_DATE, END_DATE, SCH_CERT_NBR_NUM, SCH_SEQ_NUM
        FROM BONDS ORDER BY SCH_CERT_NBR_NUM, SCH_SEQ_NUM, EFFECTIVE_DATE, DATE_CREATED, BOND_NUMBER"""):
        k = xc.get((c, int(float(q)))) if c else None
        if k not in loaded:
            st["school not loaded"] += 1
            continue
        seq[k] += 1
        f, t = day(eff, "1950", "2026"), day(end, "1950", "4000")
        if (end or "")[:4] > "4000":
            t = "4000-12-31"  # latest date Salesforce accepts
        active = (not f or f <= AS_OF) and (not t or t >= AS_OF)
        if not f:
            st["no usable start date"] += 1
        num = "" if num is None else str(num).strip()
        w.writerow([f"{k}-B-{seq[k]:03d}", f"Surety Bond {num}".strip(), k, "Surety Bond",
                    "Active" if active else "Expired", "", f, t, (uw or "").strip()[:120]])
        st["Active" if active else "Expired"] += 1
print(dict(st), "schools with an active bond", "see query")
