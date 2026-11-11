import zipfile, re, sys, html
def pptx(p):
    z=zipfile.ZipFile(p)
    slides=sorted([n for n in z.namelist() if re.match(r'ppt/slides/slide\d+\.xml',n)], key=lambda n:int(re.findall(r'\d+',n)[-1]))
    for n in slides:
        x=z.read(n).decode('utf8')
        print('--- ',n)
        for para in re.findall(r'<a:p>.*?</a:p>|<a:p [^>]*>.*?</a:p>', x, flags=re.S):
            t=''.join(re.findall(r'<a:t>([^<]*)</a:t>', para))
            if t.strip(): print(html.unescape(t))
def xlsx(p, maxrows=400):
    z=zipfile.ZipFile(p)
    ss=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        x=z.read('xl/sharedStrings.xml').decode('utf8')
        for si in re.findall(r'<si>(.*?)</si>', x, flags=re.S):
            ss.append(html.unescape(''.join(re.findall(r'<t[^>]*>([^<]*)</t>', si))))
    for n in sorted(k for k in z.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml',k)):
        x=z.read(n).decode('utf8'); rows=re.findall(r'<row [^>]*>(.*?)</row>', x, flags=re.S)
        print('--- ',n, len(rows),'rows')
        for r in rows[:maxrows]:
            out=[]
            for attrs,inner in re.findall(r'<c ([^>]*?)(?:/>|>(.*?)</c>)', r, flags=re.S):
                v=re.search(r'<v>([^<]*)</v>', inner or ''); 
                if not v: out.append(''); continue
                val=v.group(1)
                out.append(ss[int(val)] if 't="s"' in attrs else html.unescape(val))
            print(' | '.join(out))
p=sys.argv[1]
(pptx if p.endswith('.pptx') else xlsx)(p)
