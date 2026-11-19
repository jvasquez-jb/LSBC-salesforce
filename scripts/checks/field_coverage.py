"""Checks that every custom field in force-app has admin field access and sits on its object's layout.

Usage, from the repo root:  python3 -I scripts/checks/field_coverage.py
Exits 1 and lists the gaps when a field is missing from PublicSectorAccessAdminPSL or from a layout
in force-app/main/default/layouts. Run it before committing a new field.

- Field access: every custom field except required and master-detail fields (Salesforce grants
  those itself) needs a fieldPermissions entry in PublicSectorAccessAdminPSL.
- Layout: every custom field must be on at least one layout of its object (Contact fields on the
  Person Account layout, as __pc). An object with custom fields but no layout in the repo fails:
  retrieve its layout into force-app and add the fields.
- Custom metadata types are skipped (no field access, and their layouts are admin-only).
- EXCEPTIONS lists the fields kept off layouts on purpose, with the reason.
"""
import glob
import os
import re
import sys

ROOT = 'force-app/main/default'
PERMSET = f'{ROOT}/permissionsets/PublicSectorAccessAdminPSL.permissionset-meta.xml'

# Fields deliberately left off every layout. Field access is still checked.
EXCEPTIONS = {
    'Contact.SocialSecurityNumber__c': 'Sensitive and on the encrypted list; shown nowhere on staff pages.',
}

perm = set(re.findall(r'<field>([^<]+)</field>', open(PERMSET).read()))
layouts = {}
for f in glob.glob(f'{ROOT}/layouts/*.layout-meta.xml'):
    obj = os.path.basename(f).split('-')[0]
    layouts.setdefault(obj, set()).update(re.findall(r'<field>([^<]+)</field>', open(f).read()))

gaps = []
for d in sorted(glob.glob(f'{ROOT}/objects/*/fields')):
    obj = d.split('/')[-2]
    if obj.endswith('__mdt'):
        continue
    lay_obj = 'PersonAccount' if obj == 'Contact' else obj
    for f in sorted(glob.glob(f'{d}/*.field-meta.xml')):
        x = open(f).read()
        name = os.path.basename(f).replace('.field-meta.xml', '')
        if not name.endswith('__c'):
            continue  # a standard field's file only switches on its field history (scripts/generators/history.py)
        full = f'{obj}.{name}'
        auto = '<required>true</required>' in x or '<type>MasterDetail</type>' in x
        if not auto and full not in perm:
            gaps.append(f'{full}: no field access in PublicSectorAccessAdminPSL')
        if full in EXCEPTIONS:
            continue
        lay_name = name.replace('__c', '__pc') if obj == 'Contact' else name
        if lay_obj not in layouts:
            gaps.append(f'{full}: no {lay_obj} layout in force-app (retrieve it and add the field)')
        elif lay_name not in layouts[lay_obj]:
            gaps.append(f'{full}: not on any {lay_obj} layout')

if gaps:
    print('\n'.join(gaps))
    sys.exit(1)
print('Every custom field has admin field access and is on a layout.')
