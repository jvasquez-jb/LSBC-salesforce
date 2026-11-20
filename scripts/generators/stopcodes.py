"""Generates ScreenFlowAccountStopCodes.flow-meta.xml. Usage: python3 -I stopcodes.py <flows dir>

A read-only list of an account's stop codes (Record Alerts on the holder through WhatId), open ones first, for the
Stop Codes tab of the person and business account page. The OmniStudio alert card there needs an OmniStudio seat that
only administrators have, so desk staff see their stop codes through this flow. It runs as the user: a desk that can't
read stop codes (no Record Alert access) gets a plain message instead of an error."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flowlib as F

els = F.els
e, conn, loc = F.e, F.conn, F.loc
REF, NUM = F.REF, F.NUM
els['textTemplates'] = []

FIELDS = ['Id', 'Subject', 'Description', 'EffectiveDate', 'ValidUntilDate', 'IsActive']


def lookup(name, label, desc, active, sort, nxt, fault):
    """Get Records with a fault path and a newest-first sort (flowlib's lookup has neither)."""
    x = (f'<recordLookups><name>{name}</name><description>{e(desc)}</description><label>{e(label)}</label>{loc()}'
         f'<assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>{conn(nxt)}{conn(fault, "faultConnector")}'
         '<filterLogic>and</filterLogic>'
         f'<filters><field>WhatId</field><operator>EqualTo</operator><value>{F.val(REF("recordId"))}</value></filters>'
         f'<filters><field>IsActive</field><operator>EqualTo</operator><value>{F.val(F.BOOL(active))}</value></filters>'
         '<getFirstRecordOnly>false</getFirstRecordOnly><object>RecordAlert</object>'
         + ''.join(f'<queriedFields>{f}</queriedFields>' for f in FIELDS)
         + f'<sortField>{sort}</sortField><sortOrder>Desc</sortOrder><storeOutputAutomatically>true</storeOutputAutomatically></recordLookups>')
    els['recordLookups'].append(x)


def template(name, desc, html):
    els['textTemplates'].append(f'<textTemplates><name>{name}</name><description>{e(desc)}</description>'
                                f'<isViewedAsPlainText>false</isViewedAsPlainText><text>{e(html)}</text></textTemplates>')


F.var('recordId', 'String', 'The person or business account the page shows. Named recordId because the Lightning page passes the record under that name.', inp=True)
F.var('varT_OpenRows', 'String', 'One table row per open stop code, built in the loop.')
F.var('varT_EndedRows', 'String', 'One table row per ended stop code, built in the loop.')
F.var('varN_OpenCount', 'Number', 'How many open stop codes the account has.', default=NUM(0), scale=0)
F.var('varN_EndedCount', 'Number', 'How many ended stop codes the account has.', default=NUM(0), scale=0)

CELL = '<td style="padding:4px 8px;vertical-align:top;border-top:1px solid #e5e5e5">'
template('textT_OpenRow', 'One open stop code as a table row: code, description and start date.',
         f'<tr>{CELL}<b>{{!LoopThroughOpenStopCodes.Subject}}</b></td>{CELL}{{!LoopThroughOpenStopCodes.Description}}</td>'
         f'{CELL}{{!forT_OpenStart}}</td></tr>')
template('textT_EndedRow', 'One ended stop code as a table row: code, description, start date and end date.',
         f'<tr>{CELL}{{!LoopThroughEndedStopCodes.Subject}}</td>{CELL}{{!LoopThroughEndedStopCodes.Description}}</td>'
         f'{CELL}{{!forT_EndedStart}}</td>{CELL}{{!forT_EndedEnd}}</td></tr>')

# DATEVALUE gives the date in the user's own time zone (Louisiana for staff), so an evening end shows that day's date.
def local_date(ref):
    return f'TEXT(MONTH(DATEVALUE({ref}))) & "/" & TEXT(DAY(DATEVALUE({ref}))) & "/" & TEXT(YEAR(DATEVALUE({ref})))'


F.formula('forT_OpenStart', 'String', local_date('{!LoopThroughOpenStopCodes.EffectiveDate}'),
          'The open stop code\'s start date (month/day/year, in the user\'s time zone).')
F.formula('forT_EndedStart', 'String', local_date('{!LoopThroughEndedStopCodes.EffectiveDate}'),
          'The ended stop code\'s start date (month/day/year, in the user\'s time zone).')
F.formula('forT_EndedEnd', 'String',
          'IF(YEAR(DATEVALUE({!LoopThroughEndedStopCodes.ValidUntilDate})) >= 4000, "", '
          + local_date('{!LoopThroughEndedStopCodes.ValidUntilDate}') + ')',
          'The date the stop code ended (month/day/year, in the user\'s time zone). Blank when it was ended without a date (12/31/4000).')
TABLE = "<table style='width:100%;border-collapse:collapse'><tr>"
TH = "<th style='padding:4px 8px;text-align:left'>"
F.formula('forT_Display', 'String',
          'IF({!varN_OpenCount} = 0 && {!varN_EndedCount} = 0, "<p>No stop codes on this record.</p>", '
          '"<p><b>Open stop codes (" & TEXT({!varN_OpenCount}) & ")</b></p>" & '
          'IF({!varN_OpenCount} = 0, "<p>None.</p>", '
          f'"{TABLE}{TH}Code</th>{TH}Description</th>{TH}Start date</th></tr>" & {{!varT_OpenRows}} & "</table>") & '
          'IF({!varN_EndedCount} = 0, "", "<p>&nbsp;</p><p><b>Ended stop codes (" & TEXT({!varN_EndedCount}) & ")</b></p>'
          f'{TABLE}{TH}Code</th>{TH}Description</th>{TH}Start date</th>{TH}End date</th></tr>" & {{!varT_EndedRows}} & "</table>"))',
          'The two tables shown on the page (open stop codes first, then ended ones), or a note when the account has none.')

lookup('GetOpenStopCodes', 'Get Open Stop Codes', 'The account\'s open stop codes, newest first. Runs as the user: a user who can\'t read stop codes goes to the no-access message.',
       True, 'EffectiveDate', 'LoopThroughOpenStopCodes', 'ShowNoAccess')
F.loop('LoopThroughOpenStopCodes', 'Loop Through Open Stop Codes', 'GetOpenStopCodes', 'AddOpenRow', 'GetEndedStopCodes')
F.assignment('AddOpenRow', 'Add Open Row', [('varT_OpenRows', 'Add', REF('textT_OpenRow')), ('varN_OpenCount', 'Add', NUM(1))],
             'LoopThroughOpenStopCodes')
lookup('GetEndedStopCodes', 'Get Ended Stop Codes', 'The account\'s ended stop codes, most recently ended first.',
       False, 'ValidUntilDate', 'LoopThroughEndedStopCodes', 'ShowNoAccess')
F.loop('LoopThroughEndedStopCodes', 'Loop Through Ended Stop Codes', 'GetEndedStopCodes', 'AddEndedRow', 'ShowStopCodes')
F.assignment('AddEndedRow', 'Add Ended Row', [('varT_EndedRows', 'Add', REF('textT_EndedRow')), ('varN_EndedCount', 'Add', NUM(1))],
             'LoopThroughEndedStopCodes')


def show(name, label, html):
    els['screens'].append(
        f'<screens><name>{name}</name><label>{label}</label>{loc()}<allowBack>false</allowBack><allowFinish>true</allowFinish>'
        '<allowPause>false</allowPause>' + F.display(name.replace('Show', 'SSC_'), html)
        + '<showFooter>false</showFooter><showHeader>false</showHeader></screens>')


show('ShowStopCodes', 'Show Stop Codes', '{!forT_Display}')
show('ShowNoAccess', 'Show No Access', '<p>Your desk doesn\'t have access to stop codes. Ask a supervisor if you need to check one.</p>')

desc = ('Read-only list of an account\'s stop codes, open ones first, on the Stop Codes tab of the person and business account page. '
        'Runs as the user, so a desk that can\'t read stop codes sees a short message instead of an error. '
        'Stop codes are added and ended with Add Stop Code and End Stop Code, not here.')
label = 'Screen Flow: Account Stop Codes'
head = '<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>66.0</apiVersion>'
body = ''.join(els['assignments']) + f'<description>{e(desc)}</description><environments>Default</environments>' + ''.join(els['formulas'])
body += f'<interviewLabel>{label} {{!$Flow.CurrentDateTime}}</interviewLabel><label>{label}</label>' + ''.join(els['loops'])
for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
    body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
body += '<processType>Flow</processType>' + ''.join(els['recordLookups'])
body += '<runInMode>DefaultMode</runInMode>' + ''.join(els['screens'])
body += f'<start>{loc()}{conn("GetOpenStopCodes")}</start><status>Active</status>' + ''.join(els['textTemplates'])
body += ''.join(els['variables']) + '</Flow>\n'
open(sys.argv[1] + '/ScreenFlowAccountStopCodes.flow-meta.xml', 'w').write(head + body)
print('written')
