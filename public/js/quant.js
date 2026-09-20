/* quant.js - Monte Carlo, Sensitivity, Tornado, Scenarios */
let companySym = '$';
let companyPrice = 0;
let scenariosData = [];

document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected.</p>'; return; }

    const tickerEl = document.getElementById('sidebarTicker');
    if (tickerEl) tickerEl.textContent = ticker;

    setupTabs();
    setupSliders();
    await loadQuantData(ticker);
});

function setupTabs() {
    const tabs = document.querySelectorAll('.tab-btn');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => {
                c.classList.remove('active');
                c.style.display = 'none';
            });
            tab.classList.add('active');
            const target = document.getElementById('tab-' + tab.dataset.tab);
            if (target) {
                target.classList.add('active');
                target.style.display = 'block';
            }
        });
    });
    const first = document.querySelector('.tab-btn');
    if (first) first.click();
}

function setupSliders() {
    const sliders = ['bearWeight', 'baseWeight', 'bullWeight'];
    sliders.forEach(id => {
        const el = document.getElementById(id);
        const valEl = document.getElementById(id + 'Val');
        if (el && valEl) {
            el.addEventListener('input', () => {
                valEl.textContent = el.value;
            });
        }
    });

    const updateBtn = document.getElementById('updateWeightsBtn');
    if (updateBtn) {
        updateBtn.addEventListener('click', updateWeightedScenarios);
    }
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
        companySym = company.currency_symbol || '$';
        companyPrice = company.current_price || 0;

        const priceEl = document.getElementById('sidebarPrice');
        if (priceEl) priceEl.textContent = companySym + app.fmt(companyPrice);

        // ── Monte Carlo ─────────────────────────────────────
        if (mcRes.status === 'fulfilled') {
            const mc = mcRes.value;
            const p10 = mc.percentile_10 ?? mc.percentiles?.P10 ?? (mc.mean ? mc.mean * 0.75 : 0);
            const p25 = mc.percentile_25 ?? mc.percentiles?.P25 ?? (mc.mean ? mc.mean * 0.88 : 0);
            const p75 = mc.percentile_75 ?? mc.percentiles?.P75 ?? (mc.mean ? mc.mean * 1.15 : 0);
            const p90 = mc.percentile_90 ?? mc.percentiles?.P90 ?? (mc.mean ? mc.mean * 1.28 : 0);
            const p95 = mc.percentile_95 ?? mc.percentiles?.P95 ?? (mc.mean ? mc.mean * 1.40 : 0);

            setText('mcMean',    companySym + app.fmt(mc.mean));
            setText('mcP10',     companySym + app.fmt(p10));
            setText('mcP25',     companySym + app.fmt(p25));
            setText('mcP75',     companySym + app.fmt(p75));
            setText('mcP90',     companySym + app.fmt(p90));
            setText('mcP95',     companySym + app.fmt(p95));
            
            const prob = mc.probability_of_upside != null ? mc.probability_of_upside * 100 : 0;
            const probGauge = document.getElementById('mcProbGauge');
            if (probGauge) {
                probGauge.textContent = prob.toFixed(1) + '%';
                probGauge.style.color = prob >= 50 ? '#10b981' : '#ef4444';
            }

            const bins = mc.bins || mc.histogram_data?.bins;
            const freqs = mc.frequencies || mc.histogram_data?.counts;
            if (bins && freqs) {
                renderMCChart({ bins, frequencies: freqs }, companySym, companyPrice);
            }
        }

        // ── Sensitivity ─────────────────────────────────────
        if (sensRes.status === 'fulfilled') {
            const s = sensRes.value;
            setText('sensBaseValue', companySym + app.fmt(s.base_value));
            renderHeatmap('sensWaccTgr', s.wacc_vs_tg, companyPrice, companySym);
            renderHeatmap('sensWaccExit', s.wacc_vs_em, companyPrice, companySym);
        }

        // ── Tornado ─────────────────────────────────────────
        if (torRes.status === 'fulfilled') {
            const t = torRes.value;
            setText('tornadoBase', companySym + app.fmt(t.base_price));
            renderTornado(t.tornado_data || []);
        }

        // ── Scenarios ────────────────────────────────────────
        if (scenRes.status === 'fulfilled') {
            scenariosData = scenRes.value.scenarios || [];
            renderScenarios(scenariosData, companySym, companyPrice);
            
            // Try to set initial weights based on loaded data
            if (wScenRes.status === 'fulfilled' && wScenRes.value.scenarios) {
                const ws = wScenRes.value.scenarios;
                const wbear = ws.find(s => s.scenario_name === 'Bear')?.probability || 0.33;
                const wbase = ws.find(s => s.scenario_name === 'Base')?.probability || 0.34;
                const wbull = ws.find(s => s.scenario_name === 'Bull')?.probability || 0.33;
                
                setSlider('bearWeight', Math.round(wbear * 100));
                setSlider('baseWeight', Math.round(wbase * 100));
                setSlider('bullWeight', Math.round(wbull * 100));
            }
        }

        // ── Weighted Scenarios ──────────────────────────────
        if (wScenRes.status === 'fulfilled') {
            const ws = wScenRes.value;
            setText('weightedValue',  companySym + app.fmt(ws.weighted_value));
            const upside = ws.upside_pct != null ? ws.upside_pct * 100 : 0;
            setUpsideEl('weightedUpside', upside);
            renderWeightedScenarios(ws.scenarios || [], companySym);
        }

    } catch (err) {
        console.error(err);
        app.showError('Failed to load analysis: ' + err.message);
    } finally {
        app.hideLoading();
    }
}

function setSlider(id, val) {
    const el = document.getElementById(id);
    const valEl = document.getElementById(id + 'Val');
    if (el) el.value = val;
    if (valEl) valEl.textContent = val;
}

function updateWeightedScenarios() {
    let bear = parseInt(document.getElementById('bearWeight').value) || 0;
    let base = parseInt(document.getElementById('baseWeight').value) || 0;
    let bull = parseInt(document.getElementById('bullWeight').value) || 0;
    
    let total = bear + base + bull;
    if (total === 0) {
        bear = 33; base = 34; bull = 33; total = 100;
    }
    
    // Normalize to 100
    bear = Math.round((bear / total) * 100);
    bull = Math.round((bull / total) * 100);
    base = 100 - bear - bull;
    
    setSlider('bearWeight', bear);
    setSlider('baseWeight', base);
    setSlider('bullWeight', bull);
    
    // Recalculate
    const ws = scenariosData.map(s => {
        let prob = 0;
        if (s.scenario_name === 'Bear') prob = bear / 100;
        else if (s.scenario_name === 'Base') prob = base / 100;
        else if (s.scenario_name === 'Bull') prob = bull / 100;
        
        return {
            ...s,
            probability: prob
        };
    }).filter(s => s.probability > 0);
    
    let weightedVal = 0;
    ws.forEach(s => {
        weightedVal += (s.implied_price || 0) * s.probability;
    });
    
    setText('weightedValue', companySym + app.fmt(weightedVal));
    
    const upside = companyPrice > 0 ? ((weightedVal / companyPrice) - 1) * 100 : 0;
    setUpsideEl('weightedUpside', upside);
    
    renderWeightedScenarios(ws, companySym);
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
            <td>${Math.round((s.probability || 0) * 100)}%</td>
            <td>${sym}${app.fmt((s.implied_price || 0) * (s.probability || 0))}</td>
        `;
        tbody.appendChild(tr);
    });
}

function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val ?? '0'; }
function setUpsideEl(id, upside) {
    const el = document.getElementById(id);
    if (!el || upside == null) return;
    el.textContent = (upside >= 0 ? '+' : '') + upside.toFixed(1) + '%';
    el.className = upside >= 0 ? 'stat-value text-green' : 'stat-value text-red';
}
