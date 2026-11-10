"""Generates ScreenFlowAccountNewApplication.flow-meta.xml. Usage: python3 -I newapp.py <flows dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flowlib as F

els = F.els
els['subflows'] = []
e, conn, loc = F.e, F.conn, F.loc
STR, cond = F.STR, F.cond

FORMS = [
    ('Renewal', 'License Renewal (renewal or duplicate)', 'ScreenFlowIndividualApplicationRenewal'),
    ('Reciprocity', 'Reciprocity Application', 'ScreenFlowIndividualApplicationReciprocity'),
    ('Retake', 'Retake Exam Application', 'ScreenFlowIndividualApplicationRetake'),
    ('TemporaryPermit', 'Temporary Permit Application', 'ScreenFlowIndividualApplicationTemporaryPermit'),
    ('ThreadingPermit', 'Threading Permit Application', 'ScreenFlowIndividualApplicationThreadingPermit'),
    ('Affidavit', 'Affidavit Request', 'ScreenFlowIndividualApplicationAffidavit'),
    ('Shop', 'Shop Application (salon, booth rental and others)', 'ScreenFlowBusinessLicenseApplicationShop'),
    ('Facility', 'Facility Application (alternative hair design or threading)', 'ScreenFlowBusinessLicenseApplicationFacility'),
    ('School', 'New School Application', 'ScreenFlowBusinessLicenseApplicationSchool'),
]

F.var('recordId', 'String', 'The applicant\'s Person Account. Named recordId because the quick action passes the record under that name.', inp=True)
for key, text, _ in FORMS:
    els['choices'].append(f'<choices><name>choice_{key}</name><choiceText>{e(text)}</choiceText><dataType>String</dataType><value><stringValue>{key}</stringValue></value></choices>')

F.lookup('GetApplicant', 'Get Applicant', 'Account', [('Id', 'EqualTo', F.REF('recordId'))], ['Id', 'Name', 'IsPersonAccount'], 'IsItAPerson', first=True, sort=None)
F.decision('IsItAPerson', 'Is the Account a Person?', [('Person', 'Yes', [cond('GetApplicant.IsPersonAccount', 'EqualTo', F.BOOL(True))], 'ChooseForm', 'and')], 'NotAPerson')
F.screen('ChooseForm', 'Choose Form', [
    F.display('CF_Intro', '<p>Enter a paper application for <b>{!GetApplicant.Name}</b>. Choose the form that matches the paper application. '
              'Shop, facility and school applications are entered on the owner\'s or director\'s person account.</p>'
              '<p>Copy the answers from the paper form. On the certification step, tick it and type the name as the applicant signed it. '
              'At the pay step, record the payment afterwards with Record Payment.</p>'),
    '<fields><name>CF_Form</name>' + ''.join(f'<choiceReferences>choice_{k}</choiceReferences>' for k, _, _ in FORMS) +
    '<dataType>String</dataType><fieldText>Form</fieldText><fieldType>RadioButtons</fieldType><isRequired>true</isRequired></fields>',
], 'WhichForm', next_label='Start Form')
first = FORMS[0]
F.decision('WhichForm', 'Which Form?', [(k, t.split(' (')[0], [cond('CF_Form', 'EqualTo', STR(k))], f'Run{k}', 'and') for k, t, _ in FORMS[1:]], f'Run{first[0]}', default_label=first[1].split(' (')[0])
for key, text, flow in FORMS:
    els['subflows'].append(
        f'<subflows><name>Run{key}</name><label>Run {e(text.split(" (")[0])}</label>{loc()}<flowName>{flow}</flowName>'
        '<inputAssignments><name>recordId</name><value><elementReference>recordId</elementReference></value></inputAssignments></subflows>')
F.screen('NotAPerson', 'Not a Person', [
    F.display('NAP_Message', '<p>Applications are entered on the applicant\'s person account. For a shop, facility or school, open the owner\'s or director\'s person account and use New Application there.</p>')], None, next_label='Done')

desc = ('Lets staff enter a paper application for a person, from New Application on the Person Account. Staff choose one of the nine portal forms, '
        'which opens with that person as the applicant (its recordId input); the form saves the application, its checklist and fees exactly as on the portal, '
        'and its pay step tells staff to record the payment with Record Payment. Shop, facility and school forms are entered on the owner\'s or director\'s person account.')
label = 'Screen Flow: Account New Application'
head = '<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>66.0</apiVersion>'
body = ''.join(els['choices']) + ''.join(els['decisions']) + f'<description>{e(desc)}</description><environments>Default</environments>'
body += f'<interviewLabel>{label} {{!$Flow.CurrentDateTime}}</interviewLabel><label>{label}</label>'
for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
    body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
body += '<processType>Flow</processType>' + ''.join(els['recordLookups']) + '<runInMode>DefaultMode</runInMode>' + ''.join(els['screens'])
body += f'<start>{loc()}{conn("GetApplicant")}</start><status>Active</status>' + ''.join(els['subflows']) + ''.join(els['variables']) + '</Flow>\n'
open(sys.argv[1] + '/ScreenFlowAccountNewApplication.flow-meta.xml', 'w').write(head + body)
print('written')
