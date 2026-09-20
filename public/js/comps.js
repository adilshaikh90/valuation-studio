/* comps.js - trading comps, implied values, regression chart */
let peersList = [];
let companySym = '$';
let companyPrice = 0;

document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected.</p>'; return; }

    const tickerEl = document.getElementById('sidebarTicker');
    if (tickerEl) tickerEl.textContent = ticker;
    
    const tickerDisp = document.getElementById('currentTickerDisplay');
    if (tickerDisp) tickerDisp.textContent = ticker;

    const addPeerBtn = document.getElementById('addPeerBtn');
    if (addPeerBtn) addPeerBtn.addEventListener('click', addPeer);

    await loadComps(ticker);
});

async function loadComps(ticker) {
    app.showLoading();
    try {
        const data = await api.getComps(ticker, peersList);
        const company = await api.getCompany(ticker);
        companySym = company.currency_symbol || '$';
        companyPrice = company.current_price || 0;

        const priceEl = document.getElementById('sidebarPrice');
        if (priceEl) priceEl.textContent = companySym + app.fmt(companyPrice);

        // ── Peer Universe Context ────────────────────────────
        const badge = document.getElementById('peerSourceBadge');
        if (badge && data.peer_source) {
            badge.textContent = data.peer_source;
        }
        const subtitle = document.getElementById('compsSubtitle');
        if (subtitle && (data.matched_industry || company.industry)) {
            subtitle.textContent = `Industry: ${data.matched_industry || company.industry} (${data.matched_region || 'Global'}) - Institutional Peer Comps`;
        }

        // ── Peer stats table & details ──────────────────────
        renderPeerTable(data.peer_data || []);
        renderPeerStats(data.peer_stats || {}, companySym);


        // ── Implied values ────────────────────────────────────
        renderImpliedValues(data.implied_values || {}, data.peer_stats || {}, companyPrice, companySym);

        // ── Regression chart ──────────────────────────────────
        if (data.regression_results && Object.keys(data.regression_results).length > 0) {
            renderRegressionChart(data.regression_results, ticker);
        } else {
            const rc = document.getElementById('regressionChart');
            if (rc && rc.parentElement) rc.parentElement.style.display = 'none';
        }

    } catch (err) {
        console.error(err);
        app.showError('Failed to load comps: ' + err.message);
    } finally {
        app.hideLoading();
    }
}

function renderPeerTable(peers) {
    const tbody = document.querySelector('#compsTable tbody');
    if (!tbody) return;
    
    if (!peers || peers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="11" style="text-align:center; padding: 2rem;">Peer data loading or not available for this ticker</td></tr>';
        return;
    }
    
    tbody.innerHTML = '';
    peers.forEach(p => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${p.ticker || 'N/A'}</strong></td>
            <td>${p.company_name || p.ticker || 'N/A'}</td>
            <td>${p.market_cap ? companySym + app.fmtLarge(p.market_cap) : 'N/A'}</td>
            <td>${p.ev_ebitda != null ? app.fmt(p.ev_ebitda) + 'x' : 'N/A'}</td>
            <td>${p.ev_ebit != null ? app.fmt(p.ev_ebit) + 'x' : 'N/A'}</td>
            <td>${p.p_e != null ? app.fmt(p.p_e) + 'x' : 'N/A'}</td>
            <td>${p.p_b != null ? app.fmt(p.p_b) + 'x' : 'N/A'}</td>
            <td>${p.ev_rev != null || p.ev_revenue != null ? app.fmt(p.ev_rev || p.ev_revenue) + 'x' : 'N/A'}</td>
            <td>${p.rev_growth != null ? (p.rev_growth * 100).toFixed(1) + '%' : 'N/A'}</td>
            <td>${p.ebitda_margin != null ? (p.ebitda_margin * 100).toFixed(1) + '%' : 'N/A'}</td>
            <td><button class="btn btn-sm btn-ghost" onclick="removePeer('${p.ticker}')" style="color:#ef4444; padding:0;">Remove</button></td>
        `;
        tbody.appendChild(tr);
    });
}

function renderPeerStats(stats, sym) {
    const tfoot = document.getElementById('compsFooter');
    if (!tfoot) return;
    
    let html = '';
    
    // Mean Row
    html += '<tr style="background: rgba(255,255,255,0.02); font-weight: 500;">';
    html += '<td colspan="3" style="text-align: right;"><strong>Mean</strong></td>';
    html += `<td>${stats.ev_ebitda?.mean != null ? app.fmt(stats.ev_ebitda.mean) + 'x' : 'N/A'}</td>`;
    html += `<td>${stats.ev_ebit?.mean != null ? app.fmt(stats.ev_ebit.mean) + 'x' : 'N/A'}</td>`;
    html += `<td>${stats.p_e?.mean != null ? app.fmt(stats.p_e.mean) + 'x' : 'N/A'}</td>`;
    html += `<td>${stats.p_b?.mean != null ? app.fmt(stats.p_b.mean) + 'x' : 'N/A'}</td>`;
    html += `<td>${stats.ev_revenue?.mean != null ? app.fmt(stats.ev_revenue.mean) + 'x' : 'N/A'}</td>`;
    html += '<td colspan="3"></td></tr>';
    
    // Median Row
    html += '<tr style="background: rgba(255,255,255,0.02); font-weight: 500;">';
    html += '<td colspan="3" style="text-align: right;"><strong>Median</strong></td>';
    html += `<td>${stats.ev_ebitda?.median != null ? app.fmt(stats.ev_ebitda.median) + 'x' : 'N/A'}</td>`;
    html += `<td>${stats.ev_ebit?.median != null ? app.fmt(stats.ev_ebit.median) + 'x' : 'N/A'}</td>`;
    html += `<td>${stats.p_e?.median != null ? app.fmt(stats.p_e.median) + 'x' : 'N/A'}</td>`;
    html += `<td>${stats.p_b?.median != null ? app.fmt(stats.p_b.median) + 'x' : 'N/A'}</td>`;
    html += `<td>${stats.ev_revenue?.median != null ? app.fmt(stats.ev_revenue.median) + 'x' : 'N/A'}</td>`;
    html += '<td colspan="3"></td></tr>';

    tfoot.innerHTML = html;
}

function renderImpliedValues(implied, stats, price, sym) {
    const tbody = document.querySelector('#impliedValueTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    const labels = { ev_ebitda: 'EV/EBITDA', ev_ebit: 'EV/EBIT', p_e: 'P/E', p_b: 'P/B', ev_revenue: 'EV/Rev' };
    
    let hasData = false;
    Object.entries(implied).forEach(([metric, val]) => {
        if (val == null || val === 0) return;
        hasData = true;
        const diff = price > 0 ? ((val / price) - 1) * 100 : 0;
        const cl   = diff >= 0 ? 'text-green' : 'text-red';
        const tr   = document.createElement('tr');
        
        let peerMed = stats[metric]?.median;
        let peerMedStr = peerMed != null ? app.fmt(peerMed) + 'x' : 'N/A';
        
        tr.innerHTML = `
            <td>${labels[metric] || metric}</td>
            <td>${peerMedStr}</td>
            <td>${sym}${app.fmt(val)}</td>
            <td class="${cl}">${diff >= 0 ? '+' : ''}${diff.toFixed(1)}%</td>
        `;
        tbody.appendChild(tr);
    });
    
    if (!hasData) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;">No implied values available</td></tr>';
    }
}

function renderRegressionChart(reg, ticker) {
    const ctx = document.getElementById('regressionChart')?.getContext('2d');
    if (!ctx) return;
    app.destroyChart('reg');

    const result = reg.ev_ebitda || Object.values(reg)[0];
    if (!result?.peers_data) return;

    const peerPoints  = result.peers_data.map(p => ({ x: p.growth, y: p.multiple }));
    const targetPoint = result.target ? [{ x: result.target.growth, y: result.target.multiple }] : [];

    app.saveChart('reg', new Chart(ctx, {
        type: 'scatter',
        data: {
            datasets: [
                { label: 'Peers',  data: peerPoints,  backgroundColor: 'rgba(59,130,246,0.7)', pointRadius: 6 },
                { label: ticker,   data: targetPoint, backgroundColor: '#f0b429', pointRadius: 10 },
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: {
                x: { title: { display: true, text: 'Revenue Growth', color: '#9ca3af' }, ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { title: { display: true, text: 'EV/EBITDA',      color: '#9ca3af' }, ticks: { color: '#9ca3af' }, grid: { color: 'rgba(255,255,255,0.05)' } },
            }
        }
    }));
}

async function addPeer() {
    const inp = document.getElementById('addPeerInput');
    const peer = inp?.value.trim().toUpperCase();
    if (peer && !peersList.includes(peer)) {
        peersList.push(peer);
        if (inp) inp.value = '';
        await loadComps(app.getTicker());
    }
}

window.removePeer = async function(peer) {
    peersList = peersList.filter(p => p !== peer);
    await loadComps(app.getTicker());
};

function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val ?? '0'; }
