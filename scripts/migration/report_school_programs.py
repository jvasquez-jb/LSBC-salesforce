#!/usr/bin/env python3
"""Report for the Board: where the portal's Find a School programs and schools came from in CLOSE.

Usage:
  sf data query -q "SELECT CourseName.Name, School__r.LegacyKey__c FROM CourseOffering" --result-format csv > offerings.csv
  sf data query -q "SELECT Name, LegacyKey__c, BillingCity FROM Account WHERE RecordType.DeveloperName='School'" --result-format csv > schools.csv
  python3 -I report_school_programs.py <lsbc_deid.sqlite> offerings.csv schools.csv <out.xlsx>

Needs openpyxl. Writes three sheets: Programs (CLOSE student types and what the portal lists), Schools (each
active or migrated CLOSE school: CLOSE approved hours per program next to what the portal lists), Sources.
School name and city only: no certificate numbers, owners or other identifiers. Test schools (no LegacyKey__c)
are left out.
"""
import csv, sqlite3, sys
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

SINCE = "2025-11-11"  # the student load's cut-off (build_students.py)
COURSE = {"C": "Cosmetology", "M": "Manicurist", "E": "Esthetician", "ME": "Manicurist Esthetician",
          "CI": "Teacher", "CIS": "Teacher", "EI": "Teacher", "MI": "Teacher", "SA": "Shampoo Assistant",
          "A": "Alternative Hair Design", "MB": "Microdermabrasion", "AD": "Advanced Training",
          "BU": "Advanced Training", "MU": "Make-up Application"}
HOURS_COL = {"Cosmetology": "COSMO_HOURS_REQ", "Manicurist": "MANI_HOURS_REQ", "Esthetician": "ESTH_HOURS_REQ",
             "Teacher": "TEACH_HOURS_REQ", "Shampoo Assistant": "SHAM_HOURS_REQ",
             "Alternative Hair Design": "ALTE_HOURS_REQ", "Manicurist Esthetician": "MAN_EST",
             "Advanced Training": "ADV_TRAIN", "Microdermabrasion": "MICRODERM", "Make-up Application": None}
PROGRAMS = list(HOURS_COL)  # the ten programs in the portal's dropdown

deid, offerings_csv, schools_csv, out = sys.argv[1:5]
db = sqlite3.connect(f"file:{deid}?mode=ro", uri=True)
num = lambda v: float(v) if v not in (None, "") and str(v).replace(".", "", 1).isdigit() else 0.0

# Salesforce: migrated schools and their offerings
org = {r["LegacyKey__c"]: r for r in csv.DictReader(open(schools_csv)) if r["LegacyKey__c"]}
offered = {}  # legacy key -> set of programs listed on the portal
for r in csv.DictReader(open(offerings_csv)):
    k = r["School__r.LegacyKey__c"]
    if k:
        offered.setdefault(k, set()).add(r["CourseName.Name"])

# CLOSE schools: active ones and any that were migrated
xw = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SCHOOL")}
cols = ", ".join(c for c in HOURS_COL.values() if c)
schools = []
for row in db.execute(f"SELECT CERT_NBR_NUM, SEQ_NUM, NAME, STATUS, {cols} FROM SCHOOLS"):
    cert, seq, name, status, *hours = row
    key = xw.get((cert, int(float(seq)))) if seq is not None else None
    if status != "Y" and key not in org:
        continue
    approved = dict(zip([p for p in PROGRAMS if HOURS_COL[p]], hours))
    schools.append((org[key]["Name"] if key in org else (name or "").strip(),
                    org[key]["BillingCity"] if key in org else "",
                    "Yes" if status == "Y" else "No", "Yes" if key in org else "No",
                    approved, offered.get(key, set())))
schools.sort(key=lambda s: s[0].lower())

# CLOSE student types: registrations ever and recent ones (the rule the student load used)
last = {}
for a, s, q, t, d in db.execute("""SELECT REG_APP_APPLICANT_ID, REG_SCH_CERT_NBR_NUM, REG_SCH_SEQ_NUM,
        REG_ST_STUDENT_TYPE, MAX(DATE_HOURS_COMPLETED) FROM HOURS GROUP BY 1, 2, 3, 4"""):
    last[(a, s, q, t)] = d or ""
ever, recent = {}, {}
for a, s, q, t, rd, cur in db.execute("""SELECT APP_APPLICANT_ID, SCH_CERT_NBR_NUM, SCH_SEQ_NUM, ST_STUDENT_TYPE,
        REGISTRATION_DATE, CURRENTLY_ENROLLED FROM REGISTRATIONS"""):
    t = (t or "").strip()
    ever[t] = ever.get(t, 0) + 1
    if cur == "Y" and ((rd or "") >= SINCE or last.get((a, s, q, t), "") >= SINCE):
        recent[t] = recent.get(t, 0) + 1

wb = Workbook()
HEAD = Font(bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="111111")
ASK = PatternFill("solid", fgColor="FFF2CC")
WRAP = Alignment(wrap_text=True, vertical="top")


def sheet(ws, header, rows, widths, ask_cols=()):
    ws.append(header)
    for c in ws[1]:
        c.font, c.fill, c.alignment = HEAD, FILL, WRAP
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for col in ask_cols:
        for r in range(2, ws.max_row + 1):
            ws.cell(r, col).fill = ASK
    ws.freeze_panes = "B2"
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = WRAP


# Programs
ws = wb.active
ws.title = "Programs"
rows = []
for code, desc in db.execute("SELECT STUDENT_TYPE, DESCRIPTION FROM STUDENT_TYPES ORDER BY STUDENT_TYPE"):
    p = COURSE.get(code)
    rows.append([code, desc, ever.get(code, 0), recent.get(code, 0), p or "Not loaded",
                 "Yes" if p else "No",
                 sum(1 for s in schools if p in s[5]) if p else "",
                 sum(1 for s in schools if p and HOURS_COL.get(p) and num(s[4][p]) > 0 and s[2] == "Yes") if p else "",
                 "", ""])
sheet(ws, ["CLOSE code (STUDENT_TYPES)", "CLOSE description", "Registrations in CLOSE (all years)",
           "Currently enrolled, active since 11 Nov 2025", "Portal program it became",
           "In the Find a School program list?", "Schools the portal lists for it",
           "Active CLOSE schools with approved hours for it", "Board: does LSBC approve schools to teach this? (Yes/No)",
           "Board: comments"], rows, [12, 32, 14, 16, 26, 14, 14, 16, 26, 36], ask_cols=(9, 10))

# Schools
ws = wb.create_sheet("Schools")
header = ["School", "City", "Active in CLOSE", "On the portal"]
for p in PROGRAMS:
    header += [f"{p}: approved hours in CLOSE", f"{p}: listed on portal"]
header += ["Board: correct programs for this school", "Board: comments"]
rows = []
for name, city, active, migrated, approved, listed in schools:
    r = [name, city, active, migrated]
    for p in PROGRAMS:
        h = num(approved.get(p)) if HOURS_COL[p] else 0
        r += [int(h) if h else ("no column in CLOSE" if not HOURS_COL[p] else ""), "Yes" if p in listed else ""]
    rows.append(r + ["", ""])
n = len(header)
sheet(ws, header, rows, [40, 18, 10, 10] + [13] * (2 * len(PROGRAMS)) + [40, 36], ask_cols=(n - 1, n))

# Sources
ws = wb.create_sheet("Sources")
sheet(ws, ["What the portal shows", "Where it came from in CLOSE", "Notes"], [
    ["Find a School program list",
     "Table STUDENT_TYPES (the student type codes on each registration, REGISTRATIONS.ST_STUDENT_TYPE)",
     "Each CLOSE student type became a program. Instructor types (CI, CIS, EI, MI) became Teacher; Advanced (AD) and "
     "Brushup (BU) became Advanced Training. Barber, remedial and reciprocity hours were not loaded."],
    ["Which schools are listed for a program",
     "Tables REGISTRATIONS and HOURS",
     f"A school is listed for a program when CLOSE shows a student currently enrolled in it there who registered or "
     f"reported hours on or after {SINCE}. It reflects recent students, not the programs a school is approved for."],
    ["(Not used yet) programs a school is approved for",
     "Table SCHOOLS, approved hours columns: COSMO_HOURS_REQ, MANI_HOURS_REQ, ESTH_HOURS_REQ, TEACH_HOURS_REQ, "
     "SHAM_HOURS_REQ, ALTE_HOURS_REQ, MAN_EST, ADV_TRAIN, MICRODERM",
     "Shown on the Schools sheet next to what the portal lists. CLOSE has no column for Make-up Application."],
    ["The schools themselves",
     "Table SCHOOLS",
     "Schools active in CLOSE, or holding a current license, were loaded. Name and city come from the loaded record."],
    ["What we need from the Board",
     "",
     "Programs sheet: which programs LSBC approves schools to teach. Schools sheet: the correct programs for each "
     "school (yellow columns). We will load your list so the portal shows approved programs, not recent enrollments."],
], [34, 60, 80])

wb.save(out)
print(f"{len(schools)} schools, {len(PROGRAMS)} programs -> {out}")
