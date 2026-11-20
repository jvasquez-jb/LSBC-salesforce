"""Generates the address change flows. Usage: python3 -I addresschange.py <flows dir>

- ScreenFlowCaseAddressChangeRequest (portal, label "Change My Address"): a licensee asks to change their mailing
  address and uploads proof. Follows the portal form pattern: a draft holds the proof until the licensee certifies,
  then the form creates a Case (Type Address Change) in the General Inquiries queue and moves the proof to it.
  Like the other forms, it records the saved-form link on the draft (so Save for later shows on My Applications),
  offers a saved address change to continue, and discards at most three abandoned drafts per start. The last screen
  has no Finish button (Finish would restart the form) but a link back to My Applications.
- ScreenFlowCaseApplyAddressChange (staff, the Apply Address Change action on Case): after checking the proof, staff
  copy the requested address to the person's mailing address, the proof of address item is accepted and the Case
  closes.

Person accounts only: the Board decided (18 Nov 2026) that salons, schools, facilities and manager licenses change
their address through staff, not the portal.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flowlib as F

e, val, conn, loc = F.e, F.val, F.conn, F.loc
REF, STR, BOOL, NUM, cond = F.REF, F.STR, F.BOOL, F.NUM, F.cond
MY_APPS = '/LPI/s/view-license-permit-status'
# The last screens' button, the same on every portal form: a link styled as the portal's button (lsbc-button in the theme
# CSS) that opens My Applications in the same tab (a link in a flow opens a new tab unless the target is set).
BACK_LINK = f'<p><a class="lsbc-button" target="_self" href="{MY_APPS}">Back to My Applications</a></p>'
ADDR = ['Street', 'City', 'State', 'PostalCode', 'Country']
OUT = sys.argv[1]


def reset():
    for k in list(F.els):
        F.els[k] = []
    for k in ['recordUpdates', 'recordDeletes', 'subflows']:
        F.els[k] = []


def update(name, label, idref, objname, assigns, nxt, fault):
    x = f'<recordUpdates><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}{conn(fault, "faultConnector")}'
    x += f'<filterLogic>and</filterLogic><filters><field>Id</field><operator>EqualTo</operator><value><elementReference>{idref}</elementReference></value></filters>'
    for f, v in assigns:
        x += f'<inputAssignments><field>{f}</field><value>{val(v)}</value></inputAssignments>'
    F.els['recordUpdates'].append(x + f'<object>{objname}</object></recordUpdates>')


def delete_one(name, label, idref, objname, nxt, desc):
    F.els['recordDeletes'].append(
        f'<recordDeletes><name>{name}</name><description>{e(desc)}</description><label>{e(label)}</label>{loc()}{conn(nxt)}'
        f'<filterLogic>and</filterLogic><filters><field>Id</field><operator>EqualTo</operator><value><elementReference>{idref}</elementReference></value></filters>'
        f'<object>{objname}</object></recordDeletes>')


def subflow(name, label, flow, inputs, nxt, outputs=()):
    x = f'<subflows><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}<flowName>{flow}</flowName>'
    for n, v in inputs:
        x += f'<inputAssignments><name>{n}</name><value>{val(v)}</value></inputAssignments>'
    for n in outputs:
        x += f'<outputAssignments><assignToReference>{n}</assignToReference><name>{n}</name></outputAssignments>'
    F.els['subflows'].append(x + '</subflows>')


def address_field(name, label):
    rule = ('Enter a 5-digit ZIP code (or ZIP+4).',
            f'OR({{!{name}.country}} <> "United States", REGEX(TRIM({{!{name}.postalCode}}), "\\\\d{{5}}(-\\\\d{{4}})?"))')
    return (f'<fields><name>{name}</name><extensionName>flowruntime:address</extensionName><fieldType>ComponentInstance</fieldType>'
            f'<inputParameters><name>required</name><value><booleanValue>true</booleanValue></value></inputParameters>'
            f'<inputParameters><name>addressLabel</name><value><stringValue>{e(label)}</stringValue></value></inputParameters>'
            f'<inputParameters><name>province</name><value><stringValue>Louisiana</stringValue></value></inputParameters>'
            f'<inputParameters><name>country</name><value><stringValue>United States</stringValue></value></inputParameters>'
            f'<inputsOnNextNavToAssocScrn>UseStoredValues</inputsOnNextNavToAssocScrn><isRequired>true</isRequired>'
            f'<storeOutputAutomatically>true</storeOutputAutomatically>'
            f'<validationRule><errorMessage>{e(rule[0])}</errorMessage><formulaExpression>{e(rule[1])}</formulaExpression></validationRule></fields>')


def end_screen(name, label, prefix, html):
    """A last screen without footer buttons: Finish on a portal page restarts the form (and makes a new draft), so the
    screen links back to My Applications instead."""
    F.screen(name, label, [F.display(f'{prefix}_Message', html + BACK_LINK)], None)
    F.els['screens'][-1] = F.els['screens'][-1].replace('<showFooter>true</showFooter>', '<showFooter>false</showFooter>')


def louisiana_time(dt):
    """Formula text: a DateTime (GMT) as Louisiana (Central) date and time, for example "November 19, 2026 at 9:54 PM".
    Central daylight time runs from 2 AM on the second Sunday of March (08:00 GMT) to 2 AM on the first Sunday of
    November (07:00 GMT)."""
    y = f'YEAR(DATEVALUE({dt}))'
    mar = f'(DATE({y}, 3, 8) + MOD(8 - WEEKDAY(DATE({y}, 3, 8)), 7))'
    nov = f'(DATE({y}, 11, 1) + MOD(8 - WEEKDAY(DATE({y}, 11, 1)), 7))'
    dst = f'AND({dt} >= DATETIMEVALUE(TEXT({mar}) & " 08:00:00"), {dt} < DATETIMEVALUE(TEXT({nov}) & " 07:00:00"))'
    return f'{dt} - IF({dst}, 5, 6) / 24'


def write(filename, label, desc, start, run_mode, extra_head=''):
    els = F.els
    body = ''.join(els['assignments']) + ''.join(els['decisions']) + f'<description>{e(desc)}</description><environments>Default</environments>' + ''.join(els['formulas'])
    body += f'<interviewLabel>{e(label)} {{!$Flow.CurrentDateTime}}</interviewLabel>{extra_head}<label>{e(label)}</label>' + ''.join(els['loops'])
    for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
        body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
    body += '<processType>Flow</processType>' + ''.join(els['recordCreates']) + ''.join(els['recordDeletes'])
    body += ''.join(els['recordLookups']) + ''.join(els['recordUpdates'])
    body += f'<runInMode>{run_mode}</runInMode>' + ''.join(els['screens'])
    body += f'<start>{loc()}{conn(start)}</start><status>Active</status>' + ''.join(els['subflows']) + ''.join(els['variables']) + '</Flow>\n'
    head = '<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>66.0</apiVersion>'
    open(os.path.join(OUT, filename), 'w').write(head + body)
    print('written', filename)


# ---------------------------------------------------------------- Portal: Change My Address
reset()
F.lookup('GetRunningUser', 'Get Running User', 'User', [('Id', 'EqualTo', REF('$User.Id'))], ['Id', 'AccountId'],
         'GetApplicant', first=True, sort=None)
F.lookup('GetApplicant', 'Get Applicant', 'Account', [('Id', 'EqualTo', REF('GetRunningUser.AccountId'))],
         ['Id', 'Name', 'IsPersonAccount', 'PersonContactId'] + [f'PersonMailing{a}' for a in ADDR],
         'IsTheApplicantAPerson', first=True, sort=None)
F.decision('IsTheApplicantAPerson', 'Is the Applicant a Person?', [
    ('Person', 'Yes', [cond('GetApplicant.IsPersonAccount', 'EqualTo', BOOL(True))], 'GetEarlierDrafts', 'and')], 'NotAvailable')
end_screen('NotAvailable', 'Not Available', 'NA',
    '<h2>Address changes for licensees only</h2><p>This form changes the mailing address of an individual licensee. '
    'To change the address of a salon, school or facility, or of a manager license, please contact the Board.</p>')

# Earlier drafts: offer a saved one, discard abandoned ones (at most three per start), as the other portal forms do
F.lookup('GetEarlierDrafts', 'Get Earlier Drafts', 'PreliminaryApplicationRef', [
    ('OwnerId', 'EqualTo', REF('$User.Id')), ('IsSubmitted', 'EqualTo', BOOL(False)),
    ('ApplicationName', 'EqualTo', STR('Address Change'))], ['Id', 'SavedApplicationUrl', 'CreatedDate'], 'LoopThroughEarlierDrafts')
F.els['recordLookups'][-1] = F.els['recordLookups'][-1].replace('<sortOrder>Asc</sortOrder>', '<sortOrder>Desc</sortOrder>')
F.loop('LoopThroughEarlierDrafts', 'Loop Through Earlier Drafts', 'GetEarlierDrafts', 'GetEarlierSavedForm', 'IsThereASavedApplication')
F.formula('forT_EarlierGuid', 'String', 'SUBSTITUTE({!LoopThroughEarlierDrafts.SavedApplicationUrl}, "/LPI/s/continue-application?guid=", "")',
          'The earlier draft\'s interview GUID, from its saved-form link.')
F.lookup('GetEarlierSavedForm', 'Get Earlier Saved Form', 'FlowInterview', [
    ('Guid', 'EqualTo', REF('forT_EarlierGuid')), ('InterviewStatus', 'EqualTo', STR('Paused'))], ['Id'],
    'WasTheEarlierDraftSaved', first=True, sort=None)
F.formula('forB_AbandonedDraft', 'Boolean', '{!LoopThroughEarlierDrafts.CreatedDate} < NOW() - 1',
          'A draft over a day old that was never saved for later was abandoned.')
F.decision('WasTheEarlierDraftSaved', 'Was the Earlier Draft Saved for Later?', [
    ('Saved', 'Saved', [cond('GetEarlierSavedForm.Id', 'IsNull', BOOL(False))], 'AddSavedApplication', 'and'),
    ('Abandoned', 'Abandoned', [cond('forB_AbandonedDraft', 'EqualTo', BOOL(True))], 'IsTheDiscardLimitReached', 'and')],
    'LoopThroughEarlierDrafts', 'Neither')
F.formula('forT_SavedFormId', 'String', 'BLANKVALUE({!varT_SavedFormId}, {!GetEarlierSavedForm.Id})',
          'The most recent saved address change (drafts are read newest first).')
F.assignment('AddSavedApplication', 'Add Saved Application', [
    ('varT_SavedDraftIds', 'Add', REF('LoopThroughEarlierDrafts.Id')), ('varT_SavedFormId', 'Assign', REF('forT_SavedFormId'))],
    'LoopThroughEarlierDrafts')
F.decision('IsTheDiscardLimitReached', 'Is the Discard Limit Reached?', [
    ('LimitReached', 'Yes', [cond('varN_DiscardedDrafts', 'GreaterThanOrEqualTo', NUM(3))], 'LoopThroughEarlierDrafts', 'and')],
    'AddDiscardedDraft')
F.els['decisions'][-1] = F.els['decisions'][-1].replace('<label>Is the Discard Limit Reached?</label>',
    '<description>Discards at most 3 abandoned drafts each time the form starts, so an applicant with many abandoned drafts '
    'does not hit the query limit. The rest go next time or in the nightly clean-up.</description><label>Is the Discard Limit Reached?</label>')
F.assignment('AddDiscardedDraft', 'Add Discarded Draft', [('varN_DiscardedDrafts', 'Add', NUM(1))], 'DiscardAbandonedDraft')
subflow('DiscardAbandonedDraft', 'Discard Abandoned Draft', 'SubflowPreliminaryApplicationDiscard',
        [('varT_PreliminaryApplicationId', REF('LoopThroughEarlierDrafts.Id'))], 'LoopThroughEarlierDrafts')
F.decision('IsThereASavedApplication', 'Is There a Saved Application?', [
    ('HasSavedApplication', 'Yes', [cond('varT_SavedFormId', 'IsNull', BOOL(False))], 'SavedApplication', 'and')], 'CreateDraft')
F.screen('SavedApplication', 'Saved Application', [F.display('SV_Message',
    '<h2>You have a saved address change</h2><p><a target="_self" href="/LPI/s/continue-application?interviewId={!varT_SavedFormId}">'
    '<b>Continue your saved address change</b></a> to pick up where you left off. Saved applications are kept for 30 days '
    'from when you last worked on them.</p><p>Or start again. Your saved one, and anything uploaded to it, will be deleted.</p>')],
    'LoopThroughSavedDrafts', next_label='Start again')
F.loop('LoopThroughSavedDrafts', 'Loop Through Saved Drafts', 'varT_SavedDraftIds', 'DiscardSavedDraft', 'CreateDraft')
subflow('DiscardSavedDraft', 'Discard Saved Draft', 'SubflowPreliminaryApplicationDiscard',
        [('varT_PreliminaryApplicationId', REF('LoopThroughSavedDrafts'))], 'LoopThroughSavedDrafts')
F.var('varN_DiscardedDrafts', 'Number', 'How many abandoned drafts this start has discarded.', default=NUM(0), scale=0)
F.var('varT_SavedFormId', 'String', 'The most recent saved address change for the applicant.')
F.var('varT_SavedDraftIds', 'String', 'Saved address changes for the applicant.', coll=True)

F.formula('forT_SavedApplicationUrl', 'String', '"/LPI/s/continue-application?guid=" & {!$Flow.InterviewGuid}',
          'Records this form\'s interview GUID on the draft, as every form does, so a saved form shows on My Applications.')
F.create_one('CreateDraft', 'Create Draft', 'PreliminaryApplicationRef', [
    ('ApplicationName', STR('Address Change')), ('ApplicationType', STR('ApplicationForm')),
    ('OwnerId', REF('$User.Id')), ('IsSubmitted', BOOL(False)), ('SavedApplicationUrl', REF('forT_SavedApplicationUrl'))],
    'GenerateDraftChecklist', 'CouldNotSubmit')
subflow('GenerateDraftChecklist', 'Generate Draft Checklist', 'SubflowDocumentChecklistGenerate', [
    ('varT_ApplicationId', REF('CreateDraft')), ('varT_AccountId', REF('GetApplicant.Id')),
    ('varT_RecordType', STR('Case')), ('varT_ApplicationType', STR('Address Change'))], 'NewAddress')
F.screen('NewAddress', 'New Address', [
    F.display('NA_Intro', '<p>Your mailing address on file:</p>'
              '<p>{!GetApplicant.PersonMailingStreet}<br>{!GetApplicant.PersonMailingCity}, {!GetApplicant.PersonMailingState} '
              '{!GetApplicant.PersonMailingPostalCode}<br>{!GetApplicant.PersonMailingCountry}</p>'
              '<p>Enter your new address. On the next page, upload a document that shows your name at the new address. '
              'Board staff check it before the change is made, and your licenses are mailed to the new address.</p>'),
    address_field('NA_Address', 'New mailing address'),
], 'UploadDocuments', next_label='Next')
subflow('UploadDocuments', 'Upload Documents', 'SubflowDocumentChecklistUpload', [
    ('varB_IsStaffEntry', BOOL(False)), ('varT_ApplicationId', REF('CreateDraft'))], 'Certification')
subflow('Certification', 'Certification', 'SubflowApplicationCertification', [
    ('varT_AttestationText', STR('')), ('varT_ApplicantName', REF('GetApplicant.Name'))], 'GetGeneralInquiriesQueue',
    outputs=['varB_IsCertified', 'varT_CertifiedName', 'varDT_CertifiedDateTime'])
F.var('varB_IsCertified', 'Boolean', 'Whether the applicant ticked the certification.')
F.var('varT_CertifiedName', 'String', 'The name the applicant typed to certify.')
F.var('varDT_CertifiedDateTime', 'DateTime', 'When the applicant certified.')
F.lookup('GetGeneralInquiriesQueue', 'Get General Inquiries Queue', 'Group',
         [('DeveloperName', 'EqualTo', STR('GeneralInquiries')), ('Type', 'EqualTo', STR('Queue'))], ['Id'],
         'CreateCase', first=True, sort=None)
F.formula('forDT_CertifiedLouisiana', 'DateTime', louisiana_time('{!varDT_CertifiedDateTime}'),
          'When the applicant certified, moved from GMT to Louisiana (Central) time, daylight saving included. Only for display.')
LT = '{!forDT_CertifiedLouisiana}'
MONTHS = ', '.join(f'{i}, "{m}"' for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July',
                                                         'August', 'September', 'October', 'November', 'December'], 1))
F.formula('forT_CertifiedLouisianaTime', 'String',
          f'CASE(VALUE(MID(TEXT({LT}), 6, 2)), {MONTHS}, "") & " " & TEXT(VALUE(MID(TEXT({LT}), 9, 2))) & ", " & LEFT(TEXT({LT}), 4) & " at " & '
          f'TEXT(MOD(VALUE(MID(TEXT({LT}), 12, 2)) + 11, 12) + 1) & ":" & MID(TEXT({LT}), 15, 2) & " " & '
          f'IF(VALUE(MID(TEXT({LT}), 12, 2)) < 12, "AM", "PM")',
          'When the applicant certified, in Louisiana time, for example November 19, 2026 at 9:54 PM.')
F.formula('forT_Description', 'String',
          '"Address change requested on the portal." & BR() & BR() & "From: " & {!GetApplicant.PersonMailingStreet} & ", " & '
          '{!GetApplicant.PersonMailingCity} & ", " & {!GetApplicant.PersonMailingState} & " " & {!GetApplicant.PersonMailingPostalCode} & '
          '", " & {!GetApplicant.PersonMailingCountry} & BR() & "To: " & {!NA_Address.street} & ", " & {!NA_Address.city} & ", " & '
          '{!NA_Address.province} & " " & {!NA_Address.postalCode} & ", " & {!NA_Address.country} & BR() & BR() & '
          '"Certified by " & {!varT_CertifiedName} & " on " & {!forT_CertifiedLouisianaTime} & " (Louisiana time)."',
          'The Case description: the old and new address and the certification, so staff see the request at a glance.')
F.create_one('CreateCase', 'Create Address Change Case', 'Case', [
    ('AccountId', REF('GetApplicant.Id')), ('ContactId', REF('GetApplicant.PersonContactId')),
    ('Origin', STR('Web')), ('Type', STR('Address Change')), ('Status', STR('New')),
    ('Subject', STR('Address change request')), ('Description', REF('forT_Description')),
    ('OwnerId', REF('GetGeneralInquiriesQueue.Id')),
    ('RequestedStreet__c', REF('NA_Address.street')), ('RequestedCity__c', REF('NA_Address.city')),
    ('RequestedState__c', REF('NA_Address.province')), ('RequestedPostalCode__c', REF('NA_Address.postalCode')),
    ('RequestedCountry__c', REF('NA_Address.country'))], 'TransferDraft', 'CouldNotSubmit')
subflow('TransferDraft', 'Transfer Draft Documents', 'SubflowPreliminaryApplicationTransfer', [
    ('varT_PreliminaryApplicationId', REF('CreateDraft')), ('varT_ApplicationId', REF('CreateCase'))], 'DeleteDraft')
delete_one('DeleteDraft', 'Delete Draft', 'CreateDraft', 'PreliminaryApplicationRef', 'Submitted',
           'The proof has moved to the Case, so the draft is no longer needed (there is no payment step).')
end_screen('Submitted', 'Submitted', 'SUB',
    '<h2>Your address change has been sent</h2><p>Board staff will check your document and update your mailing address. '
    'Until then, mail goes to your current address.</p>')
end_screen('CouldNotSubmit', 'Could Not Submit', 'CNS',
    '<p>Your address change could not be sent. Please try again later or contact the Board.</p>')

write('ScreenFlowCaseAddressChangeRequest.flow-meta.xml', 'Change My Address',
      'Portal flow (Screen Flow: Case Address Change Request). A licensee asks to change their mailing address: they '
      'enter the new address, upload proof (a Proof of Address checklist item) and certify. The proof waits on a draft '
      'until they certify; then the form creates a Case (Origin Web, Type Address Change) in the General Inquiries queue '
      'with the new address in its Requested fields, moves the proof to it and deletes the draft. Like the other forms, '
      'the draft holds the saved-form link (Save for later shows on My Applications), a saved request is offered to '
      'continue, abandoned drafts are discarded (at most three per start), and the last screen links back to My '
      'Applications instead of a Finish button that would restart the form. Staff apply it with '
      'Apply Address Change. Person accounts only: salons, schools, facilities and manager licenses go through staff. '
      'Runs in system context like the other portal forms.',
      'GetRunningUser', 'SystemModeWithoutSharing')

# ---------------------------------------------------------------- Staff: Apply Address Change
reset()
F.var('recordId', 'String', 'The address change Case. Named recordId because the quick action passes the record under that name.', inp=True)
F.lookup('GetCase', 'Get Case', 'Case', [('Id', 'EqualTo', REF('recordId'))],
         ['Id', 'CaseNumber', 'Type', 'AccountId', 'AddressChangeAppliedDate__c'] + [f'Requested{a}__c' for a in ADDR],
         'IsItAnAddressChange', first=True, sort=None)
F.decision('IsItAnAddressChange', 'Is It an Address Change Not Yet Applied?', [
    ('WasApplied', 'Already applied', [cond('GetCase.AddressChangeAppliedDate__c', 'IsNull', BOOL(False))], 'AlreadyApplied', 'and'),
    ('AddressChange', 'Yes', [cond('GetCase.Type', 'EqualTo', STR('Address Change')),
                              cond('GetCase.RequestedStreet__c', 'IsBlank', BOOL(False))], 'GetPerson', 'and')], 'NotAnAddressChange')
F.lookup('GetPerson', 'Get Person', 'Account', [('Id', 'EqualTo', REF('GetCase.AccountId'))],
         ['Id', 'Name', 'IsPersonAccount'] + [f'PersonMailing{a}' for a in ADDR], 'IsItAPerson', first=True, sort=None)
F.decision('IsItAPerson', 'Is the Account a Person?', [
    ('Person', 'Yes', [cond('GetPerson.IsPersonAccount', 'EqualTo', BOOL(True))], 'GetProof', 'and')], 'NotAPerson')
F.lookup('GetProof', 'Get Proof of Address', 'DocumentChecklistItem', [('ParentRecordId', 'EqualTo', REF('recordId'))],
         ['Id', 'Name', 'Status'], 'ConfirmChange', first=True, sort=None)
F.formula('forT_ProofStatus', 'String', 'IF(ISBLANK({!GetProof.Id}), "No proof uploaded", TEXT({!GetProof.Status}))',
          'The proof of address checklist item\'s status, or a note that there is none.')
F.screen('ConfirmChange', 'Confirm Change', [
    F.display('CC_Intro', '<p><b>{!GetPerson.Name}</b>, case {!GetCase.CaseNumber}</p>'
              '<p><b>Current mailing address</b><br>{!GetPerson.PersonMailingStreet}<br>{!GetPerson.PersonMailingCity}, '
              '{!GetPerson.PersonMailingState} {!GetPerson.PersonMailingPostalCode}<br>{!GetPerson.PersonMailingCountry}</p>'
              '<p><b>Requested address</b><br>{!GetCase.RequestedStreet__c}<br>{!GetCase.RequestedCity__c}, {!GetCase.RequestedState__c} '
              '{!GetCase.RequestedPostalCode__c}<br>{!GetCase.RequestedCountry__c}</p>'
              '<p><b>Proof of address:</b> {!forT_ProofStatus}. Open it on the case\'s Checklist before you apply the change.</p>'),
    F.inp('CC_ProofChecked', 'Boolean', 'I checked the proof: it shows this person at the requested address', required=True,
          rule=('Check the proof of address before applying the change.', '{!CC_ProofChecked}')),
], 'UpdatePerson', next_label='Apply Address Change')
update('UpdatePerson', 'Set Mailing Address', 'GetPerson.Id', 'Account',
       [(f'PersonMailing{a}', REF(f'GetCase.Requested{a}__c')) for a in ADDR], 'CloseCase', 'CouldNotApply')
update('CloseCase', 'Set Applied Date and Close Case', 'recordId', 'Case', [
    ('AddressChangeAppliedDate__c', REF('$Flow.CurrentDate')), ('Status', STR('Closed'))], 'IsThereAProofToAccept', 'CouldNotApply')
F.decision('IsThereAProofToAccept', 'Is There a Proof of Address to Accept?', [
    ('ProofToAccept', 'Yes', [cond('GetProof.Id', 'IsNull', BOOL(False)), cond('GetProof.Status', 'NotEqualTo', STR('Accepted'))],
     'AcceptProof', 'and')], 'Applied')
update('AcceptProof', 'Set Proof of Address Status to Accepted', 'GetProof.Id', 'DocumentChecklistItem', [
    ('Status', STR('Accepted'))], 'Applied', 'CouldNotApply')
F.screen('Applied', 'Applied', [F.display('AP_Message',
    '<p><b>The mailing address is changed, the proof of address is accepted and the case is closed.</b> The change shows on the person\'s History tab.</p>')], None, next_label='Done')
F.screen('AlreadyApplied', 'Already Applied', [F.display('AA_Message',
    '<p>This address change was already applied on {!GetCase.AddressChangeAppliedDate__c}.</p>')], None, next_label='Done')
F.screen('NotAnAddressChange', 'Not an Address Change', [F.display('NAC_Message',
    '<p>Apply Address Change works only on a case of type Address Change with a requested address, as sent from the portal. '
    'For other address changes, edit the account directly.</p>')], None, next_label='Done')
F.screen('NotAPerson', 'Not a Person', [F.display('NAP_Message',
    '<p>This case is not on a person. Salon, school and facility addresses are changed by editing the account, not through the portal.</p>')],
    None, next_label='Done')
F.screen('CouldNotApply', 'Could Not Apply', [F.display('CNA_Message',
    '<p>The address could not be changed. Nothing was saved if the person was not updated.</p><p>{!$Flow.FaultMessage}</p>')], None)

write('ScreenFlowCaseApplyAddressChange.flow-meta.xml', 'Screen Flow: Case Apply Address Change',
      'Applies a portal address change, from the Apply Address Change action on an Address Change case. Shows the '
      'current and requested mailing address and the proof\'s status; once staff confirm they checked the proof, it '
      'copies the requested address to the person\'s mailing address, sets the case\'s Address Change Applied Date, '
      'closes it and accepts the proof of address checklist item (the confirmation is the check). Refuses cases that are not address changes, are already applied, or are not on a person account.',
      'GetCase', 'SystemModeWithSharing', extra_head='<isAdditionalPermissionRequiredToRun>true</isAdditionalPermissionRequiredToRun>')
