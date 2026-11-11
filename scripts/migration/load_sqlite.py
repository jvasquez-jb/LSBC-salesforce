import sqlite3, csv, json, sys, os
csv.field_size_limit(10**9)
inv=json.load(open('extract/inventory.json'))
db=sqlite3.connect('extract/lsbc.sqlite'); db.execute('PRAGMA journal_mode=OFF'); db.execute('PRAGMA synchronous=OFF')
skip=('SM','EVT_')
for r in inv:
    if r['status']!='ok' or r['rows']==0 or r['table'].startswith(skip): continue
    t=r['table'].replace('$','_'); cols=[c['name'] for c in r['columns']]
    db.execute('DROP TABLE IF EXISTS "%s"'%t)
    db.execute('CREATE TABLE "%s" (%s)'%(t, ','.join('"%s" %s'%(c['name'],'NUMERIC' if c['otype']==2 else 'TEXT') for c in r['columns'])))
    with open('extract/'+r['csv'],newline='',encoding='utf-8') as fh:
        rd=csv.reader(fh); next(rd)
        db.executemany('INSERT INTO "%s" VALUES (%s)'%(t,','.join('?'*len(cols))), ([v if v!='' else None for v in row] for row in rd))
    db.commit()
for s in ['CREATE INDEX i_lic_app ON LICENSES(APP_APPLICANT_ID)','CREATE INDEX i_lic_sho ON LICENSES(SHO_CERT_NBR_NUM,SHO_SEQ_NUM)',
          'CREATE INDEX i_lfd_r ON LICENSE_FINANCIAL_DETAILS(LFT_RECEIPT_NUMBER)','CREATE INDEX i_lfd_fs ON LICENSE_FINANCIAL_DETAILS(FS1_SEQ_NUM)',
          'CREATE UNIQUE INDEX i_app ON APPLICANTS(APPLICANT_ID)','CREATE INDEX i_fs ON FINANCIAL_SUMMARIES(SEQ_NUM)','CREATE INDEX i_lft ON LICENSE_FINANCIAL_TRANSACTIONS(RECEIPT_NUMBER)']:
    try: db.execute(s)
    except Exception as e: print('IDX FAIL', s, e)
db.commit(); print('loaded')
