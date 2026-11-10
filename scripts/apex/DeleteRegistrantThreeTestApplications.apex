// Test data cleanup: deletes StopCodeTest Registrant Three's portal applications, checklist items, files,
// today's fees and holds. Files must be unlinked from checklist items before either can be deleted.
Id acc = [SELECT AccountId FROM BusinessLicense WHERE Identifier = 'SCT40003'].AccountId;
List<IndividualApplication> apps = [SELECT Id FROM IndividualApplication WHERE AccountId = :acc];
Set<Id> appIds = new Map<Id, IndividualApplication>(apps).keySet();
List<DocumentChecklistItem> items = [SELECT Id FROM DocumentChecklistItem WHERE ParentRecordId IN :appIds];
List<RegulatoryTrxnFee> fees = [SELECT Id FROM RegulatoryTrxnFee WHERE AccountId = :acc AND CreatedDate = TODAY];
List<RegulatoryTrxnFeeItem> feeItems = [SELECT Id FROM RegulatoryTrxnFeeItem WHERE RegulatoryTrxnFeeId IN :fees];
Set<Id> docIds = new Set<Id>();
Set<Id> linked = new Set<Id>(appIds); for (DocumentChecklistItem i : items) linked.add(i.Id);
if (!linked.isEmpty()) for (ContentDocumentLink l : [SELECT ContentDocumentId FROM ContentDocumentLink WHERE LinkedEntityId IN :linked]) docIds.add(l.ContentDocumentId);
List<ContentDocument> docs = [SELECT Id FROM ContentDocument WHERE Id IN :docIds];
List<RecordAlert> alerts = [SELECT Id FROM RecordAlert WHERE WhatId = :acc AND CreatedDate = TODAY];
List<ContentDocumentLink> links = linked.isEmpty() ? new List<ContentDocumentLink>() : [SELECT Id FROM ContentDocumentLink WHERE LinkedEntityId IN :linked];
String step = 'links';
try { delete links; step = 'docs'; delete docs; step = 'items'; delete items; } catch (Exception e) { System.debug(LoggingLevel.ERROR, 'CLEAN FAILED at ' + step + ': ' + e.getMessage()); throw e; } delete feeItems; delete fees; delete apps; delete alerts;
System.debug(LoggingLevel.ERROR, 'CLEAN apps ' + apps.size() + ' items ' + items.size() + ' fees ' + fees.size() + ' docs ' + docs.size() + ' alerts ' + alerts.size());
