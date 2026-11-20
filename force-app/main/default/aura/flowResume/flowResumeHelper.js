({
    UNAVAILABLE: 'This saved application is no longer available. Start a new one from <a href="/LPI/s/apply-license-permit">Apply</a>, or check <a href="/LPI/s/view-license-permit-status">My Applications</a>.',

    // True when the browser loaded this page from its address (not an in-portal page change).
    loadedHere: function (interviewId) {
        try {
            var entries = window.performance && window.performance.getEntriesByType ? window.performance.getEntriesByType('navigation') : [];
            if (!entries || !entries.length) {
                return true;
            }
            return new URL(entries[0].name).searchParams.get('interviewId') === interviewId;
        } catch (e) {
            return true;
        }
    },

    clearReload: function () {
        try { window.sessionStorage.removeItem('lsbcResumeReload'); } catch (e) { /* storage blocked: nothing to clear */ }
    },

    // Reload at most once per saved form, so a browser that reports the address differently can't loop.
    reloadedOnce: function (interviewId) {
        var key = 'lsbcResumeReload';
        try {
            if (window.sessionStorage.getItem(key) === interviewId) {
                window.sessionStorage.removeItem(key);
                return true;
            }
            window.sessionStorage.setItem(key, interviewId);
            return false;
        } catch (e) {
            return true;
        }
    }
})
