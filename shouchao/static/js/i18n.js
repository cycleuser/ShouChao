/* ShouChao i18n - client-side internationalization */
const T = window.SERVER_CONFIG?.translations || {};
let currentLang = window.SERVER_CONFIG?.currentLang || 'en';

function getT(key) {
    const entry = T[key];
    if (!entry) return key;
    return entry[currentLang] || entry['en'] || key;
}

function applyI18n() {
    requestAnimationFrame(function() {
        document.querySelectorAll('[data-i18n]').forEach(function(el) {
            const key = el.getAttribute('data-i18n');
            const text = getT(key);
            if (el.tagName === 'OPTION') {
                el.textContent = text;
            } else {
                el.textContent = text;
            }
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach(function(el) {
            el.placeholder = getT(el.getAttribute('data-i18n-placeholder'));
        });
    });
}

document.addEventListener('DOMContentLoaded', function() {
    applyI18n();
    const langSelect = document.getElementById('langSelect');
    if (langSelect) {
        langSelect.addEventListener('change', function() {
            currentLang = this.value;
            applyI18n();
            fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({language: currentLang})
            });
        });
    }
});
