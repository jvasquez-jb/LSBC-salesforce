"""Writes the school portal forms: the Board's School Forms packet, filed by a school's School Administrator.

Each form follows its page of docs/School Forms .pdf section by section. The person signed in must be an active
School Administrator of the school (Account Contact Relation role); students' records are read and written by the
flow (system context) and are never shared to the school. Where the paper carries the student's signature, the
School Administrator certifies that the student signed the paper statement, which the school keeps on file
(Jonathan, 19 Nov 2026).

Run: python3 -I scripts/generators/schoolforms.py force-app/main/default/flows
"""
import os
import sys
from xml.sax.saxutils import escape as e

PHONE = '225-756-3404'
ORDER = ['actionCalls', 'assignments', 'choices', 'decisions', 'description', 'dynamicChoiceSets', 'environments',
         'formulas', 'interviewLabel', 'label', 'loops', 'processMetadataValues', 'processType', 'recordCreates',
         'recordDeletes', 'recordLookups', 'recordUpdates', 'runInMode', 'screens', 'start', 'status', 'subflows',
         'variables']


def val(v):
    if v is None:
        return ''
    if isinstance(v, bool):
        return f'<booleanValue>{"true" if v else "false"}</booleanValue>'
    if isinstance(v, (int, float)):
        return f'<numberValue>{v}</numberValue>'
    if v.startswith('='):
        return f'<elementReference>{v[1:]}</elementReference>'
    return f'<stringValue>{e(v)}</stringValue>'


def conn(t, tag='connector'):
    return f'<{tag}><targetReference>{t}</targetReference></{tag}>' if t else ''


LOC = '<locationX>0</locationX><locationY>0</locationY>'


class Flow:
    def __init__(self, api, label, desc, process='Flow'):
        self.api, self.label, self.desc, self.process = api, label, desc, process
        self.el = {k: [] for k in ORDER}
        self.first = None

    # data
    def lookup(self, name, label, obj, filters, fields, nxt, first=False, sort=None, logic='and', desc=False):
        x = f'<recordLookups><name>{name}</name><label>{e(label)}</label>{LOC}<assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>{conn(nxt)}<filterLogic>{logic}</filterLogic>'
        for f, op, v in filters:
            x += f'<filters><field>{f}</field><operator>{op}</operator><value>{val(v)}</value></filters>'
        x += f'<getFirstRecordOnly>{"true" if first else "false"}</getFirstRecordOnly><object>{obj}</object>'
        x += ''.join(f'<queriedFields>{f}</queriedFields>' for f in fields)
        if sort:
            x += f'<sortField>{sort}</sortField><sortOrder>{"Desc" if desc else "Asc"}</sortOrder>'
        self.el['recordLookups'].append(x + '<storeOutputAutomatically>true</storeOutputAutomatically></recordLookups>')

    def create(self, name, label, obj, assigns, nxt, fault=None):
        x = f'<recordCreates><name>{name}</name><label>{e(label)}</label>{LOC}{conn(nxt)}{conn(fault, "faultConnector")}'
        for f, v in assigns:
            x += f'<inputAssignments><field>{f}</field><value>{val(v)}</value></inputAssignments>'
        self.el['recordCreates'].append(x + f'<object>{obj}</object><storeOutputAutomatically>true</storeOutputAutomatically></recordCreates>')

    def create_many(self, name, label, ref, nxt, fault=None):
        self.el['recordCreates'].append(f'<recordCreates><name>{name}</name><label>{e(label)}</label>{LOC}{conn(nxt)}{conn(fault, "faultConnector")}<inputReference>{ref}</inputReference></recordCreates>')

    def update(self, name, label, obj, idref, assigns, nxt, fault=None):
        x = f'<recordUpdates><name>{name}</name><label>{e(label)}</label>{LOC}{conn(nxt)}{conn(fault, "faultConnector")}<filterLogic>and</filterLogic>'
        x += f'<filters><field>Id</field><operator>EqualTo</operator><value>{val("=" + idref)}</value></filters>'
        for f, v in assigns:
            x += f'<inputAssignments><field>{f}</field>' + (f'<value>{val(v)}</value>' if v is not None else '') + '</inputAssignments>'
        self.el['recordUpdates'].append(x + f'<object>{obj}</object></recordUpdates>')

    def delete(self, name, label, obj, idref, nxt):
        self.el['recordDeletes'].append(f'<recordDeletes><name>{name}</name><label>{e(label)}</label>{LOC}{conn(nxt)}<filterLogic>and</filterLogic><filters><field>Id</field><operator>EqualTo</operator><value>{val("=" + idref)}</value></filters><object>{obj}</object></recordDeletes>')

    # logic
    def assign(self, name, label, items, nxt):
        x = f'<assignments><name>{name}</name><label>{e(label)}</label>{LOC}'
        for ref, op, v in items:
            x += f'<assignmentItems><assignToReference>{ref}</assignToReference><operator>{op}</operator><value>{val(v)}</value></assignmentItems>'
        self.el['assignments'].append(x + conn(nxt) + '</assignments>')

    def decide(self, name, label, rules, default, default_label='No'):
        """rules: (name, label, [(left, op, value)], next, logic)"""
        x = f'<decisions><name>{name}</name><label>{e(label)}</label>{LOC}{conn(default, "defaultConnector")}<defaultConnectorLabel>{e(default_label)}</defaultConnectorLabel>'
        for rn, rl, conds, nxt, logic in rules:
            c = ''.join(f'<conditions><leftValueReference>{l}</leftValueReference><operator>{op}</operator><rightValue>{val(v)}</rightValue></conditions>' for l, op, v in conds)
            x += f'<rules><name>{rn}</name><conditionLogic>{logic}</conditionLogic>{c}{conn(nxt)}<label>{e(rl)}</label></rules>'
        self.el['decisions'].append(x + '</decisions>')

    def loop(self, name, label, coll, nxt, done):
        self.el['loops'].append(f'<loops><name>{name}</name><label>{e(label)}</label>{LOC}<collectionReference>{coll}</collectionReference><iterationOrder>Asc</iterationOrder>{conn(nxt, "nextValueConnector")}{conn(done, "noMoreValuesConnector")}</loops>')

    def formula(self, name, dtype, expr, desc, scale=None):
        s = f'<scale>{scale}</scale>' if scale is not None else ''
        self.el['formulas'].append(f'<formulas><name>{name}</name><description>{e(desc)}</description><dataType>{dtype}</dataType><expression>{e(expr)}</expression>{s}</formulas>')

    def var(self, name, dtype, desc, coll=False, inp=False, obj=None, default=None, scale=None):
        x = f'<variables><name>{name}</name><description>{e(desc)}</description><dataType>{dtype}</dataType><isCollection>{"true" if coll else "false"}</isCollection><isInput>{"true" if inp else "false"}</isInput><isOutput>false</isOutput>'
        if obj:
            x += f'<objectType>{obj}</objectType>'
        if scale is not None or dtype == 'Number':
            x += f'<scale>{scale if scale is not None else 2}</scale>'
        if default is not None:
            x += f'<value>{val(default)}</value>'
        self.el['variables'].append(x + '</variables>')

    def choice(self, name, text, value=None):
        self.el['choices'].append(f'<choices><name>{name}</name><choiceText>{e(text)}</choiceText><dataType>String</dataType><value>{val(value if value is not None else text)}</value></choices>')

    def collection_choices(self, name, coll, obj, display, value='Id'):
        self.el['dynamicChoiceSets'].append(f'<dynamicChoiceSets><name>{name}</name><collectionReference>{coll}</collectionReference><dataType>String</dataType><displayField>{display}</displayField><object>{obj}</object><valueField>{value}</valueField></dynamicChoiceSets>')

    def subflow(self, name, label, flow, inputs, nxt, outputs=()):
        x = f'<subflows><name>{name}</name><label>{e(label)}</label>{LOC}{conn(nxt)}<flowName>{flow}</flowName>'
        for n, v in inputs:
            x += f'<inputAssignments><name>{n}</name><value>{val(v)}</value></inputAssignments>'
        for n, ref in outputs:
            x += f'<outputAssignments><assignToReference>{ref}</assignToReference><name>{n}</name></outputAssignments>'
        self.el['subflows'].append(x + '<storeOutputAutomatically>false</storeOutputAutomatically></subflows>' if outputs else x + '</subflows>')

    def action(self, name, label, aname, atype, params, nxt, fault=None):
        x = f'<actionCalls><name>{name}</name><label>{e(label)}</label>{LOC}<actionName>{aname}</actionName><actionType>{atype}</actionType>{conn(nxt)}{conn(fault, "faultConnector")}<flowTransactionModel>CurrentTransaction</flowTransactionModel>'
        for n, v in params:
            x += f'<inputParameters><name>{n}</name><value>{val(v)}</value></inputParameters>'
        self.el['actionCalls'].append(x + '<storeOutputAutomatically>true</storeOutputAutomatically></actionCalls>')

    def screen(self, name, label, fields, nxt, back=True, pause=True, next_label=None):
        # A last screen (no next element, no button label of its own) ends with a Back to My Applications button
        # instead of Finish: Finish on a portal page restarts the form. Back stays where the screen has it; a screen
        # without Back hides its footer (a flow screen can't turn off both Back and Finish).
        last = nxt is None and not next_label
        x = (f'<screens><name>{name}</name><label>{e(label)}</label>{LOC}<allowBack>{"true" if back else "false"}</allowBack>'
             f'<allowFinish>{"false" if last and back else "true"}</allowFinish><allowPause>{"true" if pause else "false"}</allowPause>{conn(nxt)}')
        x += ''.join(fields)
        if last:
            x += display(fields[0].split('<name>')[1].split('_')[0] + '_BackToMyApplications', BACK_TO_MY_APPLICATIONS)
        if next_label:
            x += f'<nextOrFinishButtonLabel>{e(next_label)}</nextOrFinishButtonLabel>'
        if pause:
            x += f'<pauseButtonLabel>Save for later</pauseButtonLabel><pausedText>{e(PAUSED_TEXT)}</pausedText>'
        footer = 'false' if last and not back else 'true'
        self.el['screens'].append(x + f'<showFooter>{footer}</showFooter><showHeader>false</showHeader></screens>')

    def write(self, outdir, first):
        j = lambda t: ''.join(self.el[t])
        meta = ''.join(f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
                       for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')])
        x = ('<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><apiVersion>66.0</apiVersion>'
             + j('actionCalls') + j('assignments') + j('choices') + j('decisions') + f'<description>{e(self.desc)}</description>'
             + j('dynamicChoiceSets') + '<environments>Default</environments>' + j('formulas')
             + f'<interviewLabel>{e(self.label)} {{!$Flow.CurrentDateTime}}</interviewLabel><label>{e(self.label)}</label>' + j('loops')
             + meta + f'<processType>{self.process}</processType>' + j('recordCreates') + j('recordDeletes') + j('recordLookups')
             + j('recordUpdates') + '<runInMode>SystemModeWithoutSharing</runInMode>' + j('screens')
             + f'<start>{LOC}{conn(first)}</start><status>Active</status>' + j('subflows') + j('variables') + '</Flow>\n')
        open(os.path.join(outdir, self.api + '.flow-meta.xml'), 'w').write(x)
        print('wrote', self.api)


# The saved message every portal form shows after Save for later (the same as the Apply forms').
PAUSED_TEXT = ('<p><b>Your application is saved.</b></p><p>To pick it up where you left off, go to '
               '<a target="_self" href="/LPI/s/view-license-permit-status">My Applications</a> and choose Continue. Saved applications are '
               'kept for 30 days from when you last worked on them, then deleted.</p>')

# The button a form's last screen shows instead of Finish. A link styled as the portal's button (lsbc-button in the
# theme CSS), opening My Applications in the same tab (a link in a flow opens a new tab unless the target is set).
BACK_TO_MY_APPLICATIONS = ('<p><a class="lsbc-button" target="_self" href="/LPI/s/view-license-permit-status">'
                           'Back to My Applications</a></p>')


# ---- screen field helpers ----
def display(name, html, vis=None):
    return f'<fields><name>{name}</name><fieldText>{e(html)}</fieldText><fieldType>DisplayText</fieldType>{vis or ""}</fields>'


def inp(name, dtype, label, required=False, help=None, rule=None, vis=None, scale=None, default=None):
    x = f'<fields><name>{name}</name><dataType>{dtype}</dataType>'
    if default is not None:
        x += f'<defaultValue>{val(default)}</defaultValue>'
    x += f'<fieldText>{e(label)}</fieldText><fieldType>InputField</fieldType>'
    if help:
        x += f'<helpText>{e(help)}</helpText>'
    x += f'<inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn><isRequired>{"true" if required else "false"}</isRequired>'
    if scale is not None:
        x += f'<scale>{scale}</scale>'
    if rule:
        x += f'<validationRule><errorMessage>{e(rule[0])}</errorMessage><formulaExpression>{e(rule[1])}</formulaExpression></validationRule>'
    return x + (vis or '') + '</fields>'


def textarea(name, label, required=False, vis=None):
    return (f'<fields><name>{name}</name><fieldText>{e(label)}</fieldText><fieldType>LargeTextArea</fieldType>'
            f'<inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn><isRequired>{"true" if required else "false"}</isRequired>{vis or ""}</fields>')


def radio(name, label, choices, required=True, vis=None, default=None, help=None):
    x = f'<fields><name>{name}</name>' + ''.join(f'<choiceReferences>{c}</choiceReferences>' for c in choices)
    x += f'<dataType>String</dataType>'
    if default:
        x += f'<defaultSelectedChoiceReference>{default}</defaultSelectedChoiceReference>'
    x += f'<fieldText>{e(label)}</fieldText><fieldType>RadioButtons</fieldType>'
    if help:
        x += f'<helpText>{e(help)}</helpText>'
    return x + f'<inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn><isRequired>{"true" if required else "false"}</isRequired>{vis or ""}</fields>'


def vis_if(left, op, v, logic='and', more=()):
    c = f'<conditions><leftValueReference>{left}</leftValueReference><operator>{op}</operator><rightValue>{val(v)}</rightValue></conditions>'
    c += ''.join(f'<conditions><leftValueReference>{l}</leftValueReference><operator>{o}</operator><rightValue>{val(w)}</rightValue></conditions>' for l, o, w in more)
    return f'<visibilityRule><conditionLogic>{logic}</conditionLogic>{c}</visibilityRule>'


# ---- shared start: the signed-in School Administrator and the school ----
def school_start(f, form_name, after_school):
    """GetRunningUser -> the schools the user administers -> choose one (SC_School) -> GetSchool -> after_school."""
    f.lookup('GetRunningUser', 'Get Running User', 'User', [('Id', 'EqualTo', '=$User.Id')],
             ['Id', 'ContactId', 'FirstName', 'LastName'], 'GetSchoolRelationships', first=True)
    f.lookup('GetSchoolRelationships', 'Get School Relationships', 'AccountContactRelation',
             [('ContactId', 'EqualTo', '=GetRunningUser.ContactId'), ('IsActive', 'EqualTo', True)],
             ['Id', 'AccountId', 'Roles'], 'LoopThroughSchoolRelationships', sort='Id')
    f.loop('LoopThroughSchoolRelationships', 'Loop Through School Relationships', 'GetSchoolRelationships',
           'IsTheUserASchoolAdministrator', 'AreThereSchools')
    f.formula('forB_IsSchoolAdministrator', 'Boolean', 'INCLUDES({!LoopThroughSchoolRelationships.Roles}, "School Administrator")',
              'The relationship makes the signed-in person a School Administrator of the account.')
    f.decide('IsTheUserASchoolAdministrator', 'Is the User a School Administrator?', [
        ('SchoolAdministrator', 'Yes', [('forB_IsSchoolAdministrator', 'EqualTo', True)], 'AddSchoolId', 'and')],
        'LoopThroughSchoolRelationships')
    f.var('varT_SchoolIds', 'String', 'The schools the signed-in person administers.', coll=True)
    f.assign('AddSchoolId', 'Add School Id', [('varT_SchoolIds', 'Add', '=LoopThroughSchoolRelationships.AccountId')],
             'LoopThroughSchoolRelationships')
    f.decide('AreThereSchools', 'Does the User Administer a School?', [
        ('HasSchools', 'Yes', [('varT_SchoolIds', 'IsEmpty', False)], 'GetSchools', 'and')], 'NotSchoolAdministrator')
    f.screen('NotSchoolAdministrator', 'Not Available', [display('NSA_Message',
             f'<p>{form_name} is for a school\'s School Administrator. Your portal account isn\'t linked to a school as its '
             f'School Administrator. Ask the Board to add you: call {PHONE}.</p>')], None, back=False, pause=False)
    f.lookup('GetSchools', 'Get Schools', 'Account', [('Id', 'In', '=varT_SchoolIds')], ['Id', 'Name'], 'ChooseSchool', sort='Name')
    f.collection_choices('choice_Schools', 'GetSchools', 'Account', 'Name')
    return after_school


# ---- Student Enrollment ----
def student_enrollment(outdir):
    f = Flow('ScreenFlowIndividualApplicationStudentEnrollment', 'Student Enrollment',
             'Screen Flow: Individual Application Student Enrollment. The Board\'s Student Enrollment Application, filed on '
             'the portal by a school\'s School Administrator for a new student, a transfer or a student seeking additional '
             'training. Finds the student by name and date of birth (the date of birth is compared after the query, never '
             'filtered on) or adds them as a person, owned by the school\'s owner at the Board, never by the school. Asks the '
             'student\'s details, education, prior enrollment, course, schedule and class start date, the documents for the '
             'student type, and the school\'s certification, then creates a Student Registration application (Student '
             'Registration license type) with the $10.00 enrollment fee; a student\'s first in-state transfer is free. '
             'Nothing is written to the application until the school certifies; the documents wait on a draft.')
    school_start(f, 'The Student Enrollment Application', 'GetSchool')
    for n, t in [('choice_New', 'New'), ('choice_Transfer', 'Transfer'), ('choice_AdditionalTraining', 'Additional Training'),
                 ('choice_Yes', 'Yes'), ('choice_No', 'No'), ('choice_FullTime', 'Full Time'), ('choice_PartTime', 'Part-Time'),
                 ('choice_Evening', 'Evening')]:
        f.choice(n, t)
    f.screen('ChooseSchool', 'Student Enrollment Application', [
        display('CS_Intro', '<p><b>STUDENT ENROLLMENT APPLICATION</b></p><p>This form must be used to enroll all students in '
                'school, including new, transfers and those seeking additional training. Please provide the additional '
                'information as required for your student type along with this completed application.</p>'
                '<p>A new student needs: a copy of their birth certificate (preferred) or driver\'s license for proof of age; '
                'a copy of their Social Security card; proof of education (must have completed the 10th grade or equivalent): '
                'a copy of their diploma or transcript; and two photographs measuring about 2 by 2 inches.</p>'
                '<p>The enrollment fee is $10.00. A student\'s first in-state transfer is free.</p>'),
        radio('CS_School', 'Cosmetology school', ['choice_Schools']),
        radio('CS_StudentType', 'Student type', ['choice_New', 'choice_Transfer', 'choice_AdditionalTraining']),
    ], 'GetSchool', back=False, pause=False)
    f.lookup('GetSchool', 'Get School', 'Account', [('Id', 'EqualTo', '=CS_School')],
             ['Id', 'Name', 'OwnerId', 'CertificationNumber__c', 'ShippingCity', 'Phone'], 'GetSchoolOwner', first=True)
    # the owner's own lookup: a cross-object reference through Owner on a Get Records result isn't loaded
    f.lookup('GetSchoolOwner', 'Get School Owner', 'User', [('Id', 'EqualTo', '=GetSchool.OwnerId')], ['Id', 'IsPortalEnabled'],
             'IsTheSchoolApproved', first=True)
    f.decide('IsTheSchoolApproved', 'Is the School Approved?', [
        ('Approved', 'Yes', [('GetSchoolOwner.IsPortalEnabled', 'EqualTo', False)], 'GetSchoolLicense', 'and')],
        'SchoolNotApproved')
    f.lookup('GetSchoolLicense', 'Get School License', 'BusinessLicense', [('AccountId', 'EqualTo', '=GetSchool.Id'),
             ('Identifier', 'IsNull', False)], ['Id', 'Identifier'], 'GetCourseOfferings', first=True, sort='CreatedDate', desc=True)
    f.formula('forT_SchoolLicenseNumber', 'String', 'BLANKVALUE({!GetSchool.CertificationNumber__c}, {!GetSchoolLicense.Identifier})',
              'The school\'s license number: schools keep a typed number on their license, not a Board certification number.')
    f.screen('SchoolNotApproved', 'Not Available', [display('SNA_Message',
             f'<p>{{!GetSchool.Name}} can file school forms once the Board has approved the school. Call {PHONE} with any '
             'questions.</p>')], None, back=False, pause=False)
    f.lookup('GetCourseOfferings', 'Get Course Offerings', 'CourseOffering', [('School__c', 'EqualTo', '=GetSchool.Id')],
             ['Id', 'Name'], 'AreThereCourses', sort='Name')
    f.decide('AreThereCourses', 'Does the School Have Courses?', [
        ('HasCourses', 'Yes', [('GetCourseOfferings', 'IsNull', False)], 'CreateDraft', 'and')], 'NoCourses')
    f.screen('NoCourses', 'Not Available', [display('NC_Message',
             f'<p>The Board has no approved courses on file for {{!GetSchool.Name}}, so a student can\'t be enrolled yet. '
             f'Call {PHONE}.</p>')], None, back=False, pause=False)
    f.collection_choices('choice_Courses', 'GetCourseOfferings', 'CourseOffering', 'Name')
    f.formula('forT_SavedApplicationUrl', 'String', '"/LPI/s/continue-application?guid=" & {!$Flow.InterviewGuid}',
              'Records this form\'s interview GUID on the draft, so a saved form can be found again.')
    f.create('CreateDraft', 'Create Draft', 'PreliminaryApplicationRef', [
        ('ApplicationName', 'Student Enrollment Application'), ('ApplicationType', 'IndividualApplication'),
        ('OwnerId', '=$User.Id'), ('IsSubmitted', False), ('SavedApplicationUrl', '=forT_SavedApplicationUrl')], 'StudentName')

    # 1-5: the student
    f.screen('StudentName', 'Student', [
        display('SN_Intro', '<p><b>TO BE COMPLETED BY APPLICANT</b> (applicant must read, speak and understand English)</p>'
                '<p><b>1. Name</b></p>'),
        inp('SN_FirstName', 'String', 'First name', required=True),
        inp('SN_MiddleName', 'String', 'Middle initial'),
        inp('SN_LastName', 'String', 'Last name', required=True),
        inp('SN_MaidenName', 'String', 'Maiden name'),
        inp('SN_DateOfBirth', 'Date', '4. Date of birth', required=True,
            rule=('Enter a date of birth in the past.', '{!SN_DateOfBirth} < TODAY()')),
    ], 'GetSameNamePeople')
    f.formula('forT_FirstName', 'String', 'TRIM({!SN_FirstName})', 'The first name as typed, trimmed.')
    f.formula('forT_LastName', 'String', 'TRIM({!SN_LastName})', 'The last name as typed, trimmed.')
    f.lookup('GetSameNamePeople', 'Get People With the Same Name', 'Account', [
        ('IsPersonAccount', 'EqualTo', True), ('FirstName', 'EqualTo', '=forT_FirstName'), ('LastName', 'EqualTo', '=forT_LastName')],
        ['Id', 'DateOfBirth__pc'], 'LoopThroughSameName', sort='Id')
    f.var('varT_StudentId', 'String', 'The student\'s person account.')
    f.loop('LoopThroughSameName', 'Loop Through People With the Same Name', 'GetSameNamePeople', 'IsItTheSameBirthday', 'IsTheStudentFound')
    f.decide('IsItTheSameBirthday', 'Is It the Same Date of Birth?', [
        ('SameBirthday', 'Yes', [('LoopThroughSameName.DateOfBirth__pc', 'EqualTo', '=SN_DateOfBirth')], 'SetStudent', 'and')],
        'LoopThroughSameName')
    f.assign('SetStudent', 'Set Student', [('varT_StudentId', 'Assign', '=LoopThroughSameName.Id')], 'LoopThroughSameName')
    f.decide('IsTheStudentFound', 'Is the Student on File?', [
        ('Found', 'Yes', [('varT_StudentId', 'IsNull', False)], 'StudentDetails', 'and')], 'NewStudent')
    f.screen('NewStudent', 'New Student', [
        display('NS_Intro', '<p>The Board has no record of {!forT_FirstName} {!forT_LastName} with that date of birth, so they will be '
                'added as a new student.</p>'),
        inp('NS_SocialSecurityNumber', 'String', '2. Social Security number', required=True,
            rule=('Enter the 9-digit Social Security number.', 'REGEX(SUBSTITUTE({!NS_SocialSecurityNumber}, "-", ""), "\\\\d{9}")')),
    ], 'GetPersonRecordType')
    f.lookup('GetPersonRecordType', 'Get Person Account Record Type', 'RecordType', [
        ('SobjectType', 'EqualTo', 'Account'), ('DeveloperName', 'EqualTo', 'PersonAccount')], ['Id'], 'CreateStudent', first=True)
    f.formula('forT_SocialSecurityNumber', 'String', 'SUBSTITUTE({!NS_SocialSecurityNumber}, "-", "")', 'The number without dashes.')
    f.create('CreateStudent', 'Create Student', 'Account', [
        ('RecordTypeId', '=GetPersonRecordType.Id'), ('FirstName', '=forT_FirstName'), ('MiddleName', '=SN_MiddleName'),
        ('LastName', '=forT_LastName'), ('MaidenName__pc', '=SN_MaidenName'), ('DateOfBirth__pc', '=SN_DateOfBirth'),
        ('SocialSecurityNumber__pc', '=forT_SocialSecurityNumber'), ('OwnerId', '=GetSchool.OwnerId')], 'SetNewStudent', 'CouldNotSave')
    f.assign('SetNewStudent', 'Set New Student', [('varT_StudentId', 'Assign', '=CreateStudent')], 'StudentDetails')
    f.subflow('StudentDetails', 'Student Details', 'SubflowApplicantDetails', [
        ('varT_AccountId', '=varT_StudentId'), ('varB_IsStaffEntry', False), ('varB_AskGender', False)], 'Education')
    # 6-9: education
    f.subflow('Education', 'Education', 'SubflowSchoolsAttended', [
        ('varT_AccountId', '=varT_StudentId'), ('varT_Heading', '6-9. Education: the last grade the student completed (8, 9, 10, 11, 12 or GED), the year, and the school where they completed it'),
        ('varB_AskEducationLevel', True)], 'PriorEnrollment')
    # 1-2 questions, 10-11 explanation
    f.screen('PriorEnrollment', 'Prior Enrollment', [
        radio('PE_EnrolledInLouisiana', '1. Have you ever been enrolled in a Louisiana cosmetology school?', ['choice_Yes', 'choice_No'],
              help='If yes, a Certification of Contractual Fees from that school is needed.'),
        radio('PE_Licensed', '2. Have you ever been licensed as a cosmetologist, hairdresser or manicurist in Louisiana or elsewhere?',
              ['choice_Yes', 'choice_No']),
        textarea('PE_Explanation', '10-11. If the answer to question 1 or 2 is yes, please explain.', required=True,
                 vis=vis_if('PE_EnrolledInLouisiana', 'EqualTo', 'Yes', 'or', [('PE_Licensed', 'EqualTo', 'Yes')])),
    ], 'Course')
    # 12-17, 19
    f.screen('Course', 'School and Course', [
        display('CO_School', '<p>I hereby make application to enroll in the following cosmetology school:</p>'
                '<p><b>12. School:</b> {!GetSchool.Name}<br/><b>13. School license number:</b> {!forT_SchoolLicenseNumber}'
                '<br/><b>15. Telephone:</b> {!GetSchool.Phone}</p>'),
        radio('CO_Course', '16. For the following course', ['choice_Courses']),
        radio('CO_Schedule', 'Attendance', ['choice_FullTime', 'choice_PartTime', 'choice_Evening']),
        display('CO_HoursIntro', '<p><b>17. Please indicate the number of hours attending each day.</b></p>'),
    ] + [inp(f'CO_{d}Hours', 'Number', d, scale=1, rule=('Enter between 0 and 24 hours.', f'OR(ISBLANK({{!CO_{d}Hours}}), AND({{!CO_{d}Hours}} >= 0, {{!CO_{d}Hours}} <= 24))'))
         for d in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']] + [
        display('CO_SchoolPart', '<p><b>TO BE COMPLETED BY COSMETOLOGY SCHOOL</b></p><p>19. The above named applicant has been accepted '
                'for enrollment into our school and may begin with our class starting:</p>'),
        inp('CO_ClassStartDate', 'Date', 'Class start date', required=True),
    ], 'GenerateDraftChecklist')
    f.formula('forT_ApplicationPath', 'String', 'IF({!PE_EnrolledInLouisiana} = "Yes", "Previously Enrolled", "")',
              'Previously Enrolled adds the Certification of Contractual Fees to the checklist.')
    f.subflow('GenerateDraftChecklist', 'Generate Draft Checklist', 'SubflowDocumentChecklistGenerate', [
        ('varT_ApplicationId', '=CreateDraft'), ('varT_AccountId', '=varT_StudentId'),
        ('varT_RecordType', 'IndividualApplication.StudentRegistration'), ('varT_LicenseTypeName', 'Student Registration'),
        ('varT_ApplicationType', '=CS_StudentType'), ('varT_ApplicationPath', '=forT_ApplicationPath'),
        ('varB_LeaveOutReceipt', True)], 'UploadDocuments')
    f.subflow('UploadDocuments', 'Upload Documents', 'SubflowDocumentChecklistUpload', [
        ('varT_ApplicationId', '=CreateDraft'), ('varB_IsStaffEntry', False)], 'Certification')
    f.formula('forT_SchoolAdministratorName', 'String', '{!GetRunningUser.FirstName} & " " & {!GetRunningUser.LastName}',
              'The School Administrator certifying the form.')
    f.subflow('Certification', 'Certification', 'SubflowApplicationCertification', [
        ('varT_AttestationText',
         '18. The applicant swears and affirms that this application is complete and the answers set forth above are true and '
         'correct to the best of their knowledge and belief. They understand they must be registered with the Louisiana State '
         'Board of Cosmetology and will be allowed credit for school attendance in accordance with Louisiana Administrative '
         'Code 46:XXXI.715, and that at the time of the State Board examination, if the exam team determines they cannot '
         'understand, read and speak English, they will not be allowed to take the exam. 19-21. We hereby certify that this '
         'application has been completed to the best of our knowledge, and that the applicant signed the paper application, '
         'which the school keeps on file.'),
        ('varT_ApplicantName', '=forT_SchoolAdministratorName')], 'GetRecordType',
        outputs=[('varB_IsCertified', 'varB_IsCertified'), ('varT_CertifiedName', 'varT_CertifiedName'), ('varDT_CertifiedDateTime', 'varDT_CertifiedDateTime')])
    f.var('varB_IsCertified', 'Boolean', 'The school certified the form.')
    f.var('varT_CertifiedName', 'String', 'The name typed to certify.')
    f.var('varDT_CertifiedDateTime', 'DateTime', 'When the form was certified.')
    f.lookup('GetRecordType', 'Get Student Registration Record Type', 'RecordType', [
        ('SobjectType', 'EqualTo', 'IndividualApplication'), ('DeveloperName', 'EqualTo', 'StudentRegistration')], ['Id'],
        'GetLicenseType', first=True)
    f.lookup('GetLicenseType', 'Get Student Registration License Type', 'RegulatoryAuthorizationType', [
        ('Name', 'EqualTo', 'Student Registration')], ['Id'], 'GetEarlierTransfers', first=True)
    f.lookup('GetEarlierTransfers', 'Get Earlier Transfers', 'IndividualApplication', [
        ('AccountId', 'EqualTo', '=varT_StudentId'), ('RecordTypeId', 'EqualTo', '=GetRecordType.Id'), ('ApplicationType', 'EqualTo', 'Transfer')],
        ['Id'], 'CreateApplication', first=True)
    f.formula('forB_FeeDue', 'Boolean', 'NOT(AND({!CS_StudentType} = "Transfer", ISBLANK({!GetEarlierTransfers.Id})))',
              'The $10.00 enrollment fee applies, except to a student\'s first in-state transfer.')
    hours = [(f'{d}Hours__c', f'=CO_{d}Hours') for d in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']]
    f.formula('forB_EnrolledInLouisiana', 'Boolean', '{!PE_EnrolledInLouisiana} = "Yes"', 'Answer to question 1.')
    f.formula('forB_PreviouslyLicensed', 'Boolean', '{!PE_Licensed} = "Yes"', 'Answer to question 2.')
    f.create('CreateApplication', 'Create Application', 'IndividualApplication', [
        ('RecordTypeId', '=GetRecordType.Id'), ('AccountId', '=varT_StudentId'), ('LicenseTypeId', '=GetLicenseType.Id'),
        ('Category', 'License'), ('ApplicationType', '=CS_StudentType'), ('Status', 'Submitted'), ('AppliedDate', '=$Flow.CurrentDateTime'),
        ('CourseOffering__c', '=CO_Course'), ('AttendanceSchedule__c', '=CO_Schedule'), ('ClassStartDate__c', '=CO_ClassStartDate'),
        ('PreviouslyEnrolledInLouisiana__c', '=forB_EnrolledInLouisiana'), ('PreviouslyLicensed__c', '=forB_PreviouslyLicensed'),
        ('PriorEnrollmentExplanation__c', '=PE_Explanation'), ('IsCertified__c', '=varB_IsCertified'),
        ('CertifiedName__c', '=varT_CertifiedName'), ('CertifiedDateTime__c', '=varDT_CertifiedDateTime')] + hours,
        'TransferDraft', 'CouldNotSave')
    f.subflow('TransferDraft', 'Transfer Draft', 'SubflowPreliminaryApplicationTransfer', [
        ('varT_PreliminaryApplicationId', '=CreateDraft'), ('varT_ApplicationId', '=CreateApplication')], 'IsTheFeeDue')
    f.decide('IsTheFeeDue', 'Is the Enrollment Fee Due?', [
        ('FeeDue', 'Yes', [('forB_FeeDue', 'EqualTo', True)], 'LookUpEnrollmentFee', 'and')], 'DeleteDraft', default_label='No, a first transfer')
    f.action('LookUpEnrollmentFee', 'Look Up Enrollment Fee', 'FeeSchedule', 'runDecisionMatrix', [('FeeName', 'Student Registration')], 'CreateFee')
    f.create('CreateFee', 'Create Fee', 'RegulatoryTrxnFee', [
        ('AccountId', '=varT_StudentId'), ('ParentRecordId', '=CreateApplication'), ('Status', 'DUE'),
        ('DueDate', '=$Flow.CurrentDateTime'), ('Description', 'Student enrollment')], 'CreateFeeItem')
    f.formula('forT_ThisYear', 'String', 'TEXT(YEAR(TODAY()))', 'This year, the fee item\'s year.')
    f.create('CreateFeeItem', 'Create Fee Item', 'RegulatoryTrxnFeeItem', [
        ('RegulatoryTrxnFeeId', '=CreateFee'), ('Name', 'Student Registration'), ('FeeAmount', '=LookUpEnrollmentFee.Amount'),
        ('ForYear__c', '=forT_ThisYear'), ('CalculationInfo', 'Student enrollment fee, from the Fee Schedule.')], 'GenerateReceiptItem')
    f.subflow('GenerateReceiptItem', 'Generate Receipt Checklist Item', 'SubflowDocumentChecklistGenerate', [
        ('varT_ApplicationId', '=CreateApplication'), ('varT_AccountId', '=varT_StudentId'),
        ('varT_RecordType', 'IndividualApplication.StudentRegistration'), ('varT_LicenseTypeName', 'Student Registration'),
        ('varT_ApplicationType', '=CS_StudentType'), ('varT_ApplicationPath', '=forT_ApplicationPath')], 'SetPaymentIds')
    f.var('varT_FeeIds', 'String', 'The fees to pay.', coll=True)
    f.var('varT_ApplicationIds', 'String', 'The application the fees are for.', coll=True)
    f.assign('SetPaymentIds', 'Set Payment Ids', [('varT_FeeIds', 'Add', '=CreateFee'), ('varT_ApplicationIds', 'Add', '=CreateApplication')], 'Payment')
    f.subflow('Payment', 'Payment', 'SubflowApplicationPayment', [
        ('varB_IsStaffEntry', False), ('varT_FeeIds', '=varT_FeeIds'), ('varT_ApplicationIds', '=varT_ApplicationIds')], 'DeleteDraft')
    f.delete('DeleteDraft', 'Delete Draft', 'PreliminaryApplicationRef', 'CreateDraft', 'Submitted')
    f.screen('Submitted', 'Submitted', [display('SUB_Message',
             '<h2>The enrollment application has been submitted</h2><p>The Board will review it and register {!forT_FirstName} '
             '{!forT_LastName} as a student at {!GetSchool.Name}. You can follow it on <b>My School</b>.</p>')], None, back=False, pause=False)
    f.screen('CouldNotSave', 'Could Not Save', [display('CNS_Message',
             f'<p><b>The application could not be saved.</b> {{!$Flow.FaultMessage}}</p><p>Go back and try again, or call the Board at {PHONE}.</p>')],
             None, back=True, pause=False)
    f.write(outdir, 'GetRunningUser')


# ---- forms about a student already enrolled at the school ----
def student_start(f, form_name, intro_html, after):
    """School (ChooseSchool -> GetSchool), then one of its students (ChooseStudent -> GetStudent) and the
    student's latest registration at the school (GetRegistration). Students are those with a Student
    Registration application on one of the school's course offerings."""
    school_start(f, form_name, 'GetSchool')
    f.screen('ChooseSchool', form_name, [display('CS_Intro', intro_html),
             radio('CS_School', 'Cosmetology school', ['choice_Schools'])], 'GetSchool', back=False, pause=False)
    f.lookup('GetSchool', 'Get School', 'Account', [('Id', 'EqualTo', '=CS_School')],
             ['Id', 'Name', 'OwnerId', 'CertificationNumber__c', 'Phone'], 'GetSchoolOwner', first=True)
    # the owner's own lookup: a cross-object reference through Owner on a Get Records result isn't loaded
    f.lookup('GetSchoolOwner', 'Get School Owner', 'User', [('Id', 'EqualTo', '=GetSchool.OwnerId')], ['Id', 'IsPortalEnabled'],
             'IsTheSchoolApproved', first=True)
    f.decide('IsTheSchoolApproved', 'Is the School Approved?', [
        ('Approved', 'Yes', [('GetSchoolOwner.IsPortalEnabled', 'EqualTo', False)], 'GetCourseOfferings', 'and')],
        'SchoolNotApproved')
    f.screen('SchoolNotApproved', 'Not Available', [display('SNA_Message',
             f'<p>{{!GetSchool.Name}} can file school forms once the Board has approved the school. Call {PHONE}.</p>')],
             None, back=False, pause=False)
    f.lookup('GetCourseOfferings', 'Get Course Offerings', 'CourseOffering', [('School__c', 'EqualTo', '=GetSchool.Id')],
             ['Id', 'Name'], 'LoopThroughCourseOfferings', sort='Name')
    f.var('varT_OfferingIds', 'String', 'The school\'s course offerings.', coll=True)
    f.loop('LoopThroughCourseOfferings', 'Loop Through Course Offerings', 'GetCourseOfferings', 'AddOfferingId', 'AreThereOfferings')
    f.assign('AddOfferingId', 'Add Offering Id', [('varT_OfferingIds', 'Add', '=LoopThroughCourseOfferings.Id')], 'LoopThroughCourseOfferings')
    f.decide('AreThereOfferings', 'Does the School Have Courses?', [
        ('HasOfferings', 'Yes', [('varT_OfferingIds', 'IsEmpty', False)], 'GetRegistrationRecordType', 'and')], 'NoStudents')
    f.lookup('GetRegistrationRecordType', 'Get Student Registration Record Type', 'RecordType', [
        ('SobjectType', 'EqualTo', 'IndividualApplication'), ('DeveloperName', 'EqualTo', 'StudentRegistration')], ['Id'],
        'GetRegistrations', first=True)
    f.lookup('GetRegistrations', 'Get Student Registrations', 'IndividualApplication', [
        ('RecordTypeId', 'EqualTo', '=GetRegistrationRecordType.Id'), ('CourseOffering__c', 'In', '=varT_OfferingIds')],
        ['Id', 'AccountId'], 'LoopThroughRegistrations', sort='Id')
    f.var('varT_StudentIds', 'String', 'The school\'s students.', coll=True)
    f.loop('LoopThroughRegistrations', 'Loop Through Student Registrations', 'GetRegistrations', 'AddStudentId', 'AreThereStudents')
    f.assign('AddStudentId', 'Add Student Id', [('varT_StudentIds', 'Add', '=LoopThroughRegistrations.AccountId')], 'LoopThroughRegistrations')
    f.decide('AreThereStudents', 'Does the School Have Students?', [
        ('HasStudents', 'Yes', [('varT_StudentIds', 'IsEmpty', False)], 'GetStudents', 'and')], 'NoStudents')
    f.screen('NoStudents', 'Not Available', [display('NST_Message',
             '<p>The Board has no students registered at {!GetSchool.Name} yet. Enroll a student with <b>Student Enrollment</b> first.</p>')],
             None, back=False, pause=False)
    f.lookup('GetStudents', 'Get Students', 'Account', [('Id', 'In', '=varT_StudentIds')], ['Id', 'Name'], 'ChooseStudent', sort='Name')
    f.collection_choices('choice_Students', 'GetStudents', 'Account', 'Name')
    f.screen('ChooseStudent', 'Student', [radio('ST_Student', 'Student', ['choice_Students'])], 'GetStudent', pause=False)
    f.lookup('GetStudent', 'Get Student', 'Account', [('Id', 'EqualTo', '=ST_Student')],
             ['Id', 'FirstName', 'LastName', 'PersonContactId', 'PersonIndividualId'], 'GetRegistration', first=True)
    f.lookup('GetRegistration', 'Get Latest Registration', 'IndividualApplication', [
        ('AccountId', 'EqualTo', '=GetStudent.Id'), ('RecordTypeId', 'EqualTo', '=GetRegistrationRecordType.Id'),
        ('CourseOffering__c', 'In', '=varT_OfferingIds')], ['Id', 'Name', 'CourseOffering__c', 'EnrolledDate__c', 'ClassStartDate__c'],
        after, first=True, sort='CreatedDate', desc=True)
    f.formula('forT_StudentName', 'String', '{!GetStudent.FirstName} & " " & {!GetStudent.LastName}', 'The student\'s name.')
    f.formula('forT_SchoolAdministratorName', 'String', '{!GetRunningUser.FirstName} & " " & {!GetRunningUser.LastName}',
              'The School Administrator certifying the form.')


def certify(f, name, text, nxt):
    f.subflow(name, 'Certification', 'SubflowApplicationCertification', [
        ('varT_AttestationText', text), ('varT_ApplicantName', '=forT_SchoolAdministratorName')], nxt,
        outputs=[('varB_IsCertified', 'varB_IsCertified'), ('varT_CertifiedName', 'varT_CertifiedName'),
                 ('varDT_CertifiedDateTime', 'varDT_CertifiedDateTime')])
    f.var('varB_IsCertified', 'Boolean', 'The school certified the form.')
    f.var('varT_CertifiedName', 'String', 'The name typed to certify.')
    f.var('varDT_CertifiedDateTime', 'DateTime', 'When the form was certified.')


def draft(f, app_name, app_type, nxt):
    """The draft every portal form makes at its start, so a form saved for later shows in My Applications, can be
    discarded there and is deleted by the nightly clean-up. app_type is the object the form writes to: a form that
    writes no application uses ApplicationForm, as Address Change does."""
    f.formula('forT_SavedApplicationUrl', 'String', '"/LPI/s/continue-application?guid=" & {!$Flow.InterviewGuid}',
              'Records this form\'s interview GUID on the draft, so a saved form can be found again.')
    f.create('CreateDraft', 'Create Draft', 'PreliminaryApplicationRef', [
        ('ApplicationName', app_name), ('ApplicationType', app_type), ('OwnerId', '=$User.Id'), ('IsSubmitted', False),
        ('SavedApplicationUrl', '=forT_SavedApplicationUrl')], nxt)


def finish(f, target=None):
    """After the form's records are written: move the draft's documents to target (when the form has documents),
    then delete the draft and show Submitted."""
    if target:
        f.subflow('TransferDraft', 'Transfer Draft', 'SubflowPreliminaryApplicationTransfer', [
            ('varT_PreliminaryApplicationId', '=CreateDraft'), ('varT_ApplicationId', target)], 'DeleteDraft')
    f.delete('DeleteDraft', 'Delete Draft', 'PreliminaryApplicationRef', 'CreateDraft', 'Submitted')


def documents(f, name, form_type, nxt):
    """The form's documents (the checklist template named after the form) as checklist items on the draft, then the
    upload screen. The draft holds only this form's items, so earlier forms' documents don't show, and each filing
    gets its own items; finish() moves them to the student's registration on submit."""
    f.subflow(name, 'Generate Checklist', 'SubflowDocumentChecklistGenerate', [
        ('varT_ApplicationId', '=CreateDraft'), ('varT_AccountId', '=GetStudent.Id'),
        ('varT_RecordType', 'IndividualApplication.StudentRegistration'), ('varT_ApplicationType', form_type),
        ('varB_LeaveOutReceipt', True)], name + 'Upload')
    f.subflow(name + 'Upload', 'Upload Documents', 'SubflowDocumentChecklistUpload', [
        ('varT_ApplicationId', '=CreateDraft'), ('varB_IsStaffEntry', False)], nxt)


def noon(date_ref):
    """A date as a DateTime at noon Louisiana time (17:00 GMT), so it shows as the same date in every US time zone;
    a plain date written to a DateTime is midnight GMT, the day before in Pacific."""
    return f'DATETIMEVALUE({{!{date_ref}}}) + (17 / 24)'


def mdy(date_expr):
    """A date formula as MM/DD/YYYY text."""
    return (f'LPAD(TEXT(MONTH({date_expr})), 2, "0") & "/" & LPAD(TEXT(DAY({date_expr})), 2, "0") & "/" & TEXT(YEAR({date_expr}))')


def done(f, title, body):
    f.screen('Submitted', 'Submitted', [display('SUB_Message', f'<h2>{title}</h2><p>{body}</p>')], None, back=False, pause=False)
    f.screen('CouldNotSave', 'Could Not Save', [display('CNS_Message',
             f'<p><b>The form could not be saved.</b> {{!$Flow.FaultMessage}}</p><p>Go back and try again, or call the Board at {PHONE}.</p>')],
             None, back=True, pause=False)


def hours_entry(f, name, entry_type, assigns, nxt):
    f.create(name, f'Create {entry_type} Hours Entry', 'TrainingCourseParticipant', [
        ('ContactId', '=GetStudent.PersonContactId'), ('CourseOfferingId', '=GetRegistration.CourseOffering__c'),
        ('EntryType__c', entry_type), ('ReceivedDate__c', '=$Flow.CurrentDate')] + assigns, nxt, 'CouldNotSave')


SECTION_I = 'Section I: Certification of payment of contractual fees'
SECTION_II = 'Section II: Certification of non-payment of contractual fees'


def contractual_fees(outdir):
    f = Flow('ScreenFlowIndividualApplicationContractualFees', 'Certification of Contractual Fees',
             'Screen Flow: Individual Application Contractual Fees. The Board\'s Certification of Contractual Fees, filed by a '
             'School Administrator for one of the school\'s students: Section I, the student has paid all contractual fees, or '
             'Section II, the student entered a contract on or after 21 August 1992 and has not paid them all. Sets Contractual '
             'Fees Status on the student\'s latest registration and asks for the notarized original as a checklist item there.')
    student_start(f, 'Certification of Contractual Fees', '<p><b>CERTIFICATION OF CONTRACTUAL FEES</b></p><p>Section I or II must be '
                  'completed by the school owner or authorized school personnel. The official signature must be notarized: upload '
                  'the notarized form on a later screen.</p>', 'CreateDraft')
    draft(f, 'Certification of Contractual Fees', 'IndividualApplication', 'WhichSection')
    # The section wording shows from the radio itself: a formula isn't recalculated while the screen is open. A radio
    # returns its choice's label, so both the label and the stored value are tested.
    f.choice('choice_Paid', SECTION_I, 'Paid')
    f.choice('choice_NotPaid', SECTION_II, 'Not Paid')
    f.screen('WhichSection', 'Section', [
        display('WS_Student', '<p><b>Student:</b> {!forT_StudentName}</p>'),
        radio('WS_Section', 'Which section does the school certify?', ['choice_Paid', 'choice_NotPaid']),
        display('WS_Paid', '<p>This is to certify that the above named student has paid all contractual fees, pursuant to Louisiana '
                'R.S. 37:508.B, to this school and is therefore eligible to be scheduled for examination or transfer by the Louisiana '
                'State Board of Cosmetology.</p>', vis_if('WS_Section', 'EqualTo', 'Paid', 'or', [('WS_Section', 'EqualTo', SECTION_I)])),
        display('WS_NotPaid', '<p>This is to certify that the above-named student entered a contract with this school on or after '
                'August 21, 1992 and has not paid all contractual fees, pursuant to Louisiana R.S. 37:508.B/37:542.C, to this school. '
                'Upon payment of all said contractual fees I shall file a Certificate of Payment of Contractual Fees with the '
                'Louisiana State Board of Cosmetology within 10 days of said payment. I understand that the above-named individual '
                'will not be eligible for examination or transfer in the state of Louisiana until all contractual fees have been '
                'paid and I have submitted the required certification.</p>', vis_if('WS_Section', 'EqualTo', 'Not Paid', 'or', [('WS_Section', 'EqualTo', SECTION_II)])),
    ], 'Documents')
    f.formula('forT_ContractualFeesStatus', 'String', 'IF(OR({!WS_Section} = "Not Paid", CONTAINS({!WS_Section}, "non-payment")), "Not Paid", "Paid")',
              'Paid for Section I, Not Paid for Section II.')
    documents(f, 'Documents', 'Contractual Fees', 'Certification')
    certify(f, 'Certification', 'I certify, as the school owner or authorized school personnel, the section of the Certification of '
            'Contractual Fees chosen above for this student, and that the notarized original is uploaded with this form.', 'SetContractualFeesStatus')
    f.update('SetContractualFeesStatus', 'Set Contractual Fees Status', 'IndividualApplication', 'GetRegistration.Id',
             [('ContractualFeesStatus__c', '=forT_ContractualFeesStatus')], 'TransferDraft', 'CouldNotSave')
    finish(f, '=GetRegistration.Id')
    done(f, 'The certification has been filed', 'The Board has recorded the contractual fees status for {!forT_StudentName} and will review the notarized form.')
    f.write(outdir, 'GetRunningUser')


def transfer_hours(outdir):
    f = Flow('ScreenFlowTrainingCourseParticipantTransferHours', 'Transfer Hours',
             'Screen Flow: Training Course Participant Transfer Hours. The Board\'s Student Registration Transfer Hours form, filed by '
             'a School Administrator for a student who brings hours from another state: the hours submitted, the hours the school '
             'accepts, and the state and school they come from. Creates a Transfer hours entry (Total Hours = hours accepted) on the '
             'student\'s course at the school and asks for the other state board\'s certification of the hours, unless the Board '
             'already has it.')
    student_start(f, 'Transfer Hours', '<p><b>STUDENT REGISTRATION TRANSFER HOURS</b></p><p>Certification from the State Board of '
                  'Cosmetology of the transferring state must already be in our office (preferred) or accompany this request.</p>', 'CreateDraft')
    draft(f, 'Transfer Hours', 'IndividualApplication', 'Hours')
    f.el['dynamicChoiceSets'].append('<dynamicChoiceSets><name>choice_States</name><dataType>Picklist</dataType><displayField xsi:nil="true"/>'
                                     '<object xsi:nil="true"/><picklistField>SourceState__c</picklistField><picklistObject>TrainingCourseParticipant</picklistObject></dynamicChoiceSets>')
    f.choice('choice_CertificationHere', 'Already sent to the Board by the other state', 'Yes')
    f.choice('choice_CertificationUpload', 'I will upload it with this request', 'No')
    f.screen('Hours', 'Transfer Hours', [
        display('H_Student', '<p><b>Student:</b> {!forT_StudentName}<br/><b>School:</b> {!GetSchool.Name}</p>'),
        inp('H_Submitted', 'Number', 'Number of total transfer hours', required=True, scale=1,
            rule=('Enter a number of hours greater than 0.', '{!H_Submitted} > 0')),
        inp('H_Accepted', 'Number', 'Number of hours accepted by school', required=True, scale=1,
            rule=('Hours accepted can\'t be more than the hours submitted.', 'AND({!H_Accepted} >= 0, {!H_Accepted} <= {!H_Submitted})')),
        '<fields><name>H_State</name><choiceReferences>choice_States</choiceReferences><dataType>String</dataType><fieldText>State transferring from</fieldText>'
        '<fieldType>DropdownBox</fieldType><inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn><isRequired>true</isRequired></fields>',
        inp('H_School', 'String', 'School transferring from', required=True),
        radio('H_Certification', 'Certification from the transferring state\'s board', ['choice_CertificationHere', 'choice_CertificationUpload']),
    ], 'IsTheCertificationToUpload')
    f.decide('IsTheCertificationToUpload', 'Is the Certification to Upload?', [
        ('Upload', 'Yes', [('forB_UploadCertification', 'EqualTo', True)], 'Documents', 'and')], 'Certification')
    f.formula('forB_UploadCertification', 'Boolean', 'OR({!H_Certification} = "No", CONTAINS({!H_Certification}, "upload"))',
              'The school uploads the other state\'s certification with the form.')
    documents(f, 'Documents', 'Transfer Hours', 'Certification')
    certify(f, 'Certification', 'I certify, as the school\'s representative, that the transfer hours above are correct and that the '
            'school accepts the hours shown.', 'CreateTransferEntry')
    hours_entry(f, 'CreateTransferEntry', 'Transfer', [('TotalHours', '=H_Accepted'), ('HoursSubmitted__c', '=H_Submitted'),
                ('SourceState__c', '=H_State'), ('SourceSchool__c', '=H_School')], 'TransferDraft')
    finish(f, '=GetRegistration.Id')
    done(f, 'The transfer hours have been filed', 'The Board will add {!H_Accepted} hours to {!forT_StudentName}\'s record once the '
         'transferring state\'s certification is checked.')
    f.write(outdir, 'GetRunningUser')


def relinquish_hours(outdir):
    f = Flow('ScreenFlowTrainingCourseParticipantRelinquishHours', 'Relinquish Hours',
             'Screen Flow: Training Course Participant Relinquish Hours. The Board\'s Notarized Letter to Relinquish Hours, filed by a '
             'School Administrator for a student giving up hours earned at the school: the course and the hours. Creates a '
             'Relinquished hours entry (a negative number of hours) and asks for the student\'s notarized letter.')
    student_start(f, 'Relinquish Hours', '<p><b>NOTARIZED LETTER TO RELINQUISH HOURS</b></p><p>The student\'s signed and notarized '
                  'letter is uploaded on a later screen.</p>', 'CreateDraft')
    draft(f, 'Relinquish Hours', 'IndividualApplication', 'Hours')
    f.collection_choices('choice_Courses', 'GetCourseOfferings', 'CourseOffering', 'Name')
    f.screen('Hours', 'Hours Relinquished', [
        display('H_Student', '<p>I, <b>{!forT_StudentName}</b>, am relinquishing a total of the following hours in the course curriculum, '
                'obtained at <b>{!GetSchool.Name}</b>, an approved school of the State Board of Cosmetology.</p>'),
        inp('H_Hours', 'Number', 'Hours relinquished', required=True, scale=1, rule=('Enter a number of hours greater than 0.', '{!H_Hours} > 0')),
        radio('H_Course', 'Course curriculum (cosmetology, manicurist, esthetician, etc.)', ['choice_Courses']),
    ], 'Documents')
    documents(f, 'Documents', 'Relinquish Hours', 'Certification')
    certify(f, 'Certification', 'I certify, as the school\'s representative, that the student signed the notarized letter uploaded '
            'with this form, relinquishing the hours shown.', 'CreateRelinquishedEntry')
    f.formula('forN_Relinquished', 'Number', '0 - {!H_Hours}', 'Relinquished hours are recorded as a negative number.', scale=1)
    f.create('CreateRelinquishedEntry', 'Create Relinquished Hours Entry', 'TrainingCourseParticipant', [
        ('ContactId', '=GetStudent.PersonContactId'), ('CourseOfferingId', '=H_Course'), ('EntryType__c', 'Relinquished'),
        ('ReceivedDate__c', '=$Flow.CurrentDate'), ('TotalHours', '=forN_Relinquished')], 'TransferDraft', 'CouldNotSave')
    finish(f, '=GetRegistration.Id')
    done(f, 'The letter has been filed', 'The Board will take {!H_Hours} hours off {!forT_StudentName}\'s record once the notarized letter is checked.')
    f.write(outdir, 'GetRunningUser')


def termination(outdir):
    f = Flow('ScreenFlowTrainingCourseParticipantTermination', 'Notice of Termination',
             'Screen Flow: Training Course Participant Termination. The Board\'s Notice of Termination, filed by a School '
             'Administrator for a student (or instructor in training) who has discontinued training: the last date of physical '
             'attendance. Shows the months attended and the hours on file for the student at the school, then records a '
             'Termination hours entry (End Date = last day attended, no hours), which stop codes ignore.')
    student_start(f, 'Notice of Termination', '<p><b>NOTICE OF TERMINATION</b></p><p>This form is to be completed for either students or '
                  'instructors who have discontinued training.</p>', 'CreateDraft')
    draft(f, 'Notice of Termination', 'ApplicationForm', 'GetHoursEntries')
    f.lookup('GetHoursEntries', 'Get Hours Entries', 'TrainingCourseParticipant', [
        ('ContactId', 'EqualTo', '=GetStudent.PersonContactId'), ('CourseOfferingId', 'In', '=varT_OfferingIds'),
        ('EntryType__c', 'NotEqualTo', 'Continuing Education'), ('EntryType__c', 'NotEqualTo', 'Termination')],
        ['Id', 'TotalHours'], 'LoopThroughHoursEntries', sort='Id')
    f.var('varN_TotalHours', 'Number', 'The student\'s hours at the school.', default=0)
    f.loop('LoopThroughHoursEntries', 'Loop Through Hours Entries', 'GetHoursEntries', 'AddHours', 'LastAttendance')
    f.assign('AddHours', 'Add Hours', [('varN_TotalHours', 'Add', '=LoopThroughHoursEntries.TotalHours')], 'LoopThroughHoursEntries')
    f.formula('forD_StartDate', 'Date', 'BLANKVALUE({!GetRegistration.ClassStartDate__c}, {!GetRegistration.EnrolledDate__c})',
              'When the student started at the school.')
    f.formula('forT_StartDate', 'String', mdy('{!forD_StartDate}'), 'The start date as MM/DD/YYYY.')
    f.formula('forDT_StartDate', 'DateTime', noon('forD_StartDate'), 'The start date at noon Louisiana time.')
    f.formula('forDT_LastDate', 'DateTime', noon('LA_LastDate'), 'The last day attended at noon Louisiana time.')
    f.screen('LastAttendance', 'Training Information', [
        display('LA_Student', '<p><b>STUDENT PERSONAL DATA</b><br/>Name of student: {!forT_StudentName}<br/>Name of school: {!GetSchool.Name}</p>'
                '<p><b>TRAINING INFORMATION</b><br/>Started: {!forT_StartDate}<br/>Total hours on file with the Board for this student at the school: {!varN_TotalHours}</p>'),
        inp('LA_LastDate', 'Date', 'Last date of physical student attendance', required=True,
            rule=('The last day attended can\'t be before the class started, or in the future.',
                  'AND({!LA_LastDate} <= TODAY(), OR(ISBLANK({!forD_StartDate}), {!LA_LastDate} >= {!forD_StartDate}))')),
    ], 'Certification')
    certify(f, 'Certification', 'School: I certify that the above information is correct and complete.', 'CreateTerminationEntry')
    hours_entry(f, 'CreateTerminationEntry', 'Termination', [('EndDate', '=forDT_LastDate'), ('StartDate', '=forDT_StartDate'),
                ('TotalHours', 0)], 'DeleteDraft')
    finish(f)
    done(f, 'The notice of termination has been filed', 'The Board has recorded {!forT_StudentName}\'s last day of attendance.')
    f.write(outdir, 'GetRunningUser')


def instructors(f, nxt):
    """The school's instructors: active relations with role Instructor (GetInstructors, Contacts). The choices
    (choice_Instructors) are built in memory with a label that carries the license number, because a screen radio or
    checkbox group returns its choice's label, not its value: chosen_instructors() matches on that label."""
    f.lookup('GetSchoolRelations', 'Get School Relationships', 'AccountContactRelation', [
        ('AccountId', 'EqualTo', '=GetSchool.Id'), ('IsActive', 'EqualTo', True)], ['Id', 'ContactId', 'Roles', 'EndDate'], 'LoopThroughSchoolRelations', sort='Id')
    f.var('varT_InstructorIds', 'String', 'The school\'s instructors.', coll=True)
    f.loop('LoopThroughSchoolRelations', 'Loop Through School Relationships', 'GetSchoolRelations', 'IsItAnInstructor', 'GetInstructors')
    f.formula('forB_IsInstructor', 'Boolean', 'INCLUDES({!LoopThroughSchoolRelations.Roles}, "Instructor")', 'The relationship is an instructor\'s.')
    f.decide('IsItAnInstructor', 'Is It an Instructor?', [('Instructor', 'Yes', [('forB_IsInstructor', 'EqualTo', True)], 'AddInstructorId', 'and')],
             'LoopThroughSchoolRelations')
    f.assign('AddInstructorId', 'Add Instructor Id', [('varT_InstructorIds', 'Add', '=LoopThroughSchoolRelations.ContactId')], 'LoopThroughSchoolRelations')
    f.lookup('GetInstructors', 'Get Instructors', 'Contact', [('Id', 'In', '=varT_InstructorIds')], ['Id', 'Name', 'CertificationNumber__c'],
             'LoopThroughInstructors', sort='LastName')
    f.var('varR_InstructorChoice', 'SObject', 'One instructor choice: the Contact Id, and its label in Title (never saved).', obj='Contact')
    f.var('varR_InstructorChoices', 'SObject', 'The instructor choices shown on screen (never saved).', coll=True, obj='Contact')
    f.loop('LoopThroughInstructors', 'Loop Through Instructors', 'GetInstructors', 'AddInstructorChoice', nxt)
    f.formula('forT_InstructorLabel', 'String', '{!LoopThroughInstructors.Name} & IF(ISBLANK({!LoopThroughInstructors.CertificationNumber__c}), "", '
              '", license # " & {!LoopThroughInstructors.CertificationNumber__c})', 'The instructor\'s choice label: name and license number.')
    f.assign('AddInstructorChoice', 'Add Instructor Choice', [('varR_InstructorChoice.Id', 'Assign', '=LoopThroughInstructors.Id'),
             ('varR_InstructorChoice.Title', 'Assign', '=forT_InstructorLabel'), ('varR_InstructorChoices', 'Add', '=varR_InstructorChoice')],
             'LoopThroughInstructors')
    f.collection_choices('choice_Instructors', 'varR_InstructorChoices', 'Contact', 'Title')


def chosen_instructors(f, field, on_chosen, done):
    """Loops the instructor choices and goes to on_chosen for each one ticked in field (a radio or checkbox group,
    which returns the choice labels, separated by semicolons; the Id is also matched in case a value comes back)."""
    f.loop('LoopThroughInstructorChoices', 'Loop Through Instructor Choices', 'varR_InstructorChoices', 'IsTheInstructorChosen', done)
    f.formula('forB_IsInstructorChosen', 'Boolean',
              f'CONTAINS(";" & SUBSTITUTE({{!{field}}}, "; ", ";") & ";", ";" & {{!LoopThroughInstructorChoices.Title}} & ";") || '
              f'CONTAINS(";" & SUBSTITUTE({{!{field}}}, "; ", ";") & ";", ";" & {{!LoopThroughInstructorChoices.Id}} & ";")',
              'The school chose this instructor on the screen.')
    f.decide('IsTheInstructorChosen', 'Is the Instructor Chosen?', [('Chosen', 'Yes', [('forB_IsInstructorChosen', 'EqualTo', True)], on_chosen, 'and')],
             'LoopThroughInstructorChoices')


def activity_hours(outdir):
    f = Flow('ScreenFlowTrainingCourseParticipantActivityHours', 'Field Trips, Workshops, Shows and Community Service',
             'Screen Flow: Training Course Participant Activity Hours. The Board\'s Student Field Trips, Workshops, Shows and Community '
             'Service Reporting Form, filed by a School Administrator: the activity type, date, location, hours credited and the '
             'instructor who accompanied the students. Creates an Activity hours entry on the student\'s course, which counts as hours.')
    student_start(f, 'Field Trips, Workshops, Shows and Community Service', '<p><b>STUDENT FIELD TRIPS, WORKSHOPS, SHOWS AND COMMUNITY '
                  'SERVICE REPORTING FORM</b></p>', 'CreateDraft')
    draft(f, 'Field Trips, Workshops, Shows and Community Service', 'ApplicationForm', 'GetSchoolRelations')
    instructors(f, 'Activity')
    for code, t in [('FieldTrip', 'Field Trip (FT)'), ('Workshop', 'Workshop (WS)'), ('Show', 'Show (SH)'), ('CommunityService', 'Community Service (CS)')]:
        f.choice(f'choice_{code}', t, t.split(' (')[0])
    f.screen('Activity', 'Activity', [
        display('AC_Student', '<p><b>Student:</b> {!forT_StudentName}<br/><b>Name of school:</b> {!GetSchool.Name}</p>'),
        radio('AC_Type', 'Type of trip taken', ['choice_FieldTrip', 'choice_Workshop', 'choice_Show', 'choice_CommunityService']),
        inp('AC_Date', 'Date', 'Date of trip', required=True, rule=('The date can\'t be in the future.', '{!AC_Date} <= TODAY()')),
        inp('AC_Location', 'String', 'Location', required=True),
        inp('AC_Hours', 'Number', 'Number of hours credited', required=True, scale=1, rule=('Enter between 0 and 24 hours.', 'AND({!AC_Hours} > 0, {!AC_Hours} <= 24)')),
        radio('AC_Instructor', 'Instructor accompanying students', ['choice_Instructors'], required=False,
              help='The school\'s instructors on file with the Board.'),
    ], 'Certification')
    f.formula('forT_ActivityType', 'String', 'IF(CONTAINS({!AC_Type}, "Field"), "Field Trip", IF(CONTAINS({!AC_Type}, "Workshop"), "Workshop", '
              'IF(CONTAINS({!AC_Type}, "Community"), "Community Service", "Show")))', 'The activity type without its two-letter code.')
    certify(f, 'Certification', 'I certify, as the school\'s representative, that the activity above took place as reported, and that '
            'the student and the senior instructor signed the paper reporting form, which the school keeps on file.', 'LoopThroughInstructorChoices')
    f.var('varT_InstructorId', 'String', 'The accompanying instructor chosen.')
    chosen_instructors(f, 'AC_Instructor', 'SetInstructor', 'CreateActivityEntry')
    f.assign('SetInstructor', 'Set Accompanying Instructor', [('varT_InstructorId', 'Assign', '=LoopThroughInstructorChoices.Id')],
             'LoopThroughInstructorChoices')
    f.formula('forDT_ActivityDate', 'DateTime', noon('AC_Date'), 'The activity date at noon Louisiana time.')
    hours_entry(f, 'CreateActivityEntry', 'Activity', [('TotalHours', '=AC_Hours'), ('StartDate', '=forDT_ActivityDate'), ('EndDate', '=forDT_ActivityDate'),
                ('ActivityType__c', '=forT_ActivityType'), ('ActivityLocation__c', '=AC_Location'), ('AccompanyingInstructor__c', '=varT_InstructorId')], 'DeleteDraft')
    finish(f)
    done(f, 'The activity has been reported', 'The Board has added {!AC_Hours} hours for {!forT_StudentName}.')
    f.write(outdir, 'GetRunningUser')


def instructor_roster(outdir):
    f = Flow('ScreenFlowAccountInstructorRoster', 'Instructor Quarterly Roster',
             'Screen Flow: Account Instructor Roster. The Board\'s Instructor Quarterly Roster, filed by a School Administrator each '
             'quarter (March, June, September, December): lists the school\'s instructors on file (Account Contact Relations with role '
             'Instructor), lets the school mark those no longer teaching (the relation is ended, or loses the Instructor role if it '
             'has other roles) and add one by license number (an existing relation to the school is reactivated with the Instructor '
             'role rather than a second one created), and stamps the quarter and date on the school.')
    school_start(f, 'The Instructor Quarterly Roster', 'GetSchool')
    f.formula('forT_SchoolAdministratorName', 'String', '{!GetRunningUser.FirstName} & " " & {!GetRunningUser.LastName}',
              'The School Administrator certifying the form.')
    for m in ['March', 'June', 'September', 'December']:
        f.choice(f'choice_{m}', m)
    f.formula('forT_ThisYear', 'String', 'TEXT(YEAR(TODAY()))', 'This year.')
    f.screen('ChooseSchool', 'Instructor Quarterly Roster', [
        display('CS_Intro', '<p><b>INSTRUCTOR QUARTERLY ROSTER</b></p>'),
        radio('CS_School', 'School name', ['choice_Schools']),
        radio('CS_Month', 'Circle the appropriate month', ['choice_March', 'choice_June', 'choice_September', 'choice_December']),
        inp('CS_Year', 'String', 'Year', required=True, default='=forT_ThisYear',
            rule=('Enter this year or last year.', 'AND(REGEX(TRIM({!CS_Year}), "\\\\d{4}"), VALUE(TRIM({!CS_Year})) >= YEAR(TODAY()) - 1, '
                  'VALUE(TRIM({!CS_Year})) <= YEAR(TODAY()))')),
    ], 'GetSchool', back=False, pause=False)
    f.lookup('GetSchool', 'Get School', 'Account', [('Id', 'EqualTo', '=CS_School')], ['Id', 'Name', 'OwnerId'], 'CreateDraft', first=True)
    draft(f, 'Instructor Quarterly Roster', 'ApplicationForm', 'GetSchoolRelations')
    instructors(f, 'BuildRoster')
    f.var('varT_RosterHtml', 'String', 'The instructors on file, as a list.')
    f.loop('BuildRoster', 'Loop Through Instructors for the Roster', 'GetInstructors', 'AddRosterLine', 'Roster')
    f.formula('forT_RosterLine', 'String', '"<li>" & {!BuildRoster.Name} & IF(ISBLANK({!BuildRoster.CertificationNumber__c}), "", ", license # " & {!BuildRoster.CertificationNumber__c}) & "</li>"',
              'One instructor on the roster.')
    f.assign('AddRosterLine', 'Add Roster Line', [('varT_RosterHtml', 'Add', '=forT_RosterLine')], 'BuildRoster')
    f.screen('Roster', 'Roster', [
        display('RO_List', '<p><b>Instructors on file with the Board for {!GetSchool.Name}:</b></p><ul>{!varT_RosterHtml}</ul>'),
        f'<fields><name>RO_Left</name><choiceReferences>choice_Instructors</choiceReferences><dataType>String</dataType>'
        f'<fieldText>Instructors no longer teaching at the school</fieldText><fieldType>MultiSelectCheckboxes</fieldType>'
        f'<inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn><isRequired>false</isRequired></fields>',
        inp('RO_NewNumber', 'String', 'Add an instructor: their license number', help='Leave blank if no instructor joined this quarter.'),
    ], 'IsAnInstructorAdded')
    f.formula('forT_NewNumber', 'String', 'IF(CONTAINS(TRIM({!RO_NewNumber}), "-"), LEFT(TRIM({!RO_NewNumber}), FIND("-", TRIM({!RO_NewNumber})) - 1), TRIM({!RO_NewNumber}))',
              'The number typed, without a license type suffix.')
    f.formula('forT_NewNumberClean', 'String', 'IF(LEFT(UPPER({!forT_NewNumber}), 1) = "L", MID({!forT_NewNumber}, 2, 40), {!forT_NewNumber})',
              'The number without the L printed in front.')
    f.decide('IsAnInstructorAdded', 'Is an Instructor Added?', [
        ('Added', 'Yes', [('RO_NewNumber', 'IsBlank', False)], 'GetNewInstructor', 'and')], 'Certification')
    f.lookup('GetNewInstructor', 'Get New Instructor', 'Contact', [('CertificationNumber__c', 'EqualTo', '=forT_NewNumberClean')],
             ['Id', 'Name'], 'IsTheNewInstructorFound', first=True)
    f.decide('IsTheNewInstructorFound', 'Is the New Instructor Found?', [
        ('Found', 'Yes', [('GetNewInstructor.Id', 'IsNull', False)], 'ConfirmNewInstructor', 'and')], 'NewInstructorNotFound')
    f.screen('NewInstructorNotFound', 'Not Found', [display('NNF_Message', '<p>No licensee has license number {!RO_NewNumber}. Go back and '
             'check the number, or leave it blank and call the Board.</p>')], None, back=True, pause=False)
    f.screen('ConfirmNewInstructor', 'New Instructor', [display('CN_Message', '<p><b>{!GetNewInstructor.Name}</b> will be added to the '
             'roster as an instructor at {!GetSchool.Name}.</p>')], 'Certification')
    certify(f, 'Certification', 'I certify that this roster lists the instructors teaching at the school for the quarter shown.', 'IsANewInstructorToAdd')
    f.decide('IsANewInstructorToAdd', 'Is a New Instructor to Add?', [
        ('ToAdd', 'Yes', [('GetNewInstructor.Id', 'IsNull', False)], 'GetExistingRelation', 'and')], 'LoopThroughInstructorChoices')
    # one relation per school and person: a returning instructor, or someone with another role at the school, keeps theirs
    f.lookup('GetExistingRelation', 'Get Existing Relationship', 'AccountContactRelation', [
        ('AccountId', 'EqualTo', '=GetSchool.Id'), ('ContactId', 'EqualTo', '=GetNewInstructor.Id')],
        ['Id', 'Roles', 'IsActive', 'StartDate'], 'IsThereAnExistingRelation', first=True)
    f.decide('IsThereAnExistingRelation', 'Is There an Existing Relationship?', [
        ('Existing', 'Yes', [('GetExistingRelation.Id', 'IsNull', False)], 'SetExistingRoles', 'and')], 'CreateInstructorRelation')
    f.var('varT_ExistingRoles', 'String', 'The existing relationship\'s roles, as text.')
    f.assign('SetExistingRoles', 'Set Existing Roles', [('varT_ExistingRoles', 'Assign', '=GetExistingRelation.Roles')], 'UpdateExistingRelation')
    f.formula('forB_AlreadyTeaching', 'Boolean', 'AND({!GetExistingRelation.IsActive}, CONTAINS(";" & {!varT_ExistingRoles} & ";", ";Instructor;"))',
              'The person is already an active instructor at the school.')
    f.formula('forT_RolesWithInstructor', 'String', 'IF(CONTAINS(";" & {!varT_ExistingRoles} & ";", ";Instructor;"), {!varT_ExistingRoles}, '
              'IF(ISBLANK({!varT_ExistingRoles}), "Instructor", {!varT_ExistingRoles} & ";Instructor"))', 'The existing roles with Instructor added.')
    f.formula('forD_InstructorStartDate', 'Date', 'IF({!forB_AlreadyTeaching}, {!GetExistingRelation.StartDate}, TODAY())',
              'Today, unless the person is already teaching at the school.')
    f.update('UpdateExistingRelation', 'Update Existing Relationship', 'AccountContactRelation', 'GetExistingRelation.Id', [
        ('Roles', '=forT_RolesWithInstructor'), ('IsActive', True), ('StartDate', '=forD_InstructorStartDate'), ('EndDate', None)],
        'LoopThroughInstructorChoices', 'CouldNotSave')
    f.create('CreateInstructorRelation', 'Create Instructor Relationship', 'AccountContactRelation', [
        ('AccountId', '=GetSchool.Id'), ('ContactId', '=GetNewInstructor.Id'), ('Roles', 'Instructor'), ('IsActive', True),
        ('StartDate', '=$Flow.CurrentDate')], 'LoopThroughInstructorChoices', 'CouldNotSave')
    # instructors ticked as no longer teaching (matched on the choice label, which carries the license number)
    f.var('varT_LeftContactIds', 'String', 'The instructors ticked as no longer teaching, as Contact Ids each followed by a semicolon.')
    chosen_instructors(f, 'RO_Left', 'AddLeftContactId', 'LoopThroughRelationsToEnd')
    f.formula('forT_LeftContactId', 'String', '{!LoopThroughInstructorChoices.Id} & ";"', 'One ticked instructor\'s Contact Id.')
    f.assign('AddLeftContactId', 'Add Left Contact Id', [('varT_LeftContactIds', 'Add', '=forT_LeftContactId')], 'LoopThroughInstructorChoices')
    f.var('varR_Ended', 'SObject', 'One relationship being ended.', obj='AccountContactRelation')
    f.var('varR_EndedRelations', 'SObject', 'Relationships of instructors no longer teaching.', coll=True, obj='AccountContactRelation')
    f.var('varT_RelationRoles', 'String', 'The relationship\'s roles, as text.')
    f.loop('LoopThroughRelationsToEnd', 'Loop Through Relationships', 'GetSchoolRelations', 'HasTheInstructorLeft', 'AreThereRelationsToEnd')
    f.formula('forB_HasLeft', 'Boolean', 'AND({!forB_IsInstructorToEnd}, CONTAINS(";" & {!varT_LeftContactIds}, ";" & {!LoopThroughRelationsToEnd.ContactId} & ";"))',
              'The school marked this instructor as no longer teaching.')
    f.formula('forB_IsInstructorToEnd', 'Boolean', 'INCLUDES({!LoopThroughRelationsToEnd.Roles}, "Instructor")', 'An instructor relationship.')
    f.decide('HasTheInstructorLeft', 'Has the Instructor Left?', [('Left', 'Yes', [('forB_HasLeft', 'EqualTo', True)], 'SetRelationRoles', 'and')],
             'LoopThroughRelationsToEnd')
    f.assign('SetRelationRoles', 'Set Relationship Roles', [('varT_RelationRoles', 'Assign', '=LoopThroughRelationsToEnd.Roles')], 'SetEndedRelation')
    f.formula('forB_OnlyInstructor', 'Boolean', 'TRIM({!varT_RelationRoles}) = "Instructor"', 'Instructor is the relationship\'s only role.')
    f.formula('forB_StaysActive', 'Boolean', 'NOT({!forB_OnlyInstructor})', 'The relationship has other roles, so it stays active.')
    f.formula('forT_RolesWithoutInstructor', 'String', 'SUBSTITUTE(";" & {!varT_RelationRoles} & ";", ";Instructor;", ";")',
              'The roles without Instructor, between semicolons.')
    f.formula('forT_RemainingRoles', 'String', 'IF({!forB_OnlyInstructor}, {!varT_RelationRoles}, MID({!forT_RolesWithoutInstructor}, 2, '
              'LEN({!forT_RolesWithoutInstructor}) - 2))', 'The roles the relationship keeps.')
    f.formula('forD_RelationEndDate', 'Date', 'IF({!forB_OnlyInstructor}, TODAY(), {!LoopThroughRelationsToEnd.EndDate})',
              'Today when the relationship ends.')
    f.assign('SetEndedRelation', 'Set Ended Relationship', [('varR_Ended.Id', 'Assign', '=LoopThroughRelationsToEnd.Id'),
             ('varR_Ended.IsActive', 'Assign', '=forB_StaysActive'), ('varR_Ended.EndDate', 'Assign', '=forD_RelationEndDate'),
             ('varR_Ended.Roles', 'Assign', '=forT_RemainingRoles')], 'AddEndedRelation')
    f.assign('AddEndedRelation', 'Add Ended Relationship', [('varR_EndedRelations', 'Add', '=varR_Ended')], 'LoopThroughRelationsToEnd')
    f.decide('AreThereRelationsToEnd', 'Are There Relationships to End?', [
        ('HasEnded', 'Yes', [('varR_EndedRelations', 'IsEmpty', False)], 'EndRelations', 'and')], 'SetRosterDate')
    f.el['recordUpdates'].append(f'<recordUpdates><name>EndRelations</name><label>End Relationships</label>{LOC}{conn("SetRosterDate")}'
                                 f'{conn("CouldNotSave", "faultConnector")}<inputReference>varR_EndedRelations</inputReference></recordUpdates>')
    f.formula('forT_Quarter', 'String', '{!CS_Month} & " " & TRIM({!CS_Year})', 'The quarter the roster covers.')
    f.update('SetRosterDate', 'Set Roster Date and Quarter', 'Account', 'GetSchool.Id', [
        ('LastInstructorRosterDate__c', '=$Flow.CurrentDate'), ('LastInstructorRosterQuarter__c', '=forT_Quarter')], 'DeleteDraft', 'CouldNotSave')
    finish(f)
    done(f, 'The roster has been filed', 'The Board has the {!forT_Quarter} instructor roster for {!GetSchool.Name}.')
    f.write(outdir, 'GetRunningUser')


EXAM_FORMS = [  # (choice name, label, Application Type, needs practical+state, asks hours/dates)
    ('NationalExam', 'Application for National Exam', 'National Exam'),
    ('NationalRetake', 'Application for National Retake Exam', 'National Retake'),
    ('AlternativeHairDesign', 'Application for Alternative Hair Design Practical and State Exam', 'Practical and State'),
    ('PracticalAndState', 'Application for Practical and State Exam', 'Practical and State'),
    ('PracticalAndState1400', '1400 Hour Application for Practical and State Examinations', 'Practical and State 1400 Hour'),
    ('ExamRetake', 'Application for Retake Exam(s)', 'Exam Retake'),
    ('NoShow', 'Application for No Show Exam(s)', 'No Show'),
]
NO_SHOW_TEXT = ('I understand that if I fail to show for my scheduled examination without proper notification, a seven day notice or 24 '
                'hours emergency notice, I will be required upon reapplication to submit a $25.00 administrative fee.')


def examination(outdir):
    f = Flow('ScreenFlowIndividualApplicationExamination', 'Exam Application',
             'Screen Flow: Individual Application Examination. The Board\'s seven exam applications from the School Forms packet, filed '
             'by a School Administrator for a student: national exam, national retake, alternative hair design practical and state, '
             'practical and state, 1400 hour practical and state, retake exam(s) and no-show exam(s). Each keeps its own sections and '
             'wording. Creates an Examination application with the exams, dates and hours, the no-show acknowledgement and any '
             'accommodation request, the documents the form lists, and the fees printed on the form, from the Fee Schedule.')
    student_start(f, 'Exam Application', '<p><b>EXAM APPLICATIONS</b></p><p>Choose the school, then the student and the application.</p>', 'CreateDraft')
    f.formula('forT_SavedApplicationUrl', 'String', '"/LPI/s/continue-application?guid=" & {!$Flow.InterviewGuid}', 'Finds a saved form again.')
    f.create('CreateDraft', 'Create Draft', 'PreliminaryApplicationRef', [
        ('ApplicationName', 'Exam Application'), ('ApplicationType', 'IndividualApplication'), ('OwnerId', '=$User.Id'),
        ('IsSubmitted', False), ('SavedApplicationUrl', '=forT_SavedApplicationUrl')], 'WhichForm')
    for code, label, _ in EXAM_FORMS:
        f.choice(f'choice_{code}', label)
    for n, t in [('Cosmetology', 'Cosmetology'), ('Manicurist', 'Manicurist'), ('Esthetician', 'Esthetician'), ('Instructor', 'Instructor'),
                 ('CosmetologyInstructor', 'Cosmetology Instructor'), ('EstheticianInstructor', 'Esthetician Instructor'),
                 ('ManicuristInstructor', 'Manicurist Instructor'), ('AlternativeHair', 'Alternative Hair Design'),
                 ('English', 'English'), ('Vietnamese', 'Vietnamese'), ('Spanish', 'Spanish'),
                 ('State', 'State'), ('Practical', 'Practical'), ('StateRetake', 'State Retake'), ('PracticalRetake', 'Practical Retake')]:
        f.choice(f'choice_{n}', t)
    f.screen('WhichForm', 'Application', [
        display('WF_Student', '<p><b>Student:</b> {!forT_StudentName}<br/><b>School:</b> {!GetSchool.Name}</p>'),
        radio('WF_Form', 'Which application?', [f'choice_{c}' for c, _, _ in EXAM_FORMS]),
    ], 'ExamDetails')
    lab = {c: l for c, l, _ in EXAM_FORMS}
    is_ = lambda *codes: ' || '.join(f'{{!WF_Form}} = "{lab[c]}"' for c in codes)
    f.formula('forB_IsNational', 'Boolean', is_('NationalExam', 'NationalRetake'), 'A national exam application.')
    f.formula('forB_IsAhd', 'Boolean', is_('AlternativeHairDesign'), 'The alternative hair design application.')
    f.formula('forB_IsPracticalAndState', 'Boolean', is_('AlternativeHairDesign', 'PracticalAndState', 'PracticalAndState1400'),
              'An application for both the practical and state exams.')
    f.formula('forB_Is1400', 'Boolean', is_('PracticalAndState1400'), 'The 1400 hour application.')
    f.formula('forB_ChoosesExams', 'Boolean', is_('ExamRetake', 'NoShow'), 'The applicant chooses which exams.')
    f.formula('forT_ApplicationType', 'String', 'CASE({!WF_Form}, ' + ', '.join(f'"{l}", "{t}"' for _, l, t in EXAM_FORMS) + ', "")',
              'The application type for the form chosen.')
    vis = lambda formula: vis_if(formula, 'EqualTo', True)
    f.screen('ExamDetails', 'Applicant Personal Data', [
        display('ED_Heading', '<p><b>APPLICANT PERSONAL DATA</b></p><p>I hereby make application for license by examination to practice:</p>'),
        radio('ED_License', 'License', ['choice_Cosmetology', 'choice_Manicurist', 'choice_Esthetician', 'choice_Instructor', 'choice_AlternativeHair'],
              vis=vis_if('forB_IsAhd', 'EqualTo', False)),
        display('ED_AhdLicense', '<p><b>Alternative hair design permit</b></p>', vis=vis('forB_IsAhd')),
        radio('ED_InstructorLicense', 'Which instructor license?', ['choice_CosmetologyInstructor', 'choice_EstheticianInstructor', 'choice_ManicuristInstructor'],
              vis=vis_if('ED_License', 'EqualTo', 'Instructor')),
        radio('ED_Language', 'Select language', ['choice_English', 'choice_Vietnamese', 'choice_Spanish'], vis=vis('forB_IsNational')),
        f'<fields><name>ED_Exams</name><choiceReferences>choice_State</choiceReferences><choiceReferences>choice_Practical</choiceReferences>'
        f'<choiceReferences>choice_StateRetake</choiceReferences><choiceReferences>choice_PracticalRetake</choiceReferences><dataType>String</dataType>'
        f'<fieldText>Exams</fieldText><fieldType>MultiSelectCheckboxes</fieldType><inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn>'
        f'<isRequired>true</isRequired>{vis("forB_ChoosesExams")}</fields>',
        inp('ED_Enrolled', 'Date', 'Date enrolled', required=True, default='=GetRegistration.ClassStartDate__c', vis=vis('forB_IsPracticalAndState')),
        inp('ED_Hours', 'Number', 'Total number of hours completed', required=True, scale=1, vis=vis_if('forB_IsNational', 'EqualTo', False, 'and', [('forB_ChoosesExams', 'EqualTo', False)])),
        inp('ED_Completed', 'Date', 'Date completed training', required=True, vis=vis_if('forB_IsPracticalAndState', 'EqualTo', True, 'and', [('forB_Is1400', 'EqualTo', False)]),
            rule=('The date completed can\'t be in the future or before the date enrolled.',
                  'OR(ISBLANK({!ED_Completed}), AND({!ED_Completed} <= TODAY(), OR(ISBLANK({!ED_Enrolled}), {!ED_Completed} >= {!ED_Enrolled})))')),
        inp('ED_Attendance', 'Number', 'Hours of attendance at school', required=True, scale=1, vis=vis('forB_IsNational')),
    ], 'StudentDetails')
    f.subflow('StudentDetails', 'Student Details', 'SubflowApplicantDetails', [
        ('varT_AccountId', '=GetStudent.Id'), ('varB_IsStaffEntry', False), ('varB_AskGender', '=forB_Is1400')], 'NeedsNoShowStatement')
    f.decide('NeedsNoShowStatement', 'Does the Form Carry the No-Show Statement?', [
        ('NoShowStatement', 'Yes', [('forB_IsNational', 'EqualTo', False)], 'NoShowAcknowledgement', 'and')], 'GenerateDraftChecklist')
    f.subflow('NoShowAcknowledgement', 'No-Show Acknowledgement', 'SubflowApplicationNoShowAcknowledgement', [('varT_StatementText', NO_SHOW_TEXT)],
              'Accommodation', outputs=[('varB_Acknowledged', 'varB_NoShowAcknowledged')])
    f.var('varB_NoShowAcknowledged', 'Boolean', 'The applicant acknowledged the no-show statement.', default=False)
    f.subflow('Accommodation', 'Accommodation Request', 'SubflowAccommodationRequest', [
        ('varT_AccountId', '=GetStudent.Id'), ('varT_ExamName', '=forT_ApplicationType'), ('varB_IsStaffEntry', False), ('varT_DraftId', '=CreateDraft')],
        'GenerateDraftChecklist')
    f.subflow('GenerateDraftChecklist', 'Generate Draft Checklist', 'SubflowDocumentChecklistGenerate', [
        ('varT_ApplicationId', '=CreateDraft'), ('varT_AccountId', '=GetStudent.Id'), ('varT_RecordType', 'IndividualApplication.Examination'),
        ('varT_ApplicationType', '=forT_ApplicationType'), ('varB_LeaveOutReceipt', True)], 'UploadDocuments')
    f.subflow('UploadDocuments', 'Upload Documents', 'SubflowDocumentChecklistUpload', [('varT_ApplicationId', '=CreateDraft'), ('varB_IsStaffEntry', False)],
              'Certification')
    certify(f, 'Certification', 'The applicant hereby makes application for license by examination as shown, and the information given is '
            'true and correct. I certify, as the school\'s representative, that the applicant (and, where the form asks, the instructor) '
            'signed the paper application, which the school keeps on file.', 'GetExamRecordType')
    f.formula('forT_LicenseTypeName', 'String', 'IF({!forB_IsAhd}, "Alternative Hair Design Permit", CASE({!ED_License}, "Cosmetology", "Cosmetologist", '
              '"Manicurist", "Manicurist", "Esthetician", "Esthetician", "Alternative Hair Design", "Alternative Hair Design Permit", '
              '"Instructor", {!ED_InstructorLicense}, ""))', 'The license type sought.')
    f.lookup('GetExamRecordType', 'Get Examination Record Type', 'RecordType', [
        ('SobjectType', 'EqualTo', 'IndividualApplication'), ('DeveloperName', 'EqualTo', 'Examination')], ['Id'], 'GetLicenseType', first=True)
    f.lookup('GetLicenseType', 'Get License Type', 'RegulatoryAuthorizationType', [('Name', 'EqualTo', '=forT_LicenseTypeName')],
             ['Id', 'Name', 'RegulatoryAuthCategory'], 'CreateApplication', first=True)
    f.formula('forB_State', 'Boolean', 'OR({!forB_IsPracticalAndState}, CONTAINS({!ED_Exams}, "State"))', 'The state exam is applied for.')
    f.formula('forB_Practical', 'Boolean', 'OR({!forB_IsPracticalAndState}, CONTAINS({!ED_Exams}, "Practical"))', 'The practical exam is applied for.')
    f.formula('forT_Exams', 'String', 'IF({!forB_IsNational}, "National", IF({!forB_Practical}, "Practical", "") & IF({!forB_Practical} && {!forB_State}, ";", "") & IF({!forB_State}, "State", ""))',
              'The Exams value.')
    f.formula('forT_Category', 'String', 'IF(ISPICKVAL({!GetLicenseType.RegulatoryAuthCategory}, "Permit"), "Permit", "License")', 'License or permit.')
    f.create('CreateApplication', 'Create Application', 'IndividualApplication', [
        ('RecordTypeId', '=GetExamRecordType.Id'), ('AccountId', '=GetStudent.Id'), ('LicenseTypeId', '=GetLicenseType.Id'),
        ('Category', '=forT_Category'), ('ApplicationType', '=forT_ApplicationType'), ('Status', 'Submitted'), ('AppliedDate', '=$Flow.CurrentDateTime'),
        ('Exams__c', '=forT_Exams'), ('CourseOffering__c', '=GetRegistration.CourseOffering__c'), ('EnrolledDate__c', '=ED_Enrolled'),
        ('CompletedDate__c', '=ED_Completed'), ('TotalCompletedHours__c', '=forN_Hours'), ('NoShowFeeAcknowledged__c', '=varB_NoShowAcknowledged'),
        ('IsCertified__c', '=varB_IsCertified'), ('CertifiedName__c', '=varT_CertifiedName'), ('CertifiedDateTime__c', '=varDT_CertifiedDateTime')],
        'TransferDraft', 'CouldNotSave')
    f.formula('forN_Hours', 'Number', 'BLANKVALUE({!ED_Hours}, {!ED_Attendance})', 'Hours completed or attended.', scale=1)
    f.subflow('TransferDraft', 'Transfer Draft', 'SubflowPreliminaryApplicationTransfer', [
        ('varT_PreliminaryApplicationId', '=CreateDraft'), ('varT_ApplicationId', '=CreateApplication')], 'IsALanguageChosen')
    # national exams: the exam language joins the student's languages (Person Language) if it isn't there yet
    f.decide('IsALanguageChosen', 'Is an Exam Language Chosen?', [('LanguageChosen', 'Yes', [('forB_IsNational', 'EqualTo', True)],
             'DoesTheStudentHaveAnIndividual', 'and')], 'AreFeesDue')
    f.var('varT_IndividualId', 'String', 'The student\'s Individual, which holds their languages.')
    f.decide('DoesTheStudentHaveAnIndividual', 'Does the Student Have an Individual?', [('HasIndividual', 'Yes',
             [('GetStudent.PersonIndividualId', 'IsNull', False)], 'SetIndividual', 'and')], 'CreateIndividual', default_label='No, create one')
    f.assign('SetIndividual', 'Set Individual', [('varT_IndividualId', 'Assign', '=GetStudent.PersonIndividualId')], 'GetStudentLanguages')
    f.create('CreateIndividual', 'Create Individual', 'Individual', [('FirstName', '=GetStudent.FirstName'), ('LastName', '=GetStudent.LastName')],
             'LinkIndividualToStudent', 'CouldNotSave')
    f.update('LinkIndividualToStudent', 'Link Individual to Student', 'Account', 'GetStudent.Id', [('PersonIndividualId', '=CreateIndividual')],
             'SetNewIndividual', 'CouldNotSave')
    f.assign('SetNewIndividual', 'Set New Individual', [('varT_IndividualId', 'Assign', '=CreateIndividual')], 'GetStudentLanguages')
    f.lookup('GetStudentLanguages', 'Get Student Languages', 'PersonLanguage', [('IndividualId', 'EqualTo', '=varT_IndividualId')],
             ['Id', 'Language', 'Rank'], 'LoopThroughLanguages', sort='Rank')
    f.var('varN_LanguageCount', 'Number', 'How many languages the student has.', default=0, scale=0)
    f.var('varB_HasLanguage', 'Boolean', 'The student already has the exam language.', default=False)
    f.loop('LoopThroughLanguages', 'Loop Through Student Languages', 'GetStudentLanguages', 'CountLanguage', 'DoesTheStudentHaveTheLanguage')
    f.formula('forB_SameLanguage', 'Boolean', 'TEXT({!LoopThroughLanguages.Language}) = {!ED_Language}', 'This is the exam language.')
    f.assign('CountLanguage', 'Count Language', [('varN_LanguageCount', 'Add', 1)], 'IsItTheExamLanguage')
    f.decide('IsItTheExamLanguage', 'Is It the Exam Language?', [('Same', 'Yes', [('forB_SameLanguage', 'EqualTo', True)], 'SetHasLanguage', 'and')],
             'LoopThroughLanguages')
    f.assign('SetHasLanguage', 'Set Has Language', [('varB_HasLanguage', 'Assign', True)], 'LoopThroughLanguages')
    f.decide('DoesTheStudentHaveTheLanguage', 'Does the Student Have the Language?', [('Missing', 'No, add it', [('varB_HasLanguage', 'EqualTo', False)],
             'CreateLanguage', 'and')], 'AreFeesDue', default_label='Yes')
    f.formula('forN_NextRank', 'Number', '{!varN_LanguageCount} + 1', 'The new language\'s rank.', scale=0)
    f.create('CreateLanguage', 'Create Person Language', 'PersonLanguage', [('IndividualId', '=varT_IndividualId'),
             ('Language', '=ED_Language'), ('Rank', '=forN_NextRank')], 'AreFeesDue', 'CouldNotSave')
    # fees, as printed on each form
    f.formula('forB_InitialFee', 'Boolean', '{!forB_IsAhd} || {!WF_Form} = "Application for Practical and State Exam"', 'The initial license or permit fee applies.')
    f.formula('forB_NoShowFees', 'Boolean', '{!WF_Form} = "Application for No Show Exam(s)"', 'No-show fees apply per exam.')
    f.formula('forT_InitialFeeName', 'String', '{!GetLicenseType.Name} & " Initial"', 'The license type\'s initial fee row.')
    f.decide('AreFeesDue', 'Are Fees Due?', [('FeesDue', 'Yes', [('forB_IsNational', 'EqualTo', False)], 'CreateFee', 'and')], 'DeleteDraft',
             default_label='No, national exams are paid to the testing company')
    f.create('CreateFee', 'Create Fee', 'RegulatoryTrxnFee', [
        ('AccountId', '=GetStudent.Id'), ('ParentRecordId', '=CreateApplication'), ('Status', 'DUE'), ('DueDate', '=$Flow.CurrentDateTime'),
        ('Description', '=forT_ApplicationType')], 'IsTheInitialFeeDue')
    f.formula('forT_ThisYear', 'String', 'TEXT(YEAR(TODAY()))', 'This year, the fee items\' year.')
    f.var('varR_FeeItems', 'SObject', 'The fee items.', coll=True, obj='RegulatoryTrxnFeeItem')
    f.var('varR_FeeItem', 'SObject', 'One fee item.', obj='RegulatoryTrxnFeeItem')
    chain = [('Initial', 'forB_InitialFee', '=forT_InitialFeeName', 'Initial license fee'),
             ('Practical', 'forB_Practical', 'Practical Examination', 'Practical examination fee'),
             ('State', 'forB_State', 'State Examination', 'State examination fee'),
             ('NoShowPractical', 'forB_NoShowPractical', 'No Show', 'No-show administrative fee, practical exam'),
             ('NoShowState', 'forB_NoShowState', 'No Show', 'No-show administrative fee, state exam')]
    f.formula('forB_NoShowPractical', 'Boolean', '{!forB_NoShowFees} && {!forB_Practical}', 'A no-show fee for the practical exam.')
    f.formula('forB_NoShowState', 'Boolean', '{!forB_NoShowFees} && {!forB_State}', 'A no-show fee for the state exam.')
    for i, (k, cond, fee, text) in enumerate(chain):
        nxt = f'Is{chain[i + 1][0]}FeeDue' if i + 1 < len(chain) else 'CreateFeeItems'
        if i == 0:
            k_dec = 'IsTheInitialFeeDue'
        else:
            k_dec = f'Is{k}FeeDue'
        f.decide(k_dec, f'Is the {text} Due?', [(f'{k}Due', 'Yes', [(cond, 'EqualTo', True)], f'LookUp{k}Fee', 'and')], nxt)
        f.action(f'LookUp{k}Fee', f'Look Up {text}', 'FeeSchedule', 'runDecisionMatrix', [('FeeName', fee)], f'Set{k}FeeItem')
        f.assign(f'Set{k}FeeItem', f'Set {text} Item', [
            ('varR_FeeItem.RegulatoryTrxnFeeId', 'Assign', '=CreateFee'), ('varR_FeeItem.Name', 'Assign', text),
            ('varR_FeeItem.FeeAmount', 'Assign', f'=LookUp{k}Fee.Amount'), ('varR_FeeItem.ForYear__c', 'Assign', '=forT_ThisYear'),
            ('varR_FeeItem.CalculationInfo', 'Assign', f'{text}, from the Fee Schedule.'), ('varR_FeeItems', 'Add', '=varR_FeeItem')], nxt)
    f.create_many('CreateFeeItems', 'Create Fee Items', 'varR_FeeItems', 'GenerateReceiptItem', 'CouldNotSave')
    f.subflow('GenerateReceiptItem', 'Generate Receipt Checklist Item', 'SubflowDocumentChecklistGenerate', [
        ('varT_ApplicationId', '=CreateApplication'), ('varT_AccountId', '=GetStudent.Id'), ('varT_RecordType', 'IndividualApplication.Examination'),
        ('varT_ApplicationType', '=forT_ApplicationType')], 'SetPaymentIds')
    f.var('varT_FeeIds', 'String', 'The fees to pay.', coll=True)
    f.var('varT_ApplicationIds', 'String', 'The application the fees are for.', coll=True)
    f.assign('SetPaymentIds', 'Set Payment Ids', [('varT_FeeIds', 'Add', '=CreateFee'), ('varT_ApplicationIds', 'Add', '=CreateApplication')], 'Payment')
    f.subflow('Payment', 'Payment', 'SubflowApplicationPayment', [
        ('varB_IsStaffEntry', False), ('varT_FeeIds', '=varT_FeeIds'), ('varT_ApplicationIds', '=varT_ApplicationIds')], 'DeleteDraft')
    f.delete('DeleteDraft', 'Delete Draft', 'PreliminaryApplicationRef', 'CreateDraft', 'Submitted')
    done(f, 'The exam application has been submitted', 'The Board will review {!forT_StudentName}\'s application and schedule the exams.')
    f.write(outdir, 'GetRunningUser')


FORM_LINKS = [('student-enrollment', 'Student Enrollment'), ('contractual-fees', 'Certification of Contractual Fees'),
              ('transfer-hours', 'Transfer Hours'), ('relinquish-hours', 'Relinquish Hours'), ('notice-of-termination', 'Notice of Termination'),
              ('activity-hours', 'Field Trips, Workshops, Shows and Community Service'), ('exam-application', 'Exam Application'),
              ('instructor-roster', 'Instructor Quarterly Roster')]


def listing(f, name, coll, line_expr, desc, nxt, var):
    """Builds an HTML list in var from a collection, one <li> per record."""
    f.var(var, 'String', desc)
    f.loop(name, f'Loop Through {desc}', coll, f'Add{name}Line', nxt)
    f.formula(f'forT_{name}Line', 'String', '"<li>" & ' + line_expr + ' & "</li>"', f'One line of {desc}.')
    f.assign(f'Add{name}Line', f'Add {desc} Line', [(var, 'Add', f'=forT_{name}Line')], name)


def my_school(outdir):
    f = Flow('ScreenFlowAccountMySchool', 'My School',
             'Screen Flow: Account My School. The School Administrator\'s home on the portal: the school\'s licenses, its students '
             '(Student Registration applications on the school\'s course offerings, with status) and links to the school forms. '
             'Read only; runs in system context, showing only the schools the signed-in person administers.')
    school_start(f, 'My School', 'GetSchool')
    f.screen('ChooseSchool', 'My School', [radio('CS_School', 'School', ['choice_Schools'])], 'GetSchool', back=False, pause=False)
    f.lookup('GetSchool', 'Get School', 'Account', [('Id', 'EqualTo', '=CS_School')], ['Id', 'Name', 'LastInstructorRosterQuarter__c'], 'GetLicenses', first=True)
    f.lookup('GetLicenses', 'Get School Licenses', 'BusinessLicense', [('AccountId', 'EqualTo', '=GetSchool.Id')],
             ['Id', 'Name', 'Identifier', 'Status', 'PeriodEnd'], 'ListLicenses', sort='Name')
    listing(f, 'ListLicenses', 'GetLicenses', '{!ListLicenses.Name} & ", license " & BLANKVALUE({!ListLicenses.Identifier}, "pending") & ": " & TEXT({!ListLicenses.Status}) '
            '& IF(ISBLANK({!ListLicenses.PeriodEnd}), "", ", expires " & ' + mdy('DATEVALUE({!ListLicenses.PeriodEnd})') + ')', 'licenses', 'GetCourseOfferings', 'varT_LicensesHtml')
    f.lookup('GetCourseOfferings', 'Get Course Offerings', 'CourseOffering', [('School__c', 'EqualTo', '=GetSchool.Id')], ['Id'], 'LoopThroughCourseOfferings')
    f.var('varT_OfferingIds', 'String', 'The school\'s course offerings.', coll=True)
    f.loop('LoopThroughCourseOfferings', 'Loop Through Course Offerings', 'GetCourseOfferings', 'AddOfferingId', 'AreThereOfferings')
    f.assign('AddOfferingId', 'Add Offering Id', [('varT_OfferingIds', 'Add', '=LoopThroughCourseOfferings.Id')], 'LoopThroughCourseOfferings')
    f.decide('AreThereOfferings', 'Does the School Have Courses?', [('HasOfferings', 'Yes', [('varT_OfferingIds', 'IsEmpty', False)], 'GetRegistrations', 'and')], 'School')
    f.lookup('GetRegistrations', 'Get Student Applications', 'IndividualApplication', [('CourseOffering__c', 'In', '=varT_OfferingIds')],
             ['Id', 'Name', 'ApplicationType', 'Status', 'AccountId'], 'LoopThroughRegistrations', sort='CreatedDate', desc=True)
    f.var('varT_StudentIds', 'String', 'The students with applications.', coll=True)
    f.loop('LoopThroughRegistrations', 'Loop Through Student Applications', 'GetRegistrations', 'AddStudentId', 'GetStudentAccounts')
    f.assign('AddStudentId', 'Add Student Id', [('varT_StudentIds', 'Add', '=LoopThroughRegistrations.AccountId')], 'LoopThroughRegistrations')
    f.lookup('GetStudentAccounts', 'Get Students', 'Account', [('Id', 'In', '=varT_StudentIds')], ['Id', 'Name'], 'ListStudents', sort='Name')
    f.var('varT_StudentsHtml', 'String', 'The student applications, as a list.')
    f.var('varT_StudentName', 'String', 'The student on the application being listed.')
    f.loop('ListStudents', 'Loop Through Student Applications to List', 'GetRegistrations', 'FindStudentName', 'School')
    f.loop('FindStudentName', 'Loop Through Students', 'GetStudentAccounts', 'IsItThisStudent', 'AddListStudentsLine')
    f.decide('IsItThisStudent', 'Is It This Application\'s Student?', [('ThisStudent', 'Yes', [('FindStudentName.Id', 'EqualTo', '=ListStudents.AccountId')], 'SetStudentName', 'and')],
             'FindStudentName')
    f.assign('SetStudentName', 'Set Student Name', [('varT_StudentName', 'Assign', '=FindStudentName.Name')], 'FindStudentName')
    f.formula('forT_ListStudentsLine', 'String', '"<li>" & {!varT_StudentName} & ": " & TEXT({!ListStudents.ApplicationType}) & " (" & {!ListStudents.Name} & "), " & TEXT({!ListStudents.Status}) & "</li>"',
              'One line of student applications.')
    f.assign('AddListStudentsLine', 'Add Student Application Line', [('varT_StudentsHtml', 'Add', '=forT_ListStudentsLine')], 'ListStudents')
    links = ''.join(f'<li><a target="_self" href="/LPI/s/{u}">{e(t)}</a></li>' for u, t in FORM_LINKS)
    f.screen('School', 'My School', [display('MS_Body',
             '<h2>{!GetSchool.Name}</h2><p><b>Licenses</b></p><ul>{!varT_LicensesHtml}</ul>'
             '<p><b>Student applications</b> (newest first)</p><ul>{!varT_StudentsHtml}</ul>'
             '<p><b>Last instructor roster:</b> {!GetSchool.LastInstructorRosterQuarter__c}</p>'
             f'<p><b>School forms</b></p><ul>{links}</ul>')], None, back=True, pause=False, next_label='Done')
    f.write(outdir, 'GetRunningUser')


def my_businesses(outdir):
    f = Flow('ScreenFlowAccountMyBusinesses', 'My Businesses',
             'Screen Flow: Account My Businesses. A portal page for owners and managers: the businesses the signed-in person is '
             'related to as Owner or Manager, with their licenses, open business applications and violations. Read only; runs in '
             'system context and shows only those businesses.')
    f.lookup('GetRunningUser', 'Get Running User', 'User', [('Id', 'EqualTo', '=$User.Id')], ['Id', 'ContactId'], 'GetRelationships', first=True)
    f.lookup('GetRelationships', 'Get Business Relationships', 'AccountContactRelation', [
        ('ContactId', 'EqualTo', '=GetRunningUser.ContactId'), ('IsActive', 'EqualTo', True)], ['Id', 'AccountId', 'Roles'], 'LoopThroughRelationships', sort='Id')
    f.var('varT_BusinessIds', 'String', 'The businesses the person owns or manages.', coll=True)
    f.loop('LoopThroughRelationships', 'Loop Through Business Relationships', 'GetRelationships', 'IsAnOwnerOrManager', 'AreThereBusinesses')
    f.formula('forB_OwnerOrManager', 'Boolean', 'INCLUDES({!LoopThroughRelationships.Roles}, "Owner") || INCLUDES({!LoopThroughRelationships.Roles}, "Manager")',
              'The person owns or manages the business.')
    f.decide('IsAnOwnerOrManager', 'Is the Person an Owner or Manager?', [('OwnerOrManager', 'Yes', [('forB_OwnerOrManager', 'EqualTo', True)], 'AddBusinessId', 'and')],
             'LoopThroughRelationships')
    f.assign('AddBusinessId', 'Add Business Id', [('varT_BusinessIds', 'Add', '=LoopThroughRelationships.AccountId')], 'LoopThroughRelationships')
    f.decide('AreThereBusinesses', 'Does the Person Own or Manage a Business?', [('HasBusinesses', 'Yes', [('varT_BusinessIds', 'IsEmpty', False)], 'GetLicenses', 'and')],
             'NoBusinesses')
    f.screen('NoBusinesses', 'My Businesses', [display('NB_Message', f'<p>Your portal account isn\'t linked to a business as its owner or manager. '
             f'If it should be, call the Board at {PHONE}.</p>')], None, back=False, pause=False)
    f.lookup('GetLicenses', 'Get Licenses', 'BusinessLicense', [('AccountId', 'In', '=varT_BusinessIds')], ['Id', 'Name', 'Identifier', 'Status', 'PeriodEnd', 'AccountId'],
             'ListLicenses', sort='Name')
    listing(f, 'ListLicenses', 'GetLicenses', '{!ListLicenses.Account.Name} & ": " & {!ListLicenses.Name} & ", license " & BLANKVALUE({!ListLicenses.Identifier}, "pending") '
            '& ", " & TEXT({!ListLicenses.Status}) & IF(ISBLANK({!ListLicenses.PeriodEnd}), "", ", expires " & ' + mdy('DATEVALUE({!ListLicenses.PeriodEnd})') + ')',
            'licenses', 'GetApplications', 'varT_LicensesHtml')
    f.lookup('GetApplications', 'Get Business Applications', 'BusinessLicenseApplication', [('AccountId', 'In', '=varT_BusinessIds'),
             ('Status', 'NotEqualTo', 'Approved'), ('Status', 'NotEqualTo', 'Canceled')], ['Id', 'Name', 'Status', 'AccountId', 'ApplicationType'], 'ListApplications', sort='Name')
    listing(f, 'ListApplications', 'GetApplications', '{!ListApplications.Account.Name} & ": " & {!ListApplications.Name} & " " & TEXT({!ListApplications.ApplicationType}) & ", " & TEXT({!ListApplications.Status})',
            'open applications', 'GetViolations', 'varT_ApplicationsHtml')
    f.lookup('GetViolations', 'Get Violations', 'RegulatoryCodeViolation', [('Establishment__c', 'In', '=varT_BusinessIds')], ['Id', 'Name', 'Status', 'Establishment__c'],
             'ListViolations', sort='Name')
    listing(f, 'ListViolations', 'GetViolations', '{!ListViolations.Establishment__r.Name} & ": " & {!ListViolations.Name} & ", " & TEXT({!ListViolations.Status})',
            'violations', 'Businesses', 'varT_ViolationsHtml')
    f.screen('Businesses', 'My Businesses', [display('MB_Body',
             '<p><b>Licenses</b></p><ul>{!varT_LicensesHtml}</ul><p><b>Open applications</b></p><ul>{!varT_ApplicationsHtml}</ul>'
             '<p><b>Violations</b></p><ul>{!varT_ViolationsHtml}</ul>'
             '<p>To open a new location, report new ownership or reopen a shop, use the <a target="_self" href="/LPI/s/shop-application">Shop Application</a>.</p>')], None, back=False, pause=False, next_label='Done')
    f.write(outdir, 'GetRunningUser')


EXPERIENCE = 'force-app/main/default/experiences/LSBC_LPI1'
APP_PAGE = '39740273-a4f0-4311-b732-31661924917d'


def page(dev, label, url, intro, flow):
    """A signed-in portal page holding one form: heading, intro line and the flow. Ids are derived from the page
    name, so rerunning keeps them stable."""
    import json
    import uuid
    u = lambda part: str(uuid.uuid5(uuid.NAMESPACE_URL, f'lsbc-portal/{dev}/{part}'))
    route = {'activeViewId': u('view'), 'appPageId': APP_PAGE, 'configurationTags': [], 'devName': dev, 'id': u('route'),
             'label': label, 'pageAccess': 'RequiresLogin', 'routeType': f'custom-{url}', 'type': 'route', 'urlPrefix': url}
    comp = lambda name, attrs, part, extra=None: dict({'componentAttributes': attrs, 'componentName': name, 'id': u(part),
                                                       'renderPriority': 'NEUTRAL', 'renditionMap': {}, 'type': 'component'}, **(extra or {}))
    view = {'appPageId': APP_PAGE, 'componentName': 'siteforce:sldsOneColLayout', 'dataProviders': [], 'id': u('view'), 'label': label,
            'regions': [
                {'components': [comp('forceCommunity:richTextInline', {'richTextValue':
                    f'<!-- Page heading and one-line introduction -->\n<h1 class="lsbc-page-title">{label}</h1>\n<p class="lsbc-page-intro">{intro}</p>'}, 'heading')],
                 'id': u('header'), 'regionName': 'header', 'type': 'region'},
                {'components': [comp('forceCommunity:flowCommunity', {'flowArguments': '', 'flowName': flow}, 'flow')],
                 'id': u('content'), 'regionName': 'content', 'type': 'region'},
                {'id': u('footer'), 'regionName': 'footer', 'type': 'region'},
                {'components': [{'componentAttributes': {'customHeadTags': '', 'description': '', 'title': label},
                                 'componentName': 'forceCommunity:seoAssistant', 'id': u('seo'), 'renditionMap': {}, 'type': 'component'}],
                 'id': u('hidden'), 'regionName': 'sfdcHiddenRegion', 'type': 'region'}],
            'themeLayoutType': 'Inner', 'type': 'view', 'viewType': f'custom-{url}'}
    for kind, data in (('routes', route), ('views', view)):
        open(f'{EXPERIENCE}/{kind}/{dev}.json', 'w').write(json.dumps(data, indent=2))
    print('wrote page', url)


if __name__ == '__main__':
    student_enrollment(sys.argv[1])
    contractual_fees(sys.argv[1])
    transfer_hours(sys.argv[1])
    relinquish_hours(sys.argv[1])
    termination(sys.argv[1])
    activity_hours(sys.argv[1])
    instructor_roster(sys.argv[1])
    examination(sys.argv[1])
    my_school(sys.argv[1])
    my_businesses(sys.argv[1])
    page('studentEnrollment', 'Student Enrollment', 'student-enrollment',
         'Enroll a new student, a transfer or a student seeking additional training at your school.',
         'ScreenFlowIndividualApplicationStudentEnrollment')
    page('contractualFees', 'Certification of Contractual Fees', 'contractual-fees',
         'Certify whether a student has paid all contractual fees to your school.', 'ScreenFlowIndividualApplicationContractualFees')
    page('transferHours', 'Transfer Hours', 'transfer-hours',
         'Report hours a student brings from a school in another state.', 'ScreenFlowTrainingCourseParticipantTransferHours')
    page('relinquishHours', 'Relinquish Hours', 'relinquish-hours',
         'File a student\'s notarized letter giving up hours earned at your school.', 'ScreenFlowTrainingCourseParticipantRelinquishHours')
    page('noticeOfTermination', 'Notice of Termination', 'notice-of-termination',
         'Tell the Board a student or instructor in training has stopped attending.', 'ScreenFlowTrainingCourseParticipantTermination')
    page('activityHours', 'Field Trips, Workshops, Shows and Community Service', 'activity-hours',
         'Report hours a student earned on a field trip, workshop, show or community service.', 'ScreenFlowTrainingCourseParticipantActivityHours')
    page('instructorRoster', 'Instructor Quarterly Roster', 'instructor-roster',
         'File your school\'s instructor roster for the quarter.', 'ScreenFlowAccountInstructorRoster')
    page('examApplication', 'Exam Application', 'exam-application',
         'Apply for a student\'s national, practical or state exam, a retake or a no-show reapplication.', 'ScreenFlowIndividualApplicationExamination')
    page('mySchool', 'My School', 'my-school', 'Your school\'s licenses, students and school forms.', 'ScreenFlowAccountMySchool')
    page('myBusinesses', 'My Businesses', 'my-businesses', 'The licenses, applications and violations of the businesses you own or manage.',
         'ScreenFlowAccountMyBusinesses')
