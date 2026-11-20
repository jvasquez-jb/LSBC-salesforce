"""Load the document checklist templates (Action Plan templates) into an org.

Each form's document checklist is an Action Plan template: one Document Checklist Item per document, with its
document type, category, instruction and whether it is required. `Subflow: Document Checklist Generate` reads the
latest published version of the template whose Unique Name matches the application, and creates the checklist items.

Template metadata stores document types and categories as record Ids, which differ between orgs, so templates are
loaded as data by this script, matching document types and categories by developer name. It creates only templates
the org doesn't have yet, and publishes them. Templates that exist are left alone: once loaded, an admin edits them
in Setup, Action Plan Templates (a change is a new version, published when ready).

Source: data/actionPlanTemplates/DocumentChecklists.csv, one row per checklist item. IsSentToBoard true puts the item
in the Sent to the Board category: the subflow then ticks the item's Sent to the Board box and files it under its
document type's usual category.

Run from the repo root: python3 -I scripts/actionplans/load_templates.py [--target-org <alias>] [--dry-run]
"""
import csv, json, subprocess, sys, urllib.parse, urllib.request
from collections import OrderedDict

API = 'v66.0'
args = sys.argv[1:]
org = args[args.index('--target-org') + 1] if '--target-org' in args else None
dry = '--dry-run' in args

cmd = ['sf', 'org', 'display', '--json'] + (['--target-org', org] if org else [])
info = json.loads(subprocess.run(cmd, capture_output=True, text=True).stdout)['result']
BASE, TOKEN = info['instanceUrl'], info['accessToken']

def call(method, path, body=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else None
    except urllib.error.HTTPError as err:
        sys.exit(f'{method} {path} failed: {err.read().decode()}')

def query(soql):
    return call('GET', f'/services/data/{API}/query?q=' + urllib.parse.quote(soql))['records']

def create(records):
    """Creates records 200 at a time, all or none; returns their Ids in order."""
    ids = []
    for i in range(0, len(records), 200):
        res = call('POST', f'/services/data/{API}/composite/sobjects', {'allOrNone': True, 'records': records[i:i + 200]})
        bad = [r for r in res if not r['success']]
        if bad:
            sys.exit(f'create failed: {bad}')
        ids += [r['id'] for r in res]
    return ids

doc_types = query('SELECT Id, DeveloperName, MasterLabel FROM DocumentType')
types = {r['DeveloperName']: r['Id'] for r in doc_types}
labels = {r['DeveloperName']: r['MasterLabel'] for r in doc_types}
cats = {r['DeveloperName']: r['Id'] for r in query('SELECT Id, DeveloperName FROM DocumentCategory')}
type_cat = {r['DocumentType']['DeveloperName']: r['DocumentCategoryId'] for r in
            query('SELECT DocumentType.DeveloperName, DocumentCategoryId FROM DocumentCategoryDocumentType WHERE DocumentTypeId != null')}
if 'SentToTheBoard' not in cats:
    sys.exit('Document category SentToTheBoard is missing: deploy force-app/main/default/documentCategory first.')

templates = OrderedDict()
for row in csv.DictReader(open('data/actionPlanTemplates/DocumentChecklists.csv')):
    templates.setdefault(row['TemplateUniqueName'], []).append(row)

missing = sorted({r['DocumentType'] for rows in templates.values() for r in rows} - set(types))
if missing:
    sys.exit(f'Document types not in the org (load data/seed/DocumentType.json first): {missing}')

existing = {r['UniqueName'] for r in query('SELECT UniqueName FROM ActionPlanTemplate')}
for un, rows in templates.items():
    if un in existing:
        print(f'{un}: exists, left alone')
        continue
    print(f'{un}: creating with {len(rows)} items' + (' (dry run)' if dry else ''))
    if dry:
        continue
    first = rows[0]
    tid = create([{'attributes': {'type': 'ActionPlanTemplate'}, 'Name': first['TemplateLabel'], 'UniqueName': un,
                   'TargetEntityType': first['TargetObject'], 'ActionPlanType': 'Industries',
                   'IsAdHocItemCreationEnabled': False, 'Description': first['TemplateDescription']}])[0]
    vid = query(f"SELECT Id FROM ActionPlanTemplateVersion WHERE ActionPlanTemplateId = '{tid}' ORDER BY Version DESC LIMIT 1")[0]['Id']
    items = []
    for r in rows:
        label = r['_label'] = labels[r['DocumentType']]
        items.append({'attributes': {'type': 'ActionPlanTemplateItem'}, 'ActionPlanTemplateVersionId': vid, 'Name': label,
                      'UniqueName': f"{un}_{r['DocumentType']}"[:80], 'ItemEntityType': 'DocumentChecklistItem',
                      'IsRequired': r['IsRequired'] == 'true', 'DisplayOrder': int(r['DisplayOrder'])})
    item_ids = create(items)
    values = []
    for iid, r in zip(item_ids, rows):
        cat = cats['SentToTheBoard'] if r['IsSentToBoard'] == 'true' else type_cat.get(r['DocumentType'])
        fields = [('Name', r['_label']), ('DocumentTypeId', types[r['DocumentType']]), ('IsRequired', r['IsRequired']),
                  ('Status', 'New'), ('Instruction', r['Instruction']), ('DocumentCategoryId', cat)]
        for f, v in fields:
            if v:
                values.append({'attributes': {'type': 'ActionPlanTemplateItemValue'}, 'ActionPlanTemplateItemId': iid,
                               'Name': f'DocumentChecklistItem.{f}', 'ItemEntityFieldName': f'DocumentChecklistItem.{f}',
                               'ValueLiteral': v})
    create(values)
    call('PATCH', f'/services/data/{API}/sobjects/ActionPlanTemplateVersion/{vid}', {'Status': 'Final'})
print('done')
