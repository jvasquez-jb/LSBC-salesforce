"""Writes SubflowPortalBusinessAccessSync: portal access for a business's owners, managers and school administrators.

A sharing set can't filter Account Contact Relations by role, so this flow keeps manual share records in step
instead. For one business account it finds the active relationships with role Owner, Manager or School
Administrator, takes those people's active portal logins, and:
  - shares the account and its licenses, business applications, violations and fees (Read) with each login;
  - removes manual shares held by any other portal login (someone whose relationship ended or changed role).
Manual shares to staff are left alone. The record's owner never gets a share (they already have access).

Run: python3 -I scripts/generators/portalaccess.py force-app/main/default/flows
"""
import os
import sys
from xml.sax.saxutils import escape as e

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import flowlib as F
from flowlib import REF, STR, BOOL, cond

NAME = 'SubflowPortalBusinessAccessSync'
ROLES = ['Owner', 'Manager', 'School Administrator']

# (key, object, label plural, field linking to the business, share object, share parent field, access field)
CHILDREN = [
    ('Account', 'Account', 'Business', 'Id', 'AccountShare', 'AccountId', 'AccountAccessLevel'),
    ('License', 'BusinessLicense', 'Licenses', 'AccountId', 'BusinessLicenseShare', 'ParentId', 'AccessLevel'),
    ('Application', 'BusinessLicenseApplication', 'Applications', 'AccountId', 'BusinessLicenseApplicationShare', 'ParentId', 'AccessLevel'),
    ('Violation', 'RegulatoryCodeViolation', 'Violations', 'Establishment__c', 'RegulatoryCodeViolationShare', 'ParentId', 'AccessLevel'),
    ('Fee', 'RegulatoryTrxnFee', 'Fees', 'AccountId', 'RegulatoryTrxnFeeShare', 'ParentId', 'AccessLevel'),
]

extra = {'recordDeletes': [], 'recordUpdates': []}


def delete_many(name, label, ref, nxt):
    extra['recordDeletes'].append(f'<recordDeletes><name>{name}</name><label>{e(label)}</label>{F.loc()}{F.conn(nxt)}'
                                  f'<inputReference>{ref}</inputReference></recordDeletes>')


def build(outdir):
    F.var('varT_AccountId', 'String', 'The business account to bring up to date.', inp=True)
    F.var('varT_ContactIds', 'String', 'People related to the business as Owner, Manager or School Administrator.', coll=True)
    F.var('varT_UserKeys', 'String', 'Their active portal logins, as ;id; pairs, to test membership.')
    F.var('varT_ShareUserIds', 'String', 'Every user or group holding a manual share on the business or its records.', coll=True)
    F.var('varT_PortalShareKeys', 'String', 'Those holders who are portal logins, as ;id; pairs.')
    F.var('varT_ExistingKeys', 'String', 'Shares that stay, as ;recordId:userId; pairs, so they aren\'t created twice.')

    # Start: the business, its qualifying relationships and their portal logins.
    F.lookup('GetAccount', 'Get Account', 'Account', [('Id', 'EqualTo', REF('varT_AccountId'))],
             ['Id', 'OwnerId', 'IsPersonAccount'], 'IsItABusiness', first=True, sort=None)
    F.decision('IsItABusiness', 'Is It a Business Account?', [
        ('Business', 'Yes', [cond('GetAccount.Id', 'IsNull', BOOL(False)), cond('GetAccount.IsPersonAccount', 'EqualTo', BOOL(False))],
         'GetRelationships', 'and')], None, default_label='No, a person or not found')
    F.lookup('GetRelationships', 'Get Account Contact Relations', 'AccountContactRelation',
             [('AccountId', 'EqualTo', REF('varT_AccountId')), ('IsActive', 'EqualTo', BOOL(True))],
             ['Id', 'ContactId', 'Roles'], 'LoopThroughRelationships', sort='Id')
    F.loop('LoopThroughRelationships', 'Loop Through Account Contact Relations', 'GetRelationships',
           'DoesTheRoleGivePortalAccess', 'AreThereRelatedPeople')
    F.formula('forB_RoleGivesAccess', 'Boolean',
              ' || '.join(f'INCLUDES({{!LoopThroughRelationships.Roles}}, "{r}")' for r in ROLES),
              'The relationship has a role that sees the business on the portal: ' + ', '.join(ROLES) + '.')
    F.decision('DoesTheRoleGivePortalAccess', 'Does the Role Give Portal Access?', [
        ('GivesAccess', 'Yes', [cond('forB_RoleGivesAccess', 'EqualTo', BOOL(True))], 'AddContact', 'and')],
        'LoopThroughRelationships')
    F.assignment('AddContact', 'Add Contact', [('varT_ContactIds', 'Add', REF('LoopThroughRelationships.ContactId'))],
                 'LoopThroughRelationships')
    F.decision('AreThereRelatedPeople', 'Are There Related People?', [
        ('HasPeople', 'Yes', [cond('varT_ContactIds', 'IsEmpty', BOOL(False))], 'GetPortalUsers', 'and')],
        f'Get{CHILDREN[0][0]}Records', default_label='No')
    F.lookup('GetPortalUsers', 'Get Portal Users', 'User',
             [('ContactId', 'In', REF('varT_ContactIds')), ('IsActive', 'EqualTo', BOOL(True))],
             ['Id', 'ContactId'], 'LoopThroughPortalUsers', sort='Id')
    F.loop('LoopThroughPortalUsers', 'Loop Through Portal Users', 'GetPortalUsers', 'AddUserKey', f'Get{CHILDREN[0][0]}Records')
    F.formula('forT_UserKey', 'String', '{!LoopThroughPortalUsers.Id} & ";"', 'The portal login\'s Id followed by a separator.')
    F.assignment('AddUserKey', 'Add User Key', [('varT_UserKeys', 'Add', REF('forT_UserKey'))], 'LoopThroughPortalUsers')

    # Phase A: each object's records and their manual shares; collect every share holder.
    for i, (k, obj, plural, link, share, parent, level) in enumerate(CHILDREN):
        nxt_obj = f'Get{CHILDREN[i + 1][0]}Records' if i + 1 < len(CHILDREN) else 'AreThereShareHolders'
        F.var(f'varT_{k}Ids', 'String', f'Ids of the business\'s {plural.lower()}.', coll=True)
        F.lookup(f'Get{k}Records', f'Get {plural}', obj, [(link, 'EqualTo', REF('varT_AccountId'))],
                 ['Id', 'OwnerId'], f'AreThere{k}Records', sort='Id')
        F.decision(f'AreThere{k}Records', f'Are There {plural}?', [
            (f'Has{k}', 'Yes', [cond(f'Get{k}Records', 'IsNull', BOOL(False))], f'LoopThrough{k}Records', 'and')], nxt_obj)
        F.loop(f'LoopThrough{k}Records', f'Loop Through {plural}', f'Get{k}Records', f'Add{k}Id', f'Get{k}Shares')
        F.assignment(f'Add{k}Id', f'Add {k} Id', [(f'varT_{k}Ids', 'Add', REF(f'LoopThrough{k}Records.Id'))], f'LoopThrough{k}Records')
        F.lookup(f'Get{k}Shares', f'Get {k} Manual Shares', share,
                 [(parent, 'In', REF(f'varT_{k}Ids')), ('RowCause', 'EqualTo', STR('Manual'))],
                 ['Id', parent, 'UserOrGroupId'], f'LoopThrough{k}ShareHolders', sort='Id')
        F.loop(f'LoopThrough{k}ShareHolders', f'Loop Through {k} Share Holders', f'Get{k}Shares', f'Add{k}ShareHolder', nxt_obj)
        F.assignment(f'Add{k}ShareHolder', f'Add {k} Share Holder',
                     [('varT_ShareUserIds', 'Add', REF(f'LoopThrough{k}ShareHolders.UserOrGroupId'))], f'LoopThrough{k}ShareHolders')

    # Phase B: which share holders are portal logins.
    F.decision('AreThereShareHolders', 'Are There Manual Share Holders?', [
        ('HasHolders', 'Yes', [cond('varT_ShareUserIds', 'IsEmpty', BOOL(False))], 'GetPortalShareHolders', 'and')],
        f'Is{CHILDREN[0][0]}Checked')
    F.lookup('GetPortalShareHolders', 'Get Portal Share Holders', 'User',
             [('Id', 'In', REF('varT_ShareUserIds')), ('IsPortalEnabled', 'EqualTo', BOOL(True))],
             ['Id'], 'LoopThroughPortalShareHolders', sort='Id')
    F.loop('LoopThroughPortalShareHolders', 'Loop Through Portal Share Holders', 'GetPortalShareHolders',
           'AddPortalShareKey', f'Is{CHILDREN[0][0]}Checked')
    F.formula('forT_PortalShareKey', 'String', '{!LoopThroughPortalShareHolders.Id} & ";"', 'The holder\'s Id followed by a separator.')
    F.assignment('AddPortalShareKey', 'Add Portal Share Key', [('varT_PortalShareKeys', 'Add', REF('forT_PortalShareKey'))],
                 'LoopThroughPortalShareHolders')

    # Phase C: per object, remove shares of portal logins no longer related, create missing ones.
    for i, (k, obj, plural, link, share, parent, level) in enumerate(CHILDREN):
        nxt_obj = f'Is{CHILDREN[i + 1][0]}Checked' if i + 1 < len(CHILDREN) else None
        F.var(f'varR_{k}SharesToDelete', 'SObject', f'{k} shares to remove.', coll=True, obj=share)
        F.var(f'varR_{k}SharesToCreate', 'SObject', f'{k} shares to add.', coll=True, obj=share)
        F.var(f'varR_{k}Share', 'SObject', f'One {k.lower()} share being built.', obj=share)
        F.decision(f'Is{k}Checked', f'Were {plural} Found?', [
            (f'{k}Found', 'Yes', [cond(f'Get{k}Records', 'IsNull', BOOL(False))], f'LoopThroughExisting{k}Shares', 'and')],
            nxt_obj, default_label='No')
        F.loop(f'LoopThroughExisting{k}Shares', f'Loop Through Existing {k} Shares', f'Get{k}Shares',
               f'Is{k}ShareHolderStillRelated', f'LoopThrough{k}RecordsForUsers')
        F.formula(f'forB_{k}HolderIsPortal', 'Boolean',
                  f'CONTAINS(";" & {{!varT_PortalShareKeys}}, ";" & {{!LoopThroughExisting{k}Shares.UserOrGroupId}} & ";")',
                  'The share holder is a portal login.')
        F.formula(f'forB_{k}HolderIsRelated', 'Boolean',
                  f'CONTAINS(";" & {{!varT_UserKeys}}, ";" & {{!LoopThroughExisting{k}Shares.UserOrGroupId}} & ";")',
                  'The share holder is a portal login of a current Owner, Manager or School Administrator.')
        F.formula(f'forT_{k}ExistingKey', 'String',
                  f'{{!LoopThroughExisting{k}Shares.{parent}}} & ":" & {{!LoopThroughExisting{k}Shares.UserOrGroupId}} & ";"',
                  'The share as record:user, followed by a separator.')
        F.decision(f'Is{k}ShareHolderStillRelated', 'Is the Share Holder Still Related?', [
            (f'{k}Related', 'Yes, keep it', [cond(f'forB_{k}HolderIsRelated', 'EqualTo', BOOL(True))], f'Keep{k}Share', 'and'),
            (f'{k}NoLongerRelated', 'No, a portal login no longer related',
             [cond(f'forB_{k}HolderIsPortal', 'EqualTo', BOOL(True))], f'Remove{k}Share', 'and')],
            f'LoopThroughExisting{k}Shares', default_label='Staff share, leave it')
        F.assignment(f'Keep{k}Share', f'Keep {k} Share', [('varT_ExistingKeys', 'Add', REF(f'forT_{k}ExistingKey'))],
                     f'LoopThroughExisting{k}Shares')
        F.assignment(f'Remove{k}Share', f'Remove {k} Share', [(f'varR_{k}SharesToDelete', 'Add', REF(f'LoopThroughExisting{k}Shares'))],
                     f'LoopThroughExisting{k}Shares')

        F.loop(f'LoopThrough{k}RecordsForUsers', f'Loop Through {plural} for Portal Users', f'Get{k}Records',
               f'AreThereUsersFor{k}', f'AreThere{k}SharesToDelete')
        F.decision(f'AreThereUsersFor{k}', 'Are There Portal Users?', [
            (f'{k}HasUsers', 'Yes', [cond('GetPortalUsers', 'IsNull', BOOL(False))], f'LoopThroughPortalUsersFor{k}', 'and')],
            f'LoopThrough{k}RecordsForUsers')
        F.loop(f'LoopThroughPortalUsersFor{k}', f'Loop Through Portal Users for {k}', 'GetPortalUsers',
               f'DoesThe{k}ShareExist', f'LoopThrough{k}RecordsForUsers')
        F.formula(f'forB_{k}NeedsShare', 'Boolean',
                  f'{{!LoopThroughPortalUsersFor{k}.Id}} != {{!LoopThrough{k}RecordsForUsers.OwnerId}} && '
                  f'NOT(CONTAINS(";" & {{!varT_ExistingKeys}}, ";" & {{!LoopThrough{k}RecordsForUsers.Id}} & ":" & {{!LoopThroughPortalUsersFor{k}.Id}} & ";"))',
                  'The portal login doesn\'t own the record and has no share on it yet.')
        F.decision(f'DoesThe{k}ShareExist', 'Does the Portal User Need a Share?', [
            (f'{k}NeedsShare', 'Yes', [cond(f'forB_{k}NeedsShare', 'EqualTo', BOOL(True))], f'Set{k}ShareFields', 'and')],
            f'LoopThroughPortalUsersFor{k}', default_label='No, owner or already shared')
        items = [(f'varR_{k}Share.{parent}', 'Assign', REF(f'LoopThrough{k}RecordsForUsers.Id')),
                 (f'varR_{k}Share.UserOrGroupId', 'Assign', REF(f'LoopThroughPortalUsersFor{k}.Id')),
                 (f'varR_{k}Share.{level}', 'Assign', STR('Read'))]
        if share == 'AccountShare':
            items += [('varR_AccountShare.OpportunityAccessLevel', 'Assign', STR('None')),
                      ('varR_AccountShare.CaseAccessLevel', 'Assign', STR('None'))]
        else:
            items.append((f'varR_{k}Share.RowCause', 'Assign', STR('Manual')))
        F.assignment(f'Set{k}ShareFields', f'Set {k} Share Fields', items, f'Add{k}ShareToCreate')
        F.assignment(f'Add{k}ShareToCreate', f'Add {k} Share to Create', [(f'varR_{k}SharesToCreate', 'Add', REF(f'varR_{k}Share'))],
                     f'LoopThroughPortalUsersFor{k}')
        F.decision(f'AreThere{k}SharesToDelete', f'Are There {k} Shares to Remove?', [
            (f'{k}HasDeletes', 'Yes', [cond(f'varR_{k}SharesToDelete', 'IsEmpty', BOOL(False))], f'Delete{k}Shares', 'and')],
            f'AreThere{k}SharesToCreate')
        delete_many(f'Delete{k}Shares', f'Delete {k} Shares', f'varR_{k}SharesToDelete', f'AreThere{k}SharesToCreate')
        F.decision(f'AreThere{k}SharesToCreate', f'Are There {k} Shares to Add?', [
            (f'{k}HasCreates', 'Yes', [cond(f'varR_{k}SharesToCreate', 'IsEmpty', BOOL(False))], f'Create{k}Shares', 'and')],
            nxt_obj)
        F.els['recordCreates'].append(f'<recordCreates><name>Create{k}Shares</name><label>Create {k} Shares</label>{F.loc()}'
                                      f'{F.conn(nxt_obj)}<inputReference>varR_{k}SharesToCreate</inputReference></recordCreates>')

    desc = ('Gives the portal logins of a business\'s Owners, Managers and School Administrators read access to the business, '
            'its licenses, business applications, violations and fees, and removes that access from portal logins no longer '
            'related in one of those roles. Manual shares to staff are left alone, and a record\'s owner gets no share. Run in '
            'the background by Record-Trigger: Account After Save when Portal Access Sync Pending is ticked. A sharing set can\'t '
            'tell relationship roles apart, which is why this keeps share records instead.')
    j = lambda t: ''.join(F.els[t])
    x = ('<?xml version="1.0" encoding="UTF-8"?>\n<Flow xmlns="http://soap.sforce.com/2006/04/metadata">'
         f'<apiVersion>66.0</apiVersion>{j("assignments")}{j("decisions")}<description>{e(desc)}</description>'
         f'<environments>Default</environments>{j("formulas")}'
         '<interviewLabel>Subflow: Portal Business Access Sync {!$Flow.CurrentDateTime}</interviewLabel>'
         f'<label>Subflow: Portal Business Access Sync</label>{j("loops")}'
         '<processMetadataValues><name>BuilderType</name><value><stringValue>LightningFlowBuilder</stringValue></value></processMetadataValues>'
         '<processMetadataValues><name>CanvasMode</name><value><stringValue>AUTO_LAYOUT_CANVAS</stringValue></value></processMetadataValues>'
         '<processMetadataValues><name>OriginBuilderType</name><value><stringValue>LightningFlowBuilder</stringValue></value></processMetadataValues>'
         '<processType>AutoLaunchedFlow</processType>'
         + j('recordCreates') + ''.join(extra['recordDeletes']) + j('recordLookups')
         + '<runInMode>SystemModeWithoutSharing</runInMode>'
         f'<start>{F.loc()}{F.conn("GetAccount")}</start><status>Active</status>' + j('variables') + '</Flow>\n')
    with open(os.path.join(outdir, NAME + '.flow-meta.xml'), 'w') as f:
        f.write(x)
    print('wrote', NAME)


ORDER = ['actionCalls', 'apexPluginCalls', 'assignments', 'choices', 'collectionProcessors', 'constants', 'customErrors',
         'decisions', 'description', 'dynamicChoiceSets', 'environments', 'formulas', 'interviewLabel', 'label', 'loops',
         'processMetadataValues', 'processType', 'recordCreates', 'recordDeletes', 'recordLookups', 'recordRollbacks',
         'recordUpdates', 'runInMode', 'screens', 'stages', 'start', 'status', 'subflows', 'textTemplates', 'variables', 'waits']


def insert(s, tag, snippet):
    """Puts an element where the flow schema expects its type."""
    for t in ORDER[ORDER.index(tag):]:
        i = s.find(f'<{t}>')
        if i >= 0:
            return s[:i] + snippet + s[i:]
    return s.replace('</Flow>', snippet + '</Flow>')


def tick(name, label, idref, nxt, extra_filters=''):
    """Update element that ticks Portal Access Sync Pending on a business account."""
    return (f'<recordUpdates><name>{name}</name><description>Queues the background portal access sync for the business '
            f'(Record-Trigger: Account After Save) instead of changing access during this save.</description>'
            f'<label>{e(label)}</label>{F.loc()}{F.conn(nxt)}<filterLogic>and</filterLogic>'
            f'<filters><field>Id</field><operator>EqualTo</operator><value><elementReference>{idref}</elementReference></value></filters>'
            '<filters><field>IsPersonAccount</field><operator>EqualTo</operator><value><booleanValue>false</booleanValue></value></filters>'
            '<filters><field>PortalAccessSyncPending__c</field><operator>EqualTo</operator><value><booleanValue>false</booleanValue></value></filters>'
            f'{extra_filters}<inputAssignments><field>PortalAccessSyncPending__c</field><value><booleanValue>true</booleanValue></value>'
            '</inputAssignments><object>Account</object></recordUpdates>')


def retarget_start(s, new):
    """Points the start element at a new first element; returns the old first element."""
    st = s[s.index('<start>'):s.index('</start>')]
    old = st[st.index('<targetReference>') + 17:st.index('</targetReference>')]
    st2 = st.replace(f'<targetReference>{old}</targetReference>', f'<targetReference>{new}</targetReference>', 1)
    return s.replace(st, st2, 1), old


def new_or_moved(name, link, nxt, default):
    return (f'<decisions><name>{name}</name><label>Is It New or Moved to Another Business?</label>{F.loc()}'
            f'{F.conn(default, "defaultConnector")}<defaultConnectorLabel>No</defaultConnectorLabel>'
            f'<rules><name>NewOrMoved</name><conditionLogic>or</conditionLogic>'
            f'<conditions><leftValueReference>$Record__Prior.Id</leftValueReference><operator>IsNull</operator><rightValue><booleanValue>true</booleanValue></rightValue></conditions>'
            f'<conditions><leftValueReference>$Record.{link}</leftValueReference><operator>NotEqualTo</operator><rightValue><elementReference>$Record__Prior.{link}</elementReference></rightValue></conditions>'
            f'{F.conn(nxt)}<label>Yes</label></rules></decisions>')


def patch(outdir):
    def edit(fname, fn):
        p = os.path.join(outdir, fname + '.flow-meta.xml')
        s = open(p).read()
        if 'PortalAccessSyncPending__c' in s:
            print('already patched', fname)
            return
        open(p, 'w').write(fn(s))
        print('patched', fname)

    # Account Contact Relation: the salon's tick sits in the "first record for the salon" branch.
    def acr_after(s):
        s = s.replace('<targetReference>SetSalonStopCodeSyncPendingToTrue</targetReference>',
                      '<targetReference>SetSalonPortalAccessSyncPendingToTrue</targetReference>', 1)
        return insert(s, 'recordUpdates', tick('SetSalonPortalAccessSyncPendingToTrue', 'Set Salon Portal Access Sync Pending to True',
                                               '$Record.AccountId', 'SetSalonStopCodeSyncPendingToTrue'))
    edit('RecordTriggerAccountContactRelationAfterSave', acr_after)

    def acr_delete(s):
        s, old = retarget_start(s, 'SetSalonPortalAccessSyncPendingToTrue')
        return insert(s, 'recordUpdates', tick('SetSalonPortalAccessSyncPendingToTrue', 'Set Salon Portal Access Sync Pending to True',
                                               '$Record.AccountId', old))
    edit('RecordTriggerAccountContactRelationBeforeDelete', acr_delete)

    def child(link, kind):
        def fn(s):
            s, old = retarget_start(s, 'IsItNewOrMovedToAnotherBusiness')
            s = insert(s, 'decisions', new_or_moved('IsItNewOrMovedToAnotherBusiness', link, 'SetPortalAccessSyncPendingToTrue', old))
            return insert(s, 'recordUpdates', tick('SetPortalAccessSyncPendingToTrue', 'Set Portal Access Sync Pending to True',
                                                   f'$Record.{link}', old))
        return fn
    edit('RecordTriggerBusinessLicenseAfterSave', child('AccountId', 'license'))
    edit('RecordTriggerRegulatoryTransactionFeeAfterSave', child('AccountId', 'fee'))

    def violation(s):  # create only
        s, old = retarget_start(s, 'SetPortalAccessSyncPendingToTrue')
        return insert(s, 'recordUpdates', tick('SetPortalAccessSyncPendingToTrue', 'Set Portal Access Sync Pending to True',
                                               '$Record.Establishment__c', old))
    edit('RecordTriggerRegulatoryCodeViolationAfterSave', violation)

    # A new portal login: tick every business the person is related to.
    def user(s):
        s = s.replace('<recordCreates><name>AssignPortalLicenseeAccess</name>',
                      '<recordCreates><name>AssignPortalLicenseeAccess</name>' + F.conn('GetBusinessRelationships'), 1)
        s = insert(s, 'recordLookups',
                   '<recordLookups><name>GetBusinessRelationships</name><label>Get Business Relationships</label>'
                   f'{F.loc()}<assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>{F.conn("LoopThroughBusinessRelationships")}'
                   '<filterLogic>and</filterLogic><filters><field>ContactId</field><operator>EqualTo</operator><value><elementReference>$Record.ContactId</elementReference></value></filters>'
                   '<filters><field>IsDirect</field><operator>EqualTo</operator><value><booleanValue>false</booleanValue></value></filters>'
                   '<getFirstRecordOnly>false</getFirstRecordOnly><object>AccountContactRelation</object><queriedFields>Id</queriedFields>'
                   '<queriedFields>AccountId</queriedFields><storeOutputAutomatically>true</storeOutputAutomatically></recordLookups>')
        s = insert(s, 'loops',
                   f'<loops><name>LoopThroughBusinessRelationships</name><label>Loop Through Business Relationships</label>{F.loc()}'
                   '<collectionReference>GetBusinessRelationships</collectionReference><iterationOrder>Asc</iterationOrder>'
                   f'{F.conn("SetBusinessToSync", "nextValueConnector")}{F.conn("AreThereBusinessesToSync", "noMoreValuesConnector")}</loops>')
        s = insert(s, 'assignments',
                   f'<assignments><name>SetBusinessToSync</name><label>Set Business to Sync</label>{F.loc()}'
                   '<assignmentItems><assignToReference>varR_Business.Id</assignToReference><operator>Assign</operator><value><elementReference>LoopThroughBusinessRelationships.AccountId</elementReference></value></assignmentItems>'
                   '<assignmentItems><assignToReference>varR_Business.PortalAccessSyncPending__c</assignToReference><operator>Assign</operator><value><booleanValue>true</booleanValue></value></assignmentItems>'
                   f'{F.conn("AddBusinessToSync")}</assignments>'
                   f'<assignments><name>AddBusinessToSync</name><label>Add Business to Sync</label>{F.loc()}'
                   '<assignmentItems><assignToReference>varR_BusinessesToSync</assignToReference><operator>Add</operator><value><elementReference>varR_Business</elementReference></value></assignmentItems>'
                   f'{F.conn("LoopThroughBusinessRelationships")}</assignments>')
        s = insert(s, 'decisions',
                   f'<decisions><name>AreThereBusinessesToSync</name><label>Are There Businesses to Sync?</label>{F.loc()}'
                   '<defaultConnectorLabel>No</defaultConnectorLabel><rules><name>HasBusinesses</name><conditionLogic>and</conditionLogic>'
                   '<conditions><leftValueReference>varR_BusinessesToSync</leftValueReference><operator>IsEmpty</operator><rightValue><booleanValue>false</booleanValue></rightValue></conditions>'
                   f'{F.conn("SetPortalAccessSyncPendingOnBusinesses")}<label>Yes</label></rules></decisions>')
        s = insert(s, 'recordUpdates',
                   '<recordUpdates><name>SetPortalAccessSyncPendingOnBusinesses</name><description>Queues the background portal access '
                   'sync (Record-Trigger: Account After Save) for every business the new portal user is related to.</description>'
                   f'<label>Set Portal Access Sync Pending on Businesses</label>{F.loc()}<inputReference>varR_BusinessesToSync</inputReference></recordUpdates>')
        return insert(s, 'variables',
                      '<variables><name>varR_Business</name><description>One business to queue for the portal access sync.</description>'
                      '<dataType>SObject</dataType><isCollection>false</isCollection><isInput>false</isInput><isOutput>false</isOutput><objectType>Account</objectType></variables>'
                      '<variables><name>varR_BusinessesToSync</name><description>The businesses the new portal user is related to.</description>'
                      '<dataType>SObject</dataType><isCollection>true</isCollection><isInput>false</isInput><isOutput>false</isOutput><objectType>Account</objectType></variables>')
    edit('RecordTriggerUserAfterSave', user)


if __name__ == '__main__':
    build(sys.argv[1])
    patch(sys.argv[1])
