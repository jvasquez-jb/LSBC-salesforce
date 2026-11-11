#!/usr/bin/env python3
"""Build load/establishment_accounts.csv and load/school_accounts.csv.

Scope: shops and schools that are active or hold a current licence. Keyed on
the abstracted LegacyKey__c (XW_SHOP / XW_SCHOOL). Certificate numbers, owner
names, USERID, PWD and comments are not written: some certificate numbers are
the owner's SSN.
"""
import csv, json, os, re, sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AS_OF = "2026-11-09"
RT = {"SHOPS": "012cp00000MfMxZAAV", "SCHOOLS": "012cp00000MfMxbAAF"}
db = sqlite3.connect(os.path.join(ROOT, "extract", "lsbc.sqlite"))
db.row_factory = sqlite3.Row
us_states = set(json.load(open(os.path.join(ROOT, "sf", "us_states.json"))))
acct = json.load(open(os.path.join(ROOT, "sf", "describe_Account.json")))["result"]
parishes = [p["value"] for f in acct["fields"] if f["name"] == "Parish__c"
            for p in f["picklistValues"] if p["active"]]
norm = lambda s: re.sub(r"[^a-z]", "", (s or "").lower().replace("saint", "st"))
parish_by_norm = {norm(p): p for p in parishes}
zip_parish = {}
for z, d in db.execute("SELECT ZIP, DESCRIPTION FROM PARISHES"):
    m = parish_by_norm.get(norm(d))
    if m:
        zip_parish.setdefault(z, set()).add(m)
zip_parish = {z: next(iter(v)) for z, v in zip_parish.items() if len(v) == 1}


def clean(s, n=None):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s[:n] if n else s


def phone(s):
    d = re.sub(r"\D", "", s or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else ""


def zipcode(z, z4):
    z, z4 = re.sub(r"\D", "", z or ""), re.sub(r"\D", "", z4 or "")
    if len(z) != 5:
        return ""
    return f"{z}-{z4}" if len(z4) == 4 else z


COLS = ["LegacyKey__c", "RecordTypeId", "Name", "BillingStreet", "BillingCity",
        "BillingStateCode", "BillingPostalCode", "BillingCountryCode", "Parish__c", "Phone"]


def build(table, xw, pfx, outfile):
    ents = db.execute(f"""
        SELECT t.CERT_NBR_NUM c, t.SEQ_NUM s, x.legacy_key k, t.NAME name, t.COMPANY_NAME company
        FROM {table} t JOIN {xw} x ON x.src1 = t.CERT_NBR_NUM AND CAST(x.src2 AS INTEGER) = t.SEQ_NUM
        WHERE t.STATUS = 'Y' OR EXISTS (
            SELECT 1 FROM LICENSES l WHERE l.{pfx}_CERT_NBR_NUM = t.CERT_NBR_NUM
              AND l.{pfx}_SEQ_NUM = t.SEQ_NUM AND l.EXPIRATION_DATE >= '{AS_OF}'
              AND l.EXPIRATION_DATE < '2030-01-01')
        ORDER BY x.legacy_key""").fetchall()
    addr, ph = {}, {}
    for r in db.execute(f"""
        SELECT {pfx}_CERT_NBR_NUM c, {pfx}_SEQ_NUM s, ADDRESS1, ADDRESS2, CITY, PAR_ZIP, ZIP4,
               STA_STATE_ABBR st FROM ADDRESSES
        WHERE {pfx}_CERT_NBR_NUM <> '' AND STATUS = 'A' AND ATC_ADDRESS_TYPE_CODE = 'P'
        ORDER BY DATE_LAST_MOD, DATE_CREATED"""):
        addr[(r["c"], r["s"])] = r
    for r in db.execute(f"""
        SELECT {pfx}_CERT_NBR_NUM c, {pfx}_SEQ_NUM s, PTC_PHONE_TYPE_CODE t, PHONE_NUMBER n
        FROM PHONES WHERE {pfx}_CERT_NBR_NUM <> '' AND STATUS = 'A'
        ORDER BY DATE_LAST_MOD, DATE_CREATED"""):
        p = phone(r["n"])
        if p:
            ph.setdefault((r["c"], r["s"]), {})[r["t"]] = p
    st = dict(rows=0, no_address=0, bad_state=0, parish_blank_in_la=0, no_name=0)
    with open(os.path.join(ROOT, "load", outfile), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        for e in ents:
            row = dict.fromkeys(COLS, "")
            name = clean(e["name"], 255) or clean(e["company"], 255)
            if not name:
                name = "Unnamed " + e["k"]
                st["no_name"] += 1
            row.update(LegacyKey__c=e["k"], RecordTypeId=RT[table], Name=name)
            key = (e["c"], e["s"])
            a = addr.get(key)
            if a:
                row["BillingStreet"] = "\n".join(
                    x for x in (clean(a["ADDRESS1"]), clean(a["ADDRESS2"])) if x)[:255]
                row["BillingCity"] = clean(a["CITY"], 40)
                row["BillingPostalCode"] = zipcode(a["PAR_ZIP"], a["ZIP4"])
                s = clean(a["st"]).upper()
                if s in us_states:
                    row["BillingStateCode"], row["BillingCountryCode"] = s, "US"
                    if s == "LA":
                        row["Parish__c"] = zip_parish.get(a["PAR_ZIP"], "")
                        st["parish_blank_in_la"] += not row["Parish__c"]
                    else:
                        row["Parish__c"] = "Out of State"
                else:
                    st["bad_state"] += 1
            else:
                st["no_address"] += 1
            p = ph.get(key, {})
            row["Phone"] = p.get("W") or p.get("H") or p.get("C") or ""
            w.writerow(row)
            st["rows"] += 1
    print(outfile, json.dumps(st))


build("SHOPS", "XW_SHOP", "SHO", "establishment_accounts.csv")
build("SCHOOLS", "XW_SCHOOL", "SCH", "school_accounts.csv")
