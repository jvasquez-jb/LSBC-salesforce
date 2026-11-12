#!/usr/bin/env python3
"""Build the student load from CLOSE: active enrolments and their monthly hours.

Usage (LSBC_MIGRATION_DIR=<folder>, in order, loading each output before the next step):
  python3 -I build_students.py <deid> people        -> extract/student_ids.txt (people to load with
                                                       build_person_accounts.py <ids file> student_people.csv)
  python3 -I build_students.py <deid> offerings     -> load/course_offerings.csv (needs sf/courses.json)
  python3 -I build_students.py <deid> participants  -> load/participants.csv (needs sf/offerings.csv)

Scope: registrations CLOSE flags as currently enrolled whose student logged hours,
or registered, on or after SINCE. CLOSE never clears the flag, so older ones are
treated as finished and not loaded.
- Course Offering: one per school and programme in scope, named "<school> - <programme>",
  with the school's approved hours for that programme from SCHOOLS.
- Training Course Participant: one per CLOSE hours row (a month's hours), from the 1st
  to the last day of that month; transferred hours are entry type Transfer, on their date.
Student types map to programmes: instructor students to Teacher, advanced and
brush-up to Advanced Training. Barber, reciprocity-mandatory and remedial hours
are left out, and so are enrolments at schools CLOSE marks closed (not migrated).
"""
import collections, csv, datetime, json, os, re, sqlite3, sys

SINCE = "2025-11-11"
root = os.environ["LSBC_MIGRATION_DIR"]
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
mode = sys.argv[2]
COURSE = {"C": "Cosmetology", "M": "Manicurist", "E": "Esthetician", "ME": "Manicurist Esthetician",
          "CI": "Teacher", "CIS": "Teacher", "EI": "Teacher", "MI": "Teacher", "SA": "Shampoo Assistant",
          "A": "Alternative Hair Design", "MB": "Microdermabrasion", "AD": "Advanced Training",
          "BU": "Advanced Training", "MU": "Make-up Application"}
HOURS_COL = {"Cosmetology": "COSMO_HOURS_REQ", "Manicurist": "MANI_HOURS_REQ", "Esthetician": "ESTH_HOURS_REQ",
             "Teacher": "TEACH_HOURS_REQ", "Shampoo Assistant": "SHAM_HOURS_REQ",
             "Alternative Hair Design": "ALTE_HOURS_REQ", "Manicurist Esthetician": "MAN_EST",
             "Advanced Training": "ADV_TRAIN", "Microdermabrasion": "MICRODERM"}
xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
xc = {(a, int(float(b))): k for a, b, k in db.execute("SELECT src1, src2, legacy_key FROM XW_SCHOOL")}
day = lambda s: (s or "")[:10] if re.match(r"^(19[5-9]\d|20[0-2]\d)-\d\d-\d\d", s or "") else ""

last = {}
for a, s, q, t, d in db.execute("""SELECT REG_APP_APPLICANT_ID, REG_SCH_CERT_NBR_NUM, REG_SCH_SEQ_NUM, REG_ST_STUDENT_TYPE,
        MAX(DATE_HOURS_COMPLETED) FROM HOURS GROUP BY 1, 2, 3, 4"""):
    last[(a, s, q, t)] = d or ""
regs = []  # (applicant, school key, course, registration date, CLOSE registration key)
for a, s, q, t, rd in db.execute("""SELECT APP_APPLICANT_ID, SCH_CERT_NBR_NUM, SCH_SEQ_NUM, ST_STUDENT_TYPE, REGISTRATION_DATE
        FROM REGISTRATIONS WHERE CURRENTLY_ENROLLED = 'Y'"""):
    course = COURSE.get((t or "").strip())
    school = xc.get((s, int(float(q)))) if s and q is not None else None
    if not course or not school or a not in xp:
        continue
    if (rd or "") >= SINCE or last.get((a, s, q, t), "") >= SINCE:
        regs.append((a, school, course, day(rd), (a, s, q, t)))

if mode == "people":
    have = {r["LegacyKey__c"] for r in csv.DictReader(open(os.path.join(root, "sf", "account_ids.csv")))}
    need = sorted({a for a, *_ in regs if xp[a] not in have})
    with open(os.path.join(root, "extract", "student_ids.txt"), "w") as fh:  # mock IDs only
        fh.write("\n".join(need) + "\n")
    print(f"{len(regs)} enrolments, {len({a for a, *_ in regs})} students, {len(need)} not yet loaded")

elif mode == "offerings":
    courses = json.load(open(os.path.join(root, "sf", "courses.json")))
    ids = {r["LegacyKey__c"]: (r["Id"]) for r in csv.DictReader(open(os.path.join(root, "sf", "account_ids.csv")))}
    names = {k: n for k, n in ((r["LegacyKey__c"], r.get("Name", "")) for r in csv.DictReader(open(os.path.join(root, "sf", "school_names.csv"))))}
    hours = {}
    for c, q, *vals in db.execute(f"SELECT CERT_NBR_NUM, SEQ_NUM, {', '.join(HOURS_COL.values())} FROM SCHOOLS"):
        k = xc.get((c, int(float(q))))
        if k:
            hours[k] = dict(zip(HOURS_COL, vals))
    pairs = sorted({(school, course) for _, school, course, _, _ in regs if school in ids})  # closed schools are not loaded
    with open(os.path.join(root, "load", "course_offerings.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["Name", "School__c", "CourseNameId", "ApprovedHours__c", "Description"])
        for school, course in pairs:
            h = (hours.get(school) or {}).get(course)
            w.writerow([f"{names.get(school, school)} - {course}"[:80], ids[school], courses[course],
                        int(h) if h and float(h) > 0 else "", f"CLOSE {school} {course}"])
    print(f"{len(pairs)} course offerings")

elif mode == "participants":
    contact = {r["LegacyKey__c"]: r["PersonContactId"] for r in csv.DictReader(open(os.path.join(root, "sf", "account_ids.csv")))
               if r["PersonContactId"]}
    offering = {}
    for r in csv.DictReader(open(os.path.join(root, "sf", "offerings.csv"))):
        _, school, course = r["Description"].split(" ", 2)
        offering[(school, course)] = r["Id"]
    wanted = {key: (school, course) for _, school, course, _, key in regs}
    st = collections.Counter()
    with open(os.path.join(root, "load", "participants.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["ContactId", "CourseOfferingId", "StartDate", "EndDate", "TotalHours", "EntryType__c", "ReceivedDate__c"])
        for a, s, q, t, d, h, tr, rec in db.execute("""SELECT REG_APP_APPLICANT_ID, REG_SCH_CERT_NBR_NUM, REG_SCH_SEQ_NUM,
                REG_ST_STUDENT_TYPE, DATE_HOURS_COMPLETED, HOURS, TRANSFERRED, DATE_CREATED FROM HOURS"""):
            key = (a, s, q, t)
            if key not in wanted:
                continue
            c, o, end = contact.get(xp.get(a)), offering.get(wanted[key]), day(d)
            if not c or not o or not end or h is None:
                st["skipped: no person, offering, date or hours"] += 1
                continue
            transfer = (tr or "").strip().upper() == "T"  # CLOSE marks transferred hours T
            # CLOSE dates a month's hours on the 1st of that month: the record runs to the month's last day.
            y, m = int(end[:4]), int(end[5:7])
            start = end if transfer else end[:8] + "01"
            if not transfer:
                end = (datetime.date(y + m // 12, m % 12 + 1, 1) - datetime.timedelta(days=1)).isoformat()
            w.writerow([c, o, f"{start}T17:00:00.000Z", f"{end}T17:00:00.000Z", round(float(h), 2),
                        "Transfer" if transfer else "Monthly Hours",
                        day(rec)])  # the date CLOSE recorded the hours: when the Board received them
            st["loaded"] += 1
    print(dict(st))
