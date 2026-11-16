"""Generate LSBC record pages in the format of AccountRecordPage
(header + two equal columns: Details|History left; object tabs, Files|Notes|Chatter, Activities right)."""
import json, os, sys
from xml.sax.saxutils import escape

OUT = sys.argv[1]
DESCRIBE = sys.argv[2]

def caps(obj):
    d = json.load(open(os.path.join(DESCRIBE, obj + '.json')))['result']
    rels = {c['relationshipName'] for c in d['childRelationships'] if c['relationshipName']}
    return {'act': 'ActivityHistories' in rels and obj not in NO_NOTES, 'hist': 'Histories' in rels and obj != 'DocumentChecklistItem',
            'feed': d.get('feedEnabled', False), 'rels': rels}

NO_NOTES = {'DocumentChecklistItem', 'RecordAlert'}
FRONT_TABS = {'Relationships', 'Exams and Accommodations'}
PERSON = ('{!Record.IsPersonAccount}', 'true')
BUSINESS = ('{!Record.IsPersonAccount}', 'false')

# object: (label, description, actions, [ (tab title, [(relatedList, visibility)]) ])
PAGES = {
 'BusinessLicense': ('Business License Record Page',
   'Staff view of a license or permit: its details and history, the applications made against it, and its fees.',
   ['Edit'],
   [('Applications', [('IndividualApplicationPermit', None), ('BusinessLicenseApplicationPermit', None)]),
    ('Fees', [('RegulatoryTrxnFees', None)])]),
 'IndividualApplication': ('Individual Application Record Page',
   'Staff view of an application from a person: its details, document checklist and fees.',
   ['IndividualApplication.Decide', 'IndividualApplication.UploadDocuments', 'EditIARecord', 'IndividualApplication.GenerateLetter'],
   [('Checklist', [('DocumentChecklistItemPR', None)]),
    ('Fees', [('RegulatoryTrxnFees', None)])]),
 'BusinessLicenseApplication': ('Business License Application Record Page',
   'Staff view of an application for an establishment or school: its details, document checklist and fees.',
   ['BusinessLicenseApplication.Decide', 'BusinessLicenseApplication.UploadDocuments', 'EditRecord', 'BusinessLicenseApplication.GenerateLetter'],
   [('Checklist', [('DocumentChecklistItemPR', None)]),
    ('Fees', [('RegulatoryTrxnFees', None)])]),
 'RegulatoryTrxnFee': ('Regulatory Transaction Fee Record Page',
   'Staff view of a fee: what is owed, its items by year, and how much is paid.',
   ['Edit'],
   [('Fee Items', [('RegulatoryTrxnFeeItems', None)])]),
 'RegulatoryTrxnFeeItem': ('Regulatory Transaction Fee Item Record Page',
   'Staff view of one fee line: its year and the payments allocated to it. Change Year moves it to another license year.',
   ['Edit', 'RegulatoryTrxnFeeItem.ChangeYear'],
   [('Payment Allocations', [('PaymentAllocations__r', None)])]),
 'Payment__c': ('Payment Record Page',
   'Staff view of a payment received: amount, how it is split across fees, and any refund.',
   ['Payment__c.Refund', 'Edit'],
   [('Allocations', [('Allocations__r', None)])]),
 'PaymentAllocation__c': ('Payment Allocation Record Page',
   'Staff view of one share of a payment applied to a fee line. Deleting it re-totals the fee it paid.',
   ['Edit', 'Delete'], []),
 'RegulatoryCodeViolation': ('Regulatory Code Violation Record Page',
   'Staff view of a violation: who is cited, its fee and its documents.',
   ['Edit'],
   [('Fees', [('RegulatoryTrxnFees', None)]),
    ('Checklist', [('DocumentChecklistItemPR', None)])]),
 'PublicComplaint': ('Public Complaint Record Page',
   'Staff view of a complaint: the Cases working it and the people involved.',
   ['Edit'],
   [('Cases', [('ComplaintCaseComplaint', None)]),
    ('Participants', [('PublicComplaintParticipants', None)])]),
 'Case': ('Case Record Page',
   'Staff view of a Case: complaints and violations recorded from it, and comments; emails show in Activities. New Violation and Record Complaint are in the header.',
   ['Edit', 'Case.NewViolation', 'Case.RecordComplaint'],
   [('Complaints', [('ComplaintCaseCase', None)]),
    ('Violations', [('Violations__r', None)]),
    ('Comments', [('CaseComments', None)])]),
 'RecordAlert': ('Record Alert Record Page',
   'Staff view of a stop code (hold): its category, holder, and when it started and ended. 12/31/4000 means no end date.',
   ['RecordAlert.EndStopCode', 'Edit'], []),
 'PersonExamination': ('Person Examination Record Page',
   'Staff view of one examination attempt: result, date and documents.',
   ['Edit'],
   [('Checklist', [('DocumentChecklistItemPR', None)])]),
 'TrainingCourseParticipant': ('Training Course Participant Record Page',
   'Staff view of a student enrollment at a school, with its hours.',
   ['Edit'], []),
 'Accreditation': ('Accreditation Record Page',
   'Staff view of an approval or bond: school status, surety bonds, and CE provider and credential evaluator approvals by year.',
   ['Edit'], []),
 'CourseOffering': ('Course Offering Record Page',
   "Staff view of a school's program: approved hours, enrolled students and student applications.",
   ['Edit'],
   [('Students', [('TCPCourseOffering', None)]),
    ('Student Applications', [('StudentApplications__r', None)]),
    ('Checklist', [('DocumentChecklistItemPR', None)])]),
 'DocumentChecklistItem': ('Document Checklist Item Record Page',
   'Staff view of one required document: its status, the file, and Board comments.',
   ['Edit'], []),
 'Account': ('Account Record Page',
   'Staff view of a person or business: licenses, applications, fees and payments, stop codes, violations and Cases. Person and business accounts see the related lists that apply to them.',
   ['Edit', ('Account.NewApplication', PERSON), 'Account.NewLicense', 'Account.RecordPayment', 'Account.GenerateLetter', 'Account.AddStopCode', ('Account.NewViolationPractitioner', PERSON), ('Account.NewViolationEstablishment', BUSINESS)],
   [('Relationships', [('PersonAccountContactRelations', PERSON), ('AccountContactRelations', BUSINESS)]),
    ('Exams and Accommodations', [(('DYN', 'PersonPersonExamContact', 'Person Examinations', ['Name', 'Examination', 'ExaminationDate', 'AttemptNumber__c', 'Result'], ['New']), PERSON),
                                  (('DYN', 'PersonDisabilities', 'Accommodation Requests', ['Name', 'Status', 'Accommodations__c', 'IsAccommodationRequired'], ['New']), PERSON),
                                  (('FLOW', 'ScreenFlowAccountPersonLanguages'), PERSON)]),
    ('Licenses', [('BusinessLicenses', BUSINESS), (('DYN', 'Accreditations', 'Accreditations', ['Name', 'Type', 'AccreditingBody', 'Status', 'EffectiveTo'], ['New']), BUSINESS), (('DYN', 'BusinessLicenses', 'Licenses', ['Name', 'Identifier', 'RegulatoryAuthorizationType', 'Status', 'PeriodEnd']), PERSON)]),
    ('Applications', [(('DYN', 'IndividualApplicationAccount', 'Individual Applications', ['Name', 'LicenseType', 'Status', 'AppliedDate'], ['New']), PERSON),
                      (('DYN', 'BusinessLicenseApplicationAccount', 'Business License Applications', ['Name', 'LicenseType', 'Status', 'AppliedDate'], ['New']), BUSINESS)]),
    ('Fees and Payments', [('RegulatoryTrxnFees', None), ('PaymentsReceived__r', None)]),
    ('Stop Codes', [('ALERTCARD', None)]),
    ('Training', [(('DYN', 'PersonTCPContact', 'Training Course Participants', ['Name', 'CourseOffering', 'EntryType__c', 'TotalHours', 'StartDate', 'EndDate'], ['New']), PERSON)]),
    ('Violations', [('PractitionerViolations__r', PERSON), ('EstablishmentViolations__r', BUSINESS)]),
    ('Cases', [('Cases', None)])]),
}

class Page:
    def __init__(self, obj):
        self.obj = obj; self.n = {}; self.regions = []
    def ident(self, comp):
        base = comp.replace(':', '_')
        self.n[base] = self.n.get(base, 0) + 1
        return base if self.n[base] == 1 else f'{base}{self.n[base]}'
    def comp(self, name, props=(), vis=None, value_lists=None):
        x = '        <itemInstances>\n            <componentInstance>\n'
        for k, vals in (value_lists or {}).items():
            x += f'                <componentInstanceProperties>\n                    <name>{k}</name>\n                    <valueList>\n'
            for v in vals:
                v, iv = v if isinstance(v, tuple) else (v, None)
                x += f'                        <valueListItems>\n                            <value>{escape(v)}</value>\n'
                if iv:
                    x += ('                            <visibilityRule>\n                                <criteria>\n'
                          f'                                    <leftValue>{iv[0]}</leftValue>\n                                    <operator>EQUAL</operator>\n'
                          f'                                    <rightValue>{iv[1]}</rightValue>\n                                </criteria>\n                            </visibilityRule>\n')
                x += '                        </valueListItems>\n'
            x += '                    </valueList>\n                </componentInstanceProperties>\n'
        for k, v in props:
            x += f'                <componentInstanceProperties>\n                    <name>{k}</name>\n                    <value>{escape(v)}</value>\n                </componentInstanceProperties>\n'
        x += f'                <componentName>{name}</componentName>\n                <identifier>{self.ident(name)}</identifier>\n'
        if vis:
            x += ('                <visibilityRule>\n                    <criteria>\n'
                  f'                        <leftValue>{vis[0]}</leftValue>\n                        <operator>EQUAL</operator>\n'
                  f'                        <rightValue>{vis[1]}</rightValue>\n                    </criteria>\n                </visibilityRule>\n')
        return x + '            </componentInstance>\n        </itemInstances>\n'
    def region(self, name, items, typ='Facet'):
        self.regions.append(f'    <flexiPageRegions>\n{"".join(items)}        <name>{name}</name>\n        <type>{typ}</type>\n    </flexiPageRegions>\n')
    def related(self, rl, vis=None):
        return self.comp('force:relatedListSingleContainer', [
            ('parentFieldApiName', f'{self.obj}.Id'), ('relatedListApiName', rl),
            ('relatedListComponentOverride', 'NONE'), ('rowsToDisplay', '10'), ('showActionBar', 'true')], vis)
    def flow(self, name, vis=None):
        # A screen flow on the page, given the record's Id as recordId.
        args = '[{"label":"recordId","dataType":"String","supportsRecordId":true,"value":"{!Record.Id}"}]'
        return self.comp('flowruntime:interview', [('flowArguments', args), ('flowLayout', 'oneColumn'), ('flowName', name)], vis)
    def dynamic(self, spec, vis=None):
        # A dynamic list shows the actions of the same list on the page layout. A list that can't be on the
        # layout gets its actions here (a fifth item, e.g. ['New']), or it shows no New button. Salesforce never shows
        # New on a person account's Licenses (Organization) list, so licenses are added with the New License action.
        _, rl, label, fields, *acts = spec
        lists = {'relatedListFieldAliases': fields}
        if acts:
            lists = {'actionNames': acts[0], **lists}
        return self.comp('lst:dynamicRelatedList', [
            ('maxRecordsToDisplay', '10'), ('parentFieldApiName', f'{self.obj}.Id'),
            ('relatedListApiName', rl), ('relatedListDisplayType', 'ADVGRID'), ('relatedListLabel', label),
            ('showActionBar', 'true'), ('sortFieldAlias', '__DEFAULT__'), ('sortFieldOrder', 'Default')], vis,
            value_lists=lists)
    def tab(self, title, body, active=None):
        p = [('active', active)] if active is not None else []
        return self.comp('flexipage:tab', p + [('body', body), ('title', title)])
    def tabset(self, facet):
        return self.comp('flexipage:tabset', [('label', 'Tabs'), ('tabs', facet)])

def build(obj):
    label, desc, actions, tabs = PAGES[obj]
    c = caps(obj); p = Page(obj)
    for t, lists in tabs:
        for rl, _ in lists:
            name_ = rl[1] if isinstance(rl, tuple) else rl
            assert name_ == 'ALERTCARD' or (isinstance(rl, tuple) and rl[0] == 'FLOW') or name_ in c['rels'], f'{obj}: no related list {name_}'
    header = [p.comp('force:highlightsPanel', [('collapsed', 'false'), ('enableActionsConfiguration', 'true'),
        ('enableActionsInNative', 'true'), ('hideChatterActions', 'true'), ('hideSlackAction', 'false'),
        ('numVisibleActions', '7')], value_lists={'actionNames': actions})]
    if obj == 'Account':
        header.append(p.comp('runtime_omnistudio:flexcard', [
            ('exposedAttributes', '{"Limit":"3","ChildLimit":"5","AggregateAlerts":false}'),
            ('flexcardName', 'ServiceExcellenceAlertCard')]))
    p.region('header', header, 'Region')
    left = []
    if obj == 'Account':
        p.region('duplicatesTabContent', [p.comp('runtime_sales_merge:mergeCandidatesPreviewCard', [('displayOption', 'BOTH')])])
        p.region('duplicatesTabs', [p.tab('Duplicates', 'duplicatesTabContent')])
        left.append(p.tabset('duplicatesTabs'))
    p.region('detailTabContent', [p.comp('force:detailPanel')])
    main = [p.tab('Standard.Tab.detail', 'detailTabContent', 'true')]
    hist = 'ActivityHistories' if c['act'] else ('Histories' if c['hist'] else None)
    if hist:
        p.region('historyTabContent', [p.related(hist)])
        main.append(p.tab('History', 'historyTabContent', 'false'))
    p.region('maintabs', main)
    left.append(p.tabset('maintabs'))
    p.region('leftcol', left, 'Region')
    right = []
    if tabs:
        ts = []
        # Relationships and Exams and Accommodations sit first but don't open by default.
        first = next((i for i, (t, _) in enumerate(tabs) if t not in FRONT_TABS), 0)
        for i, (title, lists) in enumerate(tabs):
            body = ''.join(w for w in title.title() if w.isalnum()) + 'TabContent'
            body = body[0].lower() + body[1:]
            p.region(body, [p.comp('runtime_omnistudio:flexcard', [
                ('exposedAttributes', '{"Limit":"25","ChildLimit":"5","AggregateAlerts":false}'),
                ('flexcardName', 'ServiceExcellenceAlertCard')]) if rl == 'ALERTCARD'
                else p.flow(rl[1], vis) if isinstance(rl, tuple) and rl[0] == 'FLOW'
                else p.dynamic(rl, vis) if isinstance(rl, tuple) else p.related(rl, vis) for rl, vis in lists])
            ts.append(p.tab(title, body, 'true' if i == first else None))
        p.region('objectTabs', ts)
        right.append(p.tabset('objectTabs'))
    if obj == 'RecordAlert':
        p.region('rightcol', right, 'Region')
        return finish(p, obj, label, desc)
    p.region('filesTabContent', [p.related('AttachedContentDocuments')])
    if obj not in NO_NOTES:
        p.region('notesTabContent', [p.related('AttachedContentNotes')])
    ft = [p.tab('Files', 'filesTabContent', 'true')]
    if obj not in NO_NOTES:
        ft.append(p.tab('Notes', 'notesTabContent'))
    if c['feed']:
        p.region('chatterTabContent', [p.comp('forceChatter:recordFeedContainer')])
        ft.append(p.tab('Chatter', 'chatterTabContent'))
    p.region('filesTabs', ft)
    right.append(p.tabset('filesTabs'))
    if c['act']:
        p.region('activityTabContent', [p.comp('runtime_sales_activities:activityPanel', [('showLegacyActivityComposer', 'false')])])
        p.region('sidebartabs', [p.tab('Activities', 'activityTabContent', 'true')])
        right.append(p.tabset('sidebartabs'))
    p.region('rightcol', right, 'Region')
    return finish(p, obj, label, desc)

def finish(p, obj, label, desc):
    name = obj.replace('__c', '') + 'RecordPage'
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<FlexiPage xmlns="http://soap.sforce.com/2006/04/metadata">\n'
           f'    <description>{escape(desc)}</description>\n' + ''.join(p.regions) +
           f'    <masterLabel>{label}</masterLabel>\n    <sobjectType>{obj}</sobjectType>\n'
           '    <template>\n        <name>flexipage:recordHomeTwoColEqualHeaderTemplateDesktop</name>\n    </template>\n'
           '    <type>RecordPage</type>\n</FlexiPage>\n')
    open(os.path.join(OUT, name + '.flexipage-meta.xml'), 'w').write(xml)
    return name

# Optional third argument: comma-separated objects to build (default: all).
ONLY = set(sys.argv[3].split(',')) if len(sys.argv) > 3 else set(PAGES)
for o in PAGES:
    if o in ONLY:
        print(o, build(o))
