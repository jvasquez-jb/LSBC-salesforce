({
    // Resume the paused interview named in the page address (?interviewId=...).
    init: function (component) {
        var interviewId = new URL(window.location.href).searchParams.get('interviewId');
        if (!interviewId) {
            component.set('v.message', 'There is no saved application to open. Your saved applications are listed on <a href="/LPI/s/view-license-permit-status">My Applications</a>.');
            return;
        }
        // A stale or malformed link makes resumeFlow throw, or leaves the flow empty: show the message instead.
        // If the flow never reports a status (a stale link leaves an empty box), show the message after 15 seconds.
        window.setTimeout($A.getCallback(function () {
            if (component.isValid() && !component.get('v.started') && !component.get('v.message')) {
                component.set('v.message', 'This saved application is no longer available. Start a new one from <a href="/LPI/s/apply-license-permit">Apply</a>.');
            }
        }), 15000);
        try {
            component.find('flow').resumeFlow(interviewId);
        } catch (e) {
            component.set('v.message', 'This saved application is no longer available. Start a new one from <a href="/LPI/s/apply-license-permit">Apply</a>.');
        }
    },

    // An interview that was submitted, discarded or expired can't be resumed.
    statusChange: function (component, event) {
        if (event.getParam('status') !== 'ERROR') {
            component.set('v.started', true);
        }
        if (event.getParam('status') === 'ERROR') {
            component.set('v.message', 'This saved application is no longer available. Start a new one from <a href="/LPI/s/apply-license-permit">Apply</a>.');
        }
    }
})
