({
    // Resume the paused interview named in the page address (?interviewId=...).
    init: function (component) {
        var interviewId = new URL(window.location.href).searchParams.get('interviewId');
        if (!interviewId) {
            component.set('v.message', 'There is no saved application to open. Your saved applications are listed on <a href="/LPI/s/view-license-permit-status">My Applications</a>.');
            return;
        }
        component.find('flow').resumeFlow(interviewId);
    },

    // An interview that was submitted, discarded or expired can't be resumed.
    statusChange: function (component, event) {
        if (event.getParam('status') === 'ERROR') {
            component.set('v.message', 'This saved application could not be opened. It may have been submitted, discarded, or deleted after 30 days. Check <a href="/LPI/s/view-license-permit-status">My Applications</a>, or call the Board at 225-756-3404.');
        }
    }
})
