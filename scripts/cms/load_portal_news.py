"""Load the sample News items into the LSBC Portal Content CMS workspace and publish them.

    python3 -I scripts/cms/load_portal_news.py <workspace id>

The items (data/cms/PortalNewsSamples.json) are placeholders, each excerpt starting "Sample item.", until LSBC sends
real Board meeting notices, minutes and school publications. Items already in the workspace (same URL name) are skipped.
Uses the default org of the Salesforce CLI.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
API = '/services/data/v66.0/connect/cms'


def api(path, method='GET', body=None):
    cmd = ['sf', 'api', 'request', 'rest', API + path, '--method', method]
    if body is not None:
        cmd += ['--body', json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return json.loads(out[out.index(out.lstrip()[0]):]) if out.strip() else {}


def main(space):
    items = json.load(open(os.path.join(ROOT, 'data/cms/PortalNewsSamples.json')))
    ids = []
    for item in items:
        res = api('/contents', 'POST', {
            'contentSpaceOrFolderId': space,
            'contentType': 'sfdc_cms__news',
            'title': item['title'],
            'urlName': item['urlName'],
            'contentBody': {'excerpt': item['excerpt'], 'body': item['excerpt']},
        })
        if isinstance(res, list):
            print('skipped', item['urlName'], res[0].get('message', '')[:120])
            continue
        print('created', item['urlName'], res['managedContentId'])
        ids.append(res['managedContentId'])
    if ids:
        print(json.dumps(api('/contents/publish', 'POST', {'contentIds': ids, 'description': 'Sample portal news'}))[:300])


if __name__ == '__main__':
    main(sys.argv[1])
