/* news.js - company news feed */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected.</p>'; return; }

    const tickerEl = document.getElementById('sidebarTicker');
    if (tickerEl) tickerEl.textContent = ticker;

    const searchInput = document.getElementById('newsSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const filter = e.target.value.toLowerCase();
            document.querySelectorAll('.news-item').forEach(el => {
                const text = el.textContent.toLowerCase();
                el.style.display = text.includes(filter) ? 'flex' : 'none';
            });
        });
    }

    await loadNews(ticker);
});

async function loadNews(ticker) {
    const loading = document.getElementById('newsLoading');
    const container = document.getElementById('newsContainer');
    const noNews = document.getElementById('noNews');

    if (loading) loading.style.display = 'block';
    if (container) container.style.display = 'none';
    if (noNews) noNews.style.display = 'none';

    try {
        const news = await api.getNews(ticker);
        
        // Also get price for sidebar
        try {
            const company = await api.getCompany(ticker);
            const priceEl = document.getElementById('sidebarPrice');
            if (priceEl && company) priceEl.textContent = (company.currency_symbol || '$') + app.fmt(company.current_price || 0);
        } catch(e) {}
        
        if (loading) loading.style.display = 'none';

        if (!news || news.length === 0) {
            if (noNews) noNews.style.display = 'block';
            return;
        }

        if (container) {
            container.innerHTML = '';
            container.style.display = 'block';
            
            let itemsAdded = 0;

            news.forEach(item => {
                const title = item.title || item.headline || '';
                if (!title || title.trim() === '') return;

                const link = item.link || item.url || '#';
                const publisher = item.publisher || item.source || 'Yahoo Finance';
                
                let dateStr = item.published_date || '';
                if (!dateStr && item.raw_date) {
                    try {
                        const raw = item.raw_date;
                        const d = new Date(typeof raw === 'number' && raw < 1000000000000 ? raw * 1000 : raw);
                        dateStr = d.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
                    } catch(e) {
                        dateStr = '';
                    }
                }


                const summary = item.summary || item.text || '';
                const thumb = item.thumbnail_url || item.thumbnail?.resolutions?.[0]?.url || item.image || '';
                const type = item.type || (item.video ? 'VIDEO' : 'STORY');
                
                const card = document.createElement('div');
                card.className = 'card news-item';
                card.style.display = 'flex';
                card.style.gap = '1.5rem';
                card.style.alignItems = 'flex-start';
                card.style.padding = '1.25rem';

                let imageHtml = '';
                if (thumb) {
                    imageHtml = `<div style="flex-shrink:0; width:130px; height:85px; border-radius:8px; overflow:hidden; background: var(--surface-3);">
                        <img src="${thumb}" alt="" style="width:100%; height:100%; object-fit:cover;" onerror="this.parentElement.style.display='none'">
                    </div>`;
                } else {
                    imageHtml = `<div style="flex-shrink:0; width:130px; height:85px; border-radius:8px; background: var(--surface-3); border:1px solid var(--border-color); display:flex; align-items:center; justify-content:center; color:var(--text-muted); font-weight:600; font-size:11px; text-align:center; padding: 0.5rem;">
                        ${publisher.substring(0, 18)}
                    </div>`;
                }

                card.innerHTML = `
                    ${imageHtml}
                    <div style="flex-grow:1; min-width:0;">
                        <div style="display:flex; gap:0.6rem; align-items:center; margin-bottom:0.4rem; flex-wrap:wrap;">
                            <span class="badge badge-blue" style="font-size:0.75rem;">${publisher}</span>
                            ${type === 'VIDEO' ? `<span class="badge badge-red" style="font-size:0.75rem;">VIDEO</span>` : ''}
                            <span style="font-size:0.8rem; color:var(--text-muted);">${dateStr}</span>
                        </div>
                        <a href="${link}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;">
                            <h3 style="margin:0 0 0.4rem 0; font-size:1.15rem; color:var(--text-primary); line-height:1.35;">${title}</h3>
                        </a>
                        ${summary ? `<p style="margin:0; font-size:0.875rem; color:var(--text-secondary); line-height:1.5; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">${summary}</p>` : ''}
                    </div>
                `;

                container.appendChild(card);
                itemsAdded++;

            });

            if (itemsAdded === 0 && noNews) {
                container.style.display = 'none';
                noNews.style.display = 'block';
            }
        }

    } catch (err) {
        console.error(err);
        if (loading) loading.style.display = 'none';
        app.showError('Failed to load news: ' + err.message);
    }
}
