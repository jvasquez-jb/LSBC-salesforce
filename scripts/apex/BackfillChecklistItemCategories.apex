// One-off: files existing document checklist items under their document type's category
// (Document Category links). New items get their category from Subflow: Document Checklist Generate.
Map<Id, Id> categoryByType = new Map<Id, Id>();
for (DocumentCategoryDocumentType l : [SELECT DocumentTypeId, DocumentCategoryId FROM DocumentCategoryDocumentType]) {
    categoryByType.put(l.DocumentTypeId, l.DocumentCategoryId);
}
List<DocumentChecklistItem> items = new List<DocumentChecklistItem>();
for (DocumentChecklistItem i : [SELECT Id, DocumentTypeId FROM DocumentChecklistItem WHERE DocumentCategoryId = null AND DocumentTypeId IN :categoryByType.keySet()]) {
    items.add(new DocumentChecklistItem(Id = i.Id, DocumentCategoryId = categoryByType.get(i.DocumentTypeId)));
}
update items;
System.debug(LoggingLevel.ERROR, 'BACKFILLED ' + items.size() + ' checklist items');
