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
    def lookup(self, name, label, obj, filters, fields, nxt, first=False, sort=None, logic='and'):
        x = f'<recordLookups><name>{name}</name><label>{e(label)}</label>{LOC}<assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>{conn(nxt)}<filterLogic>{logic}</filterLogic>'
        for f, op, v in filters:
            x += f'<filters><field>{f}</field><operator>{op}</operator><value>{val(v)}</value></filters>'
        x += f'<getFirstRecordOnly>{"true" if first else "false"}</getFirstRecordOnly><object>{obj}</object>'
        x += ''.join(f'<queriedFields>{f}</queriedFields>' for f in fields)
        if sort:
            x += f'<sortField>{sort}</sortField><sortOrder>Asc</sortOrder>'
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

    def var(self, name, dtype, desc, coll=False, inp=False, obj=None, default=None):
        x = f'<variables><name>{name}</name><description>{e(desc)}</description><dataType>{dtype}</dataType><isCollection>{"true" if coll else "false"}</isCollection><isInput>{"true" if inp else "false"}</isInput><isOutput>false</isOutput>'
        if obj:
            x += f'<objectType>{obj}</objectType>'
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
        x = f'<screens><name>{name}</name><label>{e(label)}</label>{LOC}<allowBack>{"true" if back else "false"}</allowBack><allowFinish>true</allowFinish><allowPause>{"true" if pause else "false"}</allowPause>{conn(nxt)}'
        x += ''.join(fields)
        if next_label:
            x += f'<nextOrFinishButtonLabel>{e(next_label)}</nextOrFinishButtonLabel>'
        if pause:
            x += f'<pausedText>{e(PAUSED_TEXT)}</pausedText>'
        self.el['screens'].append(x + '<showFooter>true</showFooter><showHeader>false</showHeader></screens>')

    def write(self, outdir, first):
        j = lambda t: ''.join(self.el[t])
        meta = ''.join(f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
                       for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')])
        x = ('<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>66.0</apiVersion>'
             + j('actionCalls') + j('assignments') + j('choices') + j('decisions') + f'<description>{e(self.desc)}</description>'
             + j('dynamicChoiceSets') + '<environments>Default</environments>' + j('formulas')
             + f'<interviewLabel>{e(self.label)} {{!$Flow.CurrentDateTime}}</interviewLabel><label>{e(self.label)}</label>' + j('loops')
             + meta + f'<processType>{self.process}</processType>' + j('recordCreates') + j('recordDeletes') + j('recordLookups')
             + j('recordUpdates') + '<runInMode>SystemModeWithoutSharing</runInMode>' + j('screens')
             + f'<start>{LOC}{conn(first)}</start><status>Active</status>' + j('subflows') + j('variables') + '</Flow>\n')
        open(os.path.join(outdir, self.api + '.flow-meta.xml'), 'w').write(x)
        print('wrote', self.api)


PAUSED_TEXT = ('Your application is saved. Come back to it within 30 days from My Applications; after 30 days a saved '
               'application is deleted and you would start again.')


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
             f'<p>{form_name} is filed by a school\'s School Administrator. Your portal account isn\'t linked to a school as its '
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
             ['Id', 'Name', 'OwnerId', 'CertificationNumber__c', 'ShippingCity', 'Phone'], 'IsTheSchoolApproved', first=True)
    f.decide('IsTheSchoolApproved', 'Is the School Approved?', [
        ('Approved', 'Yes', [('GetSchool.Owner.IsPortalEnabled', 'EqualTo', False)], 'GetCourseOfferings', 'and')],
        'SchoolNotApproved')
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
                '<p><b>12. School:</b> {!GetSchool.Name}<br/><b>13. School license number:</b> {!GetSchool.CertificationNumber__c}'
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
    page('studentEnrollment', 'Student Enrollment', 'student-enrollment',
         'Enroll a new student, a transfer or a student seeking additional training at your school.',
         'ScreenFlowIndividualApplicationStudentEnrollment')
