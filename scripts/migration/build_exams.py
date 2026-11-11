#!/usr/bin/env python3
"""Build the exam load from CLOSE.

Usage:
  LSBC_MIGRATION_DIR=<folder> python3 -I build_exams.py <lsbc_deid.sqlite> examinations
      -> load/examinations.csv: one Examination per licence type and exam type (insert once)
  LSBC_MIGRATION_DIR=<folder> python3 -I build_exams.py <lsbc_deid.sqlite> attempts
      -> load/person_examinations.csv: graded attempts of migrated people
         (needs sf/examinations.json, exam name -> Id, and sf/account_ids.csv)

CLOSE has 198 exam variants: a discipline, an exam type, a city (Baton Rouge,
Shreveport), a language (Spanish, Vietnamese), retake and no-show versions.
Salesforce keeps one Examination per licence type and exam type, which is how
the stop code rules read them; city and language aren't kept and a retake is
the next attempt number. One Restoration exam serves every discipline: the
rule finds restoration attempts by exam type alone.
- Variants with no discipline (state written exam, reciprocity state exam, NIC
  reciprocity national) count as Cosmetologist.
- Not loaded: no-shows and attempts with no result, combined National & State
  or Complete sittings (one result can't be split), crossover, mock and
  workshop sessions.
Score is CLOSE's weighted score. Attempt Number counts each person's dated
attempts at the same Examination, from 1.
"""
import collections, csv, json, os, re, sqlite3, sys

root = os.environ["LSBC_MIGRATION_DIR"]
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
mode = sys.argv[2]
TYPES = ["Cosmetologist", "Manicurist", "Esthetician", "Cosmetology Instructor", "Esthetician Instructor",
         "Manicurist Instructor", "Alternative Hair Design Permit"]


def classify(name):
    """CLOSE exam name -> (licence type, exam type) or None to skip."""
    n = re.sub(r"\s+", " ", name or "").lower()
    if any(w in n for w in ("no show", "noshow", "&", " and state", "complete", "c/o", "crossover", "mock", "workshop")):
        return None
    if "restoration" in n:
        return ("", "Restoration")
    if "alternative hair" in n:
        lt = "Alternative Hair Design Permit"
    elif re.search(r"manicurist instructor|man\. instr", n):
        lt = "Manicurist Instructor"
    elif re.search(r"esthetician (instructor|teacher)", n):
        lt = "Esthetician Instructor"
    elif re.search(r"instructor|teacher|^inst", n):
        lt = "Cosmetology Instructor"
    elif re.search(r"manicurist|manaicurist|^man\b", n):
        lt = "Manicurist"
    elif re.search(r"esthetician|^esth", n):
        lt = "Esthetician"
    else:
        lt = "Cosmetologist"  # cosmetology, and variants with no discipline
    if "practical" in n:
        et = "Practical"
    elif "national" in n or "nic " in n:
        et = "National"
    elif "state" in n:
        et = "State"
    else:
        return None
    return (lt, et)


exam_name = lambda lt, et: "Restoration" if et == "Restoration" else f"{lt} {et}"

if mode == "examinations":
    with open(os.path.join(root, "load", "examinations.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["Name", "ExamType__c", "LicenseTypeName", "Status", "Description"])
        for lt in TYPES:
            for et in ("National", "State", "Practical"):
                w.writerow([exam_name(lt, et), et, lt, "Active", f"The {et.lower()} examination for the {lt} license."])
        w.writerow(["Restoration", "Restoration", "", "Active",
                    "The restoration examination, taken after a license has lapsed more than three years. One for every license type."])
    print("22 examinations")
    sys.exit()

exams = json.load(open(os.path.join(root, "sf", "examinations.json")))
contact = {r["LegacyKey__c"]: r["PersonContactId"] for r in csv.DictReader(open(os.path.join(root, "sf", "account_ids.csv")))
           if r["PersonContactId"]}
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
variant = {tid: classify(name) for tid, name in db.execute("SELECT TEX_ID, TEX_NAME FROM EXAMS")}
stats, rows = collections.Counter(), []
for app, tex, when, pf, score in db.execute("""
        SELECT APP_APPLICANT_ID, ES_EX_TEX_ID, ES_DATE_SCHEDULED, PASS_FAIL, WEIGHT_SCORE1
        FROM STUDENT_EXAM_GRADES ORDER BY ES_DATE_SCHEDULED, SEQ_NUM"""):
    c = contact.get(xp.get(app))
    if not c:
        continue
    v = variant.get(tex)
    day = (when or "")[:10]
    if pf not in ("P", "F"):
        stats["no result (no-show or not graded)"] += 1
    elif not v:
        stats["variant not loaded"] += 1
    elif not re.match(r"^(19[5-9]\d|20[0-2]\d)-\d\d-\d\d$", day):
        stats["no usable date"] += 1
    else:
        rows.append((c, exams[exam_name(*v)], day, "Pass" if pf == "P" else "Fail", score))
        stats["loaded"] += 1
attempt = collections.Counter()
with open(os.path.join(root, "load", "person_examinations.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["ContactId", "ExaminationId", "ExaminationDate", "Result", "Score", "AttemptNumber__c"])
    for c, e, day, result, score in sorted(rows, key=lambda r: (r[0], r[1], r[2])):
        attempt[(c, e)] += 1
        s = int(float(score)) if score not in (None, "") and str(score).replace(".", "", 1).isdigit() else ""
        w.writerow([c, e, f"{day}T17:00:00.000Z", result, s, attempt[(c, e)]])
print(dict(stats))
