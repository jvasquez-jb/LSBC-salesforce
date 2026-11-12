"""Generates ScreenFlowAccountPersonLanguages.flow-meta.xml. Usage: python3 -I languages.py <flows dir>

Person Language can't be a related list (on a layout or a Lightning page) for Account or Individual,
so the person account page shows the person's languages through this read-only flow instead."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flowlib as F

els = F.els
e, conn, loc = F.e, F.conn, F.loc
REF = F.REF

F.var('recordId', 'String', 'The person account the page shows. Named recordId because the Lightning page passes the record under that name.', inp=True)
F.var('varT_LanguageList', 'String', 'One list item per language, built in the loop.')

F.formula('forT_LanguageLine', 'String',
          '"<li>" & TEXT({!LoopThroughPersonLanguages.Language})'
          ' & IF(ISBLANK(TEXT({!LoopThroughPersonLanguages.SpeakingProficiencyLevel})), "", ", speaking " & TEXT({!LoopThroughPersonLanguages.SpeakingProficiencyLevel}))'
          ' & IF(ISBLANK(TEXT({!LoopThroughPersonLanguages.WritingProficiencyLevel})), "", ", writing " & TEXT({!LoopThroughPersonLanguages.WritingProficiencyLevel}))'
          ' & "</li>"',
          'One language as a list item, with its speaking and writing levels when they are recorded.')
F.formula('forT_Display', 'String',
          'IF(ISBLANK({!varT_LanguageList}), "<p>No languages recorded.</p>", "<ul>" & {!varT_LanguageList} & "</ul>")',
          'The list shown on the page, or a note when the person has no languages.')

F.lookup('GetPerson', 'Get Person', 'Account', [('Id', 'EqualTo', REF('recordId'))],
         ['Id', 'PersonIndividualId'], 'GetPersonLanguages', first=True, sort=None)
F.lookup('GetPersonLanguages', 'Get Person Languages', 'PersonLanguage', [('IndividualId', 'EqualTo', REF('GetPerson.PersonIndividualId'))],
         ['Id', 'Language', 'SpeakingProficiencyLevel', 'WritingProficiencyLevel'], 'LoopThroughPersonLanguages', sort='Language')
F.loop('LoopThroughPersonLanguages', 'Loop Through Person Languages', 'GetPersonLanguages', 'AddLanguageLine', 'ShowLanguages')
F.assignment('AddLanguageLine', 'Add Language Line', [('varT_LanguageList', 'Add', REF('forT_LanguageLine'))], 'LoopThroughPersonLanguages')

els['screens'].append(
    f'<screens><name>ShowLanguages</name><label>Show Languages</label>{loc()}<allowBack>false</allowBack><allowFinish>true</allowFinish>'
    '<allowPause>false</allowPause>'
    + F.display('SL_Languages', '<p><b>Languages</b></p>{!forT_Display}')
    + '<showFooter>false</showFooter><showHeader>false</showHeader></screens>')

desc = ('Read-only list of the languages a person speaks, shown on the person account page (Exams and Accommodations tab). '
        "Portal forms save languages on the person's Individual record, and Person Language can't be a related list, so this flow reads them.")
label = 'Screen Flow: Account Person Languages'
head = '<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>66.0</apiVersion>'
body = ''.join(els['assignments']) + f'<description>{e(desc)}</description><environments>Default</environments>' + ''.join(els['formulas'])
body += f'<interviewLabel>{label} {{!$Flow.CurrentDateTime}}</interviewLabel><label>{label}</label>' + ''.join(els['loops'])
for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
    body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
body += '<processType>Flow</processType>' + ''.join(els['recordLookups'])
body += '<runInMode>DefaultMode</runInMode>' + ''.join(els['screens'])
body += f'<start>{loc()}{conn("GetPerson")}</start><status>Active</status>' + ''.join(els['variables']) + '</Flow>\n'
open(sys.argv[1] + '/ScreenFlowAccountPersonLanguages.flow-meta.xml', 'w').write(head + body)
print('written')
