@isTest
private class DocumentChecklistUploadControllerTest {

    @isTest
    static void listsItemsByCategoryWithFiles() {
        Id personType = Schema.SObjectType.Account.getRecordTypeInfosByDeveloperName().get('PersonAccount').getRecordTypeId();
        Account acc = new Account(FirstName = 'Checklist', LastName = 'Tester', RecordTypeId = personType);
        insert acc;
        RegulatoryAuthorizationType licenseType = new RegulatoryAuthorizationType(Name = 'Checklist Test License');
        insert licenseType;
        IndividualApplication app = new IndividualApplication(AccountId = acc.Id, Category = 'License', LicenseTypeId = licenseType.Id);
        insert app;
        DocumentCategory payment = [SELECT Id FROM DocumentCategory WHERE DeveloperName = 'Payment'];
        DocumentCategory identity = [SELECT Id FROM DocumentCategory WHERE DeveloperName = 'Identity'];
        DocumentChecklistItem receipt = new DocumentChecklistItem(Name = 'Payment Receipt', ParentRecordId = app.Id, DocumentCategoryId = payment.Id, Status = 'New');
        DocumentChecklistItem photo = new DocumentChecklistItem(Name = 'Passport Photo', ParentRecordId = app.Id, DocumentCategoryId = identity.Id, Status = 'New', IsRequired = true);
        DocumentChecklistItem other = new DocumentChecklistItem(Name = 'Letter', ParentRecordId = app.Id, Status = 'New');
        insert new List<DocumentChecklistItem>{ receipt, photo, other };
        insert new ContentVersion(Title = 'photo', PathOnClient = 'photo.png', VersionData = Blob.valueOf('x'), FirstPublishLocationId = photo.Id);

        Test.startTest();
        List<DocumentChecklistUploadController.Item> all = DocumentChecklistUploadController.getItems(app.Id, null, null);
        List<DocumentChecklistUploadController.Item> receiptOnly = DocumentChecklistUploadController.getItems(app.Id, 'Payment', null);
        List<DocumentChecklistUploadController.Item> noReceipt = DocumentChecklistUploadController.getItems(app.Id, '', 'Payment');
        Test.stopTest();

        Assert.areEqual(3, all.size(), 'All items are listed');
        Assert.areEqual(1, receiptOnly.size(), 'Only the payment category is listed');
        Assert.areEqual('Payment Receipt', receiptOnly[0].name);
        Assert.areEqual(2, noReceipt.size(), 'The payment category is left out');
        for (DocumentChecklistUploadController.Item i : all) {
            if (i.id == photo.Id) {
                Assert.areEqual('Identity', i.category);
                Assert.areEqual(new List<String>{ 'photo.png' }, i.fileNames);
                Assert.isTrue(i.isRequired);
            }
            if (i.id == other.Id) Assert.areEqual('Other Documents', i.category, 'An item with no category is grouped under Other Documents');
        }
    }
}
