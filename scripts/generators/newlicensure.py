"""Generates ScreenFlowIndividualApplicationNewLicensure.flow-meta.xml. Usage: python3 -I newlicensure.py <flows dir>

Completion and Initial License: the school's completion form (the 1,500 hour completion form in School Forms.pdf),
entered by staff from New Application on the student's person account.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flowlib as F

els = F.els
for k in ['actionCalls', 'recordDeletes', 'subflows']:
    els[k] = []
e, conn, loc, val = F.e, F.conn, F.loc, F.val
REF, STR, NUM, BOOL, cond = F.REF, F.STR, F.NUM, F.BOOL, F.cond

FORM_NAME = 'Completion and Initial License'


def screen(name, label, fields, nxt, back=False, next_label=None):
    """A form screen. Back is allowed after the first screen; Save for later is not offered (staff entry)."""
    x = (f'<screens><name>{name}</name><label>{e(label)}</label>{loc()}<allowBack>{"true" if back else "false"}</allowBack>'
         f'<allowFinish>true</allowFinish><allowPause>false</allowPause>{conn(nxt)}')
    x += ''.join(fields)
    if next_label:
        x += f'<nextOrFinishButtonLabel>{e(next_label)}</nextOrFinishButtonLabel>'
    els['screens'].append(x + '<showFooter>true</showFooter><showHeader>false</showHeader></screens>')


def subflow(name, label, flow, inputs, nxt, outputs=()):
    x = f'<subflows><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}<flowName>{flow}</flowName>'
    for n, v in inputs:
        x += f'<inputAssignments><name>{n}</name><value>{val(v)}</value></inputAssignments>'
    for n, ref in outputs:
        x += f'<outputAssignments><assignToReference>{ref}</assignToReference><name>{n}</name></outputAssignments>'
    els['subflows'].append(x + '</subflows>')


def matrix(name, label, fee_name, nxt):
    els['actionCalls'].append(
        f'<actionCalls><name>{name}</name><label>{e(label)}</label>{loc()}<actionName>FeeSchedule</actionName><actionType>runDecisionMatrix</actionType>'
        f'{conn(nxt)}<flowTransactionModel>CurrentTransaction</flowTransactionModel>'
        f'<inputParameters><name>FeeName</name><value>{val(fee_name)}</value></inputParameters><storeOutputAutomatically>true</storeOutputAutomatically></actionCalls>')


def vis_true(ref, value=True):
    return f'<visibilityRule><conditionLogic>and</conditionLogic>{cond(ref, "EqualTo", BOOL(value))}</visibilityRule>'


# Inputs and working variables
F.var('recordId', 'String', 'The student\'s Person Account. Staff start this form from New Application on the person, which passes the record under this name.', inp=True)
F.var('varN_HoursOnFile', 'Number', 'Hours on the student\'s Training tab, from every school, leaving out continuing education.', default=NUM(0), scale=2)
F.var('varN_SchoolHours', 'Number', 'Hours on the Training tab for the chosen school\'s program for this license.', default=NUM(0), scale=2)
F.var('varB_IsCertified', 'Boolean', 'True once the school\'s certification was ticked on the certification step.', default=BOOL(False))
F.var('varT_CertifiedName', 'String', 'The school representative\'s name as typed on the certification step.')
F.var('varDT_CertifiedDateTime', 'DateTime', 'When the certification step was completed.')
F.var('varT_FeeIds', 'String', 'The fee raised, for the payment step.', coll=True)
F.var('varT_ApplicationIds', 'String', 'The application created, for the payment step.', coll=True)

# Formulas
F.formula('forB_IsStaffEntry', 'Boolean', 'NOT(ISBLANK({!recordId}))',
          'True when staff are entering the form for a student (from New Application). Every run is a staff entry for now; a school portal audience can be added later.')
F.formula('forT_SsnMasked', 'String', 'IF(LEN({!GetApplicant.SocialSecurityNumber__pc}) >= 4, "***-**-" & RIGHT({!GetApplicant.SocialSecurityNumber__pc}, 4), "Not on file")',
          'The Social Security number with only the last four digits shown.')
F.formula('forT_SavedApplicationUrl', 'String', '"/LPI/s/continue-application?guid=" & {!$Flow.InterviewGuid}',
          'Records this form\'s interview GUID on the draft, as every form does, so a paused form can be found again.')
F.formula('forN_EntryHours', 'Number', 'BLANKVALUE({!LoopThroughHoursEntries.TotalHours}, 0)', 'The hours on one Training tab entry, zero when blank.', scale=2)
F.formula('forB_EntryIsAtSchool', 'Boolean', 'NOT(ISBLANK({!GetSchoolCourseOffering.Id})) && {!LoopThroughHoursEntries.CourseOfferingId} = {!GetSchoolCourseOffering.Id}',
          'True when the hours entry is for the chosen school\'s program for this license.')
F.formula('forN_RequiredHours', 'Number', '{!GetLicenseType.CompletionThresholdHours__c}', 'The license type\'s completion hours, as shown on the hours check.', scale=2)
F.formula('forT_HoursWarnings', 'String',
          'IF(NOT(ISBLANK({!GetLicenseType.CompletionThresholdHours__c})) && {!CF_CompletedHours} < {!GetLicenseType.CompletionThresholdHours__c}, '
          '"<li>The school certified fewer hours than the license requires.</li>", "")'
          ' & IF(NOT(ISBLANK({!GetLicenseType.CompletionThresholdHours__c})) && {!varN_HoursOnFile} < {!GetLicenseType.CompletionThresholdHours__c}, '
          '"<li>The hours on file are below what the license requires. Stop code 04 Student Hours Incomplete opens on the person until the missing hours are entered on the Training tab.</li>", "")'
          ' & IF({!CF_CompletedHours} <> {!varN_HoursOnFile}, "<li>The hours certified and the hours on file differ. Check them against the cumulative hours report.</li>", "")',
          'Points staff to any gap between the hours certified, the hours on file and the hours the license requires.')
F.formula('forT_HoursCheck', 'String',
          'IF(ISBLANK({!forT_HoursWarnings}), "<p>The hours certified match the hours on file.</p>", "<p><b>Check before you continue:</b></p><ul>" & {!forT_HoursWarnings} & "</ul>")',
          'The result of the hours check.')
F.formula('forT_InitialFeeName', 'String', '{!GetLicenseType.Name} & " Initial"',
          'Which Fee Schedule row prices the fee: the license type\'s name followed by Initial, such as Cosmetologist Initial.')
F.formula('forN_InitialAmount', 'Currency', 'IF(ISBLANK({!LookUpInitialFee.Amount}), {!LookUpGenericInitialFee.Amount}, {!LookUpInitialFee.Amount})',
          'The fee amount: the license type\'s row, or the generic Individual License row when the type has none.', scale=2)
F.formula('forT_InitialFeeCode', 'String', 'IF(ISBLANK({!LookUpInitialFee.Amount}), {!LookUpGenericInitialFee.FeeCode}, {!LookUpInitialFee.FeeCode})',
          'The fee code from whichever Fee Schedule row priced the fee.')
F.formula('forT_FeeItemName', 'String', 'LEFT({!GetLicenseType.Name} & " Initial License", 80)', 'The fee item\'s name, such as Cosmetologist Initial License.')
F.formula('forT_ThisYear', 'String', 'TEXT(YEAR({!$Flow.CurrentDate}))', 'The license year the fee is for.')

# License types a school trains for: the ones with a school program
els['dynamicChoiceSets'].append(
    '<dynamicChoiceSets><name>recChoice_SchoolLicenseTypes</name><description>License types a school trains students for: those with a school program.</description>'
    '<dataType>String</dataType><displayField>Name</displayField><filterLogic>and</filterLogic>'
    '<filters><field>Program__c</field><operator>IsNull</operator><value><booleanValue>false</booleanValue></value></filters>'
    '<object>RegulatoryAuthorizationType</object><sortField>Name</sortField><sortOrder>Asc</sortOrder><valueField>Id</valueField></dynamicChoiceSets>')

# Applicant
F.lookup('GetApplicant', 'Get Applicant', 'Account', [('Id', 'EqualTo', REF('recordId'))],
         ['Id', 'Name', 'FirstName', 'MiddleName', 'LastName', 'MaidenName__pc', 'PersonContactId', 'IsPersonAccount', 'SocialSecurityNumber__pc'],
         'IsTheApplicantAPerson', first=True, sort=None)
F.decision('IsTheApplicantAPerson', 'Is the Applicant a Person?', [
    ('Person', 'Yes', [cond('GetApplicant.IsPersonAccount', 'EqualTo', BOOL(True))], 'CompletionForm', 'and')], 'NotAvailable')
screen('NotAvailable', 'Not Available', [
    F.display('NA_Message', '<p>The completion form is entered on the student\'s person account. Open the student\'s account and use New Application there.</p>')],
    None, next_label='Done')

# The form, section by section as printed
cf_lookup = ('<fields><name>CF_School</name><extensionName>flowruntime:lookup</extensionName><fieldType>ComponentInstance</fieldType>'
             '<inputParameters><name>objectApiName</name><value><stringValue>CourseOffering</stringValue></value></inputParameters>'
             '<inputParameters><name>fieldApiName</name><value><stringValue>School__c</stringValue></value></inputParameters>'
             '<inputParameters><name>label</name><value><stringValue>Name of School</stringValue></value></inputParameters>'
             '<inputParameters><name>required</name><value><booleanValue>true</booleanValue></value></inputParameters>'
             '<inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn><isRequired>true</isRequired><storeOutputAutomatically>true</storeOutputAutomatically></fields>')
cf_type = ('<fields><name>CF_LicenseType</name><choiceReferences>recChoice_SchoolLicenseTypes</choiceReferences><dataType>String</dataType>'
           '<fieldText>License Sought</fieldText><fieldType>DropdownBox</fieldType>'
           '<helpText>The license the student trained for. Cosmetology needs 1,500 hours; other licenses have their own completion hours.</helpText>'
           '<isRequired>true</isRequired></fields>')
screen('CompletionForm', 'Completion Form', [
    F.display('CF_Heading', '<p><b>COMPLETION FORM</b></p><p>Enter the school\'s completion form for <b>{!GetApplicant.Name}</b>, copying the answers from the paper form. '
              'The paper form for cosmetology is the 1,500 hour completion form; other licenses use the same form with their own completion hours.</p>'),
    F.display('CF_Applicant', '<p><b>Applicant\'s Name</b><br/>First Name: {!GetApplicant.FirstName}<br/>Middle Name: {!GetApplicant.MiddleName}<br/>'
              'Maiden Name: {!GetApplicant.MaidenName__pc}<br/>Last Name: {!GetApplicant.LastName}</p>'
              '<p><b>Social Security Number:</b> {!forT_SsnMasked}</p>'
              '<p>If the name or Social Security number on the form is different, close this window and correct the person\'s record first.</p>'),
    cf_type,
    cf_lookup,
    F.inp('CF_DateEnrolled', 'Date', 'Date Enrolled', required=True),
    F.inp('CF_DateCompleted', 'Date', 'Date Completed', required=True,
          rule=('Date Completed must be on or after Date Enrolled, and not in the future.', '{!CF_DateCompleted} >= {!CF_DateEnrolled} && {!CF_DateCompleted} <= {!$Flow.CurrentDate}')),
    F.inp('CF_CompletedHours', 'Number', 'Total # of Completed Hours', required=True, scale=2,
          rule=('Enter the hours the school certified.', '{!CF_CompletedHours} > 0')),
], 'GetLicenseType', next_label='Next')

F.lookup('GetLicenseType', 'Get License Type', 'RegulatoryAuthorizationType', [('Id', 'EqualTo', REF('CF_LicenseType'))],
         ['Id', 'Name', 'Program__c', 'CompletionThresholdHours__c'], 'GetSchool', first=True, sort=None)
F.lookup('GetSchool', 'Get School', 'Account', [('Id', 'EqualTo', REF('CF_School.recordId'))], ['Id', 'Name'], 'GetSchoolCourseOffering', first=True, sort=None)
F.lookup('GetSchoolCourseOffering', 'Get School Course Offering', 'CourseOffering',
         [('School__c', 'EqualTo', REF('GetSchool.Id')), ('CourseNameId', 'EqualTo', REF('GetLicenseType.Program__c'))],
         ['Id', 'Name'], 'SetHoursToZero', first=True)
F.assignment('SetHoursToZero', 'Set Hours Totals to Zero', [('varN_HoursOnFile', 'Assign', NUM(0)), ('varN_SchoolHours', 'Assign', NUM(0))], 'GetHoursEntries')
F.lookup('GetHoursEntries', 'Get Hours Entries', 'TrainingCourseParticipant',
         [('ContactId', 'EqualTo', REF('GetApplicant.PersonContactId')), ('EntryType__c', 'NotEqualTo', STR('Continuing Education')), ('EntryType__c', 'NotEqualTo', STR('Termination'))],
         ['Id', 'TotalHours', 'CourseOfferingId'], 'LoopThroughHoursEntries')
F.loop('LoopThroughHoursEntries', 'Loop Through Hours Entries', 'GetHoursEntries', 'AddEntryHours', 'HoursCheck')
F.assignment('AddEntryHours', 'Add Entry Hours to Hours on File', [('varN_HoursOnFile', 'Add', REF('forN_EntryHours'))], 'IsTheEntryForThisSchool')
F.decision('IsTheEntryForThisSchool', 'Is the Entry for This School\'s Program?', [
    ('AtSchool', 'Yes', [cond('forB_EntryIsAtSchool', 'EqualTo', BOOL(True))], 'AddSchoolHours', 'and')], 'LoopThroughHoursEntries')
F.assignment('AddSchoolHours', 'Add Entry Hours to School Hours', [('varN_SchoolHours', 'Add', REF('forN_EntryHours'))], 'LoopThroughHoursEntries')

screen('HoursCheck', 'Hours Check', [
    F.display('HC_License', '<p><b>License sought:</b> {!GetLicenseType.Name}</p>'),
    F.display('HC_RequiredHours', '<p><b>Hours the license requires:</b> {!forN_RequiredHours}</p>')
    .replace('</fields>', f'<visibilityRule><conditionLogic>and</conditionLogic>{cond("GetLicenseType.CompletionThresholdHours__c", "IsNull", BOOL(False))}</visibilityRule></fields>'),
    F.display('HC_RequiredHoursNotSet', '<p><b>Hours the license requires:</b> not set for this license type yet</p>')
    .replace('</fields>', f'<visibilityRule><conditionLogic>and</conditionLogic>{cond("GetLicenseType.CompletionThresholdHours__c", "IsNull", BOOL(True))}</visibilityRule></fields>'),
    F.display('HC_Hours', '<p><b>Hours the school certified:</b> {!CF_CompletedHours}<br/><b>Hours on file, all schools:</b> {!varN_HoursOnFile}</p>'),
    F.display('HC_SchoolHours', '<p><b>Hours on file at {!GetSchool.Name}:</b> {!varN_SchoolHours}</p>')
    .replace('</fields>', f'<visibilityRule><conditionLogic>and</conditionLogic>{cond("GetSchoolCourseOffering.Id", "IsNull", BOOL(False))}</visibilityRule></fields>'),
    F.display('HC_NoSchoolProgram', '<p><b>Hours on file at {!GetSchool.Name}:</b> the school has no {!GetLicenseType.Name} program on file, so the application won\'t be linked to a course offering.</p>')
    .replace('</fields>', f'<visibilityRule><conditionLogic>and</conditionLogic>{cond("GetSchoolCourseOffering.Id", "IsNull", BOOL(True))}</visibilityRule></fields>'),
    F.display('HC_Note', '<p>Hours on file are the entries on the person\'s Training tab, without continuing education.</p>'),
    F.display('HC_Result', '{!forT_HoursCheck}'),
], 'CreateDraft', back=True, next_label='Next')

# Draft, documents and certification, as on every form
F.create_one('CreateDraft', 'Create Draft', 'PreliminaryApplicationRef', [
    ('ApplicationName', STR(FORM_NAME)), ('ApplicationType', STR('IndividualApplication')), ('OwnerId', REF('$User.Id')),
    ('IsSubmitted', BOOL(False)), ('SavedApplicationUrl', REF('forT_SavedApplicationUrl'))], 'GenerateDraftChecklist', 'CouldNotSave')
checklist_inputs = lambda app: [
    ('varT_ApplicationId', REF(app)), ('varT_AccountId', REF('GetApplicant.Id')), ('varT_RecordType', STR('IndividualApplication.NewLicensure')),
    ('varT_LicenseTypeName', REF('GetLicenseType.Name')), ('varT_ApplicationPath', STR('Regular')), ('varT_ApplicationType', STR('New'))]
# The payment receipt item is created on staff entries too, as on the Temporary Permit and Reciprocity forms: the payment step removes it
# for staff (Subflow: Application Payment faults when it has no receipt item to remove, so varB_LeaveOutReceipt is not used here).
subflow('GenerateDraftChecklist', 'Generate Draft Checklist', 'SubflowDocumentChecklistGenerate', checklist_inputs('CreateDraft'), 'UploadDocuments')
subflow('UploadDocuments', 'Upload Documents', 'SubflowDocumentChecklistUpload',
        [('varB_IsStaffEntry', REF('forB_IsStaffEntry')), ('varT_ApplicationId', REF('CreateDraft'))], 'Certification')
ATTESTATION = ('The school certifies the following: the student has completed the required hours; the student is contractually cleared; '
               'the initial license fee is attached; the student\'s cumulative hour report reflecting the required hours is attached. '
               'I understand that by submitting this form the named student\'s license will be released upon passage of all examinations and '
               'submission of required fees. (Staff: tick the box and type the school representative\'s name as signed on the form.)')
subflow('Certification', 'Certification', 'SubflowApplicationCertification', [('varT_AttestationText', STR(ATTESTATION))], 'GetNewLicensureRecordType',
        outputs=[('varB_IsCertified', 'varB_IsCertified'), ('varT_CertifiedName', 'varT_CertifiedName'), ('varDT_CertifiedDateTime', 'varDT_CertifiedDateTime')])

# On certify: the application and its fee
F.lookup('GetNewLicensureRecordType', 'Get New Licensure Record Type', 'RecordType',
         [('SobjectType', 'EqualTo', STR('IndividualApplication')), ('DeveloperName', 'EqualTo', STR('NewLicensure'))], ['Id'], 'CreateApplication', first=True, sort=None)
F.create_one('CreateApplication', 'Create Application', 'IndividualApplication', [
    ('RecordTypeId', REF('GetNewLicensureRecordType.Id')), ('AccountId', REF('GetApplicant.Id')), ('LicenseTypeId', REF('GetLicenseType.Id')),
    ('Category', STR('License')), ('ApplicationType', STR('New')), ('ApplicationPath__c', STR('Regular')), ('Status', STR('Submitted')),
    ('AppliedDate', REF('$Flow.CurrentDateTime')), ('CourseOffering__c', REF('GetSchoolCourseOffering.Id')),
    ('TotalCompletedHours__c', REF('CF_CompletedHours')), ('EnrolledDate__c', REF('CF_DateEnrolled')), ('CompletedDate__c', REF('CF_DateCompleted')),
    ('IsCertified__c', REF('varB_IsCertified')), ('CertifiedName__c', REF('varT_CertifiedName')), ('CertifiedDateTime__c', REF('varDT_CertifiedDateTime')),
], 'LookUpInitialFee', 'CouldNotSave')
matrix('LookUpInitialFee', 'Look Up Initial License Fee', REF('forT_InitialFeeName'), 'IsThereAnInitialFeeForTheLicenseType')
F.decision('IsThereAnInitialFeeForTheLicenseType', 'Is There an Initial Fee for the License Type?', [
    ('HasInitialTypeFee', 'Yes', [cond('LookUpInitialFee.Amount', 'IsNull', BOOL(False))], 'GetInitialProduct', 'and')], 'LookUpGenericInitialFee')
matrix('LookUpGenericInitialFee', 'Look Up Generic Initial Fee', STR('Individual License'), 'GetInitialProduct')
F.lookup('GetInitialProduct', 'Get Initial Product', 'Product2',
         [('FeeCode__c', 'EqualTo', REF('forT_InitialFeeCode')), ('FeeCode__c', 'IsNull', BOOL(False))], ['Id'], 'CreateFee', first=True, sort=None)
F.create_one('CreateFee', 'Create Fee', 'RegulatoryTrxnFee', [
    ('AccountId', REF('GetApplicant.Id')), ('ParentRecordId', REF('CreateApplication')), ('Status', STR('DUE')),
    ('DueDate', REF('$Flow.CurrentDateTime')), ('Description', STR('Completion and initial license'))], 'CreateInitialFeeItem', 'CouldNotSave')
F.create_one('CreateInitialFeeItem', 'Create Initial License Fee Item', 'RegulatoryTrxnFeeItem', [
    ('RegulatoryTrxnFeeId', REF('CreateFee')), ('Name', REF('forT_FeeItemName')), ('FeeAmount', REF('forN_InitialAmount')),
    ('ForYear__c', REF('forT_ThisYear')), ('CalculationInfo', STR('Initial license fee, from the Fee Schedule.')), ('FeeProduct__c', REF('GetInitialProduct.Id'))],
    'SetPaymentIds', 'CouldNotSave')
F.assignment('SetPaymentIds', 'Set Payment Ids', [('varT_FeeIds', 'Add', REF('CreateFee')), ('varT_ApplicationIds', 'Add', REF('CreateApplication'))], 'TransferDraft')
subflow('TransferDraft', 'Transfer Draft Documents', 'SubflowPreliminaryApplicationTransfer',
        [('varT_PreliminaryApplicationId', REF('CreateDraft')), ('varT_ApplicationId', REF('CreateApplication'))], 'GenerateChecklist')
subflow('GenerateChecklist', 'Generate Checklist', 'SubflowDocumentChecklistGenerate', checklist_inputs('CreateApplication'), 'Payment')
subflow('Payment', 'Payment', 'SubflowApplicationPayment',
        [('varB_IsStaffEntry', REF('forB_IsStaffEntry')), ('varT_FeeIds', REF('varT_FeeIds')), ('varT_ApplicationIds', REF('varT_ApplicationIds'))], 'DeleteDraft')
els['recordDeletes'].append(
    f'<recordDeletes><name>DeleteDraft</name><description>The draft is kept until the payment step is done, as on every form.</description><label>Delete Draft</label>{loc()}'
    f'{conn("Submitted")}<filterLogic>and</filterLogic><filters><field>Id</field><operator>EqualTo</operator><value><elementReference>CreateDraft</elementReference></value></filters>'
    '<object>PreliminaryApplicationRef</object></recordDeletes>')
screen('Submitted', 'Submitted', [
    F.display('SUB_Message', '<h2>The completion form has been submitted</h2><p>The Board will review it. The license is released once every examination is passed and the fees are paid.</p>')
    .replace('</fields>', vis_true('forB_IsStaffEntry', False) + '</fields>'),
    F.display('SUB_StaffMessage', '<h2>The application is saved</h2><p>Find it on the person\'s Applications tab. Add any documents still to come with <b>Upload Documents</b> '
              'on the application, and record payments with <b>Record Payment</b>.</p>')
    .replace('</fields>', vis_true('forB_IsStaffEntry') + '</fields>'),
], None, next_label='Done')
screen('CouldNotSave', 'Could Not Save', [
    F.display('CNS_Message', '<p>The completion form could not be saved.</p><p>{!$Flow.FaultMessage}</p>')], None, next_label='Done')

desc = ('Screen Flow: Individual Application New Licensure. The school\'s completion form (the 1,500 hour completion form for cosmetology; other licenses use '
        'the same form with their own completion hours), entered by staff from New Application on the student\'s person account. Staff choose the license sought '
        'and the school and copy the dates enrolled and completed and the hours certified; the next screen sets those hours beside the hours on the student\'s '
        'Training tab (without continuing education) and the license type\'s completion hours. Staff upload the cumulative hours report (they may continue '
        'without it; Decide waits until it is accepted) and complete the certification step with the school representative\'s name. On certifying it creates a '
        'submitted Individual Application (New Licensure record type, path Regular, linked to the school\'s course offering) with the initial license fee from '
        'the Fee Schedule (the license type\'s Initial row, or the generic Individual License row), and tells staff to record the payment with Record Payment. '
        'Like every form it keeps a draft until certify. Runs in system context. Staff only for now; it is built like the portal forms (recordId, staff flag) so '
        'a school portal audience can be added later.')
head = ('<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<apiVersion>66.0</apiVersion>')
body = ''.join(els['actionCalls']) + ''.join(els['assignments']) + ''.join(els['choices']) + ''.join(els['decisions'])
body += f'<description>{e(desc)}</description>' + ''.join(els['dynamicChoiceSets'])
body += '<environments>Default</environments>' + ''.join(els['formulas'])
body += f'<interviewLabel>{FORM_NAME}</interviewLabel><label>{FORM_NAME}</label>' + ''.join(els['loops'])
for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
    body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
body += '<processType>Flow</processType>' + ''.join(els['recordCreates']) + ''.join(els['recordDeletes']) + ''.join(els['recordLookups'])
body += '<runInMode>SystemModeWithoutSharing</runInMode>' + ''.join(els['screens'])
body += f'<start>{loc()}{conn("GetApplicant")}</start><status>Active</status>' + ''.join(els['subflows']) + ''.join(els['variables']) + '</Flow>\n'
open(sys.argv[1] + '/ScreenFlowIndividualApplicationNewLicensure.flow-meta.xml', 'w').write(head + body)
print('written')
