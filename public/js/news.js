/* news.js — company news feed */
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
                
                let rawDate = item.published_date || item.providerPublishTime || item.published;
                let dateStr = '';
                if (rawDate) {
                    const d = new Date(typeof rawDate === 'number' && rawDate < 1000000000000 ? rawDate * 1000 : rawDate);
                    dateStr = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
                }

                const summary = item.summary || item.text || '';
                const thumb = item.thumbnail_url || item.thumbnail?.resolutions?.[0]?.url || item.image || '';
                const type = item.type || (item.video ? 'VIDEO' : 'STORY');
                
                const card = document.createElement('div');
                card.className = 'card news-item mb-4';
                card.style.display = 'flex';
                card.style.gap = '1.5rem';
                card.style.alignItems = 'flex-start';

                let imageHtml = '';
                if (thumb) {
                    imageHtml = `<div style="flex-shrink:0; width:120px; height:80px; border-radius:8px; overflow:hidden; background: #1f2937;">
                        <img src="${thumb}" alt="" style="width:100%; height:100%; object-fit:cover;" onerror="this.style.display='none'">
                    </div>`;
                } else {
                    // Placeholder gradient
                    imageHtml = `<div style="flex-shrink:0; width:120px; height:80px; border-radius:8px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); display:flex; align-items:center; justify-content:center; color:white; font-weight:bold; font-size:12px; text-align:center; padding: 0.5rem; word-break: break-word;">
                        ${publisher.substring(0, 15)}
                    </div>`;
                }

                card.innerHTML = `
                    ${imageHtml}
                    <div style="flex-grow:1;">
                        <div style="display:flex; gap:0.75rem; align-items:center; margin-bottom:0.5rem;">
                            <span class="badge" style="background-color:rgba(59,130,246,0.2); color:#60a5fa; padding:2px 8px; border-radius:12px; font-size:0.75rem;">${publisher}</span>
                            ${type === 'VIDEO' ? `<span class="badge" style="background-color:rgba(239,68,68,0.2); color:#f87171; padding:2px 8px; border-radius:12px; font-size:0.75rem;">VIDEO</span>` : ''}
                            <span style="font-size:0.85rem; color:#9ca3af;">${dateStr}</span>
                        </div>
                        <a href="${link}" target="_blank" rel="noopener noreferrer" style="text-decoration:none;">
                            <h3 style="margin:0 0 0.5rem 0; font-size:1.25rem; color:#f3f4f6;">${title}</h3>
                        </a>
                        ${summary ? `<p style="margin:0; font-size:0.95rem; color:#d1d5db; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;">${summary}</p>` : ''}
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
