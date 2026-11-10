"""Generates ScreenFlowBusinessLicenseMarkPrinted.flow-meta.xml. Usage: python3 -I markprinted.py <flows dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flowlib as F

els = F.els
els['recordUpdates'] = []
els['subflows'] = []
e, conn, loc = F.e, F.conn, F.loc
REF, STR, NUM, BOOL, cond = F.REF, F.STR, F.NUM, F.BOOL, F.cond

F.var('ids', 'String', 'The licenses ticked in the list view. The list view button passes them under this name.', coll=True, inp=True)
F.var('varN_Selected', 'Number', 'How many licenses were ticked.', default=NUM(0), scale=0)
F.var('varN_Printed', 'Number', 'How many licenses were marked printed.', default=NUM(0), scale=0)
F.var('varT_SkippedText', 'String', 'The licenses not marked, one line each, with the reason.')
F.var('varR_License', 'SObject', 'One license being marked printed.', obj='BusinessLicense')
F.var('varR_ToMark', 'SObject', 'The licenses to mark printed.', coll=True, obj='BusinessLicense')

F.formula('forT_HeldLine', 'String', '"<li>" & {!LoopThroughLicenses.Name} & " (" & {!LoopThroughLicenses.Identifier} & "): the holder has an active stop code</li>"',
          'A license skipped because of a stop code, for the summary.')
F.formula('forT_NotWaitingLine', 'String', '"<li>" & {!LoopThroughLicenses.Name} & " (" & {!LoopThroughLicenses.Identifier} & "): not waiting to print</li>"',
          'A ticked license that was not waiting to print, for the summary.')

F.assignment('CountSelected', 'Count Selected Licenses', [('varN_Selected', 'AssignCount', REF('ids'))], 'WereAnySelected')
F.decision('WereAnySelected', 'Were Any Licenses Selected?', [('Selected', 'Yes', [cond('varN_Selected', 'GreaterThan', NUM(0))], 'GetLicenses', 'and')], 'NothingSelected')
F.lookup('GetLicenses', 'Get Licenses', 'BusinessLicense', [('Id', 'In', REF('ids'))],
         ['Id', 'Name', 'Identifier', 'AccountId', 'IsReadyToPrint__c'], 'ConfirmPrinted', sort='Name')
F.screen('ConfirmPrinted', 'Confirm Printed', [
    F.display('CP_Message', '<p>Mark the <b>{!varN_Selected}</b> selected licenses as printed today?</p>'
              '<p>Each holder is checked for active stop codes first. A license whose holder has one is not marked and stays in the list.</p>'),
], 'LoopThroughLicenses', next_label='Mark Printed')
F.loop('LoopThroughLicenses', 'Loop Through Licenses', 'GetLicenses', 'IsItWaitingToPrint', 'AnyToMark')
F.decision('IsItWaitingToPrint', 'Is It Waiting to Print?', [
    ('Waiting', 'Yes', [cond('LoopThroughLicenses.IsReadyToPrint__c', 'EqualTo', BOOL(True))], 'CheckStopCodes', 'and')], 'AddNotWaiting')
F.assignment('AddNotWaiting', 'Add Not Waiting to Summary', [('varT_SkippedText', 'Add', REF('forT_NotWaitingLine'))], 'LoopThroughLicenses')
els['subflows'].append(
    f'<subflows><name>CheckStopCodes</name><label>Check Stop Codes</label>{loc()}{conn("DoesTheHolderHaveAStopCode")}'
    '<flowName>SubflowStopCodePrintCheck</flowName>'
    '<inputAssignments><name>varT_AccountId</name><value><elementReference>LoopThroughLicenses.AccountId</elementReference></value></inputAssignments>'
    '<storeOutputAutomatically>true</storeOutputAutomatically></subflows>')
F.decision('DoesTheHolderHaveAStopCode', 'Does the Holder Have a Stop Code?', [
    ('Held', 'Yes', [cond('CheckStopCodes.varB_HasOpenHold', 'EqualTo', BOOL(True))], 'AddHeld', 'and')], 'AddToMark')
F.assignment('AddHeld', 'Add Held License to Summary', [('varT_SkippedText', 'Add', REF('forT_HeldLine'))], 'LoopThroughLicenses')
F.assignment('AddToMark', 'Add License to Mark', [
    ('varR_License.Id', 'Assign', REF('LoopThroughLicenses.Id')),
    ('varR_License.PrintedDate__c', 'Assign', REF('$Flow.CurrentDate')),
    ('varR_ToMark', 'Add', REF('varR_License')),
    ('varN_Printed', 'Add', NUM(1)),
], 'LoopThroughLicenses')
F.decision('AnyToMark', 'Are There Licenses to Mark?', [('Some', 'Yes', [cond('varN_Printed', 'GreaterThan', NUM(0))], 'MarkPrinted', 'and')], 'Done')
els['recordUpdates'].append(
    f'<recordUpdates><name>MarkPrinted</name><label>Set Printed Date to Today</label>{loc()}{conn("Done")}{conn("CouldNotMarkPrinted", "faultConnector")}'
    '<inputReference>varR_ToMark</inputReference></recordUpdates>')
F.screen('Done', 'Done', [
    F.display('DN_Message', '<p><b>{!varN_Printed}</b> of {!varN_Selected} licenses marked printed today.</p>'),
    '<fields><name>DN_Skipped</name><fieldText>&lt;p&gt;Not marked:&lt;/p&gt;&lt;ul&gt;{!varT_SkippedText}&lt;/ul&gt;</fieldText><fieldType>DisplayText</fieldType>'
    '<visibilityRule><conditionLogic>and</conditionLogic><conditions><leftValueReference>varT_SkippedText</leftValueReference><operator>IsNull</operator>'
    '<rightValue><booleanValue>false</booleanValue></rightValue></conditions></visibilityRule></fields>',
], None, next_label='Done')
F.screen('NothingSelected', 'Nothing Selected', [
    F.display('NS_Message', '<p>No licenses were selected. Tick the licenses you printed in the list, then click Mark Printed.</p>')], None, next_label='Done')
F.screen('CouldNotMarkPrinted', 'Could Not Mark Printed', [
    F.display('CNMP_Message', '<p>The licenses could not be marked printed, and nothing changed.</p><p>{!$Flow.FaultMessage}</p>')], None)

desc = ('Marks licenses as printed, from the Mark Printed button on the Licenses Ready to Print list view. For each ticked license that is waiting to print, '
        'the holder is checked with Subflow: Stop Code Print Check; if the holder has an active stop code the license is not marked and stays in the list. '
        'The rest get today as their Printed Date, which takes them off the list. The summary lists every license not marked and why.')
label = 'Screen Flow: Business License Mark Printed'
head = '<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>66.0</apiVersion>'
body = ''.join(els['assignments']) + ''.join(els['decisions']) + f'<description>{e(desc)}</description><environments>Default</environments>' + ''.join(els['formulas'])
body += f'<interviewLabel>{label} {{!$Flow.CurrentDateTime}}</interviewLabel><label>{label}</label>' + ''.join(els['loops'])
for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
    body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
body += '<processType>Flow</processType>' + ''.join(els['recordLookups']) + ''.join(els['recordUpdates'])
body += '<runInMode>DefaultMode</runInMode>' + ''.join(els['screens'])
body += f'<start>{loc()}{conn("CountSelected")}</start><status>Active</status>' + ''.join(els['subflows']) + ''.join(els['variables']) + '</Flow>\n'
open(sys.argv[1] + '/ScreenFlowBusinessLicenseMarkPrinted.flow-meta.xml', 'w').write(head + body)
print('written')
