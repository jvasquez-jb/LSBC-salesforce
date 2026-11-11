#!/usr/bin/env python3
"""Build load/regulatory_codes.csv and load/violation_types.csv from CLOSE's violation list.

Usage: python3 -I build_violations.py <lsbc_deid.sqlite> <load dir> <RegulatoryAuthority Id>

CLOSE's VIOLATION_CODES has one row per violation and statute citation: 39
violations (38 once two spellings of one are merged) in 4 categories, cited under 123 statute sections.
- Each citation becomes a Regulatory Code: Name is the citation, Subject and
  Description hold the rule text (Salesforce keeps 255 characters of each).
  Effective From is the date the citation was entered in CLOSE: CLOSE does not
  record when the law took effect.
- Each violation becomes a Violation Type: Type is its CLOSE category,
  Description lists the citations. CLOSE records no severity, so every type is
  loaded as Minor Violation until the chief inspector sets it.
Both are inserts: load them once.
"""
import csv, os, re, sqlite3, sys, collections

db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
out, authority = sys.argv[2], sys.argv[3]
CATEGORY = {"01": "Unlicensed Operator", "02": "Salon", "03": "School", "04": "Administrative Rules"}
clean = lambda s: re.sub(r"\s+", " ", (s or "")).strip()

rule, first, cites = {}, {}, collections.defaultdict(list)
cat, seen = {}, {}
for vtype, code, desc, text, created in db.execute(
        "SELECT VIOLATION_TYPE_CODE, VIOLATION_CODE, DESCRIPTION, VIOLATION_RULE, DATE_CREATED FROM VIOLATION_CODES ORDER BY VIOLATION_SEQ"):
    code, desc, text = clean(code), clean(desc), clean(text)
    desc = seen.setdefault(desc.lower(), desc)  # CLOSE spells a few violations two ways; keep the first
    if len(text) > len(rule.get(code, "")):
        rule[code] = text
    d = (created or "")[:10]
    if d and (code not in first or d < first[code]):
        first[code] = d
    if code not in cites[desc]:
        cites[desc].append(code)
    cat[desc] = CATEGORY.get(str(vtype).zfill(2), "Other")

with open(os.path.join(out, "regulatory_codes.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["Name", "Subject", "Description", "Type", "EffectiveFrom", "RegulatoryAuthorityId"])
    for code in sorted(rule):
        text = rule[code] or code
        w.writerow([code, text[:255], text[255:510], "Section", f"{first.get(code, '2002-11-01')}T12:00:00.000Z", authority])

with open(os.path.join(out, "violation_types.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["Name", "Type", "Severity", "Description"])
    for desc in sorted(cites):
        w.writerow([desc, cat[desc], "Minor Violation", ("Cited under " + ", ".join(cites[desc]) + ".")[:255]])
print(f"{len(rule)} regulatory codes, {len(cites)} violation types")
