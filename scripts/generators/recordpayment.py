"""Generates ScreenFlowAccountRecordPayment.flow-meta.xml. Usage: python3 -I recordpayment.py <flows dir>"""
import sys
from xml.sax.saxutils import escape as e

def val(v):
    if v is None:
        return ''
    kind, x = v
    if kind == 'ref':
        return f'<elementReference>{x}</elementReference>'
    if kind == 'str':
        return f'<stringValue>{e(x)}</stringValue>'
    if kind == 'num':
        return f'<numberValue>{x}</numberValue>'
    if kind == 'bool':
        return f'<booleanValue>{x}</booleanValue>'
    raise ValueError(kind)

REF = lambda x: ('ref', x)
STR = lambda x: ('str', x)
NUM = lambda x: ('num', x)
BOOL = lambda x: ('bool', 'true' if x else 'false')

def conn(t, tag='connector'):
    return f'<{tag}><targetReference>{t}</targetReference></{tag}>' if t else ''

def loc():
    return '<locationX>0</locationX><locationY>0</locationY>'

els = {k: [] for k in ['assignments', 'choices', 'decisions', 'dynamicChoiceSets', 'formulas', 'loops',
                       'recordCreates', 'recordLookups', 'recordUpdates', 'screens', 'variables']}

def assignment(name, label, items, nxt):
    x = f'<assignments><name>{name}</name><label>{e(label)}</label>{loc()}'
    for ref, op, v in items:
        x += f'<assignmentItems><assignToReference>{ref}</assignToReference><operator>{op}</operator><value>{val(v)}</value></assignmentItems>'
    els['assignments'].append(x + conn(nxt) + '</assignments>')

def cond(left, op, v):
    return f'<conditions><leftValueReference>{left}</leftValueReference><operator>{op}</operator><rightValue>{val(v)}</rightValue></conditions>'

def decision(name, label, rules, default, default_label='No'):
    x = f'<decisions><name>{name}</name><label>{e(label)}</label>{loc()}{conn(default, "defaultConnector")}<defaultConnectorLabel>{default_label}</defaultConnectorLabel>'
    for rname, rlabel, conds, nxt, logic in rules:
        x += f'<rules><name>{rname}</name><conditionLogic>{logic}</conditionLogic>{"".join(conds)}{conn(nxt)}<label>{e(rlabel)}</label></rules>'
    els['decisions'].append(x + '</decisions>')

def formula(name, dtype, expr, desc, scale=None):
    s = f'<scale>{scale}</scale>' if scale is not None else ''
    els['formulas'].append(f'<formulas><name>{name}</name><description>{e(desc)}</description><dataType>{dtype}</dataType><expression>{e(expr)}</expression>{s}</formulas>')

def loop(name, label, coll, nxt, done):
    els['loops'].append(f'<loops><name>{name}</name><label>{e(label)}</label>{loc()}<collectionReference>{coll}</collectionReference><iterationOrder>Asc</iterationOrder>{conn(nxt, "nextValueConnector")}{conn(done, "noMoreValuesConnector")}</loops>')

def lookup(name, label, obj, filters, fields, nxt, first=False, logic='and', sort='CreatedDate'):
    x = f'<recordLookups><name>{name}</name><label>{e(label)}</label>{loc()}<assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>{conn(nxt)}<filterLogic>{logic}</filterLogic>'
    for f, op, v in filters:
        x += f'<filters><field>{f}</field><operator>{op}</operator><value>{val(v)}</value></filters>'
    x += f'<getFirstRecordOnly>{"true" if first else "false"}</getFirstRecordOnly><object>{obj}</object>'
    x += ''.join(f'<queriedFields>{f}</queriedFields>' for f in fields)
    if sort:
        x += f'<sortField>{sort}</sortField><sortOrder>Asc</sortOrder>'
    els['recordLookups'].append(x + '<storeOutputAutomatically>true</storeOutputAutomatically></recordLookups>')

def create_one(name, label, obj, assigns, nxt, fault):
    x = f'<recordCreates><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}{conn(fault, "faultConnector")}'
    for f, v in assigns:
        x += f'<inputAssignments><field>{f}</field><value>{val(v)}</value></inputAssignments>'
    els['recordCreates'].append(x + f'<object>{obj}</object><storeOutputAutomatically>true</storeOutputAutomatically></recordCreates>')

def create_many(name, label, ref, nxt, fault):
    els['recordCreates'].append(f'<recordCreates><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}{conn(fault, "faultConnector")}<inputReference>{ref}</inputReference></recordCreates>')

def update_filtered(name, label, obj, filters, assigns, nxt, fault, desc=None):
    d = f'<description>{e(desc)}</description>' if desc else ''
    x = f'<recordUpdates><name>{name}</name>{d}<label>{e(label)}</label>{loc()}{conn(nxt)}{conn(fault, "faultConnector")}<filterLogic>and</filterLogic>'
    for f, op, v in filters:
        x += f'<filters><field>{f}</field><operator>{op}</operator><value>{val(v)}</value></filters>'
    for f, v in assigns:
        x += f'<inputAssignments><field>{f}</field><value>{val(v)}</value></inputAssignments>'
    els['recordUpdates'].append(x + f'<object>{obj}</object></recordUpdates>')

def update_many(name, label, ref, nxt, fault):
    els['recordUpdates'].append(f'<recordUpdates><name>{name}</name><label>{e(label)}</label>{loc()}{conn(nxt)}{conn(fault, "faultConnector")}<inputReference>{ref}</inputReference></recordUpdates>')

def var(name, dtype, desc, coll=False, inp=False, obj=None, default=None, scale=None):
    x = f'<variables><name>{name}</name><description>{e(desc)}</description><dataType>{dtype}</dataType><isCollection>{"true" if coll else "false"}</isCollection><isInput>{"true" if inp else "false"}</isInput><isOutput>false</isOutput>'
    if obj:
        x += f'<objectType>{obj}</objectType>'
    if scale is not None:
        x += f'<scale>{scale}</scale>'
    if default is not None:
        x += f'<value>{val(default)}</value>'
    els['variables'].append(x + '</variables>')

def display(name, html):
    return f'<fields><name>{name}</name><fieldText>{e(html)}</fieldText><fieldType>DisplayText</fieldType></fields>'

def inp(name, dtype, label, required=False, default=None, help=None, rule=None, vis=None, scale=None, choices=None, reset=False):
    ftype = 'DropdownBox' if choices else 'InputField'
    x = f'<fields><name>{name}</name>'
    if choices:
        x += f'<choiceReferences>{choices}</choiceReferences>'
    x += f'<dataType>{dtype}</dataType>'
    if default is not None:
        x += f'<defaultValue>{val(default)}</defaultValue>'
    x += f'<fieldText>{e(label)}</fieldText><fieldType>{ftype}</fieldType>'
    if help:
        x += f'<helpText>{e(help)}</helpText>'
    if reset:
        x += '<inputsOnNextNavToAssocScrn>ResetValues</inputsOnNextNavToAssocScrn>'
    x += f'<isRequired>{"true" if required else "false"}</isRequired>'
    if scale is not None:
        x += f'<scale>{scale}</scale>'
    if rule:
        x += f'<validationRule><errorMessage>{e(rule[0])}</errorMessage><formulaExpression>{e(rule[1])}</formulaExpression></validationRule>'
    if vis:
        x += f'<visibilityRule><conditionLogic>and</conditionLogic>{vis}</visibilityRule>'
    return x + '</fields>'

def screen(name, label, fields, nxt, finish=False, next_label=None):
    x = f'<screens><name>{name}</name><label>{e(label)}</label>{loc()}<allowBack>false</allowBack><allowFinish>true</allowFinish><allowPause>false</allowPause>{conn(nxt)}'
    x += ''.join(fields)
    if next_label:
        x += f'<nextOrFinishButtonLabel>{e(next_label)}</nextOrFinishButtonLabel>'
    els['screens'].append(x + '<showFooter>true</showFooter><showHeader>true</showHeader></screens>')

# ---- choices
els['dynamicChoiceSets'].append('<dynamicChoiceSets><name>choice_Method</name><dataType>Picklist</dataType><displayField xsi:nil="true"/><object xsi:nil="true"/><picklistField>Method__c</picklistField><picklistObject>Payment__c</picklistObject></dynamicChoiceSets>')

# ---- variables
var('recordId', 'String', 'The account (person or business) that sent the payment. Named recordId because the quick action passes the record under that name.', inp=True)
var('varT_FeeIds', 'String', 'The Ids of the account\'s open fees.', coll=True)
var('varC_Remaining', 'Currency', 'How much of the payment is still to be applied as staff go through the fee items.', scale=2, default=NUM(0))
var('varC_ItemAllocated', 'Currency', 'What is already paid on the fee item being shown, from earlier payments that were not returned.', scale=2, default=NUM(0))
var('varR_Allocation', 'SObject', 'One allocation being built.', obj='PaymentAllocation__c')
var('varR_Allocations', 'SObject', 'The amounts staff applied, before the payment exists.', coll=True, obj='PaymentAllocation__c')
var('varR_AllocationToCreate', 'SObject', 'One allocation with the new payment set on it.', obj='PaymentAllocation__c')
var('varR_AllocationsToCreate', 'SObject', 'The allocations to create, linked to the new payment.', coll=True, obj='PaymentAllocation__c')

var('varT_PaidParentIds', 'String', 'The records (applications, violations, licenses) whose fees this payment was applied to.', coll=True)
var('varT_ReceiptParentIds', 'String', 'The records a Payment Receipt item pays for: its own record and, for an individual application, the others certified with it on the same form.', coll=True)
var('varB_PaymentLinked', 'Boolean', 'True once the payment is linked to a Payment Receipt item it settles.', default=BOOL(False))
var('varN_ReceiptsAccepted', 'Number', 'How many Payment Receipt items this payment settles.', default=NUM(0), scale=0)
var('varR_ReceiptItem', 'SObject', 'One Payment Receipt item being marked Accepted.', obj='DocumentChecklistItem')
var('varR_ReceiptItems', 'SObject', 'The Payment Receipt items this payment settles, marked Accepted.', coll=True, obj='DocumentChecklistItem')

# ---- formulas
formula('forT_ReceiptNote', 'String', 'IF({!varN_ReceiptsAccepted} > 0, "The application\'s Payment Receipt checklist item is now Accepted, so the applicant is no longer asked to upload a receipt.", "")',
        'A line for the last screen when the payment settled an application\'s Payment Receipt item.')
formula('forC_Outstanding', 'Currency', '{!LoopThroughFeeItems.FeeAmount} - {!varC_ItemAllocated}',
        'What is still owed on the fee item being shown.', scale=2)
formula('forC_Suggested', 'Currency', 'MIN({!forC_Outstanding}, {!varC_Remaining})',
        'The amount offered for the fee item: what it still owes, or what is left of the payment if that is less.', scale=2)
formula('forC_Applied', 'Currency', '{!RP_Amount} - {!varC_Remaining}', 'The total staff applied to fees.', scale=2)
formula('forB_CountsTowardItem', 'Boolean',
        '{!LoopThroughAllocations.FeeItem__c} = {!LoopThroughFeeItems.Id} && TEXT({!LoopThroughAllocations.Payment__r.Status__c}) <> "Returned"',
        'True when the allocation is on the fee item being shown and its payment was not returned.')
formula('forT_FeeParent', 'String', 'IF(ISBLANK({!forT_FeeParentName}), "", " (for " & {!forT_FeeParentName} & ")")',
        'The record the fee is for, such as the application number, shown next to each fee item.')
formula('forT_FeeParentName', 'String', 'BLANKVALUE({!GetFeeIndividualApplication.Name}, BLANKVALUE({!GetFeeBusinessApplication.Name}, BLANKVALUE({!GetFeeViolation.Name}, {!GetFeeLicense.Name})))',
        'The name of the record the fee is for: an application, violation or license.')
formula('forT_Year', 'String', 'IF(ISBLANK({!LoopThroughFeeItems.ForYear__c}), "", " (" & {!LoopThroughFeeItems.ForYear__c} & ")")',
        'The fee item\'s license year in brackets, or nothing when it has none.')

# ---- elements
not_card = cond('RP_Method', 'NotEqualTo', STR('Card'))
screen('RecordPayment', 'Record Payment', [
    display('RP_Intro', '<p>Enter the payment as it was received. On the next screens you apply it to this account\'s open fees. Anything not applied stays on the payment as unapplied, for a refund or a later fee.</p>'),
    inp('RP_Method', 'String', 'Method', required=True, choices='choice_Method'),
    inp('RP_Amount', 'Currency', 'Amount', required=True, scale=2,
        rule=('Enter an amount greater than zero.', '{!RP_Amount} > 0')),
    inp('RP_ReceivedDate', 'Date', 'Received date', required=True, default=REF('$Flow.CurrentDate'),
        help='The day LSBC received the payment.',
        rule=('The received date can\'t be in the future.', '{!RP_ReceivedDate} <= TODAY()')),
    inp('RP_Number', 'String', 'Check or transaction number', help='The number printed on the check or money order, or the card transaction number.'),
    inp('RP_CheckDate', 'Date', 'Check or money order date', vis=not_card),
    inp('RP_PayerName', 'String', 'Payer name', help='Only when someone other than the account holder paid, as named on the check.'),
], 'SetRemaining')
assignment('SetRemaining', 'Set Remaining to Payment Amount',
           [('varC_Remaining', 'Assign', REF('RP_Amount'))], 'GetOpenFees')
lookup('GetOpenFees', 'Get Open Fees', 'RegulatoryTrxnFee',
       [('AccountId', 'EqualTo', REF('recordId')), ('Status', 'EqualTo', STR('DUE')), ('Status', 'EqualTo', STR('PARTIALLY_PAID'))],
       ['Id'], 'AreThereOpenFees', logic='1 AND (2 OR 3)')
decision('AreThereOpenFees', 'Are There Open Fees?',
         [('Open', 'Yes', [cond('GetOpenFees', 'IsEmpty', BOOL(False))], 'LoopThroughFees', 'and')], 'CheckAndSave')
loop('LoopThroughFees', 'Loop Through Fees', 'GetOpenFees', 'AddFeeId', 'GetFeeItems')
assignment('AddFeeId', 'Add Fee Id', [('varT_FeeIds', 'Add', REF('LoopThroughFees.Id'))], 'LoopThroughFees')
lookup('GetFeeItems', 'Get Fee Items', 'RegulatoryTrxnFeeItem',
       [('RegulatoryTrxnFeeId', 'In', REF('varT_FeeIds')), ('FeeAmount', 'GreaterThan', NUM(0))],
       ['Id', 'Name', 'FeeAmount', 'ForYear__c', 'RegulatoryTrxnFeeId'], 'GetPriorAllocations')
lookup('GetPriorAllocations', 'Get Payment Allocations on the Fees', 'PaymentAllocation__c',
       [('FeeItem__c', 'In', REF('varT_FeeItemIds'))], ['Id', 'FeeItem__c', 'Amount__c', 'Payment__c'], 'LoopThroughFeeItems')
# collect item ids before allocations lookup: rewire GetFeeItems -> LoopCollectItemIds
els['recordLookups'][-2] = els['recordLookups'][-2].replace('<targetReference>GetPriorAllocations</targetReference>', '<targetReference>LoopCollectItemIds</targetReference>')
var('varT_FeeItemIds', 'String', 'The Ids of the open fees\' items.', coll=True)
loop('LoopCollectItemIds', 'Loop Through Fee Items to Collect Ids', 'GetFeeItems', 'AddFeeItemId', 'GetPriorAllocations')
assignment('AddFeeItemId', 'Add Fee Item Id', [('varT_FeeItemIds', 'Add', REF('LoopCollectItemIds.Id'))], 'LoopCollectItemIds')

loop('LoopThroughFeeItems', 'Loop Through Fee Items', 'GetFeeItems', 'ResetItemAllocated', 'CheckAndSave')
assignment('ResetItemAllocated', 'Set Item Allocated to 0', [('varC_ItemAllocated', 'Assign', NUM(0))], 'LoopThroughAllocations')
loop('LoopThroughAllocations', 'Loop Through Payment Allocations', 'GetPriorAllocations', 'DoesItCountTowardItem', 'IsThereSomethingToApply')
decision('DoesItCountTowardItem', 'Does the Allocation Count Toward This Item?',
         [('Counts', 'Yes', [cond('forB_CountsTowardItem', 'EqualTo', BOOL(True))], 'AddToItemAllocated', 'and')], 'LoopThroughAllocations')
assignment('AddToItemAllocated', 'Add Allocation to Item Allocated',
           [('varC_ItemAllocated', 'Add', REF('LoopThroughAllocations.Amount__c'))], 'LoopThroughAllocations')
decision('IsThereSomethingToApply', 'Is There Something to Apply to This Item?',
         [('Apply', 'Yes', [cond('forC_Outstanding', 'GreaterThan', NUM(0)), cond('varC_Remaining', 'GreaterThan', NUM(0))], 'GetFeeIndividualApplication', 'and')],
         'LoopThroughFeeItems')
# The fee's parent record (polymorphic, so Flow can't read its Name directly): look it up on each kind of record.
for nm, lb, obj, nxt in [('GetFeeIndividualApplication', 'Get Fee Individual Application', 'IndividualApplication', 'GetFeeBusinessApplication'),
                         ('GetFeeBusinessApplication', 'Get Fee Business Application', 'BusinessLicenseApplication', 'GetFeeViolation'),
                         ('GetFeeViolation', 'Get Fee Violation', 'RegulatoryCodeViolation', 'GetFeeLicense'),
                         ('GetFeeLicense', 'Get Fee License', 'BusinessLicense', 'ApplyToFeeItem')]:
    lookup(nm, lb, obj, [('Id', 'EqualTo', REF('LoopThroughFeeItems.RegulatoryTrxnFee.ParentRecordId'))], ['Id', 'Name'], nxt, first=True, sort=None)
screen('ApplyToFeeItem', 'Apply to Fee Item', [
    display('AFI_Item', '<p><b>{!LoopThroughFeeItems.Name}{!forT_Year}</b></p><p>Fee {!LoopThroughFeeItems.RegulatoryTrxnFee.Name}: {!LoopThroughFeeItems.RegulatoryTrxnFee.Description}{!forT_FeeParent}</p><p>Still owed: <b>{!forC_Outstanding}</b><br/>Left on the payment to apply: <b>{!varC_Remaining}</b></p>'),
    inp('AFI_Amount', 'Currency', 'Apply to this item', required=True, scale=2, default=REF('forC_Suggested'), reset=True,
        help='Enter 0 to leave this item unpaid.',
        rule=('Enter an amount from 0 up to what the item still owes and what is left on the payment.',
              '{!AFI_Amount} >= 0 && {!AFI_Amount} <= {!forC_Suggested}')),
], 'WasAnythingApplied')
decision('WasAnythingApplied', 'Was Anything Applied to This Item?',
         [('Applied', 'Yes', [cond('AFI_Amount', 'GreaterThan', NUM(0))], 'AddAllocation', 'and')], 'LoopThroughFeeItems')
assignment('AddAllocation', 'Add Allocation for This Item', [
    ('varR_Allocation.FeeItem__c', 'Assign', REF('LoopThroughFeeItems.Id')),
    ('varR_Allocation.Amount__c', 'Assign', REF('AFI_Amount')),
    ('varR_Allocation.ForYear__c', 'Assign', REF('LoopThroughFeeItems.ForYear__c')),
    ('varR_Allocations', 'Add', REF('varR_Allocation')),
    ('varC_Remaining', 'Subtract', REF('AFI_Amount')),
    ('varT_PaidParentIds', 'Add', REF('LoopThroughFeeItems.RegulatoryTrxnFee.ParentRecordId')),
], 'LoopThroughFeeItems')

screen('CheckAndSave', 'Check and Save', [
    display('CS_Summary', '<p>Payment of <b>{!RP_Amount}</b> received {!RP_ReceivedDate}.</p><p>Applied to fees: <b>{!forC_Applied}</b><br/>Left unapplied: <b>{!varC_Remaining}</b></p><p>Choose Save to record it. To change anything, close this window and start again.</p>'),
], 'CreatePayment', next_label='Save')
create_one('CreatePayment', 'Create Payment', 'Payment__c', [
    ('Account__c', REF('recordId')),
    ('Amount__c', REF('RP_Amount')),
    ('CheckDate__c', REF('RP_CheckDate')),
    ('ExternalReference__c', REF('RP_Number')),
    ('Method__c', REF('RP_Method')),
    ('PayerName__c', REF('RP_PayerName')),
    ('ReceivedDate__c', REF('RP_ReceivedDate')),
    ('Status__c', STR('Completed')),
], 'LoopThroughAllocationsToCreate', 'CouldNotRecordPayment')
loop('LoopThroughAllocationsToCreate', 'Loop Through Allocations to Create', 'varR_Allocations', 'SetAllocationPayment', 'CreateAllocations')
assignment('SetAllocationPayment', 'Set Payment on Allocation', [
    ('varR_AllocationToCreate', 'Assign', REF('LoopThroughAllocationsToCreate')),
    ('varR_AllocationToCreate.Payment__c', 'Assign', REF('CreatePayment')),
    ('varR_AllocationsToCreate', 'Add', REF('varR_AllocationToCreate')),
], 'LoopThroughAllocationsToCreate')
create_many('CreateAllocations', 'Create Payment Allocations', 'varR_AllocationsToCreate', 'GetReceiptDocumentType', 'CouldNotRecordPayment')

# ---- Payment receipts: a mailed or counter payment that settles an application's fees also settles its Payment Receipt
# checklist item, so the portal stops asking the applicant to upload a receipt. The payment is linked to the first
# receipt it settles before the item is accepted, so the checklist trigger's receipt subflow finds a payment for it and
# records no second (Card) payment. A receipt is settled only when nothing is still Due or Partially Paid on its record
# (and, for an individual application, on the others certified with it): the subflow would charge nothing there either.
lookup('GetReceiptDocumentType', 'Get Receipt Document Type', 'DocumentType',
       [('DeveloperName', 'EqualTo', STR('PaymentReceipt'))], ['Id'], 'GetOpenReceiptItems', first=True, sort=None)
lookup('GetOpenReceiptItems', 'Get Open Payment Receipt Items', 'DocumentChecklistItem',
       [('ParentRecordId', 'In', REF('varT_PaidParentIds')), ('DocumentTypeId', 'EqualTo', REF('GetReceiptDocumentType.Id')),
        ('Status', 'NotEqualTo', STR('Accepted'))], ['Id', 'ParentRecordId'], 'AreThereOpenReceiptItems')
decision('AreThereOpenReceiptItems', 'Are There Open Payment Receipt Items?',
         [('OpenReceipts', 'Yes', [cond('GetOpenReceiptItems', 'IsEmpty', BOOL(False))], 'LoopThroughReceiptItems', 'and')], 'PaymentRecorded')
loop('LoopThroughReceiptItems', 'Loop Through Payment Receipt Items', 'GetOpenReceiptItems', 'SetReceiptParentIds', 'WereAnyReceiptsSettled')
assignment('SetReceiptParentIds', 'Set Receipt Records to the Receipt\'s Record', [
    ('varT_ReceiptParentIds', 'RemoveAll', REF('varT_ReceiptParentIds')),
    ('varT_ReceiptParentIds', 'Add', REF('LoopThroughReceiptItems.ParentRecordId')),
], 'GetReceiptApplication')
lookup('GetReceiptApplication', 'Get Receipt Application', 'IndividualApplication',
       [('Id', 'EqualTo', REF('LoopThroughReceiptItems.ParentRecordId'))], ['Id', 'AccountId', 'CertifiedDateTime__c'],
       'GetSameSubmission', first=True, sort=None)
lookup('GetSameSubmission', 'Get Applications from the Same Submission', 'IndividualApplication',
       [('AccountId', 'EqualTo', REF('GetReceiptApplication.AccountId')),
        ('CertifiedDateTime__c', 'EqualTo', REF('GetReceiptApplication.CertifiedDateTime__c')),
        ('CertifiedDateTime__c', 'IsNull', BOOL(False))], ['Id'], 'LoopThroughSameSubmission', sort=None)
loop('LoopThroughSameSubmission', 'Loop Through Same Submission', 'GetSameSubmission', 'AddSubmissionApplication', 'GetFeeStillOwed')
assignment('AddSubmissionApplication', 'Add Application to Receipt Records',
           [('varT_ReceiptParentIds', 'Add', REF('LoopThroughSameSubmission.Id'))], 'LoopThroughSameSubmission')
lookup('GetFeeStillOwed', 'Get Fee Still Owed on the Receipt\'s Records', 'RegulatoryTrxnFee',
       [('ParentRecordId', 'In', REF('varT_ReceiptParentIds')), ('Status', 'EqualTo', STR('DUE')), ('Status', 'EqualTo', STR('PARTIALLY_PAID'))],
       ['Id'], 'AreTheReceiptFeesPaid', first=True, logic='1 AND (2 OR 3)', sort=None)
decision('AreTheReceiptFeesPaid', 'Are the Receipt\'s Fees All Paid?',
         [('AllPaid', 'Yes', [cond('GetFeeStillOwed.Id', 'IsNull', BOOL(True))], 'IsThePaymentLinkedToAReceipt', 'and')], 'LoopThroughReceiptItems')
decision('IsThePaymentLinkedToAReceipt', 'Is the Payment Already Linked to a Receipt?',
         [('Linked', 'Yes', [cond('varB_PaymentLinked', 'EqualTo', BOOL(True))], 'AddAcceptedReceipt', 'and')], 'LinkPaymentToReceipt')
update_filtered('LinkPaymentToReceipt', 'Set Checklist Item on Payment to Receipt', 'Payment__c',
                [('Id', 'EqualTo', REF('CreatePayment'))], [('ChecklistItem__c', REF('LoopThroughReceiptItems.Id'))],
                'SetPaymentLinked', 'CouldNotAcceptReceipt',
                desc='Links the payment to the receipt it settles, so accepting the receipt records no second payment.')
assignment('SetPaymentLinked', 'Set Payment Linked to True', [('varB_PaymentLinked', 'Assign', BOOL(True))], 'AddAcceptedReceipt')
assignment('AddAcceptedReceipt', 'Add Receipt Item with Status Accepted', [
    ('varR_ReceiptItem.Id', 'Assign', REF('LoopThroughReceiptItems.Id')),
    ('varR_ReceiptItem.Status', 'Assign', STR('Accepted')),
    ('varR_ReceiptItems', 'Add', REF('varR_ReceiptItem')),
    ('varN_ReceiptsAccepted', 'Add', NUM(1)),
], 'LoopThroughReceiptItems')
decision('WereAnyReceiptsSettled', 'Were Any Payment Receipts Settled?',
         [('Settled', 'Yes', [cond('varR_ReceiptItems', 'IsEmpty', BOOL(False))], 'UpdateReceiptItems', 'and')], 'PaymentRecorded')
update_many('UpdateReceiptItems', 'Update Payment Receipt Items', 'varR_ReceiptItems', 'PaymentRecorded', 'CouldNotAcceptReceipt')

screen('PaymentRecorded', 'Payment Recorded', [
    display('PR_Message', '<p><b>The payment is recorded.</b></p><p>Applied to fees: {!forC_Applied}. Left unapplied: {!varC_Remaining}.</p><p>The fees\' Amount Paid and Status update on their own.</p><p>{!forT_ReceiptNote}</p>'),
], None, next_label='Done')
screen('CouldNotAcceptReceipt', 'Could Not Accept Payment Receipt', [
    display('CNAR_Message', '<p><b>The payment is recorded</b>, but the application\'s Payment Receipt checklist item could not be marked Accepted.</p><p>{!$Flow.FaultMessage}</p><p>Open the application\'s checklist and accept the Payment Receipt item there. No second payment is recorded for it.</p>'),
], None)
screen('CouldNotRecordPayment', 'Could Not Record Payment', [
    display('CNRP_Message', '<p>The payment could not be recorded, and nothing was saved.</p><p>{!$Flow.FaultMessage}</p>'),
], None)

desc = ('Records a payment that came in by mail or at the counter (check, money order, cashier\'s check or card) for a person or business, '
        'from the Record Payment action on the account. Staff enter the payment, then go through each of the account\'s open fee items, oldest first, '
        'and apply part of it; each item offers what it still owes, after earlier payments that were not returned. Anything not applied stays on the payment '
        'as unapplied. The payment and its allocations are saved together at the end, and the fees\' Amount Paid and Status then update through the payment '
        'allocation trigger. Online (PayStar) payments are recorded automatically when staff accept the receipt, not here. When the payment leaves nothing Due or Partially Paid on an application (and on the others certified with it), the application\'s open Payment Receipt checklist item is marked Accepted, so the portal stops asking for a receipt; the payment is first linked to that item, so accepting it records no second (Card) payment.')

order = ['assignments', 'choices', 'decisions', 'dynamicChoiceSets']
head = ('<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        '<apiVersion>66.0</apiVersion>')
body = ''.join(els['assignments']) + ''.join(els['decisions']) + f'<description>{e(desc)}</description>' + ''.join(els['dynamicChoiceSets'])
body += '<environments>Default</environments>' + ''.join(els['formulas'])
body += '<interviewLabel>Screen Flow: Account Record Payment {!$Flow.CurrentDateTime}</interviewLabel><label>Screen Flow: Account Record Payment</label>'
body += ''.join(els['loops'])
for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
    body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
body += '<processType>Flow</processType>' + ''.join(els['recordCreates']) + ''.join(els['recordLookups']) + ''.join(els['recordUpdates'])
body += '<runInMode>DefaultMode</runInMode>' + ''.join(els['screens'])
body += f'<start>{loc()}{conn("RecordPayment")}</start><status>Active</status>' + ''.join(els['variables']) + '</Flow>\n'
open(sys.argv[1] + '/ScreenFlowAccountRecordPayment.flow-meta.xml', 'w').write(head + body)
print('written')
