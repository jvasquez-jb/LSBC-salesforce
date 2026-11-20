"""Desk access check: moves a test user through each desk (role + permission set group) and compares their
access with docs/LSBC Access Matrix.xlsx: record access on one sample record of each kind (UserRecordAccess),
whether each object opens in the screens at all (UserEntityAccess: an object can be shared and still closed, for
example without the Public Sector Access or Record Alert user permission), and the staff flows and custom permissions
they hold. Changes the test user's role and group; put them back after.

  python3 scripts/checks/desk_access.py <test user id> [Desk,Desk,...]

Needs openpyxl (user site) and the sf CLI on the default org. The test user needs the LSBC Standard User profile
and the Public Sector Access and Document Checklist licences.
"""
import json, subprocess, sys, re, time, site
sys.path.append(site.getusersitepackages()); import openpyxl
TIM = sys.argv[1]; DESKS_ARG = sys.argv[2].split(',') if len(sys.argv) > 2 else None
import tempfile
S = tempfile.mkdtemp()
ROLE = {'Inspector': 'Inspector'}
def sf(*a):
    r = subprocess.run(['sf', *a, '--json'], capture_output=True, text=True).stdout
    return json.loads(r[r.find('{'):])
def q(soql): return sf('data', 'query', '-q', soql)['result']['records']
def apex(code):
    open(f'{S}/swap.apex', 'w').write(code)
    r = subprocess.run(['sf', 'apex', 'run', '-f', f'{S}/swap.apex'], capture_output=True, text=True).stdout
    assert 'DONE' in r, r[-1500:]
def sample_records(TIM):
    """One record of each kind the test user doesn't own."""
    ns = f"OwnerId != '{TIM}'"
    S={
     'Person Account':"SELECT Id FROM Account WHERE IsPersonAccount=true AND {ns} LIMIT 1",
     'Establishment':"SELECT Id FROM Account WHERE RecordType.DeveloperName='Establishment' AND {ns} LIMIT 1",
     'School':"SELECT Id FROM Account WHERE RecordType.DeveloperName='School' AND {ns} LIMIT 1",
     'Organization':"SELECT Id FROM Account WHERE RecordType.DeveloperName='Organization' AND {ns} LIMIT 1",
     'License':"SELECT Id FROM BusinessLicense WHERE {ns} LIMIT 1",
     'Individual Application|NewLicensure':"SELECT Id FROM IndividualApplication WHERE RecordType.DeveloperName='NewLicensure' AND {ns} LIMIT 1",
     'Individual Application|Renewal':"SELECT Id FROM IndividualApplication WHERE RecordType.DeveloperName='Renewal' AND {ns} LIMIT 1",
     'Individual Application|Reciprocity':"SELECT Id FROM IndividualApplication WHERE RecordType.DeveloperName='Reciprocity' AND {ns} LIMIT 1",
     'Business Application|NewEstablishment':"SELECT Id FROM BusinessLicenseApplication WHERE RecordType.DeveloperName='NewEstablishment' AND {ns} LIMIT 1",
     'Business Application|NewSchool':"SELECT Id FROM BusinessLicenseApplication WHERE RecordType.DeveloperName='NewSchool' AND {ns} LIMIT 1",
     'Business Application|Renewal':"SELECT Id FROM BusinessLicenseApplication WHERE RecordType.DeveloperName='Renewal' AND {ns} LIMIT 1",
     'License Type':"SELECT Id FROM RegulatoryAuthorizationType LIMIT 1",
     'Fee Product':"SELECT Id FROM Product2 LIMIT 1",
     'Fee Owed':"SELECT Id FROM RegulatoryTrxnFee WHERE {ns} LIMIT 1",
     'Payment':"SELECT Id FROM Payment__c WHERE {ns} LIMIT 1",
     'Hold (Stop Code)':"SELECT Id FROM RecordAlert WHERE {ns} LIMIT 1",
     'Examination':"SELECT Id FROM PersonExamination WHERE {ns} LIMIT 1",
     'Accommodation':"SELECT Id FROM PersonDisability WHERE {ns} LIMIT 1",
     'Education':"SELECT Id FROM PersonEducation WHERE {ns} LIMIT 1",
     'Training Course':"SELECT Id FROM TrnCourse LIMIT 1",
     'Course Offering':"SELECT Id FROM CourseOffering LIMIT 1",
     'Student Hours':"SELECT Id FROM TrainingCourseParticipant WHERE {ns} LIMIT 1",
     'Accreditation / Bond':"SELECT Id FROM Accreditation WHERE {ns} LIMIT 1",
     'Complaint':"SELECT Id FROM PublicComplaint WHERE {ns} LIMIT 1",
     'Case':"SELECT Id FROM Case WHERE Owner.Type='User' AND {ns} LIMIT 1",
     'Inspection Visit':"SELECT Id FROM Visit LIMIT 1",
    }
    out = {}
    for k, v in S.items():
        r = q(v.format(ns=ns))
        out[k] = r[0]['Id'] if r else None
    return out

SAMPLES = sample_records(TIM)
# Matrix record -> objects whose screens it needs (as in scripts/generators/security.py OBJECTS).
ENTITY = {'Person Account': ['Account'], 'Establishment': ['Account'], 'School': ['Account'], 'Organization': ['Account'],
          'License': ['BusinessLicense'], 'Individual Application': ['IndividualApplication'],
          'Business Application': ['BusinessLicenseApplication'], 'Fee Owed': ['RegulatoryTrxnFee'], 'Payment': ['Payment__c'],
          'Hold (Stop Code)': ['RecordAlert'], 'Examination': ['PersonExamination'], 'Accommodation': ['PersonDisability'],
          'Education': ['PersonEducation'], 'Student Hours': ['TrainingCourseParticipant'], 'Accreditation / Bond': ['Accreditation'],
          'Complaint': ['PublicComplaint'], 'Case': ['Case'], 'Inspection Visit': ['Visit']}
wb = openpyxl.load_workbook('docs/LSBC Access Matrix.xlsx')
ss = wb['Sharing Settings']
desks = [ss.cell(4, c).value for c in range(6, 19)]
share = {d: {ss.cell(r, 1).value: ss.cell(r, 6 + i).value for r in range(5, 28)} for i, d in enumerate(desks)}
SOME = {('Individual Application', 'FrontDeskSupervisor'): {'NewLicensure'}, ('Individual Application', 'FrontDesk'): {'NewLicensure'},
        ('Individual Application', 'StudentRegistration'): {'NewLicensure'}, ('Individual Application', 'RenewalDesk'): {'Renewal'},
        ('Individual Application', 'ReciprocityDesk'): {'Reciprocity'}, ('Individual Application', 'Mailroom'): set(),
        ('Business Application', 'FrontDeskSupervisor'): {'NewEstablishment', 'NewSchool'}, ('Business Application', 'FrontDesk'): {'NewEstablishment', 'NewSchool'},
        ('Business Application', 'RenewalDesk'): {'Renewal'}, ('Business Application', 'Mailroom'): set()}
# expected flows / custom permissions from the generated files
def psg_sets(desk):
    return re.findall(r'<permissionSets>([^<]+)</permissionSets>', open(f'force-app/main/default/permissionsetgroups/{desk}.permissionsetgroup-meta.xml').read())
def from_sets(sets, tag):
    out = set()
    for s in sets:
        try: x = open(f'force-app/main/default/permissionsets/{s}.permissionset-meta.xml').read()
        except FileNotFoundError: continue
        out |= set(re.findall(rf'<{tag}>([^<]+)</{tag}>', x))
    return out
results = {}
for desk in (DESKS_ARG or desks):
    role = ROLE.get(desk, desk)
    apex(f"""Id u = '{TIM}';
User usr = [SELECT Id FROM User WHERE Id = :u];
usr.UserRoleId = [SELECT Id FROM UserRole WHERE DeveloperName = '{role}'].Id; update usr;
delete [SELECT Id FROM PermissionSetAssignment WHERE AssigneeId = :u AND PermissionSetGroupId != null];
insert new PermissionSetAssignment(AssigneeId = u, PermissionSetGroupId = [SELECT Id FROM PermissionSetGroup WHERE DeveloperName = '{desk}'].Id);
System.debug('DONE');""")
    time.sleep(20)  # group membership and sharing recalculation
    ids = [v for v in SAMPLES.values() if v]
    ura = {r['RecordId']: r for r in q(f"SELECT RecordId, HasReadAccess, HasEditAccess FROM UserRecordAccess WHERE UserId='{TIM}' AND RecordId IN ('" + "','".join(ids) + "')")}
    bad = []
    for key, rid in SAMPLES.items():
        if not rid: continue
        rec, _, rt = key.partition('|')
        v = share[desk][rec]
        if v.endswith('(some)'):
            exp = 'Edit' if rt in SOME[(rec, desk)] else 'Read'
        else:
            exp = v
        a = ura.get(rid)
        got = 'Edit' if a and a['HasEditAccess'] else 'Read' if a and a['HasReadAccess'] else '—'
        if got != exp: bad.append(f'{key}: expected {exp}, got {got}')
    # objects open in the screens: readable when any matrix record on the object is readable for the desk
    want = {}
    for rec, objs in ENTITY.items():
        for o in objs:
            want[o] = want.get(o, False) or (share[desk][rec] or '—') != '—'
    uea = {r['EntityDefinition']['QualifiedApiName']: r['IsReadable'] for r in q(
        f"SELECT EntityDefinition.QualifiedApiName, IsReadable FROM UserEntityAccess WHERE UserId='{TIM}' AND "
        "EntityDefinition.QualifiedApiName IN ('" + "','".join(want) + "')")}
    for o, w in sorted(want.items()):
        if uea.get(o, False) != w:
            bad.append(f'object {o}: expected {"opens" if w else "closed"}, got {"opens" if uea.get(o) else "closed"}')
    # flows and custom permissions
    sets = psg_sets(desk)
    exp_flows = from_sets(sets, 'flow'); exp_cp = from_sets(sets, 'name') & {'ViewConfidentialComplainant', 'ViewAccommodationDocuments'}
    psids = [r['PermissionSetId'] for r in q(f"SELECT PermissionSetId FROM PermissionSetAssignment WHERE AssigneeId='{TIM}'")]
    sea = q("SELECT SetupEntityId, SetupEntityType FROM SetupEntityAccess WHERE ParentId IN ('" + "','".join(psids) + "') AND SetupEntityType IN ('FlowDefinition','CustomPermission')")
    fd = {r['Id']: r['DeveloperName'] for r in q("SELECT Id, DeveloperName FROM FlowDefinitionView WHERE ApiName LIKE 'ScreenFlow%'")} if False else {}
    flow_ids = [r['SetupEntityId'] for r in sea if r['SetupEntityType'] == 'FlowDefinition']
    cp_ids = [r['SetupEntityId'] for r in sea if r['SetupEntityType'] == 'CustomPermission']
    got_flows = {r['ApiName'] for r in q("SELECT ApiName FROM FlowDefinitionView WHERE DurableId IN ('" + "','".join(flow_ids) + "')")} if flow_ids else set()
    got_cp = {r['DeveloperName'] for r in q("SELECT DeveloperName FROM CustomPermission WHERE Id IN ('" + "','".join(cp_ids or ['x']) + "')")} if cp_ids else set()
    gated = {f for f in got_flows if f.startswith('ScreenFlow')}
    if gated != exp_flows: bad.append(f'flows: missing {sorted(exp_flows - gated)} extra {sorted(gated - exp_flows)}')
    if got_cp & {'ViewConfidentialComplainant', 'ViewAccommodationDocuments'} != exp_cp: bad.append(f'custom permissions: expected {sorted(exp_cp)}, got {sorted(got_cp)}')
    results[desk] = bad
    print(f'{desk:22} {"PASS" if not bad else "FAIL"}  flows={len(gated)}', flush=True)
    for b in bad: print('     ', b, flush=True)
sys.exit(1 if any(results.values()) else 0)
