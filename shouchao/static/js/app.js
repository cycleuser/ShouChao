/* ShouChao main app logic */

function switchView(viewName) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.nav-links li').forEach(l => l.classList.remove('active'));
    const view = document.getElementById('view-' + viewName);
    if (view) view.classList.add('active');
    document.querySelectorAll('.nav-links li').forEach(l => {
        if (l.dataset.view === viewName) l.classList.add('active');
    });
}

function loadStats() {
    fetch('/api/stats')
        .then(r => r.json())
        .then(data => {
            const el = document.getElementById('statArticles');
            if (el) el.textContent = data.articles?.total || 0;
            const se = document.getElementById('statSources');
            if (se) se.textContent = data.sources_count || 0;
        })
        .catch(() => {});
}

function testConnection() {
    fetch('/api/test-connection')
        .then(r => r.json())
        .then(data => {
            alert(data.available ? 'Ollama is connected!' : 'Ollama is not available');
        })
        .catch(e => alert('Connection test failed: ' + e));
}

function saveSettings() {
    const settings = {
        ollama_url: document.getElementById('settOllamaUrl').value,
        chat_model: document.getElementById('settChatModel').value,
        embedding_model: document.getElementById('settEmbedModel').value,
        proxy_mode: document.getElementById('settProxyMode').value,
        proxy_http: document.getElementById('settProxyHttp').value,
        proxy_https: document.getElementById('settProxyHttps').value,
        default_fetcher: document.getElementById('settFetcher').value,
        fetch_delay: parseFloat(document.getElementById('settDelay').value),
    };
    fetch('/api/settings', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(settings)
    })
    .then(r => r.json())
    .then(() => alert('Settings saved'))
    .catch(e => alert('Error: ' + e));
}

// Navigation
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.nav-links li').forEach(li => {
        li.addEventListener('click', function() {
            switchView(this.dataset.view);
        });
    });
    loadStats();
});
