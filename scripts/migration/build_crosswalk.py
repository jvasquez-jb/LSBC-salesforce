"""Build surrogate legacy keys so no load file carries APPLICANT_ID / certificate numbers.
Keys are assigned in random order (not derived from the source value, so they cannot be reversed).
The crosswalk stays in extract/lsbc.sqlite and extract/crosswalk_*.csv, never in Salesforce."""
import sqlite3, random, csv
db=sqlite3.connect('extract/lsbc.sqlite'); rnd=random.SystemRandom()
def build(name, prefix, sql, width):
    rows=db.execute(sql).fetchall(); rnd.shuffle(rows)
    db.execute(f'DROP TABLE IF EXISTS {name}')
    ncol=len(rows[0]); cols=','.join(f'src{i+1} TEXT' for i in range(ncol))
    db.execute(f'CREATE TABLE {name} ({cols}, legacy_key TEXT UNIQUE)')
    data=[tuple(r)+(f'{prefix}-{i+1:0{width}d}',) for i,r in enumerate(rows)]
    db.executemany(f'INSERT INTO {name} VALUES ({",".join("?"*(ncol+1))})', data)
    db.execute(f'CREATE UNIQUE INDEX i_{name} ON {name}({",".join(f"src{i+1}" for i in range(ncol))})')
    with open(f'extract/crosswalk_{name.lower()}.csv','w',newline='') as fh:
        w=csv.writer(fh); w.writerow([f'src{i+1}' for i in range(ncol)]+['legacy_key']); w.writerows(data)
    print(name, len(data), data and 'e.g. format '+prefix+'-'+'0'*width)
build('XW_PERSON','LSBC-P','select APPLICANT_ID from APPLICANTS',7)
build('XW_SHOP','LSBC-S','select CERT_NBR_NUM, cast(SEQ_NUM as text) from SHOPS',6)
build('XW_SCHOOL','LSBC-SC','select CERT_NBR_NUM, cast(SEQ_NUM as text) from SCHOOLS',4)
db.commit()
