@IsTest
private class LicensePdfControllerTest {
    @TestSetup
    static void setup() {
        Id personType = Schema.SObjectType.Account.getRecordTypeInfosByDeveloperName().get('PersonAccount').getRecordTypeId();
        Account holder = new Account(RecordTypeId = personType, FirstName = 'Denada', LastName = 'Deneros', CertificationNumber__pc = '1293580101',
            PersonMailingStreet = '1 Test St', PersonMailingCity = 'Baton Rouge', PersonMailingPostalCode = '70809');
        insert holder;
        RegulatoryAuthorizationType licenseType = new RegulatoryAuthorizationType(Name = 'Test Cosmetologist', RegulatoryAuthCategory = 'License');
        insert licenseType;
        insert new List<BusinessLicense>{
            new BusinessLicense(Name = 'Ready', AccountId = holder.Id, RegulatoryAuthorizationTypeId = licenseType.Id, Identifier = '1293580101-C',
                PrintRequestedDate__c = Date.today(), RenewalCount__c = 1, PeriodEnd = Datetime.newInstanceGmt(2028, 1, 1, 18, 0, 0), Status = 'Active'),
            new BusinessLicense(Name = 'Not waiting', AccountId = holder.Id, RegulatoryAuthorizationTypeId = licenseType.Id, Identifier = '1293580101-M',
                Status = 'Active')
        };
    }

    @IsTest
    static void printsOnlyLicensesWaitingToPrint() {
        List<Id> ids = new List<Id>(new Map<Id, BusinessLicense>([SELECT Id FROM BusinessLicense]).keySet());
        LicensePdfController controller = new LicensePdfController(ids);
        Assert.areEqual(1, controller.sheets.size(), 'Only the license waiting to print gets a sheet');
        Assert.areEqual(1, controller.skippedCount);
        LicensePdfController.Sheet sheet = controller.sheets[0];
        Assert.areEqual('L1293580101', sheet.certificationNumber, 'A person prints their certification number, with the L in front');
        Assert.areEqual('Test Cosmetologist-Renewal', sheet.typeLine);
        Assert.areEqual('Deneros, Denada', sheet.holderName);
        Assert.areEqual('January 1, 2028', sheet.expirationDate);
        Assert.areEqual(2, sheet.addressLines.size());
        Assert.areEqual(Label.LicenseGovernorName, controller.governor);
    }

    @IsTest
    static void opensFromTheListButton() {
        List<BusinessLicense> licenses = [SELECT Id FROM BusinessLicense];
        Test.setCurrentPage(Page.LicensePdf);
        ApexPages.currentPage().getParameters().put('dx', '0.1');
        ApexPages.currentPage().getParameters().put('dy', 'not a number');
        ApexPages.StandardSetController setController = new ApexPages.StandardSetController(licenses);
        setController.setSelected(licenses);
        LicensePdfController controller = new LicensePdfController(setController);
        Assert.areEqual(0.1, controller.offsetX);
        Assert.areEqual(0, controller.offsetY);
        Assert.areEqual(1, controller.sheets.size());
    }

    @IsTest
    static void printsTheEstablishmentNumber() {
        Account salon = new Account(Name = 'Test Salon', CertificationNumber__c = '779947961', BillingStreet = '2 Test St', BillingCity = 'Baton Rouge');
        insert salon;
        Id licenseType = [SELECT Id FROM RegulatoryAuthorizationType LIMIT 1].Id;
        BusinessLicense license = new BusinessLicense(Name = 'Salon', AccountId = salon.Id, RegulatoryAuthorizationTypeId = licenseType,
            Identifier = '779947961-SH', PrintRequestedDate__c = Date.today(), Status = 'Active');
        insert license;
        LicensePdfController.Sheet sheet = new LicensePdfController(new List<Id>{ license.Id }).sheets[0];
        Assert.areEqual('L779947961', sheet.certificationNumber, 'An establishment prints its certification number');
        Assert.areEqual('Test Salon', sheet.holderName);
        Assert.areEqual('Test Cosmetologist-New', sheet.typeLine);
    }

    @IsTest
    static void printsATypedSchoolNumberWithoutTheL() {
        Account school = new Account(Name = 'Test School', BillingStreet = '3 Test St', BillingCity = 'Baton Rouge');
        insert school;
        Id licenseType = [SELECT Id FROM RegulatoryAuthorizationType LIMIT 1].Id;
        BusinessLicense license = new BusinessLicense(Name = 'School', AccountId = school.Id, RegulatoryAuthorizationTypeId = licenseType,
            Identifier = 'SC-1500', PrintRequestedDate__c = Date.today(), Status = 'Active');
        insert license;
        LicensePdfController.Sheet sheet = new LicensePdfController(new List<Id>{ license.Id }).sheets[0];
        Assert.areEqual('SC-1500', sheet.certificationNumber, 'A typed license number prints as it is, with no L');
    }

    @IsTest
    static void skipsARevokedLicense() {
        Account salon = new Account(Name = 'Revoked Salon', CertificationNumber__c = '779947962', BillingStreet = '4 Test St', BillingCity = 'Baton Rouge');
        insert salon;
        Id licenseType = [SELECT Id FROM RegulatoryAuthorizationType LIMIT 1].Id;
        BusinessLicense license = new BusinessLicense(Name = 'Revoked', AccountId = salon.Id, RegulatoryAuthorizationTypeId = licenseType,
            Identifier = '779947962-SH', PrintRequestedDate__c = Date.today(), Status = 'Revoked');
        insert license;
        Assert.isFalse([SELECT IsReadyToPrint__c FROM BusinessLicense WHERE Id = :license.Id].IsReadyToPrint__c,
            'A revoked license is not waiting to print');
        Assert.areEqual(0, new LicensePdfController(new List<Id>{ license.Id }).sheets.size(), 'A revoked license does not print');
    }

    @IsTest
    static void namesTheReason() {
        Date today = Date.today();
        Assert.areEqual('Duplicate', LicensePdfController.reason(new BusinessLicense(LastDuplicateDate__c = today, PrintRequestedDate__c = today, RenewalCount__c = 2)));
        Assert.areEqual('New', LicensePdfController.reason(new BusinessLicense(PrintRequestedDate__c = today)));
    }
}
