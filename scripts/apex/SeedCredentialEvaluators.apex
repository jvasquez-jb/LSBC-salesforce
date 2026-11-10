// Loads the Board's approved foreign credential evaluation agencies (2019 list, Foreign
// Reciprocity packet page 3) as Organization accounts, each with a Credential Evaluator
// Approval. Safe to run again: existing agencies are skipped.
Id orgType = Schema.SObjectType.Account.getRecordTypeInfosByDeveloperName().get('Organization').getRecordTypeId();
Map<String, String> agencies = new Map<String, String>{
    'Center for Applied Research, Evaluations, & Education, Inc' => 'https://www.iescaree.com',
    'Educational Perspectives, nfp' => 'https://www.edperspective.org',
    'International Academic Credential Evaluators, Inc' => 'https://www.iacei.net',
    'International Education Research Foundation, Inc' => 'https://www.ierf.org',
    'Josef Silny & Associates, Inc. International Education Consultants' => 'https://www.jsilny.org',
    'Transcript Research' => 'https://www.transcriptresearch.com',
    'World Education Services, Inc' => 'https://www.wes.org',
    'Academic Credentials Evaluation Institute, Inc' => 'https://www.acei-global.org',
    'American Education Research Corporation' => 'https://www.aerc-eval.com',
    'Globe Language Services, Inc' => 'https://www.globelanguage.com'
};
Set<String> existing = new Set<String>();
for (Account a : [SELECT Name FROM Account WHERE Name IN :agencies.keySet()]) existing.add(a.Name);
List<Account> accounts = new List<Account>();
for (String n : agencies.keySet()) {
    if (!existing.contains(n)) accounts.add(new Account(Name = n, RecordTypeId = orgType, Type = 'Credential Evaluation Agency', Website = agencies.get(n)));
}
insert accounts;
List<Accreditation> approvals = new List<Accreditation>();
for (Account a : accounts) {
    approvals.add(new Accreditation(Name = (a.Name.left(60) + ' approval'), AccountId = a.Id,
        Type = 'Credential Evaluator Approval', Status = 'Active',
        AccreditingBody = 'Louisiana State Board of Cosmetology', EffectiveFrom = Date.newInstance(2019, 1, 1)));
}
insert approvals;
System.debug('Agencies added: ' + accounts.size());
