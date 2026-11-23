/**
 * Data and file actions for the Document Checklist Upload screen component: an application's checklist items with
 * their category and files, plus adding a file slot and removing a file.
 *
 * Salesforce allows one file per checklist item. A row on the screen can still hold several files: each extra file
 * sits on its own extra item (same name, document type and category, optional), whose Primary Checklist Item holds the
 * original item's Id. The screen shows extra items inside the original item's row, and when staff accept or return the
 * original item, Record-Trigger: Document Checklist Item After Save gives its extra items the same status.
 *
 * Who may remove a file (only while the item is New, Pending or Returned): a portal user only a file they uploaded;
 * staff any file. A file is deleted when the person removes their own upload. It is kept on the application instead
 * when staff remove someone else's file or when the item was returned (the Board keeps what it returned).
 *
 * Reads run with sharing, so a portal user only reaches their own application's items. File names are read without
 * sharing so files staff uploaded are counted too. The calling flow sets uploaded items to Pending and decides whether
 * anything required is still missing.
 */
public with sharing class DocumentChecklistUploadController {

    private static final Set<String> OPEN_STATUSES = new Set<String>{ 'New', 'Pending', 'Rejected' };

    public class FileInfo {
        @AuraEnabled public Id contentDocumentId;
        @AuraEnabled public String name;
        @AuraEnabled public Boolean canRemove = false;
    }

    public class Item {
        @AuraEnabled public Id id;
        @AuraEnabled public String name;
        @AuraEnabled public String instruction;
        @AuraEnabled public Boolean isRequired;
        @AuraEnabled public String status;
        @AuraEnabled public String comments;
        @AuraEnabled public String category;
        @AuraEnabled public Boolean isSentToBoard;
        // Blank on an original item; on an extra item, the Id of the original item whose row it belongs to.
        @AuraEnabled public Id primaryItemId;
        @AuraEnabled public List<String> fileNames = new List<String>();
        @AuraEnabled public List<FileInfo> files = new List<FileInfo>();
        // True on an original item that holds a file and is still open: the row offers Add another file.
        @AuraEnabled public Boolean canAddFile = false;
        // True when the item holds a file staff haven't seen: any file on a New item, or on a returned item a file added
        // after it was returned (the returned file stays on the item until the applicant replaces it).
        @AuraEnabled public Boolean hasNewFile = false;
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
        Map<Id, Datetime> changed = new Map<Id, Datetime>();
        for (DocumentChecklistItem d : [
                SELECT Id, Name, Instruction, IsRequired, Status, Comments, IsSentToBoard__c, PrimaryChecklistItem__c,
                       LastModifiedDate, DocumentCategory.DeveloperName, DocumentCategory.MasterLabel
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
            i.primaryItemId = toId(d.PrimaryChecklistItem__c);
            i.category = d.DocumentCategory?.MasterLabel == null ? 'Other Documents' : d.DocumentCategory.MasterLabel;
            items.put(i.id, i);
            changed.put(i.id, d.LastModifiedDate);
        }
        if (!items.isEmpty()) {
            Boolean staff = isStaff();
            Id me = UserInfo.getUserId();
            for (ContentDocumentLink l : new FileAccess().linksFor(items.keySet())) {
                Item i = items.get(l.LinkedEntityId);
                String ext = l.ContentDocument.FileExtension;
                FileInfo f = new FileInfo();
                f.contentDocumentId = l.ContentDocumentId;
                f.name = l.ContentDocument.Title + (String.isBlank(ext) ? '' : '.' + ext);
                f.canRemove = OPEN_STATUSES.contains(i.status) && (staff || l.ContentDocument.OwnerId == me);
                i.files.add(f);
                i.fileNames.add(f.name);
                if (i.status == 'New' || (i.status == 'Rejected' && l.ContentDocument.CreatedDate > changed.get(i.id))) {
                    i.hasNewFile = true;
                }
            }
            for (Item i : items.values()) {
                i.canAddFile = i.primaryItemId == null && !i.files.isEmpty() && OPEN_STATUSES.contains(i.status);
            }
        }
        return items.values();
    }

    /**
     * Gives a row room for one more file: returns an empty extra item for the original item, reusing one left empty
     * earlier, or creating it.
     * @param itemId the row's original item (an extra item's Id is resolved to its original item)
     */
    @AuraEnabled
    public static Id addFileSlot(Id itemId) {
        DocumentChecklistItem primary = visibleItem(itemId);
        if (primary.PrimaryChecklistItem__c != null) primary = visibleItem(toId(primary.PrimaryChecklistItem__c));
        if (!OPEN_STATUSES.contains(primary.Status)) {
            throw error('This document has already been accepted, so no more files can be added.');
        }
        FileAccess files = new FileAccess();
        List<DocumentChecklistItem> emptyExtras = files.emptyExtras(primary.Id);
        if (!emptyExtras.isEmpty()) return emptyExtras[0].Id;
        DocumentChecklistItem extra = new DocumentChecklistItem(
            Name = primary.Name,
            ParentRecordId = primary.ParentRecordId,
            DocumentTypeId = primary.DocumentTypeId,
            DocumentCategoryId = primary.DocumentCategoryId,
            Instruction = primary.Instruction,
            IsSentToBoard__c = primary.IsSentToBoard__c,
            IsRequired = false,
            Status = 'New',
            PrimaryChecklistItem__c = primary.Id);
        files.insertItem(extra);
        return extra.Id;
    }

    /**
     * Takes a file off a checklist item. With no file given, removes an empty extra item (an unused file slot).
     * After the removal: an empty extra item is deleted; an original item left empty takes the first file of its extra
     * items (unless it was returned, when the applicant is replacing the files); an original item left empty and
     * Pending goes back to New so its upload box comes back.
     */
    @AuraEnabled
    public static void removeFile(Id itemId, Id contentDocumentId) {
        DocumentChecklistItem item = visibleItem(itemId);
        FileAccess files = new FileAccess();
        try {
            if (contentDocumentId == null) {
                if (item.PrimaryChecklistItem__c != null && files.linksFor(new Set<Id>{ item.Id }).isEmpty()) {
                    files.deleteItem(item);
                }
                return;
            }
            if (!OPEN_STATUSES.contains(item.Status)) {
                throw error('This document has already been accepted, so its file can\'t be removed.');
            }
            ContentDocumentLink link = files.link(item.Id, contentDocumentId);
            if (link == null) throw error('That file is no longer on this document. Refresh the page.');
            Id me = UserInfo.getUserId();
            Boolean own = link.ContentDocument.OwnerId == me;
            if (!own && !isStaff()) throw error('You can only remove files you uploaded.');

            Boolean keepCopy = !own || item.Status == 'Rejected';
            if (keepCopy) files.linkTo(contentDocumentId, item.ParentRecordId, link);
            files.deleteLink(link);
            if (!keepCopy) files.deleteDocument(contentDocumentId);

            if (!files.linksFor(new Set<Id>{ item.Id }).isEmpty()) return;
            if (item.PrimaryChecklistItem__c != null) {
                files.deleteItem(item);
                return;
            }
            if (item.Status != 'Rejected' && files.promoteExtraFile(item)) return;
            if (item.Status == 'Pending') files.setStatus(item, 'New');
        } catch (AuraHandledException e) {
            throw e;
        } catch (Exception e) {
            throw error('The file could not be removed. Refresh the page and try again, or call the Board at 225-756-3404.');
        }
    }

    // The item, read with sharing: a user who can't see it gets an error, never another user's item.
    private static DocumentChecklistItem visibleItem(Id itemId) {
        List<DocumentChecklistItem> found = [
            SELECT Id, Name, ParentRecordId, DocumentTypeId, DocumentCategoryId, Instruction, IsSentToBoard__c, Status,
                   PrimaryChecklistItem__c
            FROM DocumentChecklistItem WHERE Id = :itemId];
        if (found.isEmpty()) throw error('That document could not be found. Refresh the page.');
        return found[0];
    }

    // Lets a test act as a portal user without creating one.
    @TestVisible private static Boolean actAsPortalUser = false;

    // Staff are internal users; portal users have a contact.
    private static Boolean isStaff() {
        return !actAsPortalUser && UserInfo.getUserType() == 'Standard';
    }

    private static AuraHandledException error(String message) {
        AuraHandledException e = new AuraHandledException(message);
        e.setMessage(message);
        return e;
    }

    private static Id toId(String value) {
        return String.isBlank(value) ? null : Id.valueOf(value);
    }

    /**
     * File links and item changes, without sharing. Every caller first reads the item with sharing (visibleItem), so
     * this only reaches items the user can see. A portal user can't see a file staff uploaded, and can't always create
     * or delete checklist items or file links directly.
     */
    private without sharing class FileAccess {
        List<ContentDocumentLink> linksFor(Set<Id> itemIds) {
            return [SELECT Id, LinkedEntityId, ContentDocumentId, ContentDocument.Title, ContentDocument.FileExtension,
                           ContentDocument.OwnerId, ContentDocument.CreatedDate, ShareType, Visibility
                    FROM ContentDocumentLink WHERE LinkedEntityId IN :itemIds
                    ORDER BY ContentDocument.CreatedDate];
        }

        ContentDocumentLink link(Id itemId, Id contentDocumentId) {
            List<ContentDocumentLink> found = [
                SELECT Id, LinkedEntityId, ContentDocumentId, ContentDocument.OwnerId, ShareType, Visibility
                FROM ContentDocumentLink WHERE LinkedEntityId = :itemId AND ContentDocumentId = :contentDocumentId];
            return found.isEmpty() ? null : found[0];
        }

        List<DocumentChecklistItem> emptyExtras(Id primaryId) {
            List<DocumentChecklistItem> out = new List<DocumentChecklistItem>();
            Map<Id, DocumentChecklistItem> extras = new Map<Id, DocumentChecklistItem>([
                SELECT Id FROM DocumentChecklistItem
                WHERE PrimaryChecklistItem__c = :primaryId AND Status = 'New' ORDER BY CreatedDate]);
            if (extras.isEmpty()) return out;
            Set<Id> filled = new Set<Id>();
            for (ContentDocumentLink l : linksFor(extras.keySet())) filled.add(l.LinkedEntityId);
            for (DocumentChecklistItem d : extras.values()) if (!filled.contains(d.Id)) out.add(d);
            return out;
        }

        // Puts a copy of the file on another record (the application), unless it is already there.
        void linkTo(Id contentDocumentId, Id recordId, ContentDocumentLink source) {
            if (![SELECT Id FROM ContentDocumentLink WHERE LinkedEntityId = :recordId AND ContentDocumentId = :contentDocumentId].isEmpty()) return;
            insert new ContentDocumentLink(ContentDocumentId = contentDocumentId, LinkedEntityId = recordId,
                                           ShareType = source.ShareType, Visibility = source.Visibility);
        }

        void deleteLink(ContentDocumentLink link) {
            delete new ContentDocumentLink(Id = link.Id);
        }

        void deleteDocument(Id contentDocumentId) {
            delete new ContentDocument(Id = contentDocumentId);
        }

        void insertItem(DocumentChecklistItem item) {
            insert item;
        }

        void deleteItem(DocumentChecklistItem item) {
            delete new DocumentChecklistItem(Id = item.Id);
        }

        void setStatus(DocumentChecklistItem item, String status) {
            update new DocumentChecklistItem(Id = item.Id, Status = status);
        }

        // Moves the first file of the original item's extra items onto it and deletes that extra item, so the
        // original (possibly required) item still holds a file. False when no extra item has a file.
        Boolean promoteExtraFile(DocumentChecklistItem primary) {
            Map<Id, DocumentChecklistItem> extras = new Map<Id, DocumentChecklistItem>(
                [SELECT Id FROM DocumentChecklistItem WHERE PrimaryChecklistItem__c = :primary.Id]);
            if (extras.isEmpty()) return false;
            List<ContentDocumentLink> links = linksFor(extras.keySet());
            if (links.isEmpty()) return false;
            ContentDocumentLink first = links[0];
            delete new ContentDocumentLink(Id = first.Id);
            insert new ContentDocumentLink(ContentDocumentId = first.ContentDocumentId, LinkedEntityId = primary.Id,
                                           ShareType = first.ShareType, Visibility = first.Visibility);
            delete new DocumentChecklistItem(Id = first.LinkedEntityId);
            return true;
        }
    }

    private static Set<String> toSet(String csv) {
        Set<String> out = new Set<String>();
        if (String.isBlank(csv)) return out;
        for (String s : csv.split(',')) if (String.isNotBlank(s)) out.add(s.trim());
        return out;
    }
}
