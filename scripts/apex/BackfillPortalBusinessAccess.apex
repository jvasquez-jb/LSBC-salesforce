// One-time: queue the portal business access sync for every business whose owner, manager or school
// administrator already has a portal login. Businesses whose relationships and logins existed before the sync
// was built were never shared to those people. Ticking Portal Access Sync Pending runs the sync in the
// background (Record-Trigger: Account After Save), which unticks it. Safe to run again: the sync only adds
// missing shares and removes ones that no longer apply.
Set<Id> portalContacts = new Set<Id>();
for (User u : [SELECT ContactId FROM User WHERE IsActive = true AND ContactId != null]) {
    portalContacts.add(u.ContactId);
}
Map<Id, Account> toQueue = new Map<Id, Account>();
for (AccountContactRelation r : [
        SELECT AccountId FROM AccountContactRelation
        WHERE IsActive = true AND Account.IsPersonAccount = false AND ContactId IN :portalContacts
          AND Account.PortalAccessSyncPending__c = false
          AND Roles INCLUDES ('Owner', 'Manager', 'School Administrator')]) {
    toQueue.put(r.AccountId, new Account(Id = r.AccountId, PortalAccessSyncPending__c = true));
}
update toQueue.values();
System.debug('Businesses queued: ' + toQueue.size());
