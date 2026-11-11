#!/usr/bin/env python3
"""Build load/business_licenses.csv: one current licence per holder and type.

A legacy LICENSES row is one renewal term. The sandbox model keeps one
BusinessLicense per holder and licence type with a renewal count, so the terms
are rolled up: PeriodStart is the earliest term, PeriodEnd the current expiry.
Only combinations with a term that expires on or after AS_OF are written.
Legacy types with no licence type in the sandbox are written to
load/held_licenses.csv instead of being loaded.
"""
import csv, json, os, re, sqlite3, collections

ROOT = os.environ.get("LSBC_MIGRATION_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.environ.get("LSBC_DB", "lsbc.sqlite")  # lsbc_deid.sqlite: the de-identified copy
AS_OF = "2026-11-09"
db = sqlite3.connect(os.path.join(ROOT, "extract", DB))
types = json.load(open(os.path.join(ROOT, "sf", "auth_types.json")))

# legacy type -> sandbox licence type, by holder kind (P person, S shop, SC school)
MAP = {
    ("C", "P"): "Cosmetologist", ("M", "P"): "Manicurist", ("E", "P"): "Esthetician",
    ("CI", "P"): "Cosmetology Instructor", ("EI", "P"): "Esthetician Instructor",
    ("MI", "P"): "Manicurist Instructor", ("MA", "S"): "Manager", ("TM", "S"): "Manager",
    ("MB", "P"): "Microdermabrasion", ("MU", "P"): "Make-up Application",
    ("SA", "P"): "Shampoo Assistant", ("AH", "P"): "Alternative Hair Design Permit",
    ("AH", "S"): "Alternative Hair Design Facility", ("T", "P"): "Threading Permit",
    ("TF", "S"): "Threading Facility", ("TP", "P"): "Temporary Permit",
    ("B", "P"): "Booth Rental Permit", ("SH", "S"): "Salon", ("SC", "SC"): "School",
}
NAME = {"Salon": "Salon License", "School": "School License",
        "Booth Rental Permit": "Booth Permit", "Manager": "Manager License"}

xw = {}
for kind, t in (("P", "XW_PERSON"), ("S", "XW_SHOP"), ("SC", "XW_SCHOOL")):
    if kind == "P":
        for a, k in db.execute(f"SELECT src1, legacy_key FROM {t}"):
            xw[(kind, a, "")] = k
    else:
        for a, b, k in db.execute(f"SELECT src1, src2, legacy_key FROM {t}"):
            xw[(kind, a, str(int(float(b))))] = k


def day(s):
    s = (s or "")[:10]
    return s if re.match(r"^\d{4}-\d\d-\d\d$", s) and "1950" <= s[:4] <= "2029" else ""


combos = {}
for app, sc, ss, hc, hs, lt, renewed, created, exp in db.execute("""
    SELECT APP_APPLICANT_ID, SHO_CERT_NBR_NUM, SHO_SEQ_NUM, SCH_CERT_NBR_NUM, SCH_SEQ_NUM,
           LT_LICENSE_TYPE, DATE_LAST_RENEWED, DATE_CREATED, EXPIRATION_DATE FROM LICENSES"""):
    if app:
        holder = ("P", app, "")
    elif sc:
        holder = ("S", sc, str(int(float(ss))))
    elif hc:
        holder = ("SC", hc, str(int(float(hs))))
    else:
        continue
    c = combos.setdefault((holder, lt), dict(start="", end="", terms=0))
    c["terms"] += 1
    s, e = day(renewed) or day(created), day(exp)
    if s and (not c["start"] or s < c["start"]):
        c["start"] = s
    if e and e > c["end"]:
        c["end"] = e

cols = ["LegacyKey__c", "Name", "Account.LegacyKey__c", "RegulatoryAuthorizationTypeId",
        "Status", "PeriodStart", "PeriodEnd", "RenewalCount__c", "JurisdictionType",
        "VerificationStatus"]
stats, held = collections.Counter(), collections.Counter()
ONLY = set(filter(None, os.environ.get("LSBC_ONLY_TYPES", "").split(";")))  # e.g. "Manager;Microdermabrasion"
with open(os.path.join(ROOT, "load", "business_licenses.csv"), "w", newline="") as fh, \
     open(os.path.join(ROOT, "load", "held_licenses.csv"), "w", newline="") as hh:
    w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    hw = csv.writer(hh, lineterminator="\n")
    hw.writerow(["holder_key", "legacy_type", "period_end", "reason"])
    for (holder, lt), c in sorted(combos.items(), key=lambda kv: (xw.get(kv[0][0], ""), kv[0][1])):
        if c["end"] < AS_OF:
            continue
        hk = xw.get(holder)
        target = MAP.get((lt, holder[0]))
        if not hk or not target:
            held[lt] += 1
            hw.writerow([hk or "", lt, c["end"], "no licence type in sandbox" if hk else "no crosswalk key"])
            continue
        if ONLY and target not in ONLY:
            continue
        start = c["start"] if c["start"] and c["start"] <= c["end"] else ""
        w.writerow({
            "LegacyKey__c": f"{hk}-{lt}", "Name": NAME.get(target, target),
            "Account.LegacyKey__c": hk, "RegulatoryAuthorizationTypeId": types[target],
            "Status": "Active", "PeriodStart": f"{start}T12:00:00.000Z" if start else "",
            "PeriodEnd": f"{c['end']}T12:00:00.000Z", "RenewalCount__c": max(c["terms"] - 1, 0),
            "JurisdictionType": "STATE", "VerificationStatus": "Authorized"})
        stats[target] += 1
print("load", sum(stats.values()), dict(stats))
print("held", sum(held.values()), dict(held))
