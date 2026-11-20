"""Generates ScreenFlowPaymentRefund.flow-meta.xml. Usage: python3 -I refund.py <flows dir>"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flowlib import *  # noqa
from flowlib import els, e, val, conn, loc

els['recordUpdates'] = []


def update(name, label, assigns, nxt, fault):
    x = f'<recordUpdates><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}{conn(fault, "faultConnector")}'
    x += '<filterLogic>and</filterLogic><filters><field>Id</field><operator>EqualTo</operator><value><elementReference>recordId</elementReference></value></filters>'
    for f, v in assigns:
        x += f'<inputAssignments><field>{f}</field><value>{val(v)}</value></inputAssignments>'
    els['recordUpdates'].append(x + '<object>Payment__c</object></recordUpdates>')


def choice(name, text, value):
    els['choices'].append(f'<choices><name>{name}</name><choiceText>{e(text)}</choiceText><dataType>String</dataType><value><stringValue>{e(value)}</stringValue></value></choices>')


def radio(name, label, choices):
    refs = ''.join(f'<choiceReferences>{c}</choiceReferences>' for c in choices)
    return f'<fields><name>{name}</name>{refs}<dataType>String</dataType><fieldText>{e(label)}</fieldText><fieldType>RadioButtons</fieldType><isRequired>true</isRequired></fields>'


var('recordId', 'String', 'The payment being refunded. Named recordId because the quick action passes the record under that name.', inp=True)
var('varT_Blank', 'String', 'Left empty; used to clear a text or picklist field.')
var('varD_Blank', 'Date', 'Left empty; used to clear a date.')
var('varC_Blank', 'Currency', 'Left empty; used to clear an amount.', scale=2)

choice('choice_Verify', 'Verify the refund', 'Verify')
choice('choice_Cancel', 'Cancel the request', 'Cancel')

formula('forC_Refundable', 'Currency', '{!GetPayment.Amount__c} - BLANKVALUE({!GetPayment.AppliedAmount__c}, 0)',
        'What can be refunded: the payment less what is applied to fees.', scale=2)

formula('forC_Amount', 'Currency', '{!GetPayment.Amount__c}', 'The payment amount, shown as money.', scale=2)
formula('forC_RefundAmount', 'Currency', '{!GetPayment.RefundAmount__c}', 'The refund amount, shown as money.', scale=2)
formula('forT_StatusAfterRefund', 'String', 'IF({!GetPayment.RefundAmount__c} >= {!GetPayment.Amount__c}, "Refunded", TEXT({!GetPayment.Status__c}))',
        'The payment status once the refund is entered: Refunded only when the whole payment was refunded; after a partial refund the payment keeps its status, because part of it still stands.')

# $User.Id can come as the 15-character Id while the lookup holds 18, so a plain "equals" never matched and the
# validation rule's raw error showed instead: compare the first 15 characters.
formula('forB_IsTheRequester', 'Boolean', 'LEFT({!GetPayment.RefundRequestedByUser__c}, 15) = LEFT({!$User.Id}, 15)',
        'True when the person running the flow requested this refund (they may not verify it).')

lookup('GetPayment', 'Get Payment', 'Payment__c', [('Id', 'EqualTo', REF('recordId'))],
       ['Id', 'Name', 'Amount__c', 'AppliedAmount__c', 'Status__c', 'RefundStatus__c', 'RefundAmount__c',
        'RefundRequestedBy__c', 'RefundRequestedByUser__c', 'RefundRequestedDate__c', 'RefundVerifiedDate__c', 'RefundCheckNumber__c',
        'RefundedDate__c'],
       'WhatStepIsTheRefundAt', first=True, sort=None)

decision('WhatStepIsTheRefundAt', 'What Step Is the Refund At?', [
    ('Requested', 'Requested', [cond('GetPayment.RefundStatus__c', 'EqualTo', STR('Requested'))], 'VerifyRefund', 'and'),
    ('Verified', 'Verified', [cond('GetPayment.RefundStatus__c', 'EqualTo', STR('Verified'))], 'EnterRefund', 'and'),
    ('Refunded', 'Refunded', [cond('GetPayment.RefundStatus__c', 'EqualTo', STR('Refunded'))], 'AlreadyRefunded', 'and'),
], 'CanThePaymentBeRefunded', default_label='Not Started')

decision('CanThePaymentBeRefunded', 'Can the Payment Be Refunded?', [
    ('Returned', 'Returned', [cond('GetPayment.Status__c', 'EqualTo', STR('Returned'))], 'CannotRefundReturned', 'and'),
    ('NothingLeft', 'Nothing Unapplied', [cond('forC_Refundable', 'LessThanOrEqualTo', NUM(0))], 'NothingToRefund', 'and'),
], 'RequestRefund', default_label='Yes')

screen('RequestRefund', 'Request Refund', [
    display('RR_Intro', '<p>Payment {!GetPayment.Name}: <b>{!forC_Amount}</b>, of which <b>{!forC_Refundable}</b> is not applied to any fee and can be refunded.</p><p>The front desk verifies the request, then enters the refund once the check is issued.</p>'),
    inp('RR_Amount', 'Currency', 'Refund amount', required=True, scale=2, default=REF('forC_Refundable'),
        rule=("The refund must be more than zero and can't be more than the unapplied amount.",
              '{!RR_Amount} > 0 && {!RR_Amount} <= {!forC_Refundable}')),
    inp('RR_Department', 'String', 'Requested by (department)', required=True,
        help='The department asking for the refund, for example Front Desk or Renewals.'),
], 'SaveRequest', next_label='Request Refund')
update('SaveRequest', 'Set Refund to Requested', [
    ('RefundAmount__c', REF('RR_Amount')),
    ('RefundRequestedBy__c', REF('RR_Department')),
    ('RefundRequestedByUser__c', REF('$User.Id')),
    ('RefundRequestedDate__c', REF('$Flow.CurrentDate')),
    ('RefundStatus__c', STR('Requested')),
], None, 'CouldNotSaveRefund')

screen('VerifyRefund', 'Verify Refund', [
    display('VR_Request', '<p>Refund of <b>{!forC_RefundAmount}</b> from payment {!GetPayment.Name}, requested by {!GetPayment.RefundRequestedBy__c} on {!GetPayment.RefundRequestedDate__c}.</p><p>Check the signed request form, then verify it or cancel it.</p>'),
    radio('VR_Decision', 'Decision', ['choice_Verify', 'choice_Cancel']),
], 'VerifyOrCancel')
decision('VerifyOrCancel', 'Verify or Cancel?', [
    ('Verify', 'Verify', [cond('VR_Decision', 'EqualTo', STR('Verify'))], 'IsTheVerifierTheRequester', 'and'),
], 'CancelRequest', default_label='Cancel')
decision('IsTheVerifierTheRequester', 'Is the Verifier the Requester?', [
    ('SamePerson', 'Same Person', [cond('forB_IsTheRequester', 'EqualTo', BOOL(True))], 'VerifierIsRequester', 'and'),
], 'SaveVerified', default_label='Someone Else')
update('SaveVerified', 'Set Refund to Verified', [
    ('RefundStatus__c', STR('Verified')),
    ('RefundVerifiedBy__c', REF('$User.Id')),
    ('RefundVerifiedDate__c', REF('$Flow.CurrentDate')),
], None, 'CouldNotSaveRefund')
update('CancelRequest', 'Clear Refund Request', [
    ('RefundAmount__c', REF('varC_Blank')),
    ('RefundRequestedBy__c', REF('varT_Blank')),
    ('RefundRequestedByUser__c', REF('varT_Blank')),
    ('RefundRequestedDate__c', REF('varD_Blank')),
    ('RefundStatus__c', REF('varT_Blank')),
], None, 'CouldNotSaveRefund')

screen('EnterRefund', 'Enter Refund', [
    display('ER_Request', '<p>Refund of <b>{!forC_RefundAmount}</b> from payment {!GetPayment.Name}, verified on {!GetPayment.RefundVerifiedDate__c}.</p><p>Enter the check sent to the payer. The refund is then marked Refunded; the payment itself is marked Refunded only when all of it was refunded.</p>'),
    inp('ER_CheckNumber', 'String', 'Refund check number', required=True),
    inp('ER_RefundedDate', 'Date', 'Refunded date', required=True, default=REF('$Flow.CurrentDate'),
        rule=("The refunded date can't be in the future or before the refund was verified.",
              '{!ER_RefundedDate} <= TODAY() && {!ER_RefundedDate} >= {!GetPayment.RefundVerifiedDate__c}')),
], 'SaveRefunded', next_label='Save Refund')
update('SaveRefunded', 'Set Refund to Refunded', [
    ('RefundCheckNumber__c', REF('ER_CheckNumber')),
    ('RefundStatus__c', STR('Refunded')),
    ('RefundedDate__c', REF('ER_RefundedDate')),
    ('Status__c', REF('forT_StatusAfterRefund')),
], None, 'CouldNotSaveRefund')

screen('VerifierIsRequester', 'Someone Else Must Verify', [
    display('VIR_Message', '<p>You requested this refund, so someone else must verify it. Nothing changed.</p>'),
], None, next_label='Done')
screen('AlreadyRefunded', 'Already Refunded', [
    display('AR_Message', '<p>This refund is complete: <b>{!forC_RefundAmount}</b> was sent on check {!GetPayment.RefundCheckNumber__c} on {!GetPayment.RefundedDate__c}.</p>'),
], None, next_label='Done')
screen('NothingToRefund', 'Nothing to Refund', [
    display('NTR_Message', "<p>All of this payment is applied to fees, so there is nothing to refund. To refund money that is already applied, take it off the fee first.</p>"),
], None, next_label='Done')
screen('CannotRefundReturned', 'Cannot Refund a Returned Payment', [
    display('CRRP_Message', '<p>This payment was returned (for example, a bounced check), so there is no money to refund.</p>'),
], None, next_label='Done')
screen('CouldNotSaveRefund', 'Could Not Save Refund', [
    display('CNSR_Message', '<p>The refund could not be saved, and nothing changed.</p><p>{!$Flow.FaultMessage}</p>'),
], None)

desc = ('Moves a refund on a payment through its three steps, from the Refund action on the payment. With no refund yet, staff request one: '
        'the amount (up to what is not applied to fees) and the requesting department. A requested refund is verified, or cancelled, by someone other than the person who requested it. '
        'A verified refund is entered once the check is issued, with the check number and date; the payment then shows Refunded and its unapplied '
        'amount drops by the refund. A returned payment, or one fully applied to fees, cannot be refunded here.')

head = ('<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata">'
        '<apiVersion>66.0</apiVersion>')
body = ''.join(els['choices']) + ''.join(els['decisions']) + f'<description>{e(desc)}</description>'
body += '<environments>Default</environments>' + ''.join(els['formulas'])
body += '<interviewLabel>Screen Flow: Payment Refund {!$Flow.CurrentDateTime}</interviewLabel><label>Screen Flow: Payment Refund</label>'
for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
    body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
body += '<processType>Flow</processType>' + ''.join(els['recordLookups']) + ''.join(els['recordUpdates'])
body += '<runInMode>DefaultMode</runInMode>' + ''.join(els['screens'])
body += f'<start>{loc()}{conn("GetPayment")}</start><status>Active</status>' + ''.join(els['variables']) + '</Flow>\n'
open(sys.argv[1] + '/ScreenFlowPaymentRefund.flow-meta.xml', 'w').write(head + body)
print('written')
