"""Phase 2 staff security, generated from docs/LSBC Access Matrix.xlsx.

Writes, under force-app/main/default:
  permissionsets/<Block>.permissionset-meta.xml        the 18 building blocks (Permission Sets tab)
  permissionsetgroups/<Desk>.permissionsetgroup-meta.xml one group per desk (Membership tab)
  mutingpermissionsets/<Desk>Muting.mutingpermissionset-meta.xml
                                                        takes away what the desk's Sharing Settings column doesn't give
  sharingRules/<Object>.sharingRules-meta.xml           from the Sharing Rules tab

Field access comes from scripts/generators/security_fields.json (every field the admin can be given access to,
from FieldPermissions); refresh it when fields are added:
  sf data query --json -q "SELECT Field, PermissionsEdit FROM FieldPermissions WHERE SobjectType IN (<objects>)
    AND ParentId IN (SELECT PermissionSetId FROM PermissionSetAssignment WHERE AssigneeId = '<admin user id>')"
  then keep each Field with PermissionsEdit or-ed across rows, leaving out Contact.MockSocialSecurityNumber__c.
Fields a page layout shows read-only stay read-only.

Run from the repo root:  python3 -I scripts/generators/security.py
"""
import json
import os
import re
import site
import sys
from xml.sax.saxutils import escape

sys.path.append(site.getusersitepackages())  # openpyxl lives in the user site; -I drops it
import openpyxl  # noqa: E402

ROOT = 'force-app/main/default'
WORKBOOK = 'docs/LSBC Access Matrix.xlsx'
FIELDS = json.load(open('scripts/generators/security_fields.json'))
PSL = 'PublicSectorAccessPSL'

# Matrix record -> Salesforce objects it covers.
OBJECTS = {
    'Person Account': ['Account', 'Contact'],
    'Establishment': ['Account'],
    'School': ['Account'],
    'Organization': ['Account'],
    'Account Contact Relation': [],
    'License': ['BusinessLicense'],
    'Individual Application': ['IndividualApplication'],
    'Business Application': ['BusinessLicenseApplication'],
    'License Type': ['RegulatoryAuthorizationType'],
    'Fee Product': ['Product2'],
    'Fee Owed': ['RegulatoryTrxnFee', 'RegulatoryTrxnFeeItem'],
    'Payment': ['Payment__c', 'PaymentAllocation__c'],
    'Hold (Stop Code)': ['RecordAlert'],
    'Examination': ['PersonExamination'],
    'Accommodation': ['PersonDisability'],
    'Education': ['PersonEducation'],
    'Training Course': ['TrnCourse'],
    'Course Offering': ['CourseOffering'],
    'Student Hours': ['TrainingCourseParticipant'],
    'Accreditation / Bond': ['Accreditation'],
    'Complaint': ['PublicComplaint', 'ComplaintCase'],
    'Case': ['Case'],
    'Inspection Visit': ['Visit'],
}
# Detail objects whose permissions can't exceed their master's.
DETAIL = {'RegulatoryTrxnFeeItem', 'PaymentAllocation__c', 'ComplaintCase'}
# Objects outside the matrix that the building blocks also need (level 0-4).
EXTRA = {
    'LicensingRead': {'DocumentChecklistItem': 1, 'RegulatoryCodeViolation': 1, 'Examination': 1,
                      'RegulatoryCode': 1, 'PersonLanguage': 1},
    'PeopleMaintenance': {'PersonLanguage': 3},
    'ApplicationProcessing': {'DocumentChecklistItem': 3, 'CertificationNumberCounter__c': 3,
                              'EstablishmentNumberCounter__c': 3},
    'CaseWork': {'RegulatoryCodeViolation': 3},
    'InspectionWork': {'RegulatoryCodeViolation': 3},
}
# Muting beyond the matrix: only Inspector, Compliance Officer and Program Manager create violations.
EXTRA_MUTE = {d: {'RegulatoryCodeViolation': 1} for d in ('FrontDeskSupervisor', 'FrontDesk', 'ProblemDesk')}
# Fields only one building block may see (others never get them).
RESTRICTED = {
    'Contact.SocialSecurityNumber__c': ('IdentityAccess', True),
    'PersonDisability.AccommodationDetails__c': ('AccommodationAccess', True),
    'PersonDisability.Accommodations__c': ('AccommodationAccess', True),
}
for f in ('RefundAmount__c', 'RefundCheckNumber__c', 'RefundRequestedBy__c', 'RefundRequestedByUser__c', 'RefundRequestedDate__c',
          'RefundStatus__c', 'RefundVerifiedBy__c', 'RefundVerifiedDate__c', 'RefundedDate__c'):
    RESTRICTED['Payment__c.' + f] = ('RefundProcessing', False)  # only the Refund flow sets them
# Read on one object needs read on another (Salesforce rejects the set otherwise).
DEPENDS = {'BusinessLicenseApplication': ['RegulatoryAuthorizationType'],
           'IndividualApplication': ['RegulatoryAuthorizationType'],
           'Account': ['Contact'], 'Visit': ['Location'], 'RegulatoryCode': ['RegulatoryAuthority'], 'RecordAlert': ['Account']}


def with_dependencies(objs):
    changed = True
    while changed:  # a dependency can bring its own (stop codes need Account, Account needs Contact)
        changed = False
        for obj, deps in DEPENDS.items():
            if objs.get(obj, 0) >= 1:
                for d in deps:
                    if objs.get(d, 0) < 1:
                        objs[d] = 1
                        changed = True
    return objs


# Custom permissions granted by a building block.
CUSTOM_PERMISSIONS = {'ConfidentialComplainantAccess': ['ViewConfidentialComplainant']}
# Custom permissions a licensed block needs: they go in its unlicensed <Block>Extra set.
EXTRA_CUSTOM_PERMISSIONS = {'AccommodationAccess': ['ViewAccommodationDocuments']}

RECORD_TYPES = {
    'PeopleMaintenance': ['PersonAccount.PersonAccount', 'Account.Establishment'],
    'SchoolOversight': ['Account.School', 'Account.Organization'],
    'ApplicationProcessing': ['IndividualApplication.NewLicensure', 'IndividualApplication.Reciprocity',
                              'IndividualApplication.Renewal', 'BusinessLicenseApplication.NewEstablishment',
                              'BusinessLicenseApplication.NewSchool', 'BusinessLicenseApplication.Renewal'],
}
# Apex and Visualforce access can't sit in a Public Sector-licensed set: the LSBC Standard User profile grants
# it (profiles/LSBC Standard User). Object access still decides what the letter and licence pages can read.
CLASSES = {}
PAGES = {}
# Staff action flows: run in system context with sharing, and only by the blocks that grant them.
FLOWS = {
    'PaymentEntry': ['ScreenFlowAccountRecordPayment', 'ScreenFlowRegulatoryTransactionFeeItemChangeYear'],
    'RefundProcessing': ['ScreenFlowPaymentRefund'],
    'ApplicationProcessing': ['ScreenFlowIndividualApplicationDecide', 'ScreenFlowBusinessLicenseApplicationDecide',
                              'ScreenFlowLetterGenerate', 'ScreenFlowAccountNewApplication',
                              'ScreenFlowIndividualApplicationNewLicensure'],
    'HoldManagement': ['ScreenFlowAccountAddStopCode', 'ScreenFlowRecordAlertEndStopCode'],
    'LicenseMaintenance': ['ScreenFlowBusinessLicenseMarkPrinted'],
    'CaseWork': ['ScreenFlowCaseRecordComplaint'],
    'PeopleMaintenance': ['ScreenFlowCaseApplyAddressChange'],
}
LABELS = {
    'LicensingRead': 'Licensing Read', 'PeopleMaintenance': 'People Maintenance',
    'LicenseMaintenance': 'License Maintenance', 'ApplicationProcessing': 'Application Processing',
    'PaymentEntry': 'Payment Entry', 'RefundProcessing': 'Refund Processing', 'HoldManagement': 'Hold Management',
    'ExamAdministration': 'Exam Administration', 'AccommodationAccess': 'Accommodation Access',
    'IdentityAccess': 'Identity Access', 'StudentHours': 'Student Hours', 'SchoolOversight': 'School Oversight',
    'BondsAndApprovals': 'Bonds And Approvals', 'CaseRead': 'Case Read', 'CaseWork': 'Case Work',
    'InspectionWork': 'Inspection Work', 'ReportsRead': 'Reports Read',
    'ReferenceDataMaintenance': 'Reference Data Maintenance',
    'ConfidentialComplainantAccess': 'Confidential Complainant Access',
}
DESK_LABELS = {
    'ExecutiveDirector': 'Executive Director', 'ComplianceOfficer': 'Compliance Officer', 'Finance': 'Finance',
    'FrontDeskSupervisor': 'Front Desk Supervisor', 'FrontDesk': 'Front Desk', 'Mailroom': 'Mailroom',
    'ProblemDesk': 'Problem Desk', 'RenewalDesk': 'Renewal Desk', 'ReciprocityDesk': 'Reciprocity Desk',
    'StudentRegistration': 'Student Registration', 'ProgramManager': 'Program Manager',
    'TestingDesk': 'Testing Desk', 'Inspector': 'Inspector',
}


def read_only_on_layouts():
    """Fields some page layout shows read-only: a flow or the applicant sets them."""
    out = set()
    for name in os.listdir(f'{ROOT}/layouts'):
        obj = name.split('-')[0]
        obj = 'Account' if obj == 'PersonAccount' else obj
        s = open(f'{ROOT}/layouts/{name}').read()
        for item in re.findall(r'<layoutItems>(.*?)</layoutItems>', s, re.S):
            b = re.search(r'<behavior>(\w+)</behavior>', item)
            f = re.search(r'<field>([\w.]+)</field>', item)
            if b and f and b.group(1) == 'Readonly':
                fld = f.group(1)
                if obj == 'Account' and fld.endswith('__pc'):
                    out.add('Contact.' + fld[:-4] + '__c')
                else:
                    out.add(f'{obj}.{fld}')
    return out


READONLY = read_only_on_layouts()

# ---- workbook ----
wb = openpyxl.load_workbook(WORKBOOK)
ps, mem, ss, srt = wb['Permission Sets'], wb['Membership'], wb['Sharing Settings'], wb['Sharing Rules']
MATRIX = [ps.cell(4, c).value for c in range(3, 26)]
BLOCKS = {}
r = 5
while ps.cell(r, 1).value and ps.cell(r, 1).value != 'Object API names':
    BLOCKS[ps.cell(r, 1).value] = ({MATRIX[i]: int(ps.cell(r, 3 + i).value or 0) for i in range(23)},
                                   ps.cell(r, 2).value)
    r += 1
DESKS = [mem.cell(4, c).value for c in range(2, 15)]
HELD = {d: [list(BLOCKS)[k] for k in range(len(BLOCKS)) if mem.cell(5 + k, 2 + i).value == 'X']
        for i, d in enumerate(DESKS)}
CAP = {}
for row in range(5, 28):
    rec = ss.cell(row, 1).value
    for i, d in enumerate(ss.cell(4, c).value for c in range(6, 19)):
        v = ss.cell(row, 6 + i).value or '—'
        CAP.setdefault(d, {})[rec] = 3 if v.startswith('Edit') else 1 if v.startswith('Read') else 0


def object_levels(levels_by_record):
    """Matrix levels -> Salesforce object levels (max over the records an object covers)."""
    out = {}
    for rec, lvl in levels_by_record.items():
        for obj in OBJECTS[rec]:
            if obj == 'Contact' and rec != 'Person Account':
                continue
            out[obj] = max(out.get(obj, 0), lvl)
    return out


def obj_perm_xml(obj, lvl, muting=False):
    flags = [('allowCreate', lvl >= 3), ('allowDelete', lvl >= 4), ('allowEdit', lvl >= 2), ('allowRead', lvl >= 1),
             ('modifyAllRecords', False)]
    body = ''.join(f'        <{k}>{"true" if v else "false"}</{k}>\n' for k, v in flags)
    body += f'        <object>{obj}</object>\n        <viewAllRecords>false</viewAllRecords>\n'
    return f'    <objectPermissions>\n{body}    </objectPermissions>\n'


def field_perms(block, objs):
    out = []
    for field, admin_edit in FIELDS.items():
        obj = field.split('.')[0]
        lvl = objs.get(obj, 0)
        if lvl < 1:
            continue
        if field in RESTRICTED:
            owner, editable = RESTRICTED[field]
            if owner != block:
                continue
            edit = editable and admin_edit and lvl >= 2
        else:
            edit = admin_edit and lvl >= 2 and field not in READONLY
        out.append((field, edit))
    # Restricted fields reach their owner even if it grants no other access to the object.
    for field, (owner, editable) in RESTRICTED.items():
        if owner == block and field in FIELDS and not any(f == field for f, _ in out):
            out.append((field, editable and FIELDS[field]))
    return sorted(out)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w').write(text)


HEAD = '<?xml version="1.0" encoding="UTF-8"?>\n'
NS = 'xmlns="http://soap.sforce.com/2006/04/metadata"'
PSS_STANDARD = {'Account', 'Contact', 'Case', 'Product2'}

# ---- permission sets ----
# A set carrying the Public Sector Access licence silently drops these objects (and their fields): they go into
# an unlicensed companion, <Block>Extra, held by the same desk groups. A set's licence can't change once created.
NON_PSL = {'Payment__c', 'PaymentAllocation__c', 'CertificationNumberCounter__c', 'EstablishmentNumberCounter__c',
           'Product2', 'RecordAlert', 'DocumentChecklistItem'}
EXTRA_SETS = set()
for block, (levels, purpose) in BLOCKS.items():
    objs = object_levels(levels)
    for obj, lvl in EXTRA.get(block, {}).items():
        objs[obj] = max(objs.get(obj, 0), lvl)
    with_dependencies(objs)
    parts = []
    # The LSBC Licensing app is granted by the LSBC Standard User profile (a licensed set can't assign apps).
    for c in CLASSES.get(block, []):
        parts.append(f'    <classAccesses>\n        <apexClass>{c}</apexClass>\n        <enabled>true</enabled>\n'
                     '    </classAccesses>\n')
    for cp in CUSTOM_PERMISSIONS.get(block, []):
        parts.append(f'    <customPermissions>\n        <enabled>true</enabled>\n        <name>{cp}</name>\n'
                     '    </customPermissions>\n')
    needs_psl = any(o not in PSS_STANDARD and not o.endswith('__c') for o, l in objs.items() if l > 0)
    extra = {o: l for o, l in objs.items() if l > 0 and o in NON_PSL} if needs_psl else {}
    if extra or block in EXTRA_CUSTOM_PERMISSIONS:
        objs = {o: l for o, l in objs.items() if o not in extra}
        with_dependencies(extra)
        EXTRA_SETS.add(block)
        xp = [f'    <customPermissions>\n        <enabled>true</enabled>\n        <name>{cp}</name>\n'
              '    </customPermissions>\n' for cp in EXTRA_CUSTOM_PERMISSIONS.get(block, [])]
        xp.append(f'    <description>The part of {block} the Public Sector Access licence can\'t carry (objects such as '
                  f'payments and stop codes, and custom permissions). Generated by scripts/generators/security.py.'
                  '</description>\n')
        for field, edit in field_perms(block, extra):
            if field.split('.')[0] not in extra:
                continue
            xp.append(f'    <fieldPermissions>\n        <editable>{"true" if edit else "false"}</editable>\n'
                      f'        <field>{field}</field>\n        <readable>true</readable>\n    </fieldPermissions>\n')
        xp.append(f'    <hasActivationRequired>false</hasActivationRequired>\n    <label>{LABELS[block]} Extra</label>\n')
        for obj in sorted(extra):
            xp.append(obj_perm_xml(obj, extra[obj]))
        if block == 'LicensingRead':
            xp.append('    <tabSettings>\n        <tab>Payment__c</tab>\n        <visibility>Visible</visibility>\n'
                      '    </tabSettings>\n')
        write(f'{ROOT}/permissionsets/{block}Extra.permissionset-meta.xml',
              f'{HEAD}<PermissionSet {NS}>\n{"".join(xp)}</PermissionSet>\n')
    parts.append(f'    <description>{escape(purpose)} Generated by scripts/generators/security.py from the '
                 f'LSBC Access Matrix.</description>\n')
    for field, edit in field_perms(block, objs):
        parts.append(f'    <fieldPermissions>\n        <editable>{"true" if edit else "false"}</editable>\n'
                     f'        <field>{field}</field>\n        <readable>true</readable>\n    </fieldPermissions>\n')
    for fl in FLOWS.get(block, []):
        parts.append(f'    <flowAccesses>\n        <enabled>true</enabled>\n        <flow>{fl}</flow>\n'
                     '    </flowAccesses>\n')
    parts.append('    <hasActivationRequired>false</hasActivationRequired>\n')
    parts.append(f'    <label>{LABELS[block]}</label>\n')
    if needs_psl:
        parts.append(f'    <license>{PSL}</license>\n')
    for obj in sorted(o for o, l in objs.items() if l > 0):
        parts.append(obj_perm_xml(obj, objs[obj]))
    for pg in PAGES.get(block, []):
        parts.append(f'    <pageAccesses>\n        <apexPage>{pg}</apexPage>\n        <enabled>true</enabled>\n'
                     '    </pageAccesses>\n')
    for rt in RECORD_TYPES.get(block, []):
        parts.append(f'    <recordTypeVisibilities>\n        <recordType>{rt}</recordType>\n'
                     '        <visible>true</visible>\n    </recordTypeVisibilities>\n')
    if block == 'ReportsRead':
        for p in ('RunReports',):
            parts.append(f'    <userPermissions>\n        <enabled>true</enabled>\n        <name>{p}</name>\n'
                         '    </userPermissions>\n')
    write(f'{ROOT}/permissionsets/{block}.permissionset-meta.xml',
          f'{HEAD}<PermissionSet {NS}>\n{"".join(parts)}</PermissionSet>\n')

# ---- muting sets and groups ----
for desk in DESKS:
    granted = {}
    for b in HELD[desk]:
        objs = object_levels(BLOCKS[b][0])
        for obj, lvl in EXTRA.get(b, {}).items():
            objs[obj] = max(objs.get(obj, 0), lvl)
        for o, l in objs.items():
            granted[o] = max(granted.get(o, 0), l)
    allowed = object_levels(CAP[desk])
    for o, l in EXTRA_MUTE.get(desk, {}).items():
        allowed[o] = min(allowed.get(o, 4), l)
    mutes = []
    for obj in sorted(granted):
        g = granted[obj]
        a = allowed.get(obj, g)  # objects outside the matrix stay as granted
        if obj in DETAIL:
            master = {'RegulatoryTrxnFeeItem': 'RegulatoryTrxnFee', 'PaymentAllocation__c': 'Payment__c',
                      'ComplaintCase': 'PublicComplaint'}[obj]
            a = min(a, allowed.get(master, a))
        if a < g:
            # A muting entry's true flags are the permissions taken away.
            # Salesforce needs Delete and Modify All muted with Edit, and everything muted with Read.
            mute_read, mute_edit, mute_create = a < 1, a < 2, a < 3
            off = [('allowCreate', mute_create or mute_edit), ('allowDelete', True), ('allowEdit', mute_edit),
                   ('allowRead', mute_read), ('modifyAllRecords', True)]
            body = ''.join(f'        <{k}>{"true" if v else "false"}</{k}>\n' for k, v in off)
            body += (f'        <object>{obj}</object>\n        <viewAllRecords>{"true" if mute_read else "false"}'
                     '</viewAllRecords>\n')
            mutes.append(f'    <objectPermissions>\n{body}    </objectPermissions>\n')
    label = DESK_LABELS[desk]
    write(f'{ROOT}/mutingpermissionsets/{desk}Muting.mutingpermissionset-meta.xml',
          f'{HEAD}<MutingPermissionSet {NS}>\n    <label>{label} Muting</label>\n{"".join(mutes)}'
          '</MutingPermissionSet>\n')
    # Every desk opens checklist items, which needs Salesforce's Document Checklist set (and its licence per user).
    sets = ''.join(f'    <permissionSets>{b}</permissionSets>\n'
                   for b in sorted(HELD[desk] + [x + 'Extra' for x in HELD[desk] if x in EXTRA_SETS]) + ['force__DocumentChecklist'])
    write(f'{ROOT}/permissionsetgroups/{desk}.permissionsetgroup-meta.xml',
          f'{HEAD}<PermissionSetGroup {NS}>\n    <description>The {label} desk. Generated by '
          f'scripts/generators/security.py from the LSBC Access Matrix.</description>\n'
          f'    <hasActivationRequired>false</hasActivationRequired>\n    <label>{label}</label>\n'
          f'    <mutingPermissionSets>{desk}Muting</mutingPermissionSets>\n{sets}'
          '    <status>Updated</status>\n</PermissionSetGroup>\n')

# ---- staff action flows: only the desks whose blocks grant them may run them ----
# They run in system context with sharing: the user sees and changes only records shared with them, and the
# flow does the writes the desk's object permissions alone wouldn't allow (a licence created by Decide).
# Rerun this script after any flow generator, which writes these files afresh.
for flows in FLOWS.values():
    for fl in flows:
        path = f'{ROOT}/flows/{fl}.flow-meta.xml'
        x = open(path).read()
        x = x.replace('<runInMode>DefaultMode</runInMode>', '<runInMode>SystemModeWithSharing</runInMode>')
        if '<runInMode>' not in x:
            x = x.replace('<start>', '<runInMode>SystemModeWithSharing</runInMode><start>', 1) if '<start>' in x else x
        if 'isAdditionalPermissionRequiredToRun' not in x:
            x = re.sub(r'(</interviewLabel>)', r'\1<isAdditionalPermissionRequiredToRun>true</isAdditionalPermissionRequiredToRun>',
                       x, count=1)
        open(path, 'w').write(x)

# Administrators run every gated flow too: PublicSectorAccessAdminPSL gets their flow access (only missing
# entries are added, so other edits to that file stay).
ADMIN = f'{ROOT}/permissionsets/PublicSectorAccessAdminPSL.permissionset-meta.xml'
adm = open(ADMIN).read()
missing = sorted(fl for flows in FLOWS.values() for fl in flows if f'<flow>{fl}</flow>' not in adm)
if missing:
    add = ''.join(f'    <flowAccesses>\n        <enabled>true</enabled>\n        <flow>{fl}</flow>\n    </flowAccesses>\n'
                  for fl in missing)
    anchor = '    <hasActivationRequired>'
    adm = adm.replace(anchor, add + anchor, 1)
    open(ADMIN, 'w').write(adm)

# ---- sharing rules ----
RECORD_OBJECT = {'Accounts': 'Account', 'License': 'BusinessLicense', 'Individual Application': 'IndividualApplication',
                 'Business Application': 'BusinessLicenseApplication', 'License Type': 'RegulatoryAuthorizationType',
                 'Fee Owed': 'RegulatoryTrxnFee', 'Payment': 'Payment__c', 'Hold (Stop Code)': 'RecordAlert',
                 'Examination': 'PersonExamination', 'Accommodation': 'PersonDisability',
                 'Education': 'PersonEducation', 'Training Course': 'TrnCourse', 'Course Offering': 'CourseOffering',
                 'Student Hours': 'TrainingCourseParticipant', 'Accreditation / Bond': 'Accreditation',
                 'Complaint': 'PublicComplaint', 'Case': 'Case', 'Inspection Visit': 'Visit'}
WHICH = {
    'Record type is Person': [('RecordTypeId', 'equals', 'Person')],
    'Record type is Establishment': [('RecordTypeId', 'equals', 'Establishment')],
    'Record type is School': [('RecordTypeId', 'equals', 'School')],
    'Record type is Organization': [('RecordTypeId', 'equals', 'Organization')],
    'Record type is New Licensure': [('RecordTypeId', 'equals', 'New Licensure')],
    'Record type is Renewal': [('RecordTypeId', 'equals', 'Renewal')],
    'Record type is Reciprocity': [('RecordTypeId', 'equals', 'Reciprocity')],
    'Record type is New Establishment or New School': [('RecordTypeId', 'equals', 'New Establishment,New School')],
    'All records': [('Name', 'notEqual', '')],  # Name is always filled, so this matches every record
}
ALWAYS_FILLED = {'Case': 'CaseNumber'}
rules = {}
r = 5
while srt.cell(r, 1).value is not None:
    name, record, which, group, access = (srt.cell(r, c).value for c in range(2, 7))
    r += 1
    if name == 'No rule needed':
        continue
    obj = RECORD_OBJECT[record]
    label = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
    level = 'Edit' if access == 'Read and edit' else 'Read'
    crit = ''.join(f'        <criteriaItems>\n            <field>{f}</field>\n            <operation>{op}</operation>\n'
                   f'            <value>{v}</value>\n        </criteriaItems>\n'
                   for f, op, v in [((ALWAYS_FILLED.get(obj, f) if f == 'Name' else f), op, v) for f, op, v in WHICH[which]])
    extra = ''
    if obj == 'Account':
        extra = ('        <accountSettings>\n            <caseAccessLevel>None</caseAccessLevel>\n'
                 '            <contactAccessLevel>' + level + '</contactAccessLevel>\n'
                 '            <opportunityAccessLevel>None</opportunityAccessLevel>\n        </accountSettings>\n')
    rules.setdefault(obj, []).append(
        f'    <sharingCriteriaRules>\n        <fullName>{name}</fullName>\n'
        f'        <accessLevel>{level}</accessLevel>\n{extra}        <description>{escape(which)}, shared with {group}. '
        f'From the LSBC Access Matrix.</description>\n        <label>{label[:80]}</label>\n'
        f'        <sharedTo>\n            <group>{group}</group>\n        </sharedTo>\n{crit}'
        '        <includeRecordsOwnedByAll>true</includeRecordsOwnedByAll>\n    </sharingCriteriaRules>\n')
# Objects outside the matrix that follow it: checklist items with the applications (the accommodation
# documentation only to the desks that see Accommodation), violations with complaints, the exam catalogue
# and complaint-case links read by everyone.
ACCOMMODATION_ITEM = 'Documentation for Disability Related Needs'
APP_DESKS = ['ComplianceOfficer', 'FrontDeskSupervisor', 'FrontDesk', 'RenewalDesk', 'ReciprocityDesk',
             'StudentRegistration', 'ProgramManager']
EXTRA_RULES = [('DocumentChecklistItemStandardToAllStaff', 'DocumentChecklistItem', 'AllStaff', 'Read',
                'Every checklist item except the accommodation documentation', [('Name', 'notEqual', ACCOMMODATION_ITEM)])]
EXTRA_RULES += [(f'DocumentChecklistItemStandardTo{d}Edit', 'DocumentChecklistItem', d, 'Edit',
                 'Every checklist item except the accommodation documentation', [('Name', 'notEqual', ACCOMMODATION_ITEM)])
                for d in APP_DESKS]
EXTRA_RULES += [(f'DocumentChecklistItemAccommodationTo{d}Edit', 'DocumentChecklistItem', d, 'Edit',
                 'The accommodation documentation (health information)', [('Name', 'equals', ACCOMMODATION_ITEM)])
                for d in ('ReciprocityDesk', 'TestingDesk', 'ProgramManager')]
EXTRA_RULES += [('RegulatoryCodeViolationAllToAllStaff', 'RegulatoryCodeViolation', 'AllStaff', 'Read', 'All records',
                 [('Name', 'notEqual', '')])]
EXTRA_RULES += [(f'RegulatoryCodeViolationAllTo{d}Edit', 'RegulatoryCodeViolation', d, 'Edit', 'All records',
                 [('Name', 'notEqual', '')]) for d in ('ComplianceOfficer', 'ProgramManager', 'Inspector')]
EXTRA_RULES += [('ExaminationAllToAllStaff', 'Examination', 'AllStaff', 'Read', 'All records', [('Name', 'notEqual', '')]),
                ('ComplaintCaseAllToAllStaff', 'ComplaintCase', 'AllStaff', 'Read', 'All records', [('Name', 'notEqual', '')])]
for name, obj, group, level, which, items in EXTRA_RULES:
    label = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
    crit = ''.join(f'        <criteriaItems>\n            <field>{f}</field>\n            <operation>{op}</operation>\n'
                   f'            <value>{escape(v)}</value>\n        </criteriaItems>\n' for f, op, v in items)
    rules.setdefault(obj, []).append(
        f'    <sharingCriteriaRules>\n        <fullName>{name}</fullName>\n        <accessLevel>{level}</accessLevel>\n'
        f'        <description>{escape(which)}, shared with {group}. Follows the LSBC Access Matrix.</description>\n'
        f'        <label>{label[:80]}</label>\n        <sharedTo>\n            <group>{group}</group>\n        </sharedTo>\n'
        f'{crit}        <includeRecordsOwnedByAll>true</includeRecordsOwnedByAll>\n    </sharingCriteriaRules>\n')

for obj, items in rules.items():
    write(f'{ROOT}/sharingRules/{obj}.sharingRules-meta.xml',
          f'{HEAD}<SharingRules {NS}>\n{"".join(items)}</SharingRules>\n')

print('permission sets', len(BLOCKS), '| desks', len(DESKS), '| sharing rules',
      sum(len(v) for v in rules.values()), 'on', len(rules), 'objects')
