/* ShouChao news browsing */

function loadNewsList() {
    const lang = document.getElementById('newsLang')?.value || '';
    const dateFrom = document.getElementById('newsDateFrom')?.value || '';
    const dateTo = document.getElementById('newsDateTo')?.value || '';
    const params = new URLSearchParams();
    if (lang) params.set('language', lang);
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo) params.set('date_to', dateTo);
    params.set('per_page', '100');

    fetch('/api/news/list?' + params)
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('newsList');
            list.innerHTML = '';
            (data.articles || []).forEach(a => {
                const item = document.createElement('div');
                item.className = 'list-item';
                item.innerHTML = '<div class="title">' + escHtml(a.title || 'Untitled') + '</div>' +
                    '<div class="meta">' + escHtml(a.website || '') + ' | ' +
                    escHtml(a.language || '') + ' | ' + escHtml(a.date || '') + '</div>';
                item.addEventListener('click', function() {
                    list.querySelectorAll('.list-item').forEach(i => i.classList.remove('active'));
                    item.classList.add('active');
                    loadArticle(a.path);
                });
                list.appendChild(item);
            });
            if (!data.articles || data.articles.length === 0) {
                list.innerHTML = '<div class="placeholder">No articles found</div>';
            }
        })
        .catch(e => console.error('Failed to load news:', e));
}

function loadArticle(path) {
    fetch('/api/news/article?path=' + encodeURIComponent(path))
        .then(r => r.json())
        .then(data => {
            document.getElementById('newsDetail').textContent = data.content || 'Error loading article';
        })
        .catch(e => {
            document.getElementById('newsDetail').textContent = 'Error: ' + e;
        });
}

function startFetch() {
    const lang = document.getElementById('newsLang')?.value || 'en';
    const detail = document.getElementById('newsDetail');
    detail.textContent = 'Fetching news...\n';

    const source = new EventSource('/api/news/fetch?' +
        new URLSearchParams({language: lang, max_articles: '10'}));

    // Use POST instead
    fetch('/api/news/fetch', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({language: lang || null, max_articles: 10})
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        function read() {
            reader.read().then(({value, done}) => {
                if (done) { loadNewsList(); return; }
                const text = decoder.decode(value);
                const lines = text.split('\n');
                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        try {
                            const d = JSON.parse(line.slice(6));
                            if (d.status === 'complete') {
                                detail.textContent += '\nDone! Fetched ' + d.fetched + ' articles.\n';
                                loadNewsList();
                            } else if (d.status === 'error') {
                                detail.textContent += '\nError: ' + d.error + '\n';
                            }
                        } catch(e) {}
                    }
                });
                read();
            });
        }
        read();
    }).catch(e => {
        detail.textContent += 'Error: ' + e + '\n';
    });
}

function escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

document.addEventListener('DOMContentLoaded', loadNewsList);
