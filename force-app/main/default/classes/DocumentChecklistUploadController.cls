/**
 * Read-only data for the Document Checklist Upload screen component: an application's checklist
 * items with their category and the files already attached. Runs with sharing, so a portal user
 * only sees their own application's items. It changes nothing: the calling flow sets uploaded
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
                SELECT Id, Name, Instruction, IsRequired, Status, Comments,
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
            i.category = d.DocumentCategory?.MasterLabel == null ? 'Other Documents' : d.DocumentCategory.MasterLabel;
            items.put(i.id, i);
        }
        if (!items.isEmpty()) {
            for (ContentDocumentLink l : [
                    SELECT LinkedEntityId, ContentDocument.Title, ContentDocument.FileExtension
                    FROM ContentDocumentLink WHERE LinkedEntityId IN :items.keySet()
                    ORDER BY ContentDocument.CreatedDate]) {
                String ext = l.ContentDocument.FileExtension;
                items.get(l.LinkedEntityId).fileNames.add(l.ContentDocument.Title + (String.isBlank(ext) ? '' : '.' + ext));
            }
        }
        return items.values();
    }

    private static Set<String> toSet(String csv) {
        Set<String> out = new Set<String>();
        if (String.isBlank(csv)) return out;
        for (String s : csv.split(',')) if (String.isNotBlank(s)) out.add(s.trim());
        return out;
    }
}
