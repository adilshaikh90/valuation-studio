/* quant.js — Monte Carlo, Sensitivity, Tornado, Scenarios */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected.</p>'; return; }

    document.querySelectorAll('.currentTickerDisplay').forEach(el => el.textContent = ticker);
    setupTabs();
    await loadQuantData(ticker);
});

function setupTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
            tab.classList.add('active');
            const target = document.getElementById('tab-' + tab.dataset.tab);
            if (target) target.style.display = 'block';
        });
    });
    const first = document.querySelector('.tab-btn');
    if (first) first.click();
}

async function loadQuantData(ticker) {
    app.showLoading();
    try {
        const [mcRes, sensRes, torRes, scenRes, wScenRes] = await Promise.allSettled([
            api.getMonteCarlo(ticker, 10000),
            api.getSensitivity(ticker),
            api.getTornado(ticker),
            api.getScenarios(ticker),
            api.getScenarioWeighting(ticker),
        ]);

        const company = await api.getCompany(ticker);
        const sym = company.currency_symbol || '$';
        const price = company.current_price || 0;

        // ── Monte Carlo ─────────────────────────────────────
        if (mcRes.status === 'fulfilled') {
            const mc = mcRes.value;
            setText('mcMean',    sym + app.fmt(mc.mean));
            setText('mcMedian',  sym + app.fmt(mc.median));
            setText('mcStdDev',  sym + app.fmt(mc.std_dev || mc.std));
            setText('mcP5',      sym + app.fmt(mc.percentile_5));
            setText('mcP95',     sym + app.fmt(mc.percentile_95));
            const prob = mc.probability_of_upside != null ? mc.probability_of_upside * 100 : null;
            setText('mcProb',    prob != null ? prob.toFixed(1) + '% chance of upside' : '–');
            if (mc.bins && mc.frequencies) renderMCChart(mc, sym, price);
        }

        // ── Sensitivity ─────────────────────────────────────
        if (sensRes.status === 'fulfilled') {
            const s = sensRes.value;
            setText('sensBaseValue', sym + app.fmt(s.base_value));
            renderHeatmap('sensWaccTgr', s.wacc_vs_tg, price, sym);
            renderHeatmap('sensWaccExit', s.wacc_vs_em, price, sym);
        }

        // ── Tornado ─────────────────────────────────────────
        if (torRes.status === 'fulfilled') {
            const t = torRes.value;
            setText('tornadoBase', sym + app.fmt(t.base_price));
            renderTornado(t.tornado_data || []);
        }

        // ── Scenarios ────────────────────────────────────────
        if (scenRes.status === 'fulfilled') {
            renderScenarios(scenRes.value.scenarios || [], sym, price);
        }

        // ── Weighted Scenarios ──────────────────────────────
        if (wScenRes.status === 'fulfilled') {
            const ws = wScenRes.value;
            setText('weightedValue',  sym + app.fmt(ws.weighted_value));
            const upside = ws.upside_pct != null ? ws.upside_pct * 100 : null;
            setUpsideEl('weightedUpside', upside);
            renderWeightedScenarios(ws.scenarios || [], sym);
        }

    } catch (err) {
        console.error(err);
        app.showError('Failed to load analysis: ' + err.message);
    } finally {
        app.hideLoading();
    }
}

function renderMCChart(mc, sym, currentPrice) {
    const ctx = document.getElementById('mcChart')?.getContext('2d');
    if (!ctx) return;
    app.destroyChart('mc');
    app.saveChart('mc', new Chart(ctx, {
        type: 'bar',
        data: {
            labels: mc.bins.map(b => sym + app.fmt(b, 0)),
            datasets: [{
                label: 'Frequency',
                data: mc.frequencies,
                backgroundColor: mc.bins.map(b => b >= currentPrice ? 'rgba(16,185,129,0.7)' : 'rgba(239,68,68,0.7)'),
                borderWidth: 0,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#6b7280', maxTicksLimit: 10 } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#6b7280' } }
            }
        }
    }));
}

function renderHeatmap(containerId, data, currentPrice, sym) {
    const el = document.getElementById(containerId);
    if (!el || !data) return;
    const matrix   = data.matrix || [];
    const rowLabels = data.row_labels || [];
    const colLabels = data.col_labels || [];
    let html = '<table class="data-table"><thead><tr><th>WACC</th>';
    colLabels.forEach(c => html += `<th>${typeof c === 'number' ? (c * 100).toFixed(1) + '%' : c}</th>`);
    html += '</tr></thead><tbody>';
    matrix.forEach((row, i) => {
        const rowLabel = rowLabels[i];
        html += `<tr><td><strong>${typeof rowLabel === 'number' ? (rowLabel * 100).toFixed(1) + '%' : rowLabel}</strong></td>`;
        row.forEach(v => {
            const color = v >= currentPrice ? '#10b981' : '#ef4444';
            html += `<td style="color:${color}">${sym}${app.fmt(v)}</td>`;
        });
        html += '</tr>';
    });
    el.innerHTML = html + '</tbody></table>';
}

function renderTornado(data) {
    const ctx = document.getElementById('tornadoChart')?.getContext('2d');
    if (!ctx || !data.length) return;
    app.destroyChart('tornado');
    const sorted = [...data].sort((a, b) => b.impact - a.impact);
    app.saveChart('tornado', new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sorted.map(d => d.driver_name.replace(/_/g, ' ')),
            datasets: [
                { label: 'Low Case',  data: sorted.map(d => d.low_price),  backgroundColor: 'rgba(239,68,68,0.7)' },
                { label: 'High Case', data: sorted.map(d => d.high_price), backgroundColor: 'rgba(16,185,129,0.7)' },
            ]
        },
        options: {
            indexAxis: 'y', responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                y: { grid: { display: false }, ticks: { color: '#9ca3af' } },
            }
        }
    }));
}

function renderScenarios(scenarios, sym, price) {
    const tbody = document.querySelector('#scenariosTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    scenarios.forEach(s => {
        const upside = price > 0 ? ((s.implied_price / price) - 1) * 100 : 0;
        const cl = upside >= 0 ? 'text-green' : 'text-red';
        const tr = document.createElement('tr');
        const scenColor = s.scenario_name === 'Bull' ? '#10b981' : (s.scenario_name === 'Bear' ? '#ef4444' : '#f0b429');
        tr.innerHTML = `
            <td><span style="color:${scenColor};font-weight:600">${s.scenario_name}</span></td>
            <td>${sym}${app.fmt(s.implied_price)}</td>
            <td class="${cl}">${upside >= 0 ? '+' : ''}${upside.toFixed(1)}%</td>
            <td style="font-size:.85rem;color:#6b7280;">${Object.entries(s.assumptions || {}).map(([k,v]) => `${k.replace(/_/g,' ')}: ${(v*100).toFixed(1)}%`).join(' | ')}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderWeightedScenarios(scenarios, sym) {
    const tbody = document.querySelector('#weightedScenariosTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    scenarios.forEach(s => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${s.scenario_name}</td>
            <td>${sym}${app.fmt(s.implied_price)}</td>
            <td>
                <input type="range" min="0" max="100" step="1" value="${Math.round((s.probability || 0) * 100)}"
                    style="width:100px;vertical-align:middle;" disabled>
                <span style="margin-left:.5rem">${Math.round((s.probability || 0) * 100)}%</span>
            </td>
            <td>${sym}${app.fmt((s.implied_price || 0) * (s.probability || 0))}</td>
        `;
        tbody.appendChild(tr);
    });
}

function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val ?? '–'; }
function setUpsideEl(id, upside) {
    const el = document.getElementById(id);
    if (!el || upside == null) return;
    el.textContent = (upside >= 0 ? '+' : '') + upside.toFixed(1) + '%';
    el.className = upside >= 0 ? 'stat-value text-green' : 'stat-value text-red';
}
