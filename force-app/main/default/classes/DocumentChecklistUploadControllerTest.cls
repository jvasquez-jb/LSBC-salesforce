@isTest
private class DocumentChecklistUploadControllerTest {

    private static IndividualApplication application() {
        Id personType = Schema.SObjectType.Account.getRecordTypeInfosByDeveloperName().get('PersonAccount').getRecordTypeId();
        Account acc = new Account(FirstName = 'Checklist', LastName = 'Tester', RecordTypeId = personType);
        insert acc;
        RegulatoryAuthorizationType licenseType = new RegulatoryAuthorizationType(Name = 'Checklist Test License');
        insert licenseType;
        IndividualApplication app = new IndividualApplication(AccountId = acc.Id, Category = 'License', LicenseTypeId = licenseType.Id);
        insert app;
        return app;
    }

    private static DocumentChecklistItem item(Id appId, String status) {
        DocumentCategory identity = [SELECT Id FROM DocumentCategory WHERE DeveloperName = 'Identity'];
        DocumentChecklistItem d = new DocumentChecklistItem(Name = 'Passport Photo', ParentRecordId = appId,
            DocumentCategoryId = identity.Id, Status = status, IsRequired = true);
        insert d;
        return d;
    }

    private static Id attach(Id itemId, String title, Id ownerId) {
        ContentVersion v = new ContentVersion(Title = title, PathOnClient = title + '.png', VersionData = Blob.valueOf('x'),
            FirstPublishLocationId = itemId);
        if (ownerId != null) v.OwnerId = ownerId;
        insert v;
        return [SELECT ContentDocumentId FROM ContentVersion WHERE Id = :v.Id].ContentDocumentId;
    }

    private static Integer linkCount(Id recordId, Id docId) {
        return [SELECT COUNT() FROM ContentDocumentLink WHERE LinkedEntityId = :recordId AND ContentDocumentId = :docId];
    }

    private static DocumentChecklistUploadController.Item find(List<DocumentChecklistUploadController.Item> items, Id id) {
        for (DocumentChecklistUploadController.Item i : items) if (i.id == id) return i;
        return null;
    }

    @isTest
    static void listsItemsByCategoryWithFiles() {
        IndividualApplication app = application();
        DocumentCategory payment = [SELECT Id FROM DocumentCategory WHERE DeveloperName = 'Payment'];
        DocumentCategory identity = [SELECT Id FROM DocumentCategory WHERE DeveloperName = 'Identity'];
        DocumentChecklistItem receipt = new DocumentChecklistItem(Name = 'Payment Receipt', ParentRecordId = app.Id, DocumentCategoryId = payment.Id, Status = 'New');
        DocumentChecklistItem photo = new DocumentChecklistItem(Name = 'Passport Photo', ParentRecordId = app.Id, DocumentCategoryId = identity.Id, Status = 'New', IsRequired = true);
        DocumentChecklistItem other = new DocumentChecklistItem(Name = 'Letter', ParentRecordId = app.Id, Status = 'New', IsSentToBoard__c = true);
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
        DocumentChecklistUploadController.Item p = find(all, photo.Id);
        Assert.areEqual('Identity', p.category);
        Assert.areEqual(new List<String>{ 'photo.png' }, p.fileNames);
        Assert.isTrue(p.files[0].canRemove, 'The uploader can remove a file on a New item');
        Assert.isTrue(p.hasNewFile, 'A file on a New item is waiting for review');
        Assert.isTrue(p.canAddFile, 'A row holding a file offers another');
        Assert.isTrue(p.isRequired);
        DocumentChecklistUploadController.Item o = find(all, other.Id);
        Assert.areEqual('Other Documents', o.category, 'An item with no category is grouped under Other Documents');
        Assert.isTrue(o.isSentToBoard, 'Sent to the Board comes through');
        Assert.isFalse(o.canAddFile, 'An empty row offers no extra file');
    }

    @isTest
    static void addFileSlotCreatesAnExtraItemAndReusesAnEmptyOne() {
        IndividualApplication app = application();
        DocumentChecklistItem photo = item(app.Id, 'Pending');
        attach(photo.Id, 'front', null);

        Test.startTest();
        Id slot = DocumentChecklistUploadController.addFileSlot(photo.Id);
        Id again = DocumentChecklistUploadController.addFileSlot(photo.Id);
        Test.stopTest();

        Assert.areEqual(slot, again, 'An empty extra item is reused');
        DocumentChecklistItem extra = [SELECT Name, IsRequired, Status, PrimaryChecklistItem__c, DocumentCategoryId FROM DocumentChecklistItem WHERE Id = :slot];
        Assert.areEqual('Passport Photo', extra.Name);
        Assert.isFalse(extra.IsRequired, 'Extra items are optional');
        Assert.areEqual('New', extra.Status);
        Assert.areEqual(String.valueOf(photo.Id), extra.PrimaryChecklistItem__c);
        Assert.areEqual(photo.DocumentCategoryId, extra.DocumentCategoryId);
        Assert.areEqual(photo.Id, find(DocumentChecklistUploadController.getItems(app.Id, null, null), slot).primaryItemId);
    }

    @isTest
    static void removingYourOwnFileDeletesItAndReopensThePendingItem() {
        IndividualApplication app = application();
        DocumentChecklistItem photo = item(app.Id, 'Pending');
        Id doc = attach(photo.Id, 'wrong', null);

        Test.startTest();
        DocumentChecklistUploadController.removeFile(photo.Id, doc);
        Test.stopTest();

        Assert.areEqual(0, [SELECT COUNT() FROM ContentDocument WHERE Id = :doc], 'Your own upload is deleted');
        Assert.areEqual('New', [SELECT Status FROM DocumentChecklistItem WHERE Id = :photo.Id].Status, 'An empty Pending item goes back to New');
    }

    @isTest
    static void removingTheOriginalFileTakesTheExtraFileAndDeletesTheExtraItem() {
        IndividualApplication app = application();
        DocumentChecklistItem photo = item(app.Id, 'Pending');
        Id front = attach(photo.Id, 'front', null);
        Id slot = DocumentChecklistUploadController.addFileSlot(photo.Id);
        Id back = attach(slot, 'back', null);

        Test.startTest();
        DocumentChecklistUploadController.removeFile(photo.Id, front);
        Test.stopTest();

        Assert.areEqual(1, linkCount(photo.Id, back), 'The extra file moves to the original item');
        Assert.areEqual(0, [SELECT COUNT() FROM DocumentChecklistItem WHERE Id = :slot], 'The emptied extra item is deleted');
        Assert.areEqual('Pending', [SELECT Status FROM DocumentChecklistItem WHERE Id = :photo.Id].Status);
    }

    @isTest
    static void removingAnExtraFileOrAnUnusedSlotDeletesTheExtraItem() {
        IndividualApplication app = application();
        DocumentChecklistItem photo = item(app.Id, 'New');
        attach(photo.Id, 'front', null);
        Id slot = DocumentChecklistUploadController.addFileSlot(photo.Id);
        Id back = attach(slot, 'back', null);

        Test.startTest();
        DocumentChecklistUploadController.removeFile(slot, back);
        Id unused = DocumentChecklistUploadController.addFileSlot(photo.Id);
        DocumentChecklistUploadController.removeFile(unused, null);
        Test.stopTest();

        Assert.areEqual(0, [SELECT COUNT() FROM DocumentChecklistItem WHERE PrimaryChecklistItem__c = :photo.Id], 'No extra items are left');
    }

    @isTest
    static void replacingAReturnedFileKeepsACopyOnTheApplication() {
        IndividualApplication app = application();
        DocumentChecklistItem photo = item(app.Id, 'Pending');
        Id doc = attach(photo.Id, 'blurry', null);
        photo.Status = 'Rejected';
        update photo;
        Assert.isFalse(find(DocumentChecklistUploadController.getItems(app.Id, null, null), photo.Id).hasNewFile,
            'The file that was returned is not a new upload');

        Test.startTest();
        DocumentChecklistUploadController.removeFile(photo.Id, doc);
        Test.stopTest();

        Assert.areEqual(0, linkCount(photo.Id, doc), 'The returned file is off the item');
        Assert.areEqual(1, linkCount(app.Id, doc), 'The Board keeps the returned file on the application');
        Assert.areEqual('Rejected', [SELECT Status FROM DocumentChecklistItem WHERE Id = :photo.Id].Status, 'The item waits for the replacement');
    }

    @isTest
    static void staffRemovingSomeoneElsesFileKeepsACopyOnTheApplication() {
        List<User> others = [SELECT Id FROM User WHERE IsActive = true AND UserType = 'Standard' AND Id != :UserInfo.getUserId() LIMIT 1];
        if (others.isEmpty()) return;
        IndividualApplication app = application();
        DocumentChecklistItem photo = item(app.Id, 'Pending');
        Id doc = attach(photo.Id, 'theirs', others[0].Id);

        Test.startTest();
        DocumentChecklistUploadController.removeFile(photo.Id, doc);
        Test.stopTest();

        Assert.areEqual(0, linkCount(photo.Id, doc));
        Assert.areEqual(1, linkCount(app.Id, doc), 'Staff removing another person\'s file keeps it on the application');
    }

    @isTest
    static void portalUserCannotRemoveAFileTheyDidNotUpload() {
        List<User> others = [SELECT Id FROM User WHERE IsActive = true AND UserType = 'Standard' AND Id != :UserInfo.getUserId() LIMIT 1];
        if (others.isEmpty()) return;
        IndividualApplication app = application();
        DocumentChecklistItem photo = item(app.Id, 'Pending');
        Id doc = attach(photo.Id, 'staff', others[0].Id);
        DocumentChecklistUploadController.actAsPortalUser = true;

        Assert.isFalse(find(DocumentChecklistUploadController.getItems(app.Id, null, null), photo.Id).files[0].canRemove);
        try {
            DocumentChecklistUploadController.removeFile(photo.Id, doc);
            Assert.fail('A portal user can only remove their own files');
        } catch (AuraHandledException e) {
            Assert.isTrue(e.getMessage().contains('only remove files you uploaded'), e.getMessage());
        }
        Assert.areEqual(1, linkCount(photo.Id, doc));
    }

    @isTest
    static void nobodyRemovesAFileFromAnAcceptedItem() {
        IndividualApplication app = application();
        DocumentChecklistItem photo = item(app.Id, 'Pending');
        Id doc = attach(photo.Id, 'good', null);
        photo.Status = 'Accepted';
        update photo;

        Assert.isFalse(find(DocumentChecklistUploadController.getItems(app.Id, null, null), photo.Id).files[0].canRemove);
        try {
            DocumentChecklistUploadController.removeFile(photo.Id, doc);
            Assert.fail('An accepted item keeps its file');
        } catch (AuraHandledException e) {
            Assert.isTrue(e.getMessage().contains('already been accepted'), e.getMessage());
        }
        try {
            DocumentChecklistUploadController.addFileSlot(photo.Id);
            Assert.fail('An accepted item takes no more files');
        } catch (AuraHandledException e) {
            Assert.isTrue(e.getMessage().contains('already been accepted'), e.getMessage());
        }
    }
}
