"""Writes the record-page Paths (status chevrons under the header) and their Guidance for Success.

Usage, from the repo root:  python3 -I scripts/generators/paths.py
Writes force-app/main/default/pathAssistants/<Name>.pathAssistant-meta.xml, one per object and record type.
Deploy them with the record pages, which carry the Path component (PATH_OBJECTS in pagegen.py).

A Path shows every Status value of the record type, in picklist order. Document Checklist Item, Business
License and Regulatory Trxn Fee can't have a Path (Salesforce refuses the object). On the applications the
final statuses are set only by Decide: validation rule StatusFinalOnlyThroughDecide refuses them from the
Path, so their guidance says to use Decide.
"""
import os
from xml.sax.saxutils import escape

OUT = 'force-app/main/default/pathAssistants'

DECIDE = 'Set only by <b>Decide</b> at the top of the page, which also issues the license and its number. The Path refuses it.'
REFUSE = 'Set only by <b>Decide</b> (refuse), with the reason and an optional letter. The Path refuses it.'

INDIVIDUAL = [
    ('Submitted', 'New from the portal or from staff intake. Check the applicant, the Checklist tab and the Fees tab, then move it to Application Accepted.'),
    ('Application Accepted', 'Being worked. Accept or return each document on the Checklist tab and check the fees, then move it to In Review.'),
    ('In Review', 'Documents and fees are being checked. When every required document is accepted and the fees are paid, approve or deny with <b>Decide</b>.'),
    ('Approved', DECIDE),
    ('Denied', REFUSE),
]
BUSINESS = [
    ('Submitted', 'New from the portal or from staff intake. Check the business, the Checklist tab and the Fees tab, then move it to Application Accepted.'),
    ('Application Accepted', 'Being worked. Accept or return each document on the Checklist tab and check the fees, then move it to In Review.'),
    ('In Review', 'Documents and fees are being checked. Move it to Inspection Phase when the premises are ready to inspect.'),
    ('Inspection Phase', 'The inspector visits the premises. When the inspection passes, approve with <b>Decide</b>.'),
    ('Approved', DECIDE),
    ('Approved with Conditions', 'Not set by Decide today. Approve with <b>Decide</b>; ask an administrator if conditions must be recorded.'),
    ('Canceled', REFUSE),
]
CASE = [
    ('New', 'Not picked up yet. Read the email or form and take the case from its queue.'),
    ('In Progress', 'Being worked. Record a complaint or a violation from the header when the case needs one.'),
    ('Waiting On Response', 'Waiting on the person or another office. Note who and what in an activity.'),
    ('Closed', 'Answered, or the work moved to a complaint or violation.'),
]
COMPLAINT = [
    ('Submitted', 'Received. Read the complaint and check the people and businesses named.'),
    ('In Review', 'Being investigated. Add participants, and violations when they are found.'),
    ('Resolved', 'Finished. Record the outcome in a note before resolving.'),
]
VIOLATION = [
    ('Open', 'The $25 fee is due 15 days after the violation date; once overdue it opens stop code 21 (Non Payment).'),
    ('Referred To Attorney', "Sent to the Board's attorney."),
    ('Resolved', 'Closed: paid or otherwise settled.'),
]

PATHS = [
    # (name, label, object, field, record type, steps)
    *[(f'IndividualApplication{rt}', (f'Individual Application {lbl}' if rt != 'StudentRegistration' else 'Student Registration Application'), 'IndividualApplication', 'Status', rt, INDIVIDUAL)
      for rt, lbl in [('Examination', 'Examination'), ('NewLicensure', 'New Licensure'), ('Reciprocity', 'Reciprocity'),
                      ('Renewal', 'Renewal'), ('StudentRegistration', 'Student Registration')]],
    # Path API names and labels are at most 40 characters, so the business application paths are BusinessApplication<RecordType>.
    *[(f'BusinessApplication{rt}', f'Business Application {lbl}', 'BusinessLicenseApplication', 'Status', rt, BUSINESS)
      for rt, lbl in [('NewEstablishment', 'New Establishment'), ('NewSchool', 'New School'), ('Renewal', 'Renewal')]],
    ('CaseStatus', 'Case Status', 'Case', 'Status', '__MASTER__', CASE),
    ('PublicComplaintStatus', 'Public Complaint Status', 'PublicComplaint', 'Status', '__MASTER__', COMPLAINT),
    ('RegulatoryCodeViolationStatus', 'Violation Status', 'RegulatoryCodeViolation', 'Status', '__MASTER__', VIOLATION),
]


def xml(label, obj, field, rt, steps):
    body = ''.join(f'''    <pathAssistantSteps>
        <info>{escape('<p>' + info + '</p>')}</info>
        <picklistValueName>{escape(value)}</picklistValueName>
    </pathAssistantSteps>
''' for value, info in steps)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<PathAssistant xmlns="http://soap.sforce.com/2006/04/metadata">
    <active>true</active>
    <entityName>{obj}</entityName>
    <fieldName>{field}</fieldName>
    <masterLabel>{escape(label)}</masterLabel>
{body}    <recordTypeName>{rt}</recordTypeName>
</PathAssistant>
'''


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, label, obj, field, rt, steps in PATHS:
        with open(f'{OUT}/{name}.pathAssistant-meta.xml', 'w') as f:
            f.write(xml(label, obj, field, rt, steps))
    print(f'{len(PATHS)} paths written to {OUT}')
