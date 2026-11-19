/**
 * Lays licenses out on the Board's three-part license stock (form LBC-19) for the LicensePdf page:
 * a wall certificate at the top, the renewal stub in the middle (its wallet card is left blank), and a second
 * wall certificate at the bottom, one sheet per license.
 *
 * Opened from the Print Licenses button on the Licenses Ready to Print list view with the ticked
 * licenses. Prints only licenses waiting to print (Ready to Print) whose holder has no active stop
 * code, the same check Mark Printed makes. Printing does not mark anything printed: staff run
 * Mark Printed once the sheets have printed correctly.
 *
 * The number printed is the holder's Certification Number (a person's or an establishment's, shared by
 * all their licenses), or the License Number when the holder has none (a school). It prints with an L in
 * front, as the previous system printed it, so licensees know it is their license number. The governor's
 * name comes from the custom label License Governor Name.
 */
public with sharing class LicensePdfController {
    public List<Sheet> sheets { get; private set; }
    public Integer skippedCount { get; private set; }
    public String governor { get { return Label.LicenseGovernorName; } }
    /** Moves everything on the sheet, in inches, to suit a printer: page parameters dx (right) and dy (down). */
    public Decimal offsetX { get; private set; }
    public Decimal offsetY { get; private set; }

    public LicensePdfController(ApexPages.StandardSetController controller) {
        List<Id> ids = new List<Id>();
        for (SObject record : controller.getSelected()) {
            ids.add(record.Id);
        }
        Map<String, String> params = ApexPages.currentPage().getParameters();
        offsetX = toInches(params.get('dx'));
        offsetY = toInches(params.get('dy'));
        build(ids);
    }

    @TestVisible
    private LicensePdfController(List<Id> licenseIds) {
        offsetX = 0;
        offsetY = 0;
        build(licenseIds);
    }

    private static Decimal toInches(String value) {
        try {
            return String.isBlank(value) ? 0 : Decimal.valueOf(value);
        } catch (TypeException e) {
            return 0;
        }
    }

    private void build(List<Id> licenseIds) {
        sheets = new List<Sheet>();
        List<BusinessLicense> licenses = [
            SELECT Id, Identifier, PeriodEnd, PrintRequestedDate__c, LastDuplicateDate__c, RenewalCount__c, IsReadyToPrint__c,
                RegulatoryAuthorizationType.Name, AccountId, Account.Name, Account.IsPersonAccount, Account.FirstName, Account.LastName,
                Account.CertificationNumber__pc, Account.CertificationNumber__c, Account.PersonMailingStreet, Account.PersonMailingCity, Account.PersonMailingState,
                Account.PersonMailingPostalCode, Account.BillingStreet, Account.BillingCity, Account.BillingState, Account.BillingPostalCode
            FROM BusinessLicense
            WHERE Id IN :licenseIds
            ORDER BY Account.Name, RegulatoryAuthorizationType.Name
        ];
        Set<Id> held = new Set<Id>();
        Set<Id> holderIds = new Set<Id>();
        for (BusinessLicense license : licenses) {
            holderIds.add(license.AccountId);
        }
        for (RecordAlert alert : [
            SELECT WhatId FROM RecordAlert
            WHERE WhatId IN :holderIds AND IsActive = true AND ValidUntilDate > :Datetime.now() AND RecordAlertCategoryId != null
        ]) {
            held.add(alert.WhatId);
        }
        for (BusinessLicense license : licenses) {
            if (license.IsReadyToPrint__c && !held.contains(license.AccountId)) {
                sheets.add(new Sheet(license));
            }
        }
        skippedCount = licenses.size() - sheets.size();
    }

    /** What prints on one sheet. */
    public class Sheet {
        public String certificationNumber { get; private set; }
        public String typeLine { get; private set; }
        public String issueDate { get; private set; }
        public String expirationDate { get; private set; }
        public String holderName { get; private set; }
        public List<String> addressLines { get; private set; }

        public Sheet(BusinessLicense license) {
            Account holder = license.Account;
            String holderNumber = holder.IsPersonAccount ? holder.CertificationNumber__pc : holder.CertificationNumber__c;
            certificationNumber = 'L' + (String.isNotBlank(holderNumber) ? holderNumber : license.Identifier);
            String typeName = license.RegulatoryAuthorizationType.Name;
            typeLine = typeName + '-' + reason(license);
            issueDate = license.PrintRequestedDate__c == null ? ''
                : Datetime.newInstance(license.PrintRequestedDate__c, Time.newInstance(12, 0, 0, 0)).format('MMMM d, yyyy');
            expirationDate = license.PeriodEnd == null ? '' : license.PeriodEnd.format('MMMM d, yyyy', 'America/Chicago');
            holderName = holder.IsPersonAccount && String.isNotBlank(holder.LastName)
                ? holder.LastName + (String.isNotBlank(holder.FirstName) ? ', ' + holder.FirstName : '') : holder.Name;
            addressLines = addressOf(holder);
        }
    }

    /** Why the license is printing: a duplicate, a renewal or a new license. */
    @TestVisible
    private static String reason(BusinessLicense license) {
        if (license.LastDuplicateDate__c != null && license.LastDuplicateDate__c == license.PrintRequestedDate__c) {
            return 'Duplicate';
        }
        return license.RenewalCount__c != null && license.RenewalCount__c > 0 ? 'Renewal' : 'New';
    }

    private static List<String> addressOf(Account holder) {
        Boolean usePerson = holder.IsPersonAccount && String.isNotBlank(holder.PersonMailingStreet);
        String street = usePerson ? holder.PersonMailingStreet : holder.BillingStreet;
        String city = usePerson ? holder.PersonMailingCity : holder.BillingCity;
        String state = usePerson ? holder.PersonMailingState : holder.BillingState;
        String postal = usePerson ? holder.PersonMailingPostalCode : holder.BillingPostalCode;
        List<String> lines = new List<String>();
        if (String.isNotBlank(street)) {
            lines.addAll(street.split('\n'));
        }
        String cityLine = (String.isNotBlank(city) ? city : '') + (String.isNotBlank(state) ? ', ' + state : '') + (String.isNotBlank(postal) ? ' ' + postal : '');
        if (String.isNotBlank(cityLine)) {
            lines.add(cityLine.removeStart(', '));
        }
        return lines;
    }
}
