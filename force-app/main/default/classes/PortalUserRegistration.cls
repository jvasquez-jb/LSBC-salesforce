/**
 * Creates the portal login for a licensee who has registered on the LSBC portal.
 *
 * Called from Screen Flow: Account Portal Registration after the flow has matched the visitor
 * to their person account (license number, last or maiden name, and ZIP code). Matching stays
 * in the flow; this class only does the one thing a guest-run flow can't: create the user.
 * Salesforce then emails the new user a link to set their password.
 *
 * Licences and the Portal Licensee permission set are assigned afterwards by
 * Record-Trigger: User After Save, outside this transaction.
 */
public without sharing class PortalUserRegistration {

    public static final String PORTAL_PROFILE = 'LSBC Portal User';

    public class Request {
        @InvocableVariable(label='Person Account Id' required=true)
        public Id accountId;
        @InvocableVariable(label='Email' required=true)
        public String email;
    }

    public class Result {
        @InvocableVariable(label='User Id')
        public Id userId;
        @InvocableVariable(label='Error Message')
        public String errorMessage;
    }

    @InvocableMethod(label='Create Portal User' description='Creates the LSBC portal login for a matched person account and emails the person a link to set their password.')
    public static List<Result> createPortalUsers(List<Request> requests) {
        List<Result> results = new List<Result>();
        Id profileId = [SELECT Id FROM Profile WHERE Name = :PORTAL_PROFILE LIMIT 1].Id;
        for (Request req : requests) {
            results.add(createOne(req, profileId));
        }
        return results;
    }

    private static Result createOne(Request req, Id profileId) {
        Result res = new Result();
        String email = req.email == null ? '' : req.email.trim().toLowerCase();
        Account acc = [SELECT Id, FirstName, LastName, PersonContactId FROM Account WHERE Id = :req.accountId AND IsPersonAccount = true LIMIT 1];

        if (![SELECT Id FROM User WHERE ContactId = :acc.PersonContactId LIMIT 1].isEmpty()) {
            res.errorMessage = 'You already have a portal login. Use Log in, or Forgot your password.';
            return res;
        }
        if (![SELECT Id FROM User WHERE Username = :email LIMIT 1].isEmpty()) {
            res.errorMessage = 'That email address is already used by another login. Use a different email address, or call the Board at 225-756-3404.';
            return res;
        }

        User u = new User(
            Username = email,
            Email = email,
            FirstName = acc.FirstName,
            LastName = acc.LastName,
            ContactId = acc.PersonContactId,
            ProfileId = profileId,
            CommunityNickname = uniqueNickname(acc),
            Alias = alias(acc),
            TimeZoneSidKey = 'America/Chicago',
            LocaleSidKey = 'en_US',
            EmailEncodingKey = 'UTF-8',
            LanguageLocaleKey = 'en_US'
        );
        try {
            res.userId = Site.createExternalUser(u, acc.Id, null, true);
            if (res.userId == null) {
                res.errorMessage = 'Your login could not be created. Please call the Board at 225-756-3404.';
            }
        } catch (Exception e) {
            res.errorMessage = 'Your login could not be created. Please call the Board at 225-756-3404.';
            System.debug(LoggingLevel.ERROR, 'Portal registration failed for ' + acc.Id + ': ' + e.getMessage());
        }
        return res;
    }

    private static String uniqueNickname(Account acc) {
        String base = ((acc.FirstName == null ? '' : acc.FirstName) + '.' + acc.LastName).replaceAll('[^A-Za-z0-9.]', '').left(30);
        return base + '.' + String.valueOf(Crypto.getRandomInteger()).replace('-', '').left(6);
    }

    private static String alias(Account acc) {
        String a = ((acc.FirstName == null ? 'x' : acc.FirstName.left(1)) + acc.LastName).replaceAll('[^A-Za-z0-9]', '');
        return a.left(8);
    }
}
