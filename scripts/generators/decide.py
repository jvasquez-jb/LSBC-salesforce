"""Generates the two Decide screen flows. Usage: python3 -I decide.py <flows dir>"""
import importlib
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flowlib


def build(obj, label_obj, refuse_status, refuse_word, outdir):
    importlib.reload(flowlib)
    F = flowlib
    els = F.els
    els['recordUpdates'] = []
    els['actionCalls'] = []
    e, val, conn, loc = F.e, F.val, F.conn, F.loc
    REF, STR, NUM, BOOL, cond = F.REF, F.STR, F.NUM, F.BOOL, F.cond

    def update(name, label, idref, objname, assigns, nxt, fault):
        x = f'<recordUpdates><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}{conn(fault, "faultConnector")}'
        x += f'<filterLogic>and</filterLogic><filters><field>Id</field><operator>EqualTo</operator><value><elementReference>{idref}</elementReference></value></filters>'
        for f, v in assigns:
            x += f'<inputAssignments><field>{f}</field>' + (f'<value>{val(v)}</value>' if v is not None else '') + '</inputAssignments>'
        els['recordUpdates'].append(x + f'<object>{objname}</object></recordUpdates>')

    def choice(name, text, value):
        els['choices'].append(f'<choices><name>{name}</name><choiceText>{e(text)}</choiceText><dataType>String</dataType><value><stringValue>{e(value)}</stringValue></value></choices>')

    def action(name, label, aname, atype, params, nxt, fault):
        x = f'<actionCalls><name>{name}</name><label>{e(label)}</label>{loc()}<actionName>{aname}</actionName><actionType>{atype}</actionType>{conn(nxt)}{conn(fault, "faultConnector")}<flowTransactionModel>CurrentTransaction</flowTransactionModel>'
        for n, v in params:
            x += f'<inputParameters><name>{n}</name><value>{val(v)}</value></inputParameters>'
        if name == 'CalculateExpiration':
            x += '<outputParameters><assignToReference>varDT_NewPeriodEnd</assignToReference><name>NewPeriodEnd</name></outputParameters>'
            els['actionCalls'].append(x + '</actionCalls>')
        else:
            els['actionCalls'].append(x + '<storeOutputAutomatically>true</storeOutputAutomatically></actionCalls>')

    def vis(*conds):
        return ''.join(conds)

    is_person = obj == 'IndividualApplication'
    F.var('recordId', 'String', 'The application being decided. Named recordId because the quick action passes the record under that name.', inp=True)
    F.var('varN_OpenItems', 'Number', 'How many required checklist items are not yet accepted.', default=NUM(0), scale=0)
    F.var('varN_UnpaidFees', 'Number', 'How many of the application\'s fees are not fully paid.', default=NUM(0), scale=0)
    F.var('varN_UnpaidLicenseFees', 'Number', 'For a renewal, how many fees on the license being renewed are not fully paid. The renewal fee is raised on the license, not the application.', default=NUM(0), scale=0)
    F.var('varN_StopCodes', 'Number', 'How many stop codes are active on the holder.', default=NUM(0), scale=0)
    F.var('varDT_NewPeriodEnd', 'DateTime', 'The expiration date from License Expiration Date. The rule returns midnight GMT, so it is kept as a date and time and moved to noon Louisiana time.')
    F.var('varT_OpenItemsText', 'String', 'The open checklist items, one line each, for the summary.')
    F.var('varT_StopCodesText', 'String', 'The active stop codes, one line each, for the summary.')

    choice('choice_Approve', 'Approve', 'Approve')
    choice('choice_Return', 'Return to the applicant', 'Return')
    choice('choice_Refuse', refuse_word, 'Refuse')
    choice('choice_LetterYes', 'Yes, create the return letter', 'Yes')
    choice('choice_LetterNo', 'No', 'No')
    els['dynamicChoiceSets'].append(f'<dynamicChoiceSets><name>choice_ReturnReason</name><dataType>Picklist</dataType><displayField xsi:nil="true"/><object xsi:nil="true"/><picklistField>ReturnReason__c</picklistField><picklistObject>{obj}</picklistObject></dynamicChoiceSets>')

    F.formula('forB_Ready', 'Boolean', '{!GetApplication.IsCertified__c} && {!varN_OpenItems} = 0 && {!varN_UnpaidFees} + {!varN_UnpaidLicenseFees} = 0', 'True when the application is certified, every required document is accepted and every fee is paid, so the application can be approved. The forms certify it, on the portal and in staff intake; an application made without a form is not certified.')
    F.formula('forB_IsRenewal', 'Boolean', 'NOT(ISBLANK({!GetApplication.LicensePermitNameId})) && TEXT({!GetApplication.ApplicationType}) = "Renewal"', 'True for a renewal of an existing license.')
    F.formula('forB_IsDuplicate', 'Boolean', 'NOT(ISBLANK({!GetApplication.LicensePermitNameId})) && TEXT({!GetApplication.ApplicationType}) = "Duplicate"', 'True for a duplicate of an existing license: approving it records the date, which allows one duplicate per renewal period.')
    F.formula('forB_IsNewLicense', 'Boolean', 'ISBLANK({!GetApplication.LicensePermitNameId}) && (TEXT({!GetApplication.ApplicationType}) = "New" || ISBLANK(TEXT({!GetApplication.ApplicationType})))', 'True when approving creates a new license.')
    F.formula('forT_LicenseTypeId', 'String', 'IF({!forB_IsRenewal}, {!GetLicense.RegulatoryAuthorizationTypeId}, {!GetApplication.LicenseTypeId})', 'The license type whose expiration basis sets the new expiration date.')
    F.formula('forD_StartDate', 'Date', 'IF({!forB_IsRenewal} && DATEVALUE({!GetLicense.PeriodEnd}) > TODAY(), DATEVALUE({!GetLicense.PeriodEnd}), TODAY())', 'Where the new period starts: a renewal runs on from the current expiration date unless it has passed; a new license starts today.')
    F.formula('forT_DurationType', 'String', 'IF(TEXT({!GetLicenseType.ExpirationBasis__c}) = "From Issue Date", "Day", "Month")', 'The unit of the license type\'s term: days for licenses that run a set time from issue (the temporary permit), otherwise months.')
    F.formula('forB_BirthdayMissing', 'Boolean', 'TEXT({!GetLicenseType.ExpirationBasis__c}) = "Holders Birthday" && ISBLANK({!GetHolder.DateOfBirth__pc})', 'True when the license expires on the holder\'s birthday but the holder has no date of birth.')
    F.formula('forN_BirthMonth', 'Number', 'IF(ISBLANK({!GetHolder.DateOfBirth__pc}), 1, MONTH({!GetHolder.DateOfBirth__pc}))', 'The holder\'s birth month, for licenses that expire on the birthday.', scale=0)
    F.formula('forN_BirthDay', 'Number', 'IF(ISBLANK({!GetHolder.DateOfBirth__pc}), 1, DAY({!GetHolder.DateOfBirth__pc}))', 'The holder\'s birth day, for licenses that expire on the birthday.', scale=0)
    F.formula('forDT_PeriodEnd', 'DateTime', '{!varDT_NewPeriodEnd} + (17 / 24)', 'The new expiration date at noon Louisiana time (the rule returns midnight GMT), so it shows as the same date in every US time zone.')
    F.formula('forDT_PeriodStart', 'DateTime', 'DATETIMEVALUE(TEXT({!forD_StartDate}) & " 17:00:00")', 'The period start at noon Louisiana time.')
    F.formula('forN_RenewalCount', 'Number', 'BLANKVALUE({!GetLicense.RenewalCount__c}, 0) + 1', 'The license\'s renewal count after this renewal.', scale=0)
    F.formula('forT_LicenseName', 'String', 'LEFT({!GetHolder.Name} & " " & {!GetLicenseType.Name}, 80)', 'The new license\'s name: the holder and the license type.')
    F.formula('forT_LicenseId', 'String', 'IF(ISBLANK({!CreateLicense}), {!GetApplication.LicensePermitNameId}, {!CreateLicense})', 'The license the application is for: the one just created, or the existing one.')
    F.formula('forT_ItemLine', 'String', '"<li>" & {!LoopThroughOpenItems.Name} & " (" & TEXT({!LoopThroughOpenItems.Status}) & ")</li>"', 'One open checklist item for the summary.')
    F.formula('forT_StopCodeLine', 'String', '"<li>" & {!LoopThroughStopCodes.Subject} & "</li>"', 'One active stop code for the summary.')
    F.formula('forT_Summary', 'String',
              'IF({!forB_Ready}, "<p><b>Ready to approve:</b> the application is certified, every required document is accepted and the fees are paid.</p>", "<p><b>Not ready to approve.</b></p>")'
              ' & IF({!GetApplication.IsCertified__c}, "", "<p>The application is not certified. It was not entered through an application form: enter it with New Application on the applicant\'s person account (for a business, the owner\'s or director\'s) so it is certified.</p>")'
              ' & IF({!varN_OpenItems} > 0, "<p>Required documents not yet accepted:</p><ul>" & {!varT_OpenItemsText} & "</ul>", "")'
              ' & IF({!varN_UnpaidFees} + {!varN_UnpaidLicenseFees} > 0, "<p>Fees not fully paid: " & TEXT({!varN_UnpaidFees} + {!varN_UnpaidLicenseFees}) & IF({!varN_UnpaidLicenseFees} > 0, " (the renewal fee is on the license: see Fees and Payments on the person)", "") & "</p>", "")'
              ' & IF({!varN_StopCodes} > 0, "<p>Active stop codes on the holder (the license will not print until they end):</p><ul>" & {!varT_StopCodesText} & "</ul>", "")',
              'The review summary shown above the decision.')

    F.lookup('GetApplication', 'Get Application', obj, [('Id', 'EqualTo', REF('recordId'))],
             ['Id', 'Name', 'Status', 'AccountId', 'LicenseTypeId', 'LicensePermitNameId', 'ApplicationType', 'IsCertified__c'], 'IsItAlreadyDecided', first=True, sort=None)
    already = [cond('GetApplication.Status', 'EqualTo', STR('Approved')), cond('GetApplication.Status', 'EqualTo', STR(refuse_status))]
    if not is_person:
        already.append(cond('GetApplication.Status', 'EqualTo', STR('Approved with Conditions')))
    F.decision('IsItAlreadyDecided', 'Is the Application Already Decided?', [('Decided', 'Yes', already, 'AlreadyDecided', 'or')], 'GetOpenItems')
    F.lookup('GetOpenItems', 'Get Required Items Not Accepted', 'DocumentChecklistItem',
             [('ParentRecordId', 'EqualTo', REF('recordId')), ('IsRequired', 'EqualTo', BOOL(True)), ('Status', 'NotEqualTo', STR('Accepted'))],
             ['Id', 'Name', 'Status'], 'CountOpenItems', sort='Name')
    F.assignment('CountOpenItems', 'Count Open Items', [('varN_OpenItems', 'AssignCount', REF('GetOpenItems'))], 'LoopThroughOpenItems')
    F.loop('LoopThroughOpenItems', 'Loop Through Open Items', 'GetOpenItems', 'AddItemLine', 'GetUnpaidFees')
    F.assignment('AddItemLine', 'Add Item to Summary', [('varT_OpenItemsText', 'Add', REF('forT_ItemLine'))], 'LoopThroughOpenItems')
    F.lookup('GetUnpaidFees', 'Get Unpaid Fees', 'RegulatoryTrxnFee',
             [('ParentRecordId', 'EqualTo', REF('recordId')), ('Status', 'EqualTo', STR('DUE')), ('Status', 'EqualTo', STR('PARTIALLY_PAID'))],
             ['Id'], 'CountUnpaidFees', logic='1 AND (2 OR 3)', sort=None)
    F.assignment('CountUnpaidFees', 'Count Unpaid Fees', [('varN_UnpaidFees', 'AssignCount', REF('GetUnpaidFees'))], 'IsItALicenseRenewal' if is_person else 'GetStopCodes')
    if is_person:
        F.decision('IsItALicenseRenewal', 'Is It a License Renewal?', [
            ('LicenseRenewal', 'License Renewal', [cond('forB_IsRenewal', 'EqualTo', BOOL(True))], 'GetUnpaidLicenseFees', 'and'),
        ], 'GetStopCodes', default_label='Not a Renewal')
        F.lookup('GetUnpaidLicenseFees', 'Get Unpaid License Fees', 'RegulatoryTrxnFee',
                 [('ParentRecordId', 'EqualTo', REF('GetApplication.LicensePermitNameId')), ('Status', 'EqualTo', STR('DUE')), ('Status', 'EqualTo', STR('PARTIALLY_PAID'))],
                 ['Id'], 'CountUnpaidLicenseFees', logic='1 AND (2 OR 3)', sort=None)
        F.assignment('CountUnpaidLicenseFees', 'Count Unpaid License Fees', [('varN_UnpaidLicenseFees', 'AssignCount', REF('GetUnpaidLicenseFees'))], 'GetStopCodes')
    F.lookup('GetStopCodes', 'Get Active Stop Codes', 'RecordAlert',
             [('WhatId', 'EqualTo', REF('GetApplication.AccountId')), ('IsActive', 'EqualTo', BOOL(True))],
             ['Id', 'Subject'], 'CountStopCodes', sort='CreatedDate')
    F.assignment('CountStopCodes', 'Count Stop Codes', [('varN_StopCodes', 'AssignCount', REF('GetStopCodes'))], 'LoopThroughStopCodes')
    F.loop('LoopThroughStopCodes', 'Loop Through Stop Codes', 'GetStopCodes', 'AddStopCodeLine', 'Decide')
    F.assignment('AddStopCodeLine', 'Add Stop Code to Summary', [('varT_StopCodesText', 'Add', REF('forT_StopCodeLine'))], 'LoopThroughStopCodes')

    outcome_is = lambda v: cond('DA_Outcome', 'EqualTo', STR(v))
    radio = ('<fields><name>DA_Outcome</name><choiceReferences>choice_Approve</choiceReferences><choiceReferences>choice_Return</choiceReferences>'
             '<choiceReferences>choice_Refuse</choiceReferences><dataType>String</dataType><fieldText>Decision</fieldText><fieldType>RadioButtons</fieldType>'
             '<isRequired>true</isRequired></fields>')
    reason_pick = ('<fields><name>DA_ReturnReason</name><choiceReferences>choice_ReturnReason</choiceReferences><dataType>String</dataType>'
                   '<fieldText>Return reason</fieldText><fieldType>DropdownBox</fieldType><isRequired>true</isRequired>'
                   f'<visibilityRule><conditionLogic>and</conditionLogic>{outcome_is("Return")}</visibilityRule></fields>')
    reason_text = ('<fields><name>DA_Reason</name><dataType>String</dataType><fieldText>What the applicant needs to know</fieldText><fieldType>LargeTextArea</fieldType>'
                   '<helpText>Saved as the Decision Reason. For a return, it is printed in the return letter.</helpText><isRequired>true</isRequired>'
                   f'<visibilityRule><conditionLogic>or</conditionLogic>{outcome_is("Return")}{outcome_is("Refuse")}</visibilityRule></fields>')
    number = ('<fields><name>DA_LicenseNumber</name><dataType>String</dataType><fieldText>License number</fieldText><fieldType>InputField</fieldType>'
              '<helpText>The number to print on the new license.</helpText><isRequired>true</isRequired>'
              f'<visibilityRule><conditionLogic>and</conditionLogic>{outcome_is("Approve")}{cond("forB_IsNewLicense", "EqualTo", BOOL(True))}{cond("forB_Ready", "EqualTo", BOOL(True))}</visibilityRule></fields>')
    F.screen('Decide', 'Decide', [
        F.display('DA_Application', '<p><b>{!GetApplication.Name}</b>: {!GetApplication.ApplicationType}, status {!GetApplication.Status}.</p>'),
        F.display('DA_Summary', '{!forT_Summary}'),
        radio, number, reason_pick, reason_text,
    ], 'WhatWasDecided', next_label='Save Decision')

    F.decision('WhatWasDecided', 'What Was Decided?', [
        ('ApproveNotReady', 'Approve, Not Ready', [outcome_is('Approve'), cond('forB_Ready', 'EqualTo', BOOL(False))], 'NotReady', 'and'),
        ('Approve', 'Approve', [outcome_is('Approve')], 'WhatKindOfApproval', 'and'),
        ('Return', 'Return', [outcome_is('Return')], 'SaveReturn', 'and'),
    ], 'SaveRefusal', default_label=refuse_word)

    F.decision('WhatKindOfApproval', 'What Kind of Approval?', [
        ('Renewal', 'Renewal', [cond('forB_IsRenewal', 'EqualTo', BOOL(True))], 'GetLicense', 'and'),
        ('NewLicense', 'New License', [cond('forB_IsNewLicense', 'EqualTo', BOOL(True))], 'GetLicenseType', 'and'),
        ('Duplicate', 'Duplicate', [cond('forB_IsDuplicate', 'EqualTo', BOOL(True))], 'RecordDuplicate', 'and'),
    ], 'IsThereALicense', default_label='Other')
    update('RecordDuplicate', 'Set Last Duplicate Date', 'GetApplication.LicensePermitNameId', 'BusinessLicense', [
        ('LastDuplicateDate__c', REF('$Flow.CurrentDate')),
        ('PrintRequestedDate__c', REF('$Flow.CurrentDate')),
        ('PrintedDate__c', None)], 'ApproveApplication', 'CouldNotSaveDecision')
    F.lookup('GetLicense', 'Get License', 'BusinessLicense', [('Id', 'EqualTo', REF('GetApplication.LicensePermitNameId'))],
             ['Id', 'Identifier', 'PeriodEnd', 'RenewalCount__c', 'RegulatoryAuthorizationTypeId'], 'GetLicenseType', first=True, sort=None)
    F.lookup('GetLicenseType', 'Get License Type', 'RegulatoryAuthorizationType', [('Id', 'EqualTo', REF('forT_LicenseTypeId'))],
             ['Id', 'Name', 'ExpirationBasis__c', 'TermLength__c'], 'GetHolder', first=True, sort=None)
    F.lookup('GetHolder', 'Get Holder', 'Account', [('Id', 'EqualTo', REF('GetApplication.AccountId'))],
             ['Id', 'Name', 'DateOfBirth__pc'], 'IsTheBirthdayNeeded', first=True, sort=None)
    F.decision('IsTheBirthdayNeeded', 'Is a Missing Birthday Needed?', [
        ('BirthdayMissing', 'Yes', [cond('forB_BirthdayMissing', 'EqualTo', BOOL(True))], 'NoBirthday', 'and')], 'CalculateExpiration')
    F.screen('NoBirthday', 'No Date of Birth', [
        F.display('NB_Message', '<p><b>Nothing was saved.</b> {!GetLicenseType.Name} licenses expire on the holder\'s birthday, and {!GetHolder.Name} has no date of birth on file. Add it to their account, then run Decide again.</p>'),
    ], None, next_label='Done')
    action('CalculateExpiration', 'Calculate Expiration Date', 'LicenseExpirationDate', 'runExpressionSet', [
        ('ExpirationBasis', REF('GetLicenseType.ExpirationBasis__c')),
        ('TermLength', REF('GetLicenseType.TermLength__c')),
        ('DurationType', REF('forT_DurationType')),
        ('StartDate', REF('forD_StartDate')),
        ('BirthMonth', REF('forN_BirthMonth')),
        ('BirthDay', REF('forN_BirthDay')),
    ], 'IsItARenewal', 'CouldNotSaveDecision')
    F.decision('IsItARenewal', 'Is It a Renewal?', [('IsRenewal', 'Yes', [cond('forB_IsRenewal', 'EqualTo', BOOL(True))], 'RenewLicense', 'and')], 'CreateLicense')
    update('RenewLicense', 'Renew License', 'GetLicense.Id', 'BusinessLicense', [
        ('PeriodEnd', REF('forDT_PeriodEnd')),
        ('PrintRequestedDate__c', REF('$Flow.CurrentDate')),
        ('PrintedDate__c', None),
        ('RenewalCount__c', REF('forN_RenewalCount')),
        ('Status', STR('Active')),
    ], 'ApproveApplication', 'CouldNotSaveDecision')
    F.create_one('CreateLicense', 'Create License', 'BusinessLicense', [
        ('AccountId', REF('GetApplication.AccountId')),
        ('Identifier', REF('DA_LicenseNumber')),
        ('Name', REF('forT_LicenseName')),
        ('PeriodEnd', REF('forDT_PeriodEnd')),
        ('PeriodStart', REF('forDT_PeriodStart')),
        ('PrintRequestedDate__c', REF('$Flow.CurrentDate')),
        ('RegulatoryAuthorizationTypeId', REF('GetApplication.LicenseTypeId')),
        ('Status', STR('Active')),
    ], 'ApproveApplication', 'CouldNotSaveDecision')
    F.decision('IsThereALicense', 'Is There a License to Print?', [
        ('HasLicense', 'Yes', [cond('GetApplication.LicensePermitNameId', 'IsNull', BOOL(False))], 'RequestPrint', 'and')], 'ApproveApplication')
    update('RequestPrint', 'Set Print Requested Date', 'GetApplication.LicensePermitNameId', 'BusinessLicense', [
        ('PrintRequestedDate__c', REF('$Flow.CurrentDate')),
        ('PrintedDate__c', None)], 'ApproveApplication', 'CouldNotSaveDecision')
    update('ApproveApplication', 'Set Application to Approved', 'recordId', obj, [
        ('ApprovedDate', REF('$Flow.CurrentDateTime')), ('LicensePermitNameId', REF('forT_LicenseId')), ('Status', STR('Approved'))], 'Approved', 'CouldNotSaveDecision')
    F.screen('Approved', 'Approved', [
        F.display('AP_Message', '<p><b>{!GetApplication.Name} is approved.</b></p><p>The license is marked ready to print. It prints once the holder has no active stop codes.</p>'),
    ], None, next_label='Done')

    update('SaveReturn', 'Set Application to Returned', 'recordId', obj, [
        ('DecisionReason__c', REF('DA_Reason')), ('ReturnReason__c', REF('DA_ReturnReason')), ('WasReturned', BOOL(True))], 'OfferReturnLetter', 'CouldNotSaveDecision')
    F.screen('OfferReturnLetter', 'Offer Return Letter', [
        F.display('ORL_Message', '<p><b>{!GetApplication.Name} is returned.</b> The reason is saved on the application.</p>'),
        '<fields><name>ORL_CreateLetter</name><choiceReferences>choice_LetterYes</choiceReferences><choiceReferences>choice_LetterNo</choiceReferences>'
        '<dataType>String</dataType><fieldText>Create the return letter now?</fieldText><fieldType>RadioButtons</fieldType><isRequired>true</isRequired></fields>',
    ], 'CreateTheLetter')
    F.decision('CreateTheLetter', 'Create the Letter?', [('CreateLetter', 'Yes', [cond('ORL_CreateLetter', 'EqualTo', STR('Yes'))], 'SaveReturnLetter', 'and')], None)
    action('SaveReturnLetter', 'Save Return Letter', 'LetterPdfSaveAction', 'apex', [
        ('recordId', REF('recordId')), ('templateName', STR('ReturnLetter')), ('details', REF('DA_Reason'))], 'ReturnLetterSaved', 'CouldNotSaveDecision')
    F.screen('ReturnLetterSaved', 'Return Letter Saved', [
        F.display('RLS_Message', '<p>{!SaveReturnLetter.title} is in this application\'s Files. '
                  '<a href="/lightning/r/ContentDocument/{!SaveReturnLetter.contentDocumentId}/view" target="_blank">Open the letter</a> to print it.</p>'),
    ], None, next_label='Done')

    update('SaveRefusal', f'Set Application to {refuse_status}', 'recordId', obj, [
        ('DecisionReason__c', REF('DA_Reason')), ('Status', STR(refuse_status))], 'AreThereFeesToCancel', 'CouldNotSaveDecision')
    F.decision('AreThereFeesToCancel', 'Are There Fees to Cancel?', [
        ('FeesToCancel', 'Yes', [cond('varN_UnpaidFees', 'GreaterThan', NUM(0))], 'CancelUnpaidFees', 'and')], 'Refused')
    els['recordUpdates'].append(
        f'<recordUpdates><name>CancelUnpaidFees</name><description>The application is {refuse_status.lower()}, so its fees still Due or Partially Paid are canceled: they are no longer owed.</description>'
        f'<label>Set Unpaid Fees to Canceled</label>{loc()}{conn("Refused")}{conn("CouldNotSaveDecision", "faultConnector")}<filterLogic>1 AND (2 OR 3)</filterLogic>'
        '<filters><field>ParentRecordId</field><operator>EqualTo</operator><value><elementReference>recordId</elementReference></value></filters>'
        '<filters><field>Status</field><operator>EqualTo</operator><value><stringValue>DUE</stringValue></value></filters>'
        '<filters><field>Status</field><operator>EqualTo</operator><value><stringValue>PARTIALLY_PAID</stringValue></value></filters>'
        '<inputAssignments><field>Status</field><value><stringValue>CANCELED</stringValue></value></inputAssignments><object>RegulatoryTrxnFee</object></recordUpdates>')
    F.screen('Refused', refuse_status, [
        F.display('RF_Message', f'<p><b>{{!GetApplication.Name}} is {refuse_status.lower()}.</b> The reason is saved on the application, and its unpaid fees are canceled.</p>'),
    ], None, next_label='Done')
    F.screen('NotReady', 'Not Ready to Approve', [
        F.display('NR_Message', '<p><b>This application can\'t be approved yet.</b> Approve is available only when the application is certified, every required document is accepted and the fees are paid.</p>{!forT_Summary}'),
    ], 'Decide', next_label='Back to Decision')
    F.screen('AlreadyDecided', 'Already Decided', [
        F.display('AD_Message', '<p>{!GetApplication.Name} is already {!GetApplication.Status}, so there is nothing to decide.</p>'),
    ], None, next_label='Done')
    F.screen('CouldNotSaveDecision', 'Could Not Save Decision', [
        F.display('CNSD_Message', '<p>The decision could not be saved.</p><p>{!$Flow.FaultMessage}</p>'),
    ], None)

    refusal_text = ('refused (Denied)' if is_person else 'refused (Canceled, until a Denied status is added)')
    desc = (f'Records staff\'s decision on a {label_obj.lower()}, from the Decide action. It first shows what stands in the way: required '
            f'documents not yet accepted, fees not fully paid, and active stop codes on the holder. Approve is allowed only when the application is certified (entered through a form, on the portal or by staff), the documents are accepted and the fees paid. '
            f'Approving a new application creates the license with the number staff enter, its expiration date from License Expiration Date; approving a renewal moves the '
            f'existing license\'s expiration on and adds one to its renewal count; approving a duplicate records the date on the license as its Last Duplicate Date. Either way the license is marked ready to print (its Printed Date is cleared, so a license printed earlier goes back in the print queue) and the application is Approved with today as its Approved Date. '
            f'A return records the reason and can create the return letter; an application can also be {refusal_text}, with the reason saved and its unpaid fees set to Canceled.')
    label = f'Screen Flow: {label_obj} Decide'
    head = ('<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            '<apiVersion>66.0</apiVersion>')
    body = ''.join(els['actionCalls']) + ''.join(els['assignments']) + ''.join(els['choices']) + ''.join(els['decisions'])
    body += f'<description>{e(desc)}</description>' + ''.join(els['dynamicChoiceSets'])
    body += '<environments>Default</environments>' + ''.join(els['formulas'])
    body += f'<interviewLabel>{e(label)} {{!$Flow.CurrentDateTime}}</interviewLabel><label>{e(label)}</label>' + ''.join(els['loops'])
    for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
        body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
    body += '<processType>Flow</processType>' + ''.join(els['recordCreates']) + ''.join(els['recordLookups']) + ''.join(els['recordUpdates'])
    body += '<runInMode>DefaultMode</runInMode>' + ''.join(els['screens'])
    body += f'<start>{loc()}{conn("GetApplication")}</start><status>Active</status>' + ''.join(els['variables']) + '</Flow>\n'
    api = 'ScreenFlow' + label_obj.replace(' ', '') + 'Decide'
    open(f'{outdir}/{api}.flow-meta.xml', 'w').write(head + body)
    print('written', api)


build('IndividualApplication', 'Individual Application', 'Denied', 'Deny', sys.argv[1])
build('BusinessLicenseApplication', 'Business License Application', 'Canceled', 'Refuse (cancel the application)', sys.argv[1])
