/**
 * Renders the LetterPdf page for a record and saves it as a File on that record. Called by
 * Screen Flow: Letter Generate. Rendering a page counts as a callout, so the flow calls this in its
 * own step with no record changes before it in the same transaction.
 */
public with sharing class LetterPdfSaveAction {
    public class Request {
        @InvocableVariable(label='Record Id' description='The account or application the letter is about.' required=true)
        public Id recordId;
        @InvocableVariable(label='Template' description='Developer name of the Letter Template.' required=true)
        public String templateName;
        @InvocableVariable(label='Details' description='Text staff typed for {{Details}}.')
        public String details;
    }

    public class Result {
        @InvocableVariable(label='File Id' description='The saved letter (ContentDocument Id).')
        public Id contentDocumentId;
        @InvocableVariable(label='File Title')
        public String title;
    }

    @InvocableMethod(label='Save Letter PDF' description='Generates a letter from a Letter Template and saves it as a PDF file on the record.' category='Letters')
    public static List<Result> save(List<Request> requests) {
        List<Result> results = new List<Result>();
        for (Request request : requests) {
            LetterTemplate__mdt template = LetterTemplate__mdt.getInstance(request.templateName);
            PageReference page = Page.LetterPdf;
            page.getParameters().put('id', request.recordId);
            page.getParameters().put('template', request.templateName);
            if (String.isNotBlank(request.details)) {
                page.getParameters().put('details', request.details);
            }
            Blob pdf = Test.isRunningTest() ? Blob.valueOf('test letter') : page.getContentAsPDF();
            String title = (template == null ? request.templateName : template.MasterLabel) + ' ' + Datetime.now().format('yyyy-MM-dd HHmm');
            ContentVersion version = new ContentVersion(
                Title = title,
                PathOnClient = title + '.pdf',
                VersionData = pdf,
                FirstPublishLocationId = request.recordId
            );
            insert version;
            Result result = new Result();
            result.contentDocumentId = [SELECT ContentDocumentId FROM ContentVersion WHERE Id = :version.Id].ContentDocumentId;
            result.title = title;
            results.add(result);
        }
        return results;
    }
}
