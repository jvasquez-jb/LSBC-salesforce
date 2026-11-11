#!/usr/bin/env python3
"""Build the fee and payment load from CLOSE: open balances plus three years of payments.

Usage (LSBC_MIGRATION_DIR=<folder>, run in order, loading each file before the next step):
  python3 -I build_fees.py <deid> fees         -> load/fees.csv          (insert)
  python3 -I build_fees.py <deid> items        -> load/fee_items.csv     (needs sf/fee_ids.csv)
  python3 -I build_fees.py <deid> payments     -> load/payments.csv      (insert)
  python3 -I build_fees.py <deid> allocations  -> load/allocations.csv   (needs sf/item_ids.csv, sf/payment_ids.csv)

Scope, for people and businesses already migrated:
- every CLOSE charge (FINANCIAL_SUMMARIES row) with money still owed, and
- every charge paid by a receipt dated on or after SINCE, with those receipts.
One fee and one fee item per charge. The item's amount is what is still owed
plus what the loaded receipts paid toward it, so its balance in Salesforce is
CLOSE's balance; payments before SINCE are not loaded. A credit balance counts as
nothing owed. Open balances get no due date: they show and can be paid, but
raise no Non Payment hold until finance gives them one.
Each receipt line becomes an allocation from its payment to the charge it paid.
Lines with no charge, for a holder not migrated, or of zero or less are left out,
so that part of a receipt shows as unapplied.
Keys: the fee's Comments start "CLOSE charge <n>"; the item's Calculation Info is
CLOSE-FS-<n>; the payment's External Reference is CLOSE-R-<receipt>.
"""
import collections, csv, json, os, sqlite3, sys

SINCE = "2023-11-11"
root = os.environ["LSBC_MIGRATION_DIR"]
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
mode = sys.argv[2]
out = lambda name: open(os.path.join(root, "load", name), "w", newline="")
read = lambda name: list(csv.DictReader(open(os.path.join(root, "sf", name))))

ids = {r["LegacyKey__c"]: r["Id"] for r in read("account_ids.csv")}
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
xs = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SHOP")}
xc = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SCHOOL")}


def holder(app, sc, sq, hc, hq):
    if app:
        return xp.get(app)
    if sc and sq is not None:
        return xs.get((sc, int(float(sq))))
    if hc and hq is not None:
        return xc.get((hc, int(float(hq))))


seq = lambda v: str(int(float(v))) if v not in (None, "") else ""

# Receipt lines in the window, for migrated holders, that point at a charge.
lines = []
for r in db.execute("""SELECT TRANS_DETAIL_SEQ_NUM, LFT_RECEIPT_NUMBER, FS1_SEQ_NUM, TRANS_AMT, YEAR_PAYMENT_FOR,
        APP_APPLICANT_ID, SHO_CERT_NBR_NUM, SHO_SEQ_NUM, SCH_CERT_NBR_NUM, SCH_SEQ_NUM
        FROM LICENSE_FINANCIAL_DETAILS WHERE TRANS_DATE >= ?""", (SINCE,)):
    h = holder(*r[5:10])
    if h in ids:
        lines.append(dict(line=seq(r[0]), receipt=str(r[1] or "").strip(), fs=seq(r[2]), amt=r[3] or 0,
                          year=seq(r[4]), holder=h))
paid = collections.Counter()
for l in lines:
    if l["fs"] and l["amt"] > 0:
        paid[l["fs"]] += l["amt"]

# Charges in scope.
charges = {}
for s, fcode, year, st, owed, created, app, sc, sq, hc, hq in db.execute("""SELECT SEQ_NUM, FCODE, LAST_PAYMENT_YEAR,
        STATUS, AMT_OWED, DATE_CREATED, APP_APPLICANT_ID, SHO_CERT_NBR_NUM, SHO_SEQ_NUM, SCH_CERT_NBR_NUM, SCH_SEQ_NUM
        FROM FINANCIAL_SUMMARIES"""):
    s = seq(s)
    owed = max(owed or 0, 0)
    if not (owed > 0 or s in paid):
        continue
    h = holder(app, sc, sq, hc, hq)
    if h not in ids:
        continue
    charges[s] = dict(fcode=(fcode or "").strip().upper(), year=seq(year), owed=owed, paid=round(paid[s], 2),
                      created=(created or "")[:10], holder=h)

if mode == "fees":
    with out("fees.csv") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["AccountId", "Status", "CalculationDate", "Comments"])
        for s, c in charges.items():
            status = "PAID" if c["owed"] <= 0 else ("PARTIALLY_PAID" if c["paid"] > 0 else "DUE")
            calc = f"{c['created']}T17:00:00.000Z" if c["created"][:2] in ("19", "20") else ""
            w.writerow([ids[c["holder"]], status, calc,
                        f"CLOSE charge {s}, fee code {c['fcode'] or 'none'}. Migrated: balance owed in CLOSE plus payments since {SINCE}."])
    print(f"{len(charges)} fees, {sum(c['owed'] > 0 for c in charges.values())} with money owed "
          f"(${sum(c['owed'] for c in charges.values()):,.2f})")

elif mode == "items":
    fee = {}
    for r in read("fee_ids.csv"):
        fee[r["Comments"].split(",")[0].replace("CLOSE charge ", "")] = r["Id"]
    product = {r["FeeCode__c"]: (r["Id"], r["Name"]) for r in read("products.csv")}
    with out("fee_items.csv") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["RegulatoryTrxnFeeId", "Name", "FeeAmount", "FeeProduct__c", "ForYear__c", "CalculationInfo"])
        n = 0
        for s, c in charges.items():
            if s not in fee:
                continue
            pid, pname = product.get(c["fcode"], ("", f"Fee {c['fcode'] or 'without a code'}"))
            w.writerow([fee[s], pname[:80], round(c["owed"] + c["paid"], 2), pid, c["year"], f"CLOSE-FS-{s}"])
            n += 1
    print(f"{n} fee items")

elif mode == "payments":
    method = {"C": "Check", "M": "Money Order", "X": "Cashiers Check", "CC": "Card", "EC": "Check"}
    first_holder = {}
    for l in lines:
        first_holder.setdefault(l["receipt"], l["holder"])
    with out("payments.csv") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["Account__c", "Amount__c", "ReceivedDate__c", "Method__c", "CheckDate__c", "PayerName__c",
                    "ExternalReference__c", "Status__c"])
        n = 0
        for r, amt, d, mode_, cd, payor, nsf in db.execute("""SELECT RECEIPT_NUMBER, TRANS_AMT, TRANS_DATE, PM_PAYMENT_CODE,
                CHECK_MO_DATE, PAYOR, NSF FROM LICENSE_FINANCIAL_TRANSACTIONS WHERE TRANS_DATE >= ?""", (SINCE,)):
            r = str(r or "").strip()
            if r not in first_holder or not amt or amt <= 0:
                continue
            cd = (cd or "")[:10]
            w.writerow([ids[first_holder[r]], round(amt, 2), d[:10], method.get((mode_ or "").strip(), ""),
                        cd if cd[:2] in ("19", "20") else "", (payor or "").strip()[:120], f"CLOSE-R-{r}",
                        "Returned" if nsf == "Y" else "Completed"])
            n += 1
    print(f"{n} payments")

elif mode == "allocations":
    item = {r["CalculationInfo"].replace("CLOSE-FS-", ""): r["Id"] for r in read("item_ids.csv")}
    pay = {r["ExternalReference__c"].replace("CLOSE-R-", ""): r["Id"] for r in read("payment_ids.csv")}
    st = collections.Counter()
    with out("allocations.csv") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["Payment__c", "FeeItem__c", "Amount__c", "ForYear__c"])
        for l in lines:
            if l["amt"] <= 0:
                st["zero or less"] += 1
            elif l["fs"] not in item:
                st["no charge"] += 1
            elif l["receipt"] not in pay:
                st["payment not loaded"] += 1
            else:
                w.writerow([pay[l["receipt"]], item[l["fs"]], round(l["amt"], 2), l["year"]])
                st["loaded"] += 1
    print(dict(st))
