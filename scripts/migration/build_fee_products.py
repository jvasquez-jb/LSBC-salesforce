#!/usr/bin/env python3
"""Build load/fee_products.csv: every CLOSE fee code as a Product, keyed on FeeCode__c.

Usage: python3 -I build_fee_products.py <lsbc_deid.sqlite> <load dir>

A fee code is active when it has a current fee schedule row (no end date).
Codes with no current row are loaded inactive, so historical fees can still
point at them. Amounts are not stored on the Product: the Fee Schedule
decision matrix prices the fees the system raises.
"""
import csv, os, re, sqlite3, sys

db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
out = os.path.join(sys.argv[2], "fee_products.csv")
current = {r[0].strip() for r in db.execute(
    "SELECT DISTINCT FC_FEE_ID FROM FEE_SCHEDULES WHERE (END_DATE IS NULL OR END_DATE = '') AND FC_FEE_ID IS NOT NULL")}
n = active = 0
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["FeeCode__c", "Name", "RevenueCode__c", "IsActive"])
    for code, desc, rev in db.execute("SELECT FEE_ID, DESCRIPTION, REVENUE_CODE FROM FEE_CODES ORDER BY FEE_ID"):
        code = (code or "").strip().upper()
        if not code:
            continue
        name = re.sub(r"\s+", " ", (desc or "").strip()) or f"Fee {code}"
        name = re.sub(r"Cosmetolgist", "Cosmetologist", name)  # CLOSE misspells two fee descriptions
        is_active = code in current
        w.writerow([code, name[:255], (str(rev).strip() if rev is not None else "")[:10], "true" if is_active else "false"])
        n += 1
        active += is_active
print(f"{out}: {n} fee codes, {active} active")
