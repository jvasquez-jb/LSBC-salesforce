// Test data cleanup: deletes StopCodeTest Registrant Three's portal applications and drafts (Preliminary
// Application References), their checklist items and files, saved (paused) forms, and today's fees, holds and exam attempts.
// Files must be unlinked from checklist items before either can be deleted.
Id acc = [SELECT AccountId FROM BusinessLicense WHERE Identifier = 'SCT40003'].AccountId;
Id portalUser = [SELECT Id FROM User WHERE AccountId = :acc LIMIT 1].Id;
List<IndividualApplication> apps = [SELECT Id FROM IndividualApplication WHERE AccountId = :acc];
List<PreliminaryApplicationRef> drafts = [SELECT Id FROM PreliminaryApplicationRef WHERE OwnerId = :portalUser];
Set<Id> parents = new Set<Id>();
for (IndividualApplication a : apps) parents.add(a.Id);
for (PreliminaryApplicationRef d : drafts) parents.add(d.Id);
List<DocumentChecklistItem> items = [SELECT Id FROM DocumentChecklistItem WHERE ParentRecordId IN :parents];
Set<Id> linked = new Set<Id>(parents);
for (DocumentChecklistItem i : items) linked.add(i.Id);
Set<Id> docIds = new Set<Id>();
List<ContentDocumentLink> links = linked.isEmpty() ? new List<ContentDocumentLink>() : [SELECT Id, ContentDocumentId FROM ContentDocumentLink WHERE LinkedEntityId IN :linked];
for (ContentDocumentLink l : links) docIds.add(l.ContentDocumentId);
List<ContentDocument> docs = [SELECT Id FROM ContentDocument WHERE Id IN :docIds];
List<RegulatoryTrxnFee> fees = [SELECT Id FROM RegulatoryTrxnFee WHERE AccountId = :acc AND CreatedDate = TODAY];
List<RegulatoryTrxnFeeItem> feeItems = [SELECT Id FROM RegulatoryTrxnFeeItem WHERE RegulatoryTrxnFeeId IN :fees];
List<RecordAlert> alerts = [SELECT Id FROM RecordAlert WHERE WhatId = :acc AND CreatedDate = TODAY];
List<FlowInterview> paused = [SELECT Id FROM FlowInterview WHERE CreatedById = :portalUser];
List<PersonExamination> attempts = [SELECT Id FROM PersonExamination WHERE Contact.AccountId = :acc AND CreatedDate = TODAY];
delete links; delete docs; delete items; delete feeItems; delete fees; delete apps; delete drafts; delete alerts; delete paused; delete attempts;
System.debug(LoggingLevel.ERROR, 'CLEAN apps ' + apps.size() + ' drafts ' + drafts.size() + ' items ' + items.size() + ' fees ' + fees.size() + ' docs ' + docs.size() + ' alerts ' + alerts.size() + ' paused ' + paused.size() + ' attempts ' + attempts.size());
