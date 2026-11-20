"""Writes Subflow: Document Checklist Generate (SubflowDocumentChecklistGenerate).

Builds an application's document checklist from a document checklist template (an Action Plan template, loaded by
scripts/actionplans/load_templates.py and edited by admins in Setup). Inputs are unchanged from the earlier version
that read the Application Document Requirement settings, so the forms calling it don't change.

The template is picked by Unique Name, built from the inputs with spaces and punctuation removed; the first that
exists wins:
  1. record type + licence type        NewEstablishmentSalon, ReciprocityTemporaryPermit
  2. record type + path + type         ReciprocityMilitaryNew (only when there is a path)
  3. record type + application type    RenewalDuplicate, ExaminationNoShow, AddressChange (Case has no record type)
  4. record type                       NewSchool, StudentRegistration
where record type is the part of varT_RecordType after the dot.

Run: python3 -I scripts/generators/checklistgenerate.py force-app/main/default/flows
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from xml.sax.saxutils import escape as e
import flowlib as F
from flowlib import els, REF, STR, NUM, BOOL, cond, loc, conn

F.els['recordCreates'] = []

def clean(x):
    return f'SUBSTITUTE(SUBSTITUTE(SUBSTITUTE(SUBSTITUTE({x}, " ", ""), "-", ""), "\'", ""), "/", "")'

RT = '{!varT_RecordType}'
F.formula('forT_RecordTypePart', 'String', f'IF(CONTAINS({RT}, "."), MID({RT}, FIND(".", {RT}) + 1, 80), "")',
          'The record type part of the record type input (after the dot); blank for Case.')
P = '{!forT_RecordTypePart}'
LT, PATH, TYPE = 'BLANKVALUE({!varT_LicenseTypeName}, "")', 'BLANKVALUE({!varT_ApplicationPath}, "")', 'BLANKVALUE({!varT_ApplicationType}, "")'
F.formula('forT_NameLicenseType', 'String', f'IF(LEN({LT}) = 0, "", {P} & {clean(LT)})', 'Template name: record type and licence type.')
F.formula('forT_NamePathType', 'String', f'IF(LEN({PATH}) = 0, "", {P} & {clean(PATH)} & {clean(TYPE)})',
          'Template name: record type, path and application type, when there is a path.')
F.formula('forT_NameType', 'String', f'IF(LEN({TYPE}) = 0, "", {P} & {clean(TYPE)})', 'Template name: record type and application type.')
F.formula('forN_Rank', 'Number',
          'IF(LOWER({!LoopThroughTemplates.UniqueName}) = LOWER({!forT_NameLicenseType}), 1, '
          'IF(LOWER({!LoopThroughTemplates.UniqueName}) = LOWER({!forT_NamePathType}), 2, '
          'IF(LOWER({!LoopThroughTemplates.UniqueName}) = LOWER({!forT_NameType}), 3, '
          'IF(LOWER({!LoopThroughTemplates.UniqueName}) = LOWER({!forT_RecordTypePart}), 4, 99))))',
          'How specific this template is: 1 most specific (licence type), 4 least (record type only), 99 not a match. Names are compared ignoring case.', scale=0)
F.formula('forB_ValueIsTrue', 'Boolean', 'LOWER(BLANKVALUE({!LoopThroughItemValues.ValueLiteral}, "")) = "true"',
          'True when the template value is true.')
F.formula('forT_ExistingToken', 'String', '";" & {!LoopThroughExistingItems.DocumentTypeId}', 'An existing item\'s document type, for the list.')
F.formula('forT_DocToken', 'String', '";" & {!varT_DocTypeId}', 'This item\'s document type, for the list.')
F.formula('forB_AlreadyOnApplication', 'Boolean', 'CONTAINS(";" & {!varT_ExistingTypeIds}, {!varT_DocTypeId})',
          'True when the application already has this document type.')
F.formula('forB_LeaveOut', 'Boolean', 'AND({!varB_LeaveOutReceipt}, {!varT_DocTypeId} = {!GetPaymentReceiptType.Id})',
          'True for the payment receipt when it is to be left out.')
F.formula('forB_IsSentToBoard', 'Boolean',
          'AND(NOT(ISBLANK({!varT_TemplateCategoryId})), {!varT_TemplateCategoryId} = {!GetSentToTheBoardCategory.Id})',
          'True when the template puts the item in the Sent to the Board category: the document reaches the Board by mail or from another state or company.')
F.formula('forT_CategoryId', 'String',
          'IF(OR({!forB_IsSentToBoard}, ISBLANK({!varT_TemplateCategoryId})), {!varT_LinkCategoryId}, {!varT_TemplateCategoryId})',
          'The item\'s category: the template\'s, or the document type\'s usual category when the template says Sent to the Board or gives none.')

# Pick the template
F.lookup('GetTemplates', 'Get Document Checklist Templates', 'ActionPlanTemplate',
         [('ActionPlanType', 'EqualTo', STR('Industries'))], ['Id', 'UniqueName'], 'LoopThroughTemplates', sort='UniqueName')
F.loop('LoopThroughTemplates', 'Loop Through Templates', 'GetTemplates', 'IsThisTemplateMoreSpecific', 'WasATemplateFound')
F.decision('IsThisTemplateMoreSpecific', 'Is This Template More Specific?', [
    ('MoreSpecific', 'Yes', [cond('forN_Rank', 'LessThan', REF('varN_BestRank'))], 'SetBestTemplate', 'and')], 'LoopThroughTemplates')
F.assignment('SetBestTemplate', 'Set Template to This One', [
    ('varT_TemplateId', 'Assign', REF('LoopThroughTemplates.Id')), ('varN_BestRank', 'Assign', REF('forN_Rank'))], 'LoopThroughTemplates')
F.decision('WasATemplateFound', 'Was a Template Found?', [
    ('Found', 'Yes', [cond('varT_TemplateId', 'IsNull', BOOL(False))], 'GetTemplateVersion', 'and')], None)
F.lookup('GetTemplateVersion', 'Get Published Template Version', 'ActionPlanTemplateVersion',
         [('ActionPlanTemplateId', 'EqualTo', REF('varT_TemplateId')), ('Status', 'EqualTo', STR('Final'))],
         ['Id', 'Version'], 'WasAVersionFound', first=True, sort='Version')
F.decision('WasAVersionFound', 'Was a Published Version Found?', [
    ('VersionFound', 'Yes', [cond('GetTemplateVersion', 'IsNull', BOOL(False))], 'GetTemplateItems', 'and')], None)
F.lookup('GetTemplateItems', 'Get Template Items', 'ActionPlanTemplateItem',
         [('ActionPlanTemplateVersionId', 'EqualTo', REF('GetTemplateVersion.Id')), ('ItemEntityType', 'EqualTo', STR('DocumentChecklistItem'))],
         ['Id', 'Name', 'IsRequired', 'DisplayOrder'], 'LoopThroughItemIds', sort='DisplayOrder')
F.loop('LoopThroughItemIds', 'Loop Through Template Item Ids', 'GetTemplateItems', 'AddItemId', 'GetItemValues')
F.assignment('AddItemId', 'Add Template Item Id', [('varT_ItemIds', 'Add', REF('LoopThroughItemIds.Id'))], 'LoopThroughItemIds')
F.lookup('GetItemValues', 'Get Template Item Values', 'ActionPlanTemplateItemValue',
         [('ActionPlanTemplateItemId', 'In', REF('varT_ItemIds'))],
         ['Id', 'ActionPlanTemplateItemId', 'ItemEntityFieldName', 'ValueLiteral'], 'GetExistingItems', sort=None)

# What the application already has, and reference records
F.lookup('GetExistingItems', 'Get Existing Checklist Items', 'DocumentChecklistItem',
         [('ParentRecordId', 'EqualTo', REF('varT_ApplicationId'))], ['Id', 'DocumentTypeId'], 'LoopThroughExistingItems', sort=None)
F.loop('LoopThroughExistingItems', 'Loop Through Existing Items', 'GetExistingItems', 'AddExistingTypeId', 'GetSentToTheBoardCategory')
F.assignment('AddExistingTypeId', 'Add Existing Type Id', [('varT_ExistingTypeIds', 'Add', REF('forT_ExistingToken'))], 'LoopThroughExistingItems')
F.lookup('GetSentToTheBoardCategory', 'Get Sent to the Board Category', 'DocumentCategory',
         [('DeveloperName', 'EqualTo', STR('SentToTheBoard'))], ['Id'], 'GetPaymentReceiptType', first=True, sort=None)
F.lookup('GetPaymentReceiptType', 'Get Payment Receipt Document Type', 'DocumentType',
         [('DeveloperName', 'EqualTo', STR('PaymentReceipt'))], ['Id'], 'GetCategoryLinks', first=True, sort=None)
F.lookup('GetCategoryLinks', 'Get Document Category Links', 'DocumentCategoryDocumentType',
         [('DocumentTypeId', 'IsNull', BOOL(False))], ['Id', 'DocumentTypeId', 'DocumentCategoryId'], 'LoopThroughTemplateItems', sort=None)

# One checklist item per template item
F.loop('LoopThroughTemplateItems', 'Loop Through Template Items', 'GetTemplateItems', 'SetItemDefaults', 'AreThereItemsToCreate')
F.assignment('SetItemDefaults', 'Set Item Defaults from Template Item', [
    ('varT_DocTypeId', 'Assign', STR('')), ('varT_TemplateCategoryId', 'Assign', STR('')), ('varT_LinkCategoryId', 'Assign', STR('')),
    ('varT_Instruction', 'Assign', STR('')), ('varT_DocLabel', 'Assign', REF('LoopThroughTemplateItems.Name')),
    ('varB_Required', 'Assign', REF('LoopThroughTemplateItems.IsRequired'))], 'LoopThroughItemValues')
F.loop('LoopThroughItemValues', 'Loop Through Template Item Values', 'GetItemValues', 'WhichFieldDoesThisValueSet', 'IsTheItemNew')

def on_item(field):
    return [cond('LoopThroughItemValues.ActionPlanTemplateItemId', 'EqualTo', REF('LoopThroughTemplateItems.Id')),
            cond('LoopThroughItemValues.ItemEntityFieldName', 'EqualTo', STR(f'DocumentChecklistItem.{field}'))]

F.decision('WhichFieldDoesThisValueSet', 'Which Field Does This Value Set?', [
    ('DocumentType', 'Document Type', on_item('DocumentTypeId'), 'SetDocumentType', 'and'),
    ('Category', 'Category', on_item('DocumentCategoryId'), 'SetTemplateCategory', 'and'),
    ('Instruction', 'Instruction', on_item('Instruction'), 'SetInstruction', 'and'),
    ('ItemName', 'Name', on_item('Name'), 'SetName', 'and'),
    ('Required', 'Required', on_item('IsRequired'), 'SetRequired', 'and')], 'LoopThroughItemValues', 'Another Item or Field')
F.assignment('SetDocumentType', 'Set Document Type', [('varT_DocTypeId', 'Assign', REF('LoopThroughItemValues.ValueLiteral'))], 'LoopThroughItemValues')
F.assignment('SetTemplateCategory', 'Set Template Category', [('varT_TemplateCategoryId', 'Assign', REF('LoopThroughItemValues.ValueLiteral'))], 'LoopThroughItemValues')
F.assignment('SetInstruction', 'Set Instruction', [('varT_Instruction', 'Assign', REF('LoopThroughItemValues.ValueLiteral'))], 'LoopThroughItemValues')
F.assignment('SetName', 'Set Name', [('varT_DocLabel', 'Assign', REF('LoopThroughItemValues.ValueLiteral'))], 'LoopThroughItemValues')
F.assignment('SetRequired', 'Set Required', [('varB_Required', 'Assign', REF('forB_ValueIsTrue'))], 'LoopThroughItemValues')

F.decision('IsTheItemNew', 'Is the Item New?', [
    ('New', 'Yes', [cond('varT_DocTypeId', 'IsNull', BOOL(False)), cond('forB_AlreadyOnApplication', 'EqualTo', BOOL(False)),
                    cond('forB_LeaveOut', 'EqualTo', BOOL(False))], 'LoopThroughCategoryLinks', 'and')], 'LoopThroughTemplateItems')
F.loop('LoopThroughCategoryLinks', 'Loop Through Category Links', 'GetCategoryLinks', 'IsThisTheItemsCategory', 'SetChecklistItem')
F.decision('IsThisTheItemsCategory', "Is This the Document Type's Category?", [
    ('CategoryMatch', 'Yes', [cond('LoopThroughCategoryLinks.DocumentTypeId', 'EqualTo', REF('varT_DocTypeId'))], 'SetLinkCategory', 'and')],
    'LoopThroughCategoryLinks')
F.assignment('SetLinkCategory', "Set Document Type's Category", [('varT_LinkCategoryId', 'Assign', REF('LoopThroughCategoryLinks.DocumentCategoryId'))],
             'LoopThroughCategoryLinks')
F.assignment('SetChecklistItem', 'Set Checklist Item', [
    ('varR_Item.Name', 'Assign', REF('varT_DocLabel')), ('varR_Item.ParentRecordId', 'Assign', REF('varT_ApplicationId')),
    ('varR_Item.AccountId', 'Assign', REF('varT_AccountId')), ('varR_Item.DocumentTypeId', 'Assign', REF('varT_DocTypeId')),
    ('varR_Item.IsRequired', 'Assign', REF('varB_Required')), ('varR_Item.Instruction', 'Assign', REF('varT_Instruction')),
    ('varR_Item.IsSentToBoard__c', 'Assign', REF('forB_IsSentToBoard')), ('varR_Item.Status', 'Assign', STR('New')),
    ('varR_Item.DocumentCategoryId', 'Assign', REF('forT_CategoryId')), ('varR_Items', 'Add', REF('varR_Item')),
    ('varT_ExistingTypeIds', 'Add', REF('forT_DocToken')), ('varN_ItemsCreated', 'Add', NUM(1))], 'LoopThroughTemplateItems')
F.decision('AreThereItemsToCreate', 'Are There Items to Create?', [
    ('Items', 'Yes', [cond('varN_ItemsCreated', 'GreaterThan', NUM(0))], 'CreateChecklistItems', 'and')], None)
F.create_many('CreateChecklistItems', 'Create Checklist Items', 'varR_Items', None, None)

# Variables
F.var('varT_ApplicationId', 'String', 'The Individual Application, Business License Application, Case or draft (Preliminary Application Reference).', inp=True)
F.var('varT_AccountId', 'String', "The applicant's account, stamped on each item.", inp=True)
F.var('varT_RecordType', 'String', 'Object and record type, for example IndividualApplication.Reciprocity; Case for a Case.', inp=True)
F.var('varT_LicenseTypeName', 'String', 'The license type name, for example Threading Permit.', inp=True)
F.var('varT_ApplicationPath', 'String', 'Regular, Military, International, Welcome Home Act or Previously Enrolled; blank when there is no path.', inp=True)
F.var('varT_ApplicationType', 'String', 'New, Renewal, Duplicate, Affidavit, Retake, an exam or student form type, or Address Change.', inp=True)
F.var('varB_LeaveOutReceipt', 'Boolean',
      'True to leave out the payment receipt: when staff enter a paper application (they record the payment with Record Payment), '
      'on all but the first application of a renewal form, which shares one receipt, and on drafts whose receipt is added on the application.',
      inp=True, default=BOOL(False))
F.var('varT_TemplateId', 'String', 'The template that applies.')
F.var('varN_BestRank', 'Number', 'How specific the template picked so far is (lower is more specific).', default=NUM(9), scale=0)
F.var('varT_ItemIds', 'String', "The template's item Ids.", coll=True)
F.var('varT_ExistingTypeIds', 'String', 'Document type Ids already on the application, each preceded by a semicolon.')
F.var('varT_DocTypeId', 'String', "The document type of the item being added.")
F.var('varT_DocLabel', 'String', "The name of the item being added.")
F.var('varT_Instruction', 'String', "The instruction of the item being added.")
F.var('varB_Required', 'Boolean', 'Whether the item being added is required.', default=BOOL(False))
F.var('varT_TemplateCategoryId', 'String', "The category the template gives the item.")
F.var('varT_LinkCategoryId', 'String', "The document type's usual category.")
F.var('varR_Item', 'SObject', 'The item being added.', obj='DocumentChecklistItem')
F.var('varR_Items', 'SObject', 'The items to create.', coll=True, obj='DocumentChecklistItem')
els['variables'].append('<variables><name>varN_ItemsCreated</name><description>How many checklist items were added.</description><dataType>Number</dataType>'
                        '<isCollection>false</isCollection><isInput>false</isInput><isOutput>true</isOutput><scale>0</scale>'
                        '<value><numberValue>0</numberValue></value></variables>')

# Latest published version first
els['recordLookups'] = [x.replace('<sortField>Version</sortField><sortOrder>Asc</sortOrder>', '<sortField>Version</sortField><sortOrder>Desc</sortOrder>')
                        for x in els['recordLookups']]

desc = ("Creates an application's document checklist from its document checklist template (Setup, Action Plan Templates): one "
        "Document Checklist Item per template item in the latest published version, with the item's name, document type, "
        "instruction and whether it is required. The template is the one whose Unique Name matches the record type with the "
        "licence type, path and application type, the most specific first (see the admin guide). An item the template puts in "
        "the Sent to the Board category is ticked Sent to the Board and filed under its document type's usual category. "
        "The payment receipt is left out when asked. Items already on the application are not added twice, so it is safe "
        "to run again after an answer changes. Runs in system context to read the templates and document types.")
label = 'Subflow: Document Checklist Generate'
head = '<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata"><apiVersion>66.0</apiVersion>'
body = ''.join(els['assignments']) + ''.join(els['decisions']) + f'<description>{e(desc)}</description><environments>Default</environments>' + ''.join(els['formulas'])
body += f'<interviewLabel>{label} {{!$Flow.CurrentDateTime}}</interviewLabel><label>{label}</label>' + ''.join(els['loops'])
for k, v in [('BuilderType', 'LightningFlowBuilder'), ('CanvasMode', 'AUTO_LAYOUT_CANVAS'), ('OriginBuilderType', 'LightningFlowBuilder')]:
    body += f'<processMetadataValues><name>{k}</name><value><stringValue>{v}</stringValue></value></processMetadataValues>'
body += '<processType>AutoLaunchedFlow</processType>' + ''.join(els['recordCreates']) + ''.join(els['recordLookups'])
body += f'<runInMode>SystemModeWithoutSharing</runInMode><start>{loc()}{conn("GetTemplates")}</start><status>Active</status>'
body += ''.join(els['variables']) + '</Flow>\n'
open(sys.argv[1] + '/SubflowDocumentChecklistGenerate.flow-meta.xml', 'w').write(head + body)
print('written')
