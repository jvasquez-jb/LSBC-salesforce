#!/usr/bin/env python3
"""Write a de-identified copy of the CLOSE SQLite database.

Usage: python3 -I deidentify.py <source lsbc.sqlite> <target lsbc_deid.sqlite>

CLOSE keys people on an applicant ID shaped like a social security number, and
many shop certificate numbers are the owner's applicant ID. This copies the
database and replaces those numbers with made-up IDs starting 000, an area
number the SSA never issues. The same real value always gets the same mock, so
joins between tables still work.

Columns fall into three groups:
- ID columns (applicant ID, certificate numbers, SSN and tax ID columns, licence
  numbers): every nine-digit value is swapped.
- Free text (names, addresses, comments): every nine-digit value is swapped, in
  case someone typed an SSN.
- Reference numbers (receipts, deposits, cheques, sequences, phones, scores,
  bond numbers) and numeric columns: only values that match a known applicant
  ID or certificate number are swapped. Their own numbers are kept.
Numeric columns holding a known ID are converted to text first, so a leading
000 survives. Login, password and user ID columns are blanked. Unique indexes
are recreated as plain ones: a number stored both as 123456789 and 123-45-6789
becomes one mock.

The real-to-mock mapping lives only in memory while this runs and is never
written anywhere, so the copy can't be traced back to a real number.

Prints counts and column names only, never a value. Ends by checking that no
real ID is left anywhere and no nine-digit value outside the 000 range is left
in ID or free-text columns. Exits 1 if either check fails.
"""
import os, random, re, shutil, sqlite3, sys, time

SRC, DST = sys.argv[1], sys.argv[2]
if os.path.exists(DST):
    sys.exit(f"{DST} already exists; remove it first")

BLANK = re.compile(r"(^|_)(PWD|PASSWORD|USERID)$")
ID_COL = re.compile(r"APPLICANT_ID|CERT_NBR_NUM|CERT_NUM|SSN|TAXID|LICENSE_NUM|LICENSENO|LIC_NO|OLD_CERT"
                    r"|STUDENT_ID|SHOPID|OLD_SHOP_ID|OLD_SCH_ID|^ID$|^IDD$|^SRC1$")
REF_COL = re.compile(r"RECEIPT|DEPOSIT|CHECK|SEQ|PHONE|SCORE|ODOMETER|TIME|BOND_NUMBER")
# Nine digits in a row, or 123-45-6789. A ZIP+4 such as 70123-4567 is not matched.
NINE = re.compile(r"(?<![0-9])(?:([0-9]{9})|([0-9]{3})-([0-9]{2})-([0-9]{4}))(?![0-9])")
GLOBS = ("*[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]*",
         "*[0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9][0-9][0-9]*")
norm = lambda m: "".join(g for g in m.groups() if g)

t0 = time.time()
shutil.copyfile(SRC, DST)
db = sqlite3.connect(DST)
db.execute("PRAGMA journal_mode=OFF")
db.execute("PRAGMA synchronous=OFF")

tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
cols = {t: [(r[1], (r[2] or "").upper()) for r in db.execute(f'PRAGMA table_info("{t}")')] for t in tables}
kind = {}  # (table, column) -> "id" | "text" | "ref" | "num"
for t in tables:
    for c, ty in cols[t]:
        u = c.upper()
        kind[(t, c)] = ("num" if ty == "NUMERIC" else "id" if ID_COL.search(u)
                        else "ref" if REF_COL.search(u) else "text")
where9 = lambda c: " OR ".join(f'"{c}" GLOB \'{g}\'' for g in GLOBS)

# The known IDs: every nine-digit value in an ID column. Held in memory only.
known = set()
for (t, c), k in kind.items():
    if k == "id":
        for (v,) in db.execute(f'SELECT DISTINCT "{c}" FROM "{t}" WHERE {where9(c)}'):
            known.update(norm(m) for m in NINE.finditer(str(v)))
print("known IDs", len(known))

rnd = random.SystemRandom()
mock_of, used = {}, set()
for (t, c), k in kind.items():  # never hand out a mock that already appears in the data
    if k != "num":
        for (v,) in db.execute(f'SELECT DISTINCT "{c}" FROM "{t}" WHERE "{c}" GLOB \'*000*\''):
            used.update(norm(m) for m in NINE.finditer(str(v)) if norm(m).startswith("000"))


def mock(real):
    m = mock_of.get(real)
    if m is None:
        if len(used) > 900_000:
            sys.exit("mock range exhausted")
        while True:
            m = "000" + f"{rnd.randrange(1_000_000):06d}"
            if m not in used:
                break
        used.add(m)
        mock_of[real] = m
    return m


def swap_all(v):
    return v if v is None else NINE.sub(lambda m: mock(norm(m)), str(v))


def swap_known(v):
    return v if v is None else NINE.sub(lambda m: mock(norm(m)) if norm(m) in known else m.group(0), str(v))


db.create_function("swap_all", 1, swap_all, deterministic=True)
db.create_function("swap_known", 1, swap_known, deterministic=True)

# 1. Blank credentials.
for t in tables:
    for c, _ in cols[t]:
        if BLANK.search(c.upper()):
            n = db.execute(f'UPDATE "{t}" SET "{c}" = NULL WHERE "{c}" IS NOT NULL').rowcount
            print(f"blanked {t}.{c}: {n}")

# 2. Unique indexes become plain indexes.
for name, sql in db.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND sql LIKE '%UNIQUE%'").fetchall():
    db.execute(f'DROP INDEX "{name}"')
    db.execute(re.sub(r"UNIQUE\s+", "", sql, count=1, flags=re.I))
    print(f"made non-unique: index {name}")

# 3. Numeric columns holding a known ID become text, so a leading 000 survives.
known_int = {int(k) for k in known}


def num_text(v):
    """A whole number that is a known ID gets its leading zeros back; anything else is kept as written."""
    if v is None:
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    if isinstance(v, int):
        return f"{v:09d}" if v in known_int else str(v)
    return str(v)


db.create_function("num_text", 1, num_text, deterministic=True)
for t in tables:
    num_ids = []
    for c, ty in cols[t]:
        if ty != "NUMERIC":
            continue
        vals = db.execute(f'SELECT DISTINCT CAST("{c}" AS INTEGER) FROM "{t}" WHERE "{c}" >= 1000000 '
                          f'AND "{c}" <= 999999999 AND "{c}" = CAST("{c}" AS INTEGER)').fetchall()
        if any(v in known_int for (v,) in vals):
            num_ids.append(c)
    if not num_ids:
        continue
    defs = ", ".join(f'"{c}" {"TEXT" if c in num_ids else ty}' for c, ty in cols[t])
    sel = ", ".join(f'num_text("{c}")' if c in num_ids else f'"{c}"' for c, _ in cols[t])
    idx = [r[0] for r in db.execute("SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (t,))]
    db.execute(f'CREATE TABLE "{t}__new" ({defs})')
    db.execute(f'INSERT INTO "{t}__new" SELECT {sel} FROM "{t}"')
    db.execute(f'DROP TABLE "{t}"')
    db.execute(f'ALTER TABLE "{t}__new" RENAME TO "{t}"')
    for s in idx:
        db.execute(s)
    for c in num_ids:
        kind[(t, c)] = "ref"
    print(f"converted to text: {t}.{', '.join(num_ids)}")
db.commit()

# 4. Swap.
for (t, c), k in kind.items():
    if k == "num":
        continue
    fn = "swap_all" if k in ("id", "text") else "swap_known"
    n = db.execute(f'UPDATE "{t}" SET "{c}" = {fn}("{c}") WHERE {where9(c)}').rowcount
    if n:
        print(f"swapped ({k}) {t}.{c}: {n} rows")
db.commit()

# 5. Check.
real_left = outside_left = 0
for (t, c), k in kind.items():
    if k == "num":
        continue
    for (v,) in db.execute(f'SELECT "{c}" FROM "{t}" WHERE {where9(c)}'):
        for m in NINE.finditer(str(v)):
            d = norm(m)
            real_left += d in known
            outside_left += k in ("id", "text") and not d.startswith("000")
print("distinct values replaced", len(mock_of))
print("known IDs left anywhere", real_left)
print("nine-digit values outside the 000 range left in ID or free-text columns", outside_left)
mock_of.clear()
known.clear()
db.execute("VACUUM")
db.close()
print(f"done in {time.time() - t0:.0f}s")
sys.exit(1 if real_left or outside_left else 0)
