// Global UI behaviour.
(function () {
    "use strict";

    // Auto-dismiss success/info flash messages after a few seconds.
    document.querySelectorAll('.alert-success, .alert-info').forEach(function (el) {
        setTimeout(function () {
            if (window.bootstrap && bootstrap.Alert) {
                bootstrap.Alert.getOrCreateInstance(el).close();
            }
        }, 4000);
    });
})();
