/* news.js — company news feed */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected.</p>'; return; }

    document.querySelectorAll('.currentTickerDisplay').forEach(el => el.textContent = ticker);
    await loadNews(ticker);
});

async function loadNews(ticker) {
    app.showLoading();
    try {
        const news = await api.getNews(ticker);

        const grid   = document.getElementById('newsGrid');
        const noNews = document.getElementById('noNews');

        if (!news || news.length === 0) {
            if (grid)   grid.style.display   = 'none';
            if (noNews) noNews.style.display  = 'block';
            return;
        }

        if (noNews) noNews.style.display = 'none';
        if (grid) {
            grid.innerHTML = '';
            news.forEach(item => {
                const card = document.createElement('a');
                card.href   = item.link || item.url || '#';
                card.target = '_blank';
                card.rel    = 'noopener noreferrer';
                card.className = 'card news-card';
                card.style.cssText = 'display:block;text-decoration:none;transition:transform .2s;cursor:pointer;';

                card.addEventListener('mouseenter', () => card.style.transform = 'translateY(-4px)');
                card.addEventListener('mouseleave', () => card.style.transform = '');

                const rawDate = item.providerPublishTime || item.published || item.publishedDate;
                const date    = rawDate ? new Date(typeof rawDate === 'number' ? rawDate * 1000 : rawDate).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '';
                const source  = item.publisher || item.site || item.source || '';
                const title   = item.title || 'No title';
                const summary = item.summary || item.text || '';
                const thumb   = item.thumbnail?.resolutions?.[0]?.url || item.image || '';

                card.innerHTML = `
                    ${thumb ? `<div style="height:180px;overflow:hidden;border-radius:8px 8px 0 0;"><img src="${thumb}" alt="" style="width:100%;height:100%;object-fit:cover;" onerror="this.parentElement.style.display='none'"></div>` : ''}
                    <div style="padding:1.25rem;">
                        <div style="display:flex;gap:.5rem;align-items:center;margin-bottom:.75rem;">
                            ${source ? `<span class="badge">${source}</span>` : ''}
                            ${date ? `<span style="font-size:.75rem;color:#6b7280;">${date}</span>` : ''}
                        </div>
                        <h3 style="font-size:1rem;line-height:1.5;margin:0 0 .5rem;color:#f9fafb;">${title}</h3>
                        ${summary ? `<p style="font-size:.85rem;color:#9ca3af;margin:0;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;">${summary}</p>` : ''}
                    </div>
                `;
                grid.appendChild(card);
            });
        }

    } catch (err) {
        console.error(err);
        app.showError('Failed to load news: ' + err.message);
    } finally {
        app.hideLoading();
    }
}
