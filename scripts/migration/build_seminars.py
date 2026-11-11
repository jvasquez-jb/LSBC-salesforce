#!/usr/bin/env python3
"""Build the continuing-education load from CLOSE: seminars and who attended them.

Usage (LSBC_MIGRATION_DIR=<folder>, in order, loading each output before the next step):
  python3 -I build_seminars.py <deid> offerings <TrnCourse Id>  -> load/ce_offerings.csv
  python3 -I build_seminars.py <deid> participants              -> load/ce_participants.csv
                                                                    (needs sf/ce_offerings.csv: Id, Description)

Shape:
- One Training Course "Continuing Education" (create it by hand first; its Id is the argument).
- Course Offering: one per CLOSE seminar, named by the seminar description, dated the day it was
  held. Description "CLOSE seminar <id>, <hours> hours" is the key for the next step.
- Training Course Participant: one per attendance of a migrated person, Entry Type Continuing
  Education, Total Hours = hours credited, start and end on the day attended. Stop codes ignore this
  entry type, so loading it opens no student-hours hold.
Attendances of people who weren't migrated are counted, not loaded. CLOSE has only seminar names,
not providers, so providers are not created.
"""
import collections, csv, os, re, sqlite3, sys

root = os.environ["LSBC_MIGRATION_DIR"]
db = sqlite3.connect(f"file:{sys.argv[1]}?mode=ro", uri=True)
mode = sys.argv[2]
day = lambda s: (s or "")[:10] if re.match(r"^(19[5-9]\d|20[0-2]\d)-\d\d-\d\d", s or "") else ""
nine = re.compile(r"(?<!\d)\d{9}(?!\d)")


def guard(row):
    """Refuse any nine-digit value outside the de-identified 000 range."""
    for v in row:
        for m in nine.findall(str(v)):
            if not m.startswith("000"):
                sys.exit(f"refused: nine-digit value outside the 000 range in {row}")
    return row


def hours(h):
    return round(float(h), 2) if h not in (None, "") else ""


if mode == "offerings":
    course = sys.argv[3]
    with open(os.path.join(root, "load", "ce_offerings.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["Name", "CourseNameId", "StartDate", "EndDate", "Description"])
        n = 0
        for sid, desc, held, h in db.execute("SELECT SEMINAR_ID, DESCRIPTION, DATE_CONDUCTED, HOURS FROM SEMINARS ORDER BY DATE_CONDUCTED"):
            d = day(held)
            when = f"{d}T17:00:00.000Z" if d else ""
            w.writerow(guard([(desc or sid).strip()[:80], course, when, when,
                              f"CLOSE seminar {sid.strip()}, {hours(h)} hours"]))
            n += 1
    print(f"{n} course offerings")

elif mode == "participants":
    xp = dict(db.execute("SELECT src1, legacy_key FROM XW_PERSON"))
    contact = {r["LegacyKey__c"]: r["PersonContactId"] for r in csv.DictReader(open(os.path.join(root, "sf", "account_ids.csv")))
               if r["PersonContactId"]}
    offering = {}
    for r in csv.DictReader(open(os.path.join(root, "sf", "ce_offerings.csv"))):
        m = re.match(r"CLOSE seminar (\S+),", r["Description"])
        if m:
            offering[m.group(1)] = r["Id"]
    st, seen = collections.Counter(), set()
    with open(os.path.join(root, "load", "ce_participants.csv"), "w", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["ContactId", "CourseOfferingId", "StartDate", "EndDate", "TotalHours", "EntryType__c"])
        for a, sid, attended, h in db.execute("SELECT APP_APPLICANT_ID, SEM_SEMINAR_ID, DATE_ATTENDED, HOURS_CREDITED FROM SEMINAR_DETAILS"):
            c, o, d = contact.get(xp.get(a)), offering.get((sid or "").strip()), day(attended)
            if not c:
                st["not migrated"] += 1
                continue
            if not o or not d:
                st["skipped: no seminar or date"] += 1
                continue
            if (c, o, d) in seen:
                st["duplicate attendance"] += 1
                continue
            seen.add((c, o, d))
            w.writerow(guard([c, o, f"{d}T17:00:00.000Z", f"{d}T17:00:00.000Z", hours(h), "Continuing Education"]))
            st["loaded"] += 1
    print(dict(st))
