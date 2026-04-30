// Lightweight client-side i18n. The catalog is injected in base.html as
// window.I18N for the active locale; window.LOCALE holds the locale code.
//
// Usage: window.t("schedule.toast.session_moved", {date: "25/04"})
// Missing keys return the key itself so the UI never blanks out, and to make
// missing translations obvious during development.
(function () {
    function resolve(catalog, key) {
        var cur = catalog;
        var parts = key.split(".");
        for (var i = 0; i < parts.length; i++) {
            if (cur == null || typeof cur !== "object") return null;
            cur = cur[parts[i]];
        }
        return typeof cur === "string" ? cur : null;
    }

    function format(template, vars) {
        if (!vars) return template;
        return template.replace(/\{(\w+)\}/g, function (match, name) {
            return Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : match;
        });
    }

    window.t = function (key, vars) {
        var catalog = window.I18N || {};
        var hit = resolve(catalog, key);
        if (hit == null) return key;
        return format(hit, vars);
    };

    // Browser-locale-aware date formatter used by calendar/dashboard.
    window.tDate = function (date, options) {
        var locale = window.LOCALE || "pt-BR";
        return date.toLocaleDateString(locale, options || {});
    };
})();
