/**
 * Read-only data for the Document Checklist Upload screen component: an application's checklist
 * items with their category and the files already attached. Runs with sharing, so a portal user
 * only sees their own application's items; the names of the files on those items are read without sharing,
 * so files staff uploaded are counted too. It changes nothing: the calling flow sets uploaded
 * items to Pending and decides whether anything required is still missing.
 */
public with sharing class DocumentChecklistUploadController {

    public class Item {
        @AuraEnabled public Id id;
        @AuraEnabled public String name;
        @AuraEnabled public String instruction;
        @AuraEnabled public Boolean isRequired;
        @AuraEnabled public String status;
        @AuraEnabled public String comments;
        @AuraEnabled public String category;
        @AuraEnabled public Boolean isSentToBoard;
        @AuraEnabled public List<String> fileNames = new List<String>();
    }

    /**
     * @param applicationId the Individual Application or Business License Application
     * @param includeCategories comma-separated category developer names to show; blank shows all
     * @param excludeCategories comma-separated category developer names to leave out
     */
    @AuraEnabled
    public static List<Item> getItems(Id applicationId, String includeCategories, String excludeCategories) {
        Set<String> include = toSet(includeCategories);
        Set<String> exclude = toSet(excludeCategories);
        Map<Id, Item> items = new Map<Id, Item>();
        for (DocumentChecklistItem d : [
                SELECT Id, Name, Instruction, IsRequired, Status, Comments, IsSentToBoard__c,
                       DocumentCategory.DeveloperName, DocumentCategory.MasterLabel
                FROM DocumentChecklistItem
                WHERE ParentRecordId = :applicationId
                ORDER BY CreatedDate, Name]) {
            String cat = d.DocumentCategory?.DeveloperName;
            if (!include.isEmpty() && !include.contains(cat)) continue;
            if (cat != null && exclude.contains(cat)) continue;
            Item i = new Item();
            i.id = d.Id;
            i.name = d.Name;
            i.instruction = d.Instruction;
            i.isRequired = d.IsRequired;
            i.status = d.Status;
            i.comments = d.Comments;
            i.isSentToBoard = d.IsSentToBoard__c;
            i.category = d.DocumentCategory?.MasterLabel == null ? 'Other Documents' : d.DocumentCategory.MasterLabel;
            items.put(i.id, i);
        }
        if (!items.isEmpty()) {
            for (ContentDocumentLink l : new FileLookup().linksFor(items.keySet())) {
                String ext = l.ContentDocument.FileExtension;
                items.get(l.LinkedEntityId).fileNames.add(l.ContentDocument.Title + (String.isBlank(ext) ? '' : '.' + ext));
            }
        }
        return items.values();
    }

    /**
     * Reads the files on items the user can already see (the items query above runs with sharing). A portal user
     * can't see a file staff uploaded, so without this the screen would offer an upload box on an item that
     * already holds its one file. Only the file names are returned, never the files.
     */
    private without sharing class FileLookup {
        List<ContentDocumentLink> linksFor(Set<Id> itemIds) {
            return [SELECT LinkedEntityId, ContentDocument.Title, ContentDocument.FileExtension
                    FROM ContentDocumentLink WHERE LinkedEntityId IN :itemIds
                    ORDER BY ContentDocument.CreatedDate];
        }
    }

    private static Set<String> toSet(String csv) {
        Set<String> out = new Set<String>();
        if (String.isBlank(csv)) return out;
        for (String s : csv.split(',')) if (String.isNotBlank(s)) out.add(s.trim());
        return out;
    }
}
