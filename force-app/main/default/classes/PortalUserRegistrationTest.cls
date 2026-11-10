/**
 * Tests for PortalUserRegistration. Site.createExternalUser can't create users in a test, so
 * these cover the checks before it and that a failure comes back as a message, not an error.
 */
@IsTest
private class PortalUserRegistrationTest {

    private static Account personAccount() {
        Id personType = Schema.SObjectType.Account.getRecordTypeInfosByDeveloperName().get('PersonAccount').getRecordTypeId();
        Account a = new Account(RecordTypeId = personType, FirstName = 'Reg', LastName = 'Tester', PersonEmail = 'reg.tester@example.org');
        insert a;
        return [SELECT Id, PersonContactId FROM Account WHERE Id = :a.Id];
    }

    private static PortalUserRegistration.Request request(Id accountId, String email) {
        PortalUserRegistration.Request r = new PortalUserRegistration.Request();
        r.accountId = accountId;
        r.email = email;
        return r;
    }

    @IsTest
    static void returnsAMessageWhenTheUserCantBeCreated() {
        Account a = personAccount();
        Test.startTest();
        List<PortalUserRegistration.Result> res = PortalUserRegistration.createPortalUsers(
            new List<PortalUserRegistration.Request>{ request(a.Id, ' Reg.Tester.' + Crypto.getRandomInteger() + '@example.org ') });
        Test.stopTest();
        System.assertEquals(1, res.size());
        System.assert(res[0].userId != null || res[0].errorMessage != null, 'Either a user or a message comes back');
    }

    @IsTest
    static void refusesAnEmailAlreadyUsedAsAUsername() {
        Account a = personAccount();
        User me = [SELECT Username FROM User WHERE Id = :UserInfo.getUserId()];
        List<PortalUserRegistration.Result> res = PortalUserRegistration.createPortalUsers(
            new List<PortalUserRegistration.Request>{ request(a.Id, me.Username) });
        System.assertEquals(null, res[0].userId);
        System.assert(res[0].errorMessage.contains('already used'), res[0].errorMessage);
    }

    @IsTest
    static void refusesAPersonWhoAlreadyHasALogin() {
        Account a = personAccount();
        Id profileId = [SELECT Id FROM Profile WHERE Name = :PortalUserRegistration.PORTAL_PROFILE].Id;
        User existing = new User(ContactId = a.PersonContactId, ProfileId = profileId, FirstName = 'Reg', LastName = 'Tester',
            Username = 'reg.existing.' + Crypto.getRandomInteger() + '@example.org', Email = 'reg.existing@example.org',
            Alias = 'regex', TimeZoneSidKey = 'America/Chicago', LocaleSidKey = 'en_US', EmailEncodingKey = 'UTF-8', LanguageLocaleKey = 'en_US');
        System.runAs(new User(Id = UserInfo.getUserId())) { insert existing; }
        List<PortalUserRegistration.Result> res = PortalUserRegistration.createPortalUsers(
            new List<PortalUserRegistration.Request>{ request(a.Id, 'reg.new.' + Crypto.getRandomInteger() + '@example.org') });
        System.assertEquals(null, res[0].userId);
        System.assert(res[0].errorMessage.contains('already have'), res[0].errorMessage);
    }
}
