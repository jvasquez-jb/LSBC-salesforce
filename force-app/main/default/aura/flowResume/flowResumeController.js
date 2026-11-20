({
    // Resume the paused interview named in the page address (?interviewId=...).
    init: function (component, event, helper) {
        var interviewId = new URL(window.location.href).searchParams.get('interviewId');
        if (!interviewId) {
            component.set('v.message', 'There is no saved application to open. Your saved applications are listed on <a href="/LPI/s/view-license-permit-status">My Applications</a>.');
            return;
        }
        // Resuming uses up the saved interview, so it must happen once, on a full page load.
        // A Continue link clicked inside the portal first changes the page in place and then the
        // browser loads the page again: resuming in both would resume twice, and the first screen
        // would be thrown away with the page while the second resume finds nothing left. So when
        // this page was reached without a page load, load it properly and resume only then.
        if (!helper.loadedHere(interviewId)) {
            if (!helper.reloadedOnce(interviewId)) {
                window.location.replace(window.location.href);
                return;
            }
        } else {
            helper.clearReload();
        }
        // If no screen appears (a stale link can leave an empty box), show the message after 15 seconds.
        window.setTimeout($A.getCallback(function () {
            if (component.isValid() && !component.get('v.started') && !component.get('v.message')) {
                component.set('v.message', helper.UNAVAILABLE);
            }
        }), 15000);
        try {
            component.find('flow').resumeFlow(interviewId);
        } catch (e) {
            component.set('v.message', helper.UNAVAILABLE);
        }
    },

    // An interview that was submitted, discarded or expired can't be resumed. The status can come
    // back as ERROR or Error, so compare in capitals.
    statusChange: function (component, event, helper) {
        var status = String(event.getParam('status') || '').toUpperCase();
        if (status === 'ERROR') {
            component.set('v.message', helper.UNAVAILABLE);
        } else if (status) {
            component.set('v.started', true);
        }
    }
})
