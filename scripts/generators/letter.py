"""Generates ScreenFlowLetterGenerate.flow-meta.xml. Usage: python3 -I letter.py <flows dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flowlib import *  # noqa
from flowlib import els, e, conn, loc

var('recordId', 'String', 'The account or application the letter is for. Named recordId because the quick action passes the record under that name.', inp=True)
var('varT_ObjectName', 'String', 'The record\'s object, used to offer only the letters that apply to it.')

formula('forT_ObjectName', 'String',
        'CASE(LEFT({!recordId}, 3), "001", "Account", "0iT", "IndividualApplication", "0f0", "BusinessLicenseApplication", "")',
        'The object the record belongs to, from the first three characters of its Id (fixed for these standard objects).')

assignment('SetObjectName', 'Set Object Name', [('varT_ObjectName', 'Assign', REF('forT_ObjectName'))], 'ChooseLetter')

els['dynamicChoiceSets'].append(
    '<dynamicChoiceSets><name>choice_Template</name><dataType>String</dataType><displayField>MasterLabel</displayField>'
    '<filterLogic>and</filterLogic><filters><field>AppliesTo__c</field><operator>Contains</operator><value><elementReference>varT_ObjectName</elementReference></value></filters>'
    '<object>LetterTemplate__mdt</object><sortField>MasterLabel</sortField><sortOrder>Asc</sortOrder><valueField>DeveloperName</valueField></dynamicChoiceSets>')

screen('ChooseLetter', 'Choose Letter', [
    display('CL_Intro', '<p>Choose a letter. It is saved as a PDF in this record\'s Files, ready to print or email.</p>'),
    '<fields><name>CL_Template</name><choiceReferences>choice_Template</choiceReferences><dataType>String</dataType>'
    '<fieldText>Letter</fieldText><fieldType>RadioButtons</fieldType><isRequired>true</isRequired></fields>',
    '<fields><name>CL_Details</name><dataType>String</dataType><fieldText>Details for the letter</fieldText><fieldType>LargeTextArea</fieldType>'
    '<helpText>Printed where the letter says {{Details}}: for example, the check number and amount of a returned payment, or a note about what to send. Leave blank if there is nothing to add.</helpText>'
    '<isRequired>false</isRequired></fields>',
], 'SaveLetter', next_label='Save Letter')

els['actionCalls'] = [
    '<actionCalls><name>SaveLetter</name><label>Save Letter PDF</label>' + loc() +
    '<actionName>LetterPdfSaveAction</actionName><actionType>apex</actionType>' + conn('LetterSaved') + conn('CouldNotSaveLetter', 'faultConnector') +
    '<flowTransactionModel>CurrentTransaction</flowTransactionModel>'
    '<inputParameters><name>details</name><value><elementReference>CL_Details</elementReference></value></inputParameters>'
    '<inputParameters><name>recordId</name><value><elementReference>recordId</elementReference></value></inputParameters>'
    '<inputParameters><name>templateName</name><value><elementReference>CL_Template</elementReference></value></inputParameters>'
    '<storeOutputAutomatically>true</storeOutputAutomatically></actionCalls>'
]

screen('LetterSaved', 'Letter Saved', [
    display('LS_Message', '<p><b>The letter is saved.</b></p><p>{!SaveLetter.title} is in this record\'s Files. '
            '<a href="/lightning/r/ContentDocument/{!SaveLetter.contentDocumentId}/view" target="_blank">Open the letter</a> to print or download it.</p>'),
], None, next_label='Done')
screen('CouldNotSaveLetter', 'Could Not Save Letter', [
    display('CNSL_Message', '<p>The letter could not be created.</p><p>{!$Flow.FaultMessage}</p>'),
], None)

desc = ('Creates a letter from a Letter Template and saves it as a PDF in the record\'s Files, from the Generate Letter action on an account or an '
        'application. Staff choose one of the letters that apply to the record and can type details for it. The wording is in the Letter Template '
        'custom metadata; the PDF is laid out by the LetterPdf page and saved by the Save Letter PDF action.')

head = ('<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata">'
        '<apiVersion>66.0</apiVersion>')
body = ''.join(els['actionCalls']) + ''.join(els['assignments']) + f'<description>{e(desc)}</description>' + ''.join(els['dynamicChoiceSets'])
body += '<environments>Default</environments>' + ''.join(els['formulas'])
body += '<interviewLabel>Screen Flow: Letter Generate {!$Flow.CurrentDateTime}</interviewLabel><label>Screen Flow: Letter Generate</label>'
for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
    body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
body += '<processType>Flow</processType><runInMode>DefaultMode</runInMode>' + ''.join(els['screens'])
body += f'<start>{loc()}{conn("SetObjectName")}</start><status>Active</status>' + ''.join(els['variables']) + '</Flow>\n'
open(sys.argv[1] + '/ScreenFlowLetterGenerate.flow-meta.xml', 'w').write(head + body)
print('written')
