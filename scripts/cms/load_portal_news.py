"""Load the sample Board News & Publications into the LSBC Portal Content CMS workspace and publish them.

    python3 -I scripts/cms/load_portal_news.py <workspace id> [urlName ...]

Each item in data/cms/PortalNewsSamples.json becomes a Document (content type sfdc_cms__document) whose file is
data/cms/samples/<urlName>.pdf, with URL name <urlName>-doc. On an Aura site a CMS detail page can show only
Document or Image content, so the portal's cards open a Document page that shows the PDF. The PDFs are placeholders
(each says "Sample document, not an official Board publication") until LSBC sends real agendas, minutes and
school publications. Give URL names to load only those. Items already in the workspace with the same URL name are
reported and skipped. Uses the Salesforce CLI's default org.
"""
import json
import os
import subprocess
import sys
import urllib.request
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
API = '/services/data/v66.0/connect/cms'


def org():
    out = subprocess.run(['sf', 'org', 'display', '--json'], capture_output=True, text=True).stdout
    r = json.loads(out)['result']
    return r['instanceUrl'], r['accessToken']


def call(base, token, path, method='GET', body=None, headers=None):
    req = urllib.request.Request(base + API + path, data=body, method=method,
                                 headers={'Authorization': 'Bearer ' + token, **(headers or {})})
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read() or b'{}')
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b'[]')


def multipart(fields):
    """fields: list of (name, filename or None, content type, bytes)."""
    boundary = uuid.uuid4().hex
    parts = []
    for name, filename, ctype, data in fields:
        disp = f'form-data; name="{name}"' + (f'; filename="{filename}"' if filename else '')
        parts.append(f'--{boundary}\r\nContent-Disposition: {disp}\r\nContent-Type: {ctype}\r\n\r\n'.encode() + data + b'\r\n')
    return b''.join(parts) + f'--{boundary}--\r\n'.encode(), 'multipart/form-data; boundary=' + boundary


def main(space, only):
    base, token = org()
    items = json.load(open(os.path.join(ROOT, 'data/cms/PortalNewsSamples.json')))
    ids = []
    for item in items:
        if only and item['urlName'] not in only:
            continue
        pdf = os.path.join(ROOT, 'data/cms/samples', item['urlName'] + '.pdf')
        meta = {'contentSpaceOrFolderId': space, 'contentType': 'sfdc_cms__document', 'title': item['title'],
                'urlName': item['urlName'] + '-doc', 'contentBody': {'sfdc_cms:media': {'source': {'type': 'file'}}}}
        body, ctype = multipart([('ManagedContentInputParam', None, 'application/json', json.dumps(meta).encode()),
                                 ('contentData', item['urlName'] + '.pdf', 'application/pdf', open(pdf, 'rb').read())])
        res = call(base, token, '/contents', 'POST', body, {'Content-Type': ctype})
        if isinstance(res, list):
            print('skipped', item['urlName'], res[0].get('message', '')[:120])
            continue
        print('created', item['urlName'], res['managedContentId'])
        ids.append(res['managedContentId'])
    if ids:
        res = call(base, token, '/contents/publish', 'POST', json.dumps({'contentIds': ids, 'description': 'Sample Board documents'}).encode(),
                   {'Content-Type': 'application/json'})
        print('published', json.dumps(res)[:200])


if __name__ == '__main__':
    main(sys.argv[1], set(sys.argv[2:]))
