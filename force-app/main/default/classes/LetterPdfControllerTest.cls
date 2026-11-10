/**
 * Tests for LetterPdfController and LetterPdfSaveAction. They use the deployed Letter Templates
 * (custom metadata is visible to tests) and check the merge fields, the address and the saved file.
 */
@IsTest
private class LetterPdfControllerTest {

    private static Account person() {
        Id personType = Schema.SObjectType.Account.getRecordTypeInfosByDeveloperName().get('PersonAccount').getRecordTypeId();
        Account a = new Account(
            RecordTypeId = personType, FirstName = 'Letter', LastName = 'Tester',
            PersonMailingStreet = '100 Main Street', PersonMailingCity = 'Baton Rouge',
            PersonMailingState = 'Louisiana', PersonMailingPostalCode = '70801'
        );
        insert a;
        return a;
    }

    private static IndividualApplication application(Id accountId) {
        RegulatoryAuthorizationType licenseType = new RegulatoryAuthorizationType(Name = 'Letter Test License');
        insert licenseType;
        IndividualApplication app = new IndividualApplication(AccountId = accountId, Category = 'License', LicenseTypeId = licenseType.Id);
        insert app;
        return [SELECT Id, Name FROM IndividualApplication WHERE Id = :app.Id];
    }

    @IsTest
    static void returnLetterListsMissingItemsAndEscapesDetails() {
        Account a = person();
        IndividualApplication app = application(a.Id);
        insert new List<DocumentChecklistItem>{
            new DocumentChecklistItem(Name = 'Proof of Training Hours', ParentRecordId = app.Id, IsRequired = true, Status = 'New'),
            new DocumentChecklistItem(Name = 'Photo ID', ParentRecordId = app.Id, IsRequired = true, Status = 'Accepted')
        };

        LetterPdfController letter = new LetterPdfController(app.Id, 'ReturnLetter', 'Send <b>both</b> pages.');

        System.assertEquals('Letter Tester', letter.addresseeName);
        System.assertEquals(new List<String>{ '100 Main Street', 'Baton Rouge, Louisiana 70801' }, letter.addressLines);
        System.assert(letter.heading.contains(app.Name), letter.heading);
        System.assert(letter.bodyHtml.contains('<li>Proof of Training Hours</li>'), letter.bodyHtml);
        System.assert(!letter.bodyHtml.contains('Photo ID'), 'Accepted items are not missing');
        System.assert(letter.bodyHtml.contains('Send &lt;b&gt;both&lt;/b&gt; pages.'), 'Typed text is escaped');
        System.assert(!letter.bodyHtml.contains('{{'), 'Every merge field is replaced');
        System.assert(letter.bodyHtml.contains('Louisiana State Board of Cosmetology'), 'The whole body is used, not the first 255 characters');
    }

    @IsTest
    static void balanceDueTotalsOpenFeesOnTheAccount() {
        Account a = person();
        RegulatoryTrxnFee due = new RegulatoryTrxnFee(AccountId = a.Id, Status = 'DUE');
        RegulatoryTrxnFee paid = new RegulatoryTrxnFee(AccountId = a.Id, Status = 'PAID');
        insert new List<RegulatoryTrxnFee>{ due, paid };
        insert new List<RegulatoryTrxnFeeItem>{
            new RegulatoryTrxnFeeItem(Name = 'Renewal', RegulatoryTrxnFeeId = due.Id, FeeAmount = 1250.5),
            new RegulatoryTrxnFeeItem(Name = 'Late', RegulatoryTrxnFeeId = paid.Id, FeeAmount = 25)
        };

        LetterPdfController letter = new LetterPdfController(a.Id, 'BalanceDue', null);

        System.assert(letter.bodyHtml.contains('$1,250.50'), letter.bodyHtml);
    }

    @IsTest
    static void moneyFormatsWithoutTheUserLocale() {
        System.assertEquals('$0.00', LetterPdfController.money(0));
        System.assertEquals('$1,234,567.80', LetterPdfController.money(1234567.8));
        System.assertEquals('-$25.00', LetterPdfController.money(-25));
    }

    @IsTest
    static void refusesAnUnknownTemplate() {
        Account a = person();
        try {
            new LetterPdfController(a.Id, 'NoSuchTemplate', null);
            System.assert(false, 'An unknown template should fail');
        } catch (LetterPdfController.LetterException e) {
            System.assert(e.getMessage().contains('not found'));
        }
    }

    @IsTest
    static void saveActionAttachesTheLetterToTheRecord() {
        Account a = person();
        LetterPdfSaveAction.Request request = new LetterPdfSaveAction.Request();
        request.recordId = a.Id;
        request.templateName = 'ReturnedPayment';
        request.details = 'Check 1042 for $105.00, returned on 3 November 2026.';

        Test.startTest();
        List<LetterPdfSaveAction.Result> results = LetterPdfSaveAction.save(new List<LetterPdfSaveAction.Request>{ request });
        Test.stopTest();

        System.assertEquals(1, results.size());
        System.assert(results[0].title.startsWith('Returned Payment'), results[0].title);
        System.assertEquals(1, [SELECT COUNT() FROM ContentDocumentLink WHERE LinkedEntityId = :a.Id AND ContentDocumentId = :results[0].contentDocumentId]);
    }
}
