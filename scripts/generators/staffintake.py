"""Patches the portal forms and subflows for staff intake. Usage: python3 -I staffintake.py <flows dir>"""
import re
import sys

D = sys.argv[1]
ORDER = ['actionCalls', 'apexPluginCalls', 'assignments', 'choices', 'collectionProcessors', 'constants', 'customErrors', 'decisions',
         'description', 'dynamicChoiceSets', 'environments', 'formulas', 'interviewLabel', 'label', 'loops', 'processMetadataValues',
         'processType', 'recordCreates', 'recordDeletes', 'recordLookups', 'recordRollbacks', 'recordUpdates', 'runInMode', 'screens',
         'sourceTemplate', 'stages', 'start', 'status', 'steps', 'subflows', 'textTemplates', 'transforms', 'triggerOrder', 'variables', 'waits']


def add(s, tag, xml):
    """Inserts an element where its type belongs: before the first element of the same or a later type."""
    for t in ORDER[ORDER.index(tag):]:
        i = s.find(f'<{t}>')
        if i >= 0:
            return s[:i] + xml + s[i:]
    i = s.rindex('</Flow>')
    return s[:i] + xml + s[i:]


def rep(s, a, b, count=1):
    n = s.count(a)
    assert n == count, (a[:80], n)
    return s.replace(a, b)


def var(name, dtype, desc, inp=False, default=None):
    v = f'<value><booleanValue>{default}</booleanValue></value>' if default is not None else ''
    return (f'<variables><name>{name}</name><description>{desc}</description><dataType>{dtype}</dataType><isCollection>false</isCollection>'
            f'<isInput>{"true" if inp else "false"}</isInput><isOutput>false</isOutput>{v}</variables>')


STAFF_FLAG_INPUT = '<inputAssignments><name>varB_IsStaffEntry</name><value><elementReference>forB_IsStaffEntry</elementReference></value></inputAssignments>'

FORMS = ['BusinessLicenseApplicationFacility', 'BusinessLicenseApplicationSchool', 'BusinessLicenseApplicationShop',
         'IndividualApplicationAffidavit', 'IndividualApplicationReciprocity', 'IndividualApplicationRenewal',
         'IndividualApplicationRetake', 'IndividualApplicationTemporaryPermit', 'IndividualApplicationThreadingPermit']

for form in FORMS:
    p = f'{D}/ScreenFlow{form}.flow-meta.xml'
    s = open(p).read()
    if 'forT_ApplicantId' in s:
        print('already patched', form)
        continue
    n_ref = s.count('<elementReference>GetRunningUser.AccountId</elementReference>')
    n_merge = s.count('{!GetRunningUser.AccountId}')
    s = s.replace('<elementReference>GetRunningUser.AccountId</elementReference>', '<elementReference>forT_ApplicantId</elementReference>')
    s = s.replace('{!GetRunningUser.AccountId}', '{!forT_ApplicantId}')
    s = add(s, 'formulas',
            '<formulas><name>forT_ApplicantId</name><description>The applicant: the person staff chose when they start the form from New Application, otherwise the signed-in portal user.</description>'
            '<dataType>String</dataType><expression>IF(ISBLANK({!recordId}), {!GetRunningUser.AccountId}, {!recordId})</expression></formulas>'
            '<formulas><name>forB_IsStaffEntry</name><description>True when staff are entering the form for an applicant (from New Application).</description>'
            '<dataType>Boolean</dataType><expression>NOT(ISBLANK({!recordId}))</expression></formulas>')
    s = add(s, 'variables', var('recordId', 'String', 'The applicant&apos;s Person Account when staff start this form from New Application. Blank on the portal, where the applicant is the signed-in user.', inp=True))
    for sub in ['SubflowApplicationPayment', 'SubflowDocumentChecklistUpload']:
        s = s.replace(f'<flowName>{sub}</flowName>', f'<flowName>{sub}</flowName>{STAFF_FLAG_INPUT}')
    desc = re.search(r'<description>([^<]*)</description>(?=<dynamicChoiceSets>|<environments>|<formulas>)', s)
    s = s.replace(desc.group(0), '<description>' + desc.group(1) + ' Staff can also enter it for an applicant from New Application on the Person Account (input recordId); the pay step then tells them to record the payment.</description>', 1)
    open(p, 'w').write(s)
    print('patched', form, 'refs', n_ref, 'merges', n_merge, 'payment', s.count('<flowName>SubflowApplicationPayment</flowName>'), 'upload', s.count('<flowName>SubflowDocumentChecklistUpload</flowName>'))

# Subflow: Application Payment
p = f'{D}/SubflowApplicationPayment.flow-meta.xml'
s = open(p).read()
if 'varB_IsStaffEntry' not in s:
    s = rep(s, '<rules><name>Due</name><conditionLogic>and</conditionLogic><conditions><leftValueReference>varC_Total</leftValueReference><operator>GreaterThan</operator><rightValue><numberValue>0</numberValue></rightValue></conditions><connector><targetReference>Pay</targetReference></connector>',
            '<rules><name>Due</name><conditionLogic>and</conditionLogic><conditions><leftValueReference>varC_Total</leftValueReference><operator>GreaterThan</operator><rightValue><numberValue>0</numberValue></rightValue></conditions><connector><targetReference>IsThisAStaffEntry</targetReference></connector>')
    s = add(s, 'decisions', '<decisions><name>IsThisAStaffEntry</name><label>Is This a Staff Entry?</label><locationX>0</locationX><locationY>0</locationY>'
            '<defaultConnector><targetReference>Pay</targetReference></defaultConnector><defaultConnectorLabel>No</defaultConnectorLabel>'
            '<rules><name>StaffEntry</name><conditionLogic>and</conditionLogic><conditions><leftValueReference>varB_IsStaffEntry</leftValueReference><operator>EqualTo</operator>'
            '<rightValue><booleanValue>true</booleanValue></rightValue></conditions><connector><targetReference>StaffPay</targetReference></connector><label>Yes</label></rules></decisions>')
    s = add(s, 'screens', '<screens><name>StaffPay</name><label>Staff Pay</label><locationX>0</locationX><locationY>0</locationY><allowBack>false</allowBack><allowFinish>true</allowFinish><allowPause>false</allowPause>'
            '<fields><name>SP_Fees</name><fieldText>&lt;h2&gt;Fees due&lt;/h2&gt;{!varT_Lines}&lt;p&gt;&lt;b&gt;Total: {!forT_Total}&lt;/b&gt;&lt;/p&gt;</fieldText><fieldType>DisplayText</fieldType></fields>'
            '<fields><name>SP_HowToPay</name><fieldText>&lt;p&gt;The application is submitted. Record the payment with &lt;b&gt;Record Payment&lt;/b&gt; on the applicant&apos;s account once it is received; the fees stay due until then.&lt;/p&gt;</fieldText><fieldType>DisplayText</fieldType></fields>'
            '<nextOrFinishButtonLabel>Done</nextOrFinishButtonLabel><showFooter>true</showFooter><showHeader>false</showHeader></screens>')
    s = add(s, 'variables', var('varB_IsStaffEntry', 'Boolean', 'True when staff entered the application for the applicant: the pay step tells them to record the payment instead of linking to PayStar.', inp=True, default='false'))
    s = rep(s, 'When nothing is due, the applications&apos; empty receipt items are removed.',
            'When nothing is due, the applications&apos; empty receipt items are removed. When staff entered the application, it shows the fees and tells them to record the payment with Record Payment instead.')
    open(p, 'w').write(s)
    print('patched SubflowApplicationPayment')

# Subflow: Document Checklist Upload
p = f'{D}/SubflowDocumentChecklistUpload.flow-meta.xml'
s = open(p).read()
if 'varB_IsStaffEntry' not in s:
    s = rep(s, '<inputParameters><name>applicationId</name><value><elementReference>varT_ApplicationId</elementReference></value></inputParameters>',
            '<inputParameters><name>applicationId</name><value><elementReference>varT_ApplicationId</elementReference></value></inputParameters>'
            '<inputParameters><name>allowSentToBoard</name><value><elementReference>varB_IsStaffEntry</elementReference></value></inputParameters>')
    s = add(s, 'variables', var('varB_IsStaffEntry', 'Boolean', 'True when staff use the screen: documents sent to the Board can then be uploaded as they arrive.', inp=True, default='false'))
    s = rep(s, 'and staff upload them on arrival.', 'and staff upload them on arrival (staff screens set varB_IsStaffEntry, which allows those uploads).')
    open(p, 'w').write(s)
    print('patched SubflowDocumentChecklistUpload')

# Screen Flow: Document Checklist Item Upload
p = f'{D}/ScreenFlowDocumentChecklistItemUpload.flow-meta.xml'
s = open(p).read()
if '<name>recordId</name>' not in s:
    s = rep(s, '<start><locationX>0</locationX><locationY>0</locationY><connector><targetReference>GetRunningUser</targetReference></connector></start>',
            '<start><locationX>0</locationX><locationY>0</locationY><connector><targetReference>WasAnApplicationGiven</targetReference></connector></start>')
    s = add(s, 'assignments', '<assignments><name>SetGivenApplication</name><label>Set Chosen Application to the Given One</label><locationX>0</locationX><locationY>0</locationY>'
            '<assignmentItems><assignToReference>varT_ChosenId</assignToReference><operator>Assign</operator><value><elementReference>recordId</elementReference></value></assignmentItems>'
            '<connector><targetReference>UploadDocuments</targetReference></connector></assignments>')
    s = add(s, 'decisions', '<decisions><name>WasAnApplicationGiven</name><label>Was an Application Given?</label><locationX>0</locationX><locationY>0</locationY>'
            '<defaultConnector><targetReference>GetRunningUser</targetReference></defaultConnector><defaultConnectorLabel>No</defaultConnectorLabel>'
            '<rules><name>Given</name><conditionLogic>and</conditionLogic><conditions><leftValueReference>recordId</leftValueReference><operator>IsNull</operator>'
            '<rightValue><booleanValue>false</booleanValue></rightValue></conditions><connector><targetReference>SetGivenApplication</targetReference></connector><label>Yes</label></rules></decisions>')
    s = rep(s, '<flowName>SubflowDocumentChecklistUpload</flowName>',
            '<flowName>SubflowDocumentChecklistUpload</flowName><inputAssignments><name>varB_IsStaffEntry</name><value><elementReference>forB_IsStaffEntry</elementReference></value></inputAssignments>')
    s = add(s, 'formulas', '<formulas><name>forB_IsStaffEntry</name><description>True when staff opened the flow from Upload Documents on an application.</description>'
            '<dataType>Boolean</dataType><expression>NOT(ISBLANK({!recordId}))</expression></formulas>')
    s = add(s, 'variables', var('recordId', 'String', 'The application, when staff open this from Upload Documents on the application record. Blank on the portal, where the applicant chooses one of their applications.', inp=True))
    s = rep(s, '<description>Portal flow (Screen Flow: Document Checklist Item Upload). Sits on My Applications on the portal.',
            '<description>Portal flow (Screen Flow: Document Checklist Item Upload). Sits on My Applications on the portal, and staff run it from Upload Documents on an application, which goes straight to that application and also allows documents sent to the Board.')
    open(p, 'w').write(s)
    print('patched ScreenFlowDocumentChecklistItemUpload')
