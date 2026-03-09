/* ShouChao briefing UI */

function generateBriefing() {
    const type = document.getElementById('briefingType')?.value || 'daily';
    const lang = document.getElementById('briefingLang')?.value || '';
    const output = document.getElementById('briefingOutput');
    output.textContent = 'Generating briefing...\n';

    fetch('/api/briefing/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({type: type, language: lang || null})
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
