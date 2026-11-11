#!/usr/bin/env python3
"""Parse an Oracle classic `exp` dump (V09.02, conventional path) into CSV + a profile.
Usage: extract_exp.py <dump> <outdir>
Writes <outdir>/<SCHEMA>.<TABLE>.csv, inventory.json (ddl, rows, column profile)."""
import mmap, re, sys, json, csv, os, struct
from decimal import Decimal
from collections import Counter
SYS = {'SYS','SYSTEM','OUTLN','DBSNMP','WMSYS','WKSYS','WKPROXY','ODM','ODM_MTR','OLAPSYS','HR','OE','PM','SH',
       'QS_ADM','QS','QS_WS','QS_ES','QS_OS','QS_CBADM','QS_CB','QS_CS','SCOTT','RMAN','XDB','CTXSYS','MDSYS','ORDSYS','ANONYMOUS'}
dump, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
f = open(dump,'rb'); m = mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ); N = len(m)

def num(b):
    if not b: return None
    if b == b'\x80': return 0
    e = b[0]
    if e & 0x80:
        exp = e - 193; ds = [x-1 for x in b[1:]]; sign = 1
    else:
        exp = 62 - e; bb = b[1:]
        if bb and bb[-1] == 102: bb = bb[:-1]
        ds = [101-x for x in bb]; sign = -1
    v = Decimal(0)
    for i,d in enumerate(ds): v += Decimal(d) * (Decimal(100) ** (exp - i))
    v *= sign
    return int(v) if v == v.to_integral_value() else v.normalize()
def date(b):
    if len(b) != 7: return b.hex()
    y = (b[0]-100)*100 + (b[1]-100)
    s = '%04d-%02d-%02d' % (y, b[2], b[3])
    if (b[4],b[5],b[6]) != (1,1,1): s += ' %02d:%02d:%02d' % (b[4]-1,b[5]-1,b[6]-1)
    return s

events = [(mt.start(),'C',mt.group(1).decode('latin1')) for mt in re.finditer(rb'\nCONNECT ([^\n]+)\n', m)]
events += [(mt.start(),'T',mt.group(1).decode('latin1')) for mt in re.finditer(rb'\nTABLE "([^"\n]+)"\nCREATE TABLE ', m)]
events.sort()
inv = []; schema = None
for off, kind, name in events:
    if kind == 'C': schema = name; continue
    p = off + 1
    p = m.find(b'\n', p) + 1                      # after TABLE line
    e = m.find(b'\n', p); ddl = m[p:e].decode('cp1252','replace')
    rec = {'schema':schema,'table':name,'ddl':ddl,'rows':0,'status':'no-data','offset':off}
    inv.append(rec)
    q = e + 1
    if m[q:q+12] != b'INSERT INTO ':
        # ALTER TABLE ... MODIFY DEFAULT statements can sit between the DDL and the INSERT
        k = m.find(b'\nINSERT INTO "' + name.encode('latin1') + b'" (', q - 1, q + 20000)
        nt = m.find(b'\nTABLE "', q - 1, q + 20000)
        if k < 0 or (0 <= nt < k): continue
        q = k + 1
    e2 = m.find(b'\n', q); ins = m[q:e2].decode('cp1252','replace'); q = e2 + 1
    cols = re.findall(r'"([^"]+)"', ins.split(' VALUES ')[0])[1:]
    if schema in SYS: rec['status'] = 'system-skipped'; continue
    try:
        nc = struct.unpack_from('<H', m, q)[0]; q += 2
        types = []
        for _ in range(nc):
            t, ln = struct.unpack_from('<HH', m, q); q += 4
            if t in (1, 96, 8, 112, 9): q += 4      # charset id + form
            types.append(t)
        if m[q:q+4] != b'\x00\x00\x00\x00': raise ValueError('bad descriptor end %s types=%s' % (m[q:q+4].hex(), types))
        q += 4
        if nc != len(cols): raise ValueError('col count mismatch')
        prof = [{'name':c,'type':t,'nulls':0,'maxlen':0,'min':None,'max':None,'vals':Counter(),'over':False} for c,t in zip(cols,types)]
        path = os.path.join(out, '%s.%s.csv' % (schema, name.replace('/','_')))
        with open(path,'w',newline='',encoding='utf-8') as fh:
            w = csv.writer(fh); w.writerow(cols); rows = 0
            while True:
                if m[q:q+2] == b'\xff\xff': q += 2; break
                row = []
                for i in range(nc):
                    ln = struct.unpack_from('<H', m, q)[0]; q += 2
                    pr = prof[i]
                    if ln == 0xFFFE: row.append(''); pr['nulls'] += 1; continue
                    if ln == 0xFFFF: raise ValueError('unexpected ffff mid-row')
                    b = m[q:q+ln]; q += ln
                    t = types[i]
                    if t == 2: v = num(b)
                    elif t == 12: v = date(b)
                    elif t in (23, 24, 113): v = b.hex()
                    else: v = b.decode('cp1252','replace')
                    row.append(v)
                    if ln > pr['maxlen']: pr['maxlen'] = ln
                    if t in (2, 12) and v is not None:
                        if pr['min'] is None or v < pr['min']: pr['min'] = v
                        if pr['max'] is None or v > pr['max']: pr['max'] = v
                    if not pr['over']:
                        pr['vals'][str(v)] += 1
                        if len(pr['vals']) > 60: pr['over'] = True; pr['vals'] = Counter()
                if m[q:q+2] != b'\x00\x00': raise ValueError('row %d not terminated at %d: %s' % (rows, q, m[q:q+2].hex()))
                q += 2; w.writerow(row); rows += 1
        rec['rows'] = rows; rec['status'] = 'ok'; rec['csv'] = os.path.basename(path)
        rec['columns'] = [{'name':p['name'],'otype':p['type'],'nulls':p['nulls'],'maxlen':p['maxlen'],
                           'min':str(p['min']) if p['min'] is not None else None,'max':str(p['max']) if p['max'] is not None else None,
                           'distinct':(None if p['over'] else len(p['vals'])),
                           'top':(None if p['over'] else p['vals'].most_common(60))} for p in prof]
    except Exception as ex:
        rec['status'] = 'error: %s' % ex
json.dump(inv, open(os.path.join(out,'inventory.json'),'w'), indent=1, default=str)
ok = [r for r in inv if r['status']=='ok']
print('tables', len(inv), 'extracted', len(ok), 'rows', sum(r['rows'] for r in ok))
for r in inv:
    if r['status'].startswith('error'): print('ERR', r['schema'], r['table'], r['status'][:120])
