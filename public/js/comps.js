/* comps.js — trading comps, implied values, regression chart */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected.</p>'; return; }

    document.querySelectorAll('.currentTickerDisplay').forEach(el => el.textContent = ticker);

    const addPeerBtn = document.getElementById('addPeerBtn');
    if (addPeerBtn) addPeerBtn.addEventListener('click', addPeer);

    await loadComps(ticker);
});

let peersList = [];

async function loadComps(ticker) {
    app.showLoading();
    try {
        const data = await api.getComps(ticker, peersList);
        const company = await api.getCompany(ticker);
        const sym = company.currency_symbol || '$';
        const price = company.current_price || 0;

        // ── Target metrics ────────────────────────────────────
        const t = data.target_metrics || {};
        setText('targetEVEBITDA',  t.ev_ebitda ? app.fmt(t.ev_ebitda) + 'x' : 'N/A');
        setText('targetPE',        t.p_e ? app.fmt(t.p_e) + 'x' : 'N/A');
        setText('targetEVRev',     t.ev_revenue ? app.fmt(t.ev_revenue) + 'x' : 'N/A');
        setText('targetPB',        t.p_b ? app.fmt(t.p_b) + 'x' : 'N/A');

        // ── Peer stats table ──────────────────────────────────
        renderPeerStats(data.peer_stats || {}, sym);

        // ── Implied values ────────────────────────────────────
        renderImpliedValues(data.implied_values || {}, price, sym);

        // ── Regression chart ──────────────────────────────────
        if (data.regression_results) renderRegressionChart(data.regression_results, ticker);

        // Show active peers
        renderActivePeers();

    } catch (err) {
        console.error(err);
        app.showError('Failed to load comps: ' + err.message);
    } finally {
        app.hideLoading();
    }
}

function renderPeerStats(stats, sym) {
    const el = document.getElementById('peerStatsTable');
    if (!el) return;
    const metrics = ['ev_ebitda', 'ev_ebit', 'p_e', 'p_b', 'ev_revenue'];
    const labels  = { ev_ebitda: 'EV/EBITDA', ev_ebit: 'EV/EBIT', p_e: 'P/E', p_b: 'P/B', ev_revenue: 'EV/Revenue' };
    let html = '<table class="data-table"><thead><tr><th>Metric</th><th>Mean</th><th>Median</th><th>P25</th><th>P75</th></tr></thead><tbody>';
    metrics.forEach(m => {
        const s = stats[m];
        if (!s) return;
        html += `<tr>
            <td>${labels[m] || m}</td>
            <td>${s.mean != null ? app.fmt(s.mean) + 'x' : '–'}</td>
            <td><strong>${s.median != null ? app.fmt(s.median) + 'x' : '–'}</strong></td>
            <td>${s.p25 != null ? app.fmt(s.p25) + 'x' : '–'}</td>
            <td>${s.p75 != null ? app.fmt(s.p75) + 'x' : '–'}</td>
        </tr>`;
    });
    el.innerHTML = html + '</tbody></table>';
}

function renderImpliedValues(implied, price, sym) {
    const tbody = document.querySelector('#impliedValueTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    const labels = { ev_ebitda: 'EV/EBITDA', ev_ebit: 'EV/EBIT', p_e: 'P/E', p_b: 'P/B' };
    Object.entries(implied).forEach(([metric, val]) => {
        if (val == null || val === 0) return;
        const diff = price > 0 ? ((val / price) - 1) * 100 : 0;
        const cl   = diff >= 0 ? 'text-green' : 'text-red';
        const tr   = document.createElement('tr');
        tr.innerHTML = `
            <td>${labels[metric] || metric}</td>
            <td>${sym}${app.fmt(val)}</td>
            <td class="${cl}">${diff >= 0 ? '+' : ''}${diff.toFixed(1)}%</td>
        `;
        tbody.appendChild(tr);
    });
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

function renderActivePeers() {
    const el = document.getElementById('activePeers');
    if (!el) return;
    el.innerHTML = peersList.length
        ? peersList.map(p => `<span class="badge" style="cursor:pointer;margin:.25rem;" onclick="removePeer('${p}')">${p} ×</span>`).join('')
        : '<span style="color:#6b7280;font-size:.85rem;">Using auto-detected peers</span>';
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

function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val ?? '–'; }
