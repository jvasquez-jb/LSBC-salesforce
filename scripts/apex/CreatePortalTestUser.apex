// Creates the portal test user on the StopCodeTest person account (sandbox only) and gives it
// the portal permission set licences and the Portal Licensee permission set. Safe to run again.
Account a = [SELECT Id, FirstName, LastName, PersonContactId, Owner.UserRoleId FROM Account WHERE IsPersonAccount = true AND Name LIKE 'StopCodeTest%' ORDER BY CreatedDate LIMIT 1];
System.assert(a.Owner.UserRoleId != null, 'The account owner needs a role before a portal user can be created.');
List<User> existing = [SELECT Id FROM User WHERE ContactId = :a.PersonContactId];
User u;
if (existing.isEmpty()) {
    Profile p = [SELECT Id FROM Profile WHERE Name = 'LSBC Portal User'];
    u = new User(ContactId = a.PersonContactId, ProfileId = p.Id, FirstName = a.FirstName, LastName = a.LastName,
        Username = 'stopcodetest.portal@lsbc-partial.test', Email = 'jvasquez+lsbcportal@journeyblazers.com',
        Alias = 'sctport', CommunityNickname = 'stopcodetest.portal', TimeZoneSidKey = 'America/Chicago',
        LocaleSidKey = 'en_US', EmailEncodingKey = 'UTF-8', LanguageLocaleKey = 'en_US');
    insert u;
} else { u = existing[0]; }
Set<String> licences = new Set<String>{'PublicSectorCmtyAccessPSL', 'BRECmtyRuntime', 'DocumentChecklistPsl', 'LPIAppPSL'};
Set<Id> have = new Set<Id>();
for (PermissionSetLicenseAssign x : [SELECT PermissionSetLicenseId FROM PermissionSetLicenseAssign WHERE AssigneeId = :u.Id]) have.add(x.PermissionSetLicenseId);
List<PermissionSetLicenseAssign> psla = new List<PermissionSetLicenseAssign>();
for (PermissionSetLicense l : [SELECT Id FROM PermissionSetLicense WHERE DeveloperName IN :licences]) {
    if (!have.contains(l.Id)) psla.add(new PermissionSetLicenseAssign(AssigneeId = u.Id, PermissionSetLicenseId = l.Id));
}
insert psla;
PermissionSet ps = [SELECT Id FROM PermissionSet WHERE Name = 'PortalLicensee'];
if ([SELECT COUNT() FROM PermissionSetAssignment WHERE AssigneeId = :u.Id AND PermissionSetId = :ps.Id] == 0) {
    insert new PermissionSetAssignment(AssigneeId = u.Id, PermissionSetId = ps.Id);
}
System.debug('Portal user ' + u.Id + ', licences added ' + psla.size());
