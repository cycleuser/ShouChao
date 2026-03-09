/* ShouChao analysis and search UI */

function runAnalysis() {
    const query = document.getElementById('analysisQuery')?.value || '';
    if (!query.trim()) { alert('Enter a query'); return; }
    const scenario = document.getElementById('analysisScenario')?.value || 'general';
    const output = document.getElementById('analysisOutput');
    output.textContent = 'Analyzing...\n';

    fetch('/api/analysis', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: query, scenario: scenario})
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        output.textContent = '';
        function read() {
            reader.read().then(({value, done}) => {
                if (done) return;
                const text = decoder.decode(value);
                text.split('\n').forEach(line => {
                    if (line.startsWith('data: ')) {
                        try {
                            const d = JSON.parse(line.slice(6));
                            if (d.content) output.textContent += d.content;
                            if (d.error) output.textContent += '\nError: ' + d.error;
                        } catch(e) {}
                    }
                });
                read();
            });
        }
        read();
    }).catch(e => {
        output.textContent = 'Error: ' + e;
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const q = document.getElementById('analysisQuery');
    if (q) q.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') runAnalysis();
    });
});

function doSearch() {
    const query = document.getElementById('searchQuery')?.value || '';
    if (!query.trim()) return;
    const list = document.getElementById('searchResults');
    const detail = document.getElementById('searchDetail');
    list.innerHTML = '<div class="placeholder">Searching...</div>';
    detail.textContent = '';

    fetch('/api/search', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({query: query, top_k: 20})
    })
    .then(r => r.json())
    .then(data => {
        list.innerHTML = '';
        const results = data.data?.results || [];
        if (results.length === 0) {
            list.innerHTML = '<div class="placeholder">No results found</div>';
            return;
        }
        results.forEach(r => {
            const m = r.metadata || {};
            const dist = r.distance || 0;
            const score = dist < 2 ? (1 - dist).toFixed(2) : '0.00';
            const item = document.createElement('div');
            item.className = 'list-item';
            item.innerHTML = '<div class="title">' + escHtml(m.title || 'Untitled') + '</div>' +
                '<div class="meta">Score: ' + score + ' | ' +
                escHtml(m.website || '') + ' | ' + escHtml(m.date || '') + '</div>';
            item.addEventListener('click', function() {
                list.querySelectorAll('.list-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                detail.textContent = r.document || '';
            });
            list.appendChild(item);
        });
    })
    .catch(e => {
        list.innerHTML = '<div class="placeholder">Error: ' + e + '</div>';
    });
}

function escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

document.addEventListener('DOMContentLoaded', function() {
    const sq = document.getElementById('searchQuery');
    if (sq) sq.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') doSearch();
    });
});
