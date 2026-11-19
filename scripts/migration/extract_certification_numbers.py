#!/usr/bin/env python3
"""Copy the certification numbers that de-identification masked into the de-identified copy.

Usage: python3 -I extract_certification_numbers.py <raw lsbc.sqlite> <lsbc_deid.sqlite>

deidentify.py swaps every nine-digit value in a certificate number column for a mock, because
CLOSE once used social security numbers as certificate numbers. The Board (William, 19 Nov 2026)
confirmed that the nine-digit values now in APPLICANTS.OLD_CERT_NBR_NUM are generated numbers
(a counter plus the birth month and day), not SSNs, and that salon numbers are 77 plus a
counter. Those are licence numbers printed on the licences, so they are loaded.

This reads the raw export once and writes table CERTIFICATION_NUMBERS (legacy_key, kind, number)
into the de-identified copy, keyed on the crosswalk's legacy keys so nothing else in the copy
changes (rerunning deidentify.py would give every applicant ID a new mock). A number is kept only if:
- person (kind P): it is in OLD_CERT_NBR_NUM, is nine digits (the others are already in the copy),
  and ends in the person's birth month and day;
- shop (kind S): it is in SHOPS.OLD_SHOP_ID (the salon number; CERT_NBR_NUM, the shop's key, is
  usually the owner's applicant ID or the company's tax ID and is never loaded) and starts 77;
and in both cases it equals no applicant ID and no value in an SSN or tax ID column anywhere,
after padding to nine digits. Prints counts only, never a value.
"""
import re, sqlite3, sys

RAW, DEID = sys.argv[1], sys.argv[2]
src = sqlite3.connect(f"file:{RAW}?mode=ro", uri=True)
pad = lambda v: str(v).strip().zfill(9) if str(v).strip().isdigit() else None

# Every applicant ID and every value in an SSN or tax ID column, held in memory only.
sensitive = set()
SENSITIVE_COL = re.compile(r"APPLICANT_ID|SSN|TAXID")
for (t,) in src.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    for c in [r[1] for r in src.execute(f'PRAGMA table_info("{t}")')]:
        if SENSITIVE_COL.search(c.upper()):
            for (v,) in src.execute(f'SELECT DISTINCT "{c}" FROM "{t}" WHERE "{c}" IS NOT NULL'):
                p = pad(v)
                if p:
                    sensitive.add(p)
                    sensitive.add(str(v).strip())
print("applicant, SSN and tax ID values held", len(sensitive))

rows, counts = [], {"person kept": 0, "person no birthday match": 0, "person equals an ID": 0,
                    "shop kept": 0, "shop equals an ID": 0}
for key, num, dob in src.execute("""
        SELECT x.legacy_key, trim(a.OLD_CERT_NBR_NUM), a.APPLICANT_BIRTHDATE
        FROM APPLICANTS a JOIN XW_PERSON x ON x.src1 = a.APPLICANT_ID
        WHERE length(trim(a.OLD_CERT_NBR_NUM)) = 9 AND trim(a.OLD_CERT_NBR_NUM) GLOB '[0-9]*'"""):
    if not re.fullmatch(r"\d{9}", num):
        continue
    if not re.match(r"^\d{4}-\d\d-\d\d", dob or "") or num[-4:] != dob[5:7] + dob[8:10]:
        counts["person no birthday match"] += 1
    elif num in sensitive or pad(num) in sensitive:
        counts["person equals an ID"] += 1
    else:
        rows.append((key, "P", num))
        counts["person kept"] += 1
for key, num in src.execute("""
        SELECT x.legacy_key, trim(s.OLD_SHOP_ID)
        FROM SHOPS s JOIN XW_SHOP x ON x.src1 = s.CERT_NBR_NUM AND CAST(x.src2 AS INTEGER) = s.SEQ_NUM
        WHERE trim(s.OLD_SHOP_ID) LIKE '77%'"""):
    if not re.fullmatch(r"77\d+", num):
        continue
    if num in sensitive or pad(num) in sensitive:
        counts["shop equals an ID"] += 1
    else:
        rows.append((key, "S", num))
        counts["shop kept"] += 1
src.close()

dst = sqlite3.connect(DEID)
dst.execute("DROP TABLE IF EXISTS CERTIFICATION_NUMBERS")
dst.execute("CREATE TABLE CERTIFICATION_NUMBERS (legacy_key TEXT PRIMARY KEY, kind TEXT, number TEXT)")
dst.executemany("INSERT INTO CERTIFICATION_NUMBERS VALUES (?, ?, ?)", rows)
dst.commit()
print(counts)
print("rows written", len(rows))
