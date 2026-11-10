/**
 * Formats a letter for the LetterPdf page: the addressee, the date, and the template's heading and
 * body with its merge fields filled in. The wording lives in Letter Template custom metadata; this
 * class only reads records and lays the letter out.
 *
 * Page parameters: id (an Account, Individual Application or Business License Application),
 * template (the Letter Template's developer name) and details (text staff typed, optional).
 */
public with sharing class LetterPdfController {
    public String addresseeName { get; private set; }
    public List<String> addressLines { get; private set; }
    public String letterDate { get; private set; }
    public String heading { get; private set; }
    public String bodyHtml { get; private set; }

    private static final Set<String> OPEN_FEE_STATUSES = new Set<String>{ 'DUE', 'PARTIALLY_PAID' };
    private static final Set<String> MISSING_ITEM_STATUSES = new Set<String>{ 'New', 'Rejected' };

    public LetterPdfController() {
        Map<String, String> params = ApexPages.currentPage().getParameters();
        build(params.get('id'), params.get('template'), params.get('details'));
    }

    @TestVisible
    private LetterPdfController(String recordId, String templateName, String details) {
        build(recordId, templateName, details);
    }

    private void build(String recordId, String templateName, String details) {
        // Queried, not getInstance(): getInstance() cuts long text fields to 255 characters.
        List<LetterTemplate__mdt> templates = [SELECT Heading__c, Body__c FROM LetterTemplate__mdt WHERE DeveloperName = :templateName LIMIT 1];
        LetterTemplate__mdt template = templates.isEmpty() ? null : templates[0];
        if (template == null || String.isBlank(recordId)) {
            throw new LetterException('Letter template or record not found.');
        }
        Id parentId = (Id) recordId;
        String objectName = parentId.getSobjectType().getDescribe().getName();
        String applicationNumber = '';
        Id accountId;
        if (objectName == 'Account') {
            accountId = parentId;
        } else if (objectName == 'IndividualApplication') {
            IndividualApplication app = [SELECT Name, AccountId FROM IndividualApplication WHERE Id = :parentId];
            accountId = app.AccountId;
            applicationNumber = app.Name;
        } else if (objectName == 'BusinessLicenseApplication') {
            BusinessLicenseApplication app = [SELECT Name, AccountId FROM BusinessLicenseApplication WHERE Id = :parentId];
            accountId = app.AccountId;
            applicationNumber = app.Name;
        } else {
            throw new LetterException('Letters can only be generated from an account or an application.');
        }

        Account holder = [
            SELECT Name, IsPersonAccount, PersonMailingStreet, PersonMailingCity, PersonMailingState, PersonMailingPostalCode,
                BillingStreet, BillingCity, BillingState, BillingPostalCode
            FROM Account WHERE Id = :accountId
        ];
        addresseeName = holder.Name;
        addressLines = addressOf(holder);
        letterDate = Date.today().format();
        heading = fillMergeFields(template.Heading__c, holder.Name, applicationNumber, details, parentId, accountId, objectName, false);
        bodyHtml = fillMergeFields(template.Body__c, holder.Name, applicationNumber, details, parentId, accountId, objectName, true);
    }

    private static List<String> addressOf(Account holder) {
        String street = holder.IsPersonAccount && String.isNotBlank(holder.PersonMailingStreet) ? holder.PersonMailingStreet : holder.BillingStreet;
        String city = holder.IsPersonAccount && String.isNotBlank(holder.PersonMailingStreet) ? holder.PersonMailingCity : holder.BillingCity;
        String state = holder.IsPersonAccount && String.isNotBlank(holder.PersonMailingStreet) ? holder.PersonMailingState : holder.BillingState;
        String postal = holder.IsPersonAccount && String.isNotBlank(holder.PersonMailingStreet) ? holder.PersonMailingPostalCode : holder.BillingPostalCode;
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

    /** Replaces the merge fields. As HTML, text is escaped, blank lines become paragraphs and line breaks stay. */
    private static String fillMergeFields(String text, String name, String applicationNumber, String details, Id parentId, Id accountId, String objectName, Boolean asHtml) {
        if (text == null) {
            return '';
        }
        Map<String, String> values = new Map<String, String>{
            '{{Name}}' => name,
            '{{Date}}' => Date.today().format(),
            '{{ApplicationNumber}}' => applicationNumber,
            '{{Details}}' => details == null ? '' : details.trim()
        };
        if (text.contains('{{BalanceDue}}')) {
            values.put('{{BalanceDue}}', balanceDue(parentId, accountId, objectName));
        }
        String missingHtml = '';
        if (text.contains('{{MissingItems}}')) {
            List<String> missing = missingItems(parentId);
            values.put('{{MissingItems}}', String.join(missing, '; '));
            if (asHtml) {
                missingHtml = '<ul>';
                for (String item : missing) {
                    missingHtml += '<li>' + item.escapeHtml4() + '</li>';
                }
                missingHtml += '</ul>';
            }
        }
        if (!asHtml) {
            String result = text;
            for (String token : values.keySet()) {
                result = result.replace(token, values.get(token) == null ? '' : values.get(token));
            }
            return result;
        }
        String html = '';
        for (String paragraph : text.replace('\r\n', '\n').split('\n\\s*\n')) {
            String trimmed = paragraph.trim();
            if (trimmed == '{{MissingItems}}') {
                html += missingHtml;
                continue;
            }
            String escaped = trimmed.escapeHtml4();
            for (String token : values.keySet()) {
                String value = values.get(token) == null ? '' : values.get(token);
                escaped = escaped.replace(token, value.escapeHtml4().replace('\n', '<br/>'));
            }
            if (String.isNotBlank(escaped)) {
                html += '<p>' + escaped.replace('\n', '<br/>') + '</p>';
            }
        }
        return html;
    }

    private static List<String> missingItems(Id parentId) {
        List<String> names = new List<String>();
        for (DocumentChecklistItem item : [
            SELECT Name FROM DocumentChecklistItem
            WHERE ParentRecordId = :parentId AND IsRequired = true AND Status IN :MISSING_ITEM_STATUSES
            ORDER BY Name
        ]) {
            names.add(item.Name);
        }
        if (names.isEmpty()) {
            names.add('None. All required documents have been received.');
        }
        return names;
    }

    private static String balanceDue(Id parentId, Id accountId, String objectName) {
        Decimal total = 0;
        List<RegulatoryTrxnFee> fees = objectName == 'Account'
            ? [SELECT TotalFeeAmount, AmountPaid__c FROM RegulatoryTrxnFee WHERE AccountId = :accountId AND Status IN :OPEN_FEE_STATUSES]
            : [SELECT TotalFeeAmount, AmountPaid__c FROM RegulatoryTrxnFee WHERE ParentRecordId = :parentId AND Status IN :OPEN_FEE_STATUSES];
        for (RegulatoryTrxnFee fee : fees) {
            total += (fee.TotalFeeAmount == null ? 0 : fee.TotalFeeAmount) - (fee.AmountPaid__c == null ? 0 : fee.AmountPaid__c);
        }
        return money(total);
    }

    /** $1,234.50 style, independent of the user's locale. */
    @TestVisible
    private static String money(Decimal amount) {
        String plain = amount.setScale(2).abs().toPlainString();
        String whole = plain.substringBefore('.');
        String grouped = '';
        while (whole.length() > 3) {
            grouped = ',' + whole.right(3) + grouped;
            whole = whole.left(whole.length() - 3);
        }
        return (amount < 0 ? '-' : '') + '$' + whole + grouped + '.' + plain.substringAfter('.');
    }

    public class LetterException extends Exception {
    }
}
