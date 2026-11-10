"""Generates ScreenFlowRecordAlertEndStopCode.flow-meta.xml. Usage: python3 -I endstop.py <flows dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flowlib as F

els = F.els
els['recordUpdates'] = []
e, val, conn, loc = F.e, F.val, F.conn, F.loc
REF, STR, BOOL, cond = F.REF, F.STR, F.BOOL, F.cond


def update(name, label, idref, objname, assigns, nxt, fault):
    x = f'<recordUpdates><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}{conn(fault, "faultConnector")}'
    x += f'<filterLogic>and</filterLogic><filters><field>Id</field><operator>EqualTo</operator><value><elementReference>{idref}</elementReference></value></filters>'
    for f, v in assigns:
        x += f'<inputAssignments><field>{f}</field><value>{val(v)}</value></inputAssignments>'
    els['recordUpdates'].append(x + f'<object>{objname}</object></recordUpdates>')


F.var('recordId', 'String', 'The stop code (Record Alert) being ended. Named recordId because the quick action passes the record under that name.', inp=True)

F.formula('forT_NewName', 'String',
          'IF(CONTAINS(" " & {!GetStopCode.Description}, "New name:"), TRIM(MID({!GetStopCode.Description}, FIND("New name:", {!GetStopCode.Description}) + 9, 255)), "")',
          'The new name the licensee reported on the portal renewal, from the stop code description ("New name: First Last").')
formula_first = 'IF(CONTAINS({!forT_NewName}, " "), LEFT({!forT_NewName}, FIND(" ", {!forT_NewName}) - 1), {!forT_NewName})'
F.formula('forT_NewFirstName', 'String', formula_first, 'The first word of the reported new name, offered as the first name.')
F.formula('forT_NewLastName', 'String', 'IF(CONTAINS({!forT_NewName}, " "), TRIM(MID({!forT_NewName}, FIND(" ", {!forT_NewName}) + 1, 255)), "")',
          'The rest of the reported new name, offered as the last name.')
F.formula('forDT_EndAt', 'DateTime', 'IF({!GetStopCode.EffectiveDate} > NOW(), {!GetStopCode.EffectiveDate}, NOW())',
          'When the stop code ends: now, or its start if that is still in the future (an end can\'t come before the start).')

F.lookup('GetStopCode', 'Get Stop Code', 'RecordAlert', [('Id', 'EqualTo', REF('recordId'))],
         ['Id', 'Subject', 'Description', 'IsActive', 'WhatId', 'EffectiveDate', 'RecordAlertCategoryId'], 'IsItActive', first=True, sort=None)
F.decision('IsItActive', 'Is the Stop Code Active?', [('Active', 'Yes', [cond('GetStopCode.IsActive', 'EqualTo', BOOL(True))], 'GetNameChangeCategory', 'and')], 'AlreadyEnded')
F.lookup('GetNameChangeCategory', 'Get Name Change Category', 'RecordAlertCategory', [('DeveloperName', 'EqualTo', STR('NameChangeProofPending'))],
         ['Id'], 'IsItANameChange', first=True, sort=None)
F.decision('IsItANameChange', 'Is It a Name Change?', [
    ('NameChange', 'Yes', [cond('GetStopCode.RecordAlertCategoryId', 'EqualTo', REF('GetNameChangeCategory.Id'))], 'GetPerson', 'and')], 'ConfirmEnd')
F.lookup('GetPerson', 'Get Person', 'Account', [('Id', 'EqualTo', REF('GetStopCode.WhatId'))],
         ['Id', 'Name', 'FirstName', 'LastName', 'IsPersonAccount'], 'ConfirmNameChange', first=True, sort=None)

F.screen('ConfirmNameChange', 'Confirm Name Change', [
    F.display('CNC_Intro', '<p><b>{!GetStopCode.Subject}</b> on {!GetPerson.Name}.</p><p>{!GetStopCode.Description}</p>'
              '<p>End this stop code once proof of the new name is accepted. Check the name below against the proof; it replaces the name on the person and on their licenses when they are next printed.</p>'),
    F.inp('CNC_FirstName', 'String', 'New first name', required=True, default=REF('forT_NewFirstName')),
    F.inp('CNC_LastName', 'String', 'New last name', required=True, default=REF('forT_NewLastName')),
], 'UpdateName', next_label='Change Name and End Stop Code')
update('UpdateName', 'Set Person Name', 'GetPerson.Id', 'Account', [
    ('FirstName', REF('CNC_FirstName')), ('LastName', REF('CNC_LastName'))], 'EndStopCode', 'CouldNotEndStopCode')

F.screen('ConfirmEnd', 'Confirm End', [
    F.display('CE_Intro', '<p><b>{!GetStopCode.Subject}</b></p><p>{!GetStopCode.Description}</p>'
              '<p>Ending the stop code lets the holder\'s licenses print again. If the system set it (for example for an unpaid fee or an expired exam), '
              'it is set again at the next check unless its cause is fixed.</p>'),
], 'EndStopCode', next_label='End Stop Code')
update('EndStopCode', 'End Stop Code', 'recordId', 'RecordAlert', [
    ('IsActive', BOOL(False)), ('ValidUntilDate', REF('forDT_EndAt'))], 'Ended', 'CouldNotEndStopCode')
F.screen('Ended', 'Ended', [F.display('EN_Message', '<p><b>The stop code is ended.</b></p>')], None, next_label='Done')
F.screen('AlreadyEnded', 'Already Ended', [F.display('AE_Message', '<p>This stop code has already ended.</p>')], None, next_label='Done')
F.screen('CouldNotEndStopCode', 'Could Not End Stop Code', [
    F.display('CNESC_Message', '<p>The stop code could not be ended, and nothing changed.</p><p>{!$Flow.FaultMessage}</p>')], None)

desc = ('Ends a stop code (Record Alert), from the End Stop Code action: it is made inactive with today as its end date. For Name Change Proof Pending, '
        'staff first confirm the new name the licensee reported on the portal renewal (read from the stop code description and offered as first and last name), '
        'and the person\'s name is changed. Ending a stop code the system set automatically only lasts until the next check if its cause is not fixed.')
label = 'Screen Flow: Record Alert End Stop Code'
head = '<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>66.0</apiVersion>'
body = ''.join(els['decisions']) + f'<description>{e(desc)}</description><environments>Default</environments>' + ''.join(els['formulas'])
body += f'<interviewLabel>{label} {{!$Flow.CurrentDateTime}}</interviewLabel><label>{label}</label>'
for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
    body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
body += '<processType>Flow</processType>' + ''.join(els['recordLookups']) + ''.join(els['recordUpdates'])
body += '<runInMode>DefaultMode</runInMode>' + ''.join(els['screens'])
body += f'<start>{loc()}{conn("GetStopCode")}</start><status>Active</status>' + ''.join(els['variables']) + '</Flow>\n'
open(sys.argv[1] + '/ScreenFlowRecordAlertEndStopCode.flow-meta.xml', 'w').write(head + body)
print('written')
