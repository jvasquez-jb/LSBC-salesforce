#!/usr/bin/env python3
"""Build the person-account load file for people with a current licence.

Reads extract/lsbc.sqlite, writes load/person_accounts.csv keyed on the
abstracted LegacyKey__c from XW_PERSON. The SSN-shaped APPLICANT_ID, USERID,
PWD, sex, race and free-text comments are never written.
"""
import csv, json, os, re, sqlite3, sys

ROOT = os.environ.get("LSBC_MIGRATION_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("LSBC_DB", "lsbc.sqlite")  # lsbc_deid.sqlite: the de-identified copy
AS_OF = "2026-11-09"
PERSON_RT = "012cp00000MfMzBAAV"

db = sqlite3.connect(os.path.join(ROOT, "extract", DB))
db.row_factory = sqlite3.Row
us_states = set(json.load(open(os.path.join(ROOT, "sf", "us_states.json"))))
acct = json.load(open(os.path.join(ROOT, "sf", "describe_Account.json")))["result"]
parishes = [p["value"] for f in acct["fields"] if f["name"] == "HomeParish__pc"
            for p in f["picklistValues"] if p["active"]]
norm = lambda s: re.sub(r"[^a-z]", "", (s or "").lower().replace("saint", "st"))
parish_by_norm = {norm(p): p for p in parishes}


def clean(s, n=None):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s[:n] if n else s


def phone(s):
    d = re.sub(r"\D", "", s or "")
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    return f"({d[:3]}) {d[3:6]}-{d[6:]}" if len(d) == 10 else ""


def zipcode(z, z4):
    z = re.sub(r"\D", "", z or "")
    z4 = re.sub(r"\D", "", z4 or "")
    if len(z) != 5:
        return ""
    return f"{z}-{z4}" if len(z4) == 4 else z


# Default scope: people with a current licence. With an ids file (one legacy
# applicant ID per line, kept under extract/), the scope is those people
# instead: owners and managers of loaded salons who hold no current licence.
ids_file = sys.argv[1] if len(sys.argv) > 1 else None
out_name = sys.argv[2] if len(sys.argv) > 2 else "person_accounts.csv"
SELECT = """
    SELECT a.APPLICANT_ID id, x.legacy_key k, a.APPLICANT_FIRST_NAME fn,
           a.APPLICANT_LAST_NAME ln, a.APPLICANT_MIDDLE_INITIAL mi,
           a.APPLICANT_MAIDEN_NAME maiden, a.APPLICANT_BIRTHDATE dob,
           a.COMPANY_NAME company
    FROM APPLICANTS a JOIN XW_PERSON x ON x.src1 = a.APPLICANT_ID """
if ids_file:
    db.execute("CREATE TEMP TABLE want(id TEXT PRIMARY KEY)")
    db.executemany("INSERT OR IGNORE INTO want VALUES (?)",
                   [(l.strip(),) for l in open(ids_file) if l.strip()])
    people = db.execute(SELECT + "WHERE a.APPLICANT_ID IN (SELECT id FROM want) ORDER BY x.legacy_key").fetchall()
else:
    people = db.execute(SELECT + f"""WHERE a.APPLICANT_ID IN (
        SELECT DISTINCT APP_APPLICANT_ID FROM LICENSES
        WHERE EXPIRATION_DATE >= '{AS_OF}' AND EXPIRATION_DATE < '2030-01-01'
          AND APP_APPLICANT_ID <> '' AND (VOID_LICENSE IS NULL OR VOID_LICENSE <> 'Y'))
    ORDER BY x.legacy_key""").fetchall()

# Addresses carry no parish sequence, so the parish comes from the ZIP. A ZIP
# whose rows name more than one parish on the picklist is left blank.
zip_parish = {}
for z, d in db.execute("SELECT ZIP, DESCRIPTION FROM PARISHES"):
    m = parish_by_norm.get(norm(d))
    if m:
        zip_parish.setdefault(z, set()).add(m)
zip_parish = {z: next(iter(v)) for z, v in zip_parish.items() if len(v) == 1}

addr = {}
for r in db.execute("""
    SELECT d.APP_APPLICANT_ID id, d.ADDRESS1, d.ADDRESS2, d.CITY, d.PAR_ZIP, d.ZIP4,
           d.STA_STATE_ABBR st
    FROM ADDRESSES d
    WHERE d.APP_APPLICANT_ID <> '' AND d.STATUS = 'A' AND d.ATC_ADDRESS_TYPE_CODE = 'P'
    ORDER BY d.DATE_LAST_MOD, d.DATE_CREATED"""):
    addr[r["id"]] = r  # latest active mailing address wins

phones = {}
for r in db.execute("""
    SELECT APP_APPLICANT_ID id, PTC_PHONE_TYPE_CODE t, PHONE_NUMBER n FROM PHONES
    WHERE APP_APPLICANT_ID <> '' AND STATUS = 'A'
    ORDER BY DATE_LAST_MOD, DATE_CREATED"""):
    p = phone(r["n"])
    if p:
        phones.setdefault(r["id"], {})[r["t"]] = p

cols = ["LegacyKey__c", "RecordTypeId", "FirstName", "LastName", "MiddleName",
        "MaidenName__pc", "PersonBirthdate", "PersonMailingStreet", "PersonMailingCity",
        "PersonMailingStateCode", "PersonMailingPostalCode", "PersonMailingCountryCode",
        "HomeParish__pc", "PersonMobilePhone", "PersonHomePhone", "Phone"]
stats = dict(rows=0, no_address=0, bad_state=0, no_dob=0, parish_unmatched=0,
             out_of_state=0, no_last_name=0)
out = os.path.join(ROOT, "load", out_name)
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for p in people:
        row = dict.fromkeys(cols, "")
        row.update(LegacyKey__c=p["k"], RecordTypeId=PERSON_RT,
                   FirstName=clean(p["fn"], 40), MiddleName=clean(p["mi"], 40),
                   MaidenName__pc=clean(p["maiden"], 80))
        ln = clean(p["ln"], 80) or clean(p["company"], 80)
        if not ln:
            ln = "Unknown"
            stats["no_last_name"] += 1
        row["LastName"] = ln
        dob = (p["dob"] or "")[:10]
        if re.match(r"^\d{4}-\d\d-\d\d$", dob) and "1920" <= dob[:4] <= "2012":
            row["PersonBirthdate"] = dob
        else:
            stats["no_dob"] += 1
        a = addr.get(p["id"])
        if a:
            street = "\n".join(x for x in (clean(a["ADDRESS1"]), clean(a["ADDRESS2"])) if x)
            row["PersonMailingStreet"] = street[:255]
            row["PersonMailingCity"] = clean(a["CITY"], 40)
            row["PersonMailingPostalCode"] = zipcode(a["PAR_ZIP"], a["ZIP4"])
            st = clean(a["st"]).upper()
            if st in us_states:
                row["PersonMailingStateCode"] = st
                row["PersonMailingCountryCode"] = "US"
                if st == "LA":
                    m = zip_parish.get(a["PAR_ZIP"])
                    if m:
                        row["HomeParish__pc"] = m
                    else:
                        stats["parish_unmatched"] += 1
                else:
                    row["HomeParish__pc"] = "Out of State"
                    stats["out_of_state"] += 1
            else:
                stats["bad_state"] += 1
        else:
            stats["no_address"] += 1
        ph = phones.get(p["id"], {})
        row["PersonMobilePhone"] = ph.get("C", "")
        row["PersonHomePhone"] = ph.get("H", "")
        row["Phone"] = ph.get("W", "")
        w.writerow(row)
        stats["rows"] += 1
print(json.dumps(stats))
