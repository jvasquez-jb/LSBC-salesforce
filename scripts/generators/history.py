"""Turn on field history for the objects LSBC uses: sets trackHistory on the fields in FIELDS (writing a minimal
field file for standard fields not yet in force-app) and enableHistory on objects that have the switch.

Salesforce tracks at most 20 fields per object. The social security number and date of birth are never tracked.
Run from the repo root: python3 -I scripts/generators/history.py
"""
import os, re

OBJ = 'force-app/main/default/objects'

# Objects whose object file carries an enableHistory switch (Account, Contact, custom objects). Public Sector
# objects have none: tracking a field turns their history on.
ENABLE = ['Account', 'Contact', 'Payment__c', 'PaymentAllocation__c']

FIELDS = {
    # Person and business accounts (person fields from Contact are listed under Contact).
    'Account': ['Name', 'BillingAddress', 'ShippingAddress', 'Phone', 'OwnerId', 'Parish__c',
                'TaxIdentificationNumber__c', 'MaximumStudentCapacity__c', 'PersonMailingAddress',
                'PersonEmail', 'PersonMobilePhone', 'PersonHomePhone'],
    # Person custom fields: tracking them on Contact records nothing for person accounts. They are ticked in Setup
    # (Account, Set History Tracking: Home Parish, Certification Number, Maiden Name); metadata can't set __pc fields.
    'Contact': ['HomeParish__c', 'CertificationNumber__c', 'MaidenName__c'],
    'Accreditation': ['Name', 'Type', 'SubType', 'AccreditingBody', 'Status', 'AccreditationRating',
                      'LastFullSurveyDate', 'LastOnsiteSurveyDate', 'AccountId', 'EffectiveFrom', 'EffectiveTo',
                      'BondAmount__c', 'Underwriter__c'],
    'BusinessLicense': ['Name', 'ContactId', 'AccountId', 'Status', 'IsActive', 'Identifier', 'PeriodStart',
                        'PeriodEnd', 'RegulatoryAuthorizationTypeId', 'VerificationStatus', 'ConsecutiveCEUCycles__c',
                        'IsMasterInstructor__c', 'LastCEUDate__c', 'RenewalCount__c', 'PrintRequestedDate__c',
                        'PrintedDate__c', 'InstructorStatus__c', 'LastDuplicateDate__c'],
    'BusinessLicenseApplication': ['AccountId', 'Status', 'ApplicationType', 'LicenseTypeId', 'Category',
                                   'AppliedDate', 'ApprovedDate', 'PaymentDate', 'AmountPaid', 'WasReturned',
                                   'PrimaryOwnerId', 'ReturnReason__c', 'DecisionReason__c', 'IsCertified__c',
                                   'CertifiedName__c', 'RequestedOpeningDate__c', 'IsPremisesLeased__c'],
    'Case': ['Status', 'Priority', 'Type', 'Origin', 'Reason', 'OwnerId', 'AccountId', 'ContactId', 'Subject',
             'ComplaintType__c', 'IncidentDate__c'],
    'CourseOffering': ['Name', 'Description', 'LocationId', 'StartDate', 'EndDate', 'CourseNameId',
                       'ApprovedHours__c', 'School__c'],
    'DocumentChecklistItem': ['Name', 'Status', 'IsAccepted', 'DocumentTypeId', 'ParentRecordId',
                              'ReceivedDocumentId', 'Comments', 'ValidatedById', 'ValidationDateTime',
                              'IsSentToBoard__c'],
    'Examination': ['Name', 'Description', 'Status', 'ExamType__c', 'LicenseType__c'],
    'IndividualApplication': ['AccountId', 'Status', 'ApplicationType', 'LicenseTypeId', 'Category', 'AppliedDate',
                              'ApprovedDate', 'PaymentDate', 'AmountPaid', 'WasReturned', 'ReturnReason__c',
                              'DecisionReason__c', 'IsCertified__c', 'CourseOffering__c', 'OriginatingState__c',
                              'EnrolledDate__c', 'CompletedDate__c', 'TotalCompletedHours__c',
                              'InitiallyLicensedName__c', 'ApplicationPath__c'],
    'PaymentAllocation__c': ['Amount__c', 'FeeItem__c', 'ForYear__c'],
    'Payment__c': ['Account__c', 'Amount__c', 'ExternalReference__c', 'Method__c', 'ReceivedDate__c',
                   'RefundAmount__c', 'RefundCheckNumber__c', 'RefundRequestedBy__c', 'RefundRequestedDate__c',
                   'RefundStatus__c', 'RefundVerifiedBy__c', 'RefundVerifiedDate__c', 'RefundedDate__c',
                   'Status__c', 'CheckDate__c', 'ChecklistItem__c', 'PayerName__c'],
    'PersonDisability': ['Name', 'Status', 'Type', 'IsAccommodationRequired', 'VerificationDate', 'VerifiedBy',
                         'StartDate', 'EndDate', 'VerificationStatus', 'AccommodationDetails__c', 'Accommodations__c'],
    'PersonEducation': ['Name', 'ContactId', 'AccountId', 'Status', 'Identifier', 'StartDate', 'CompletionDate',
                        'GraduationDate', 'EducationLevel', 'VerificationStatus', 'SchoolCity__c', 'SchoolState__c'],
    'PersonExamination': ['ContactId', 'ExaminationId', 'ExaminationDate', 'Score', 'Result', 'InstitutionName',
                          'VerificationStatus', 'VerificationDateTime', 'EffectiveFrom', 'EffectiveTo',
                          'AttemptNumber__c'],
    'Product2': ['Name', 'ProductCode', 'Description', 'IsActive', 'Family', 'FeeCode__c', 'RevenueCode__c'],
    'PublicComplaint': ['AccountId', 'Status', 'Priority', 'IncidentDate', 'ComplaintType', 'ComplaintSubType',
                        'BusinessName', 'ComplaintCaseId', 'FirstName', 'LastName', 'Email', 'MobileNumber',
                        'Subject', 'IsReporterConfidential', 'ReceivedDate', 'SourceType', 'ResolutionSummary'],
    'RecordAlert': ['ParentId', 'WhatId', 'Subject', 'Description', 'EffectiveDate', 'ValidUntilDate', 'Severity',
                    'IsActive', 'RecordAlertCategoryId', 'SnoozeUntilDate'],
    'RegulatoryCodeViolation': ['ViolationTypeId', 'RegulatoryCodeId', 'Status', 'Priority', 'Description',
                                'DateCreated', 'ComplianceDueDate', 'DateResolved', 'RecurrenceCount',
                                'ResolutionNotes', 'Case__c', 'CitedParty__c', 'Establishment__c', 'Practitioner__c'],
    'RegulatoryTrxnFee': ['AccountId', 'ParentRecordId', 'Status', 'CalculationDate', 'DueDate', 'Comments',
                          'Description', 'AmountPaid__c'],
    'RegulatoryTrxnFeeItem': ['Name', 'FeeAmount', 'Comments', 'FeeProduct__c', 'ForYear__c'],
    'TrainingCourseParticipant': ['ContactId', 'InstitutionName', 'Result', 'StartDate', 'EndDate',
                                  'CourseOfferingId', 'TotalCredits', 'TotalHours', 'VerificationStatus',
                                  'VerificationDateTime', 'EntryType__c', 'ReceivedDate__c'],
}

NEVER = {'SocialSecurityNumber__c', 'MockSocialSecurityNumber__c', 'DateOfBirth__c'}


def set_tag(xml, tag, closing):
    if re.search(rf'<{tag}>\w+</{tag}>', xml):
        return re.sub(rf'<{tag}>\w+</{tag}>', f'<{tag}>true</{tag}>', xml, count=1)
    return xml.replace(closing, f'    <{tag}>true</{tag}>\n{closing}', 1)


def main():
    written = []
    for obj, fields in FIELDS.items():
        assert len(fields) <= 20, f'{obj}: {len(fields)} fields, Salesforce tracks at most 20'
        for f in fields:
            assert f not in NEVER, f
            path = os.path.join(OBJ, obj, 'fields', f + '.field-meta.xml')
            if os.path.exists(path):
                xml = open(path).read()
                new = set_tag(xml, 'trackHistory', '</CustomField>')
            else:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                new = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                       '<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">\n'
                       f'    <fullName>{f}</fullName>\n    <trackHistory>true</trackHistory>\n</CustomField>\n')
                xml = None
            if new != xml:
                open(path, 'w').write(new)
                written.append(path)
    for obj in ENABLE:
        path = os.path.join(OBJ, obj, obj + '.object-meta.xml')
        assert os.path.exists(path), f'{path} missing: retrieve the object file first'
        xml = open(path).read()
        new = set_tag(xml, 'enableHistory', '</CustomObject>')
        if new != xml:
            open(path, 'w').write(new)
            written.append(path)
    print('\n'.join(written))


if __name__ == '__main__':
    main()
