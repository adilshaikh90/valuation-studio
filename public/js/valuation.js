/* valuation.js - tabs: DCF FCFF, DCF FCFE, DDM, APV */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected. <a href="dashboard.html">Go back</a></p>'; return; }

    document.querySelectorAll('.currentTickerDisplay').forEach(el => el.textContent = ticker);

    setupTabs();
    await loadValuation(ticker);
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
    // Show first tab
    const firstTab = document.querySelector('.tab-btn');
    if (firstTab) firstTab.click();
}

async function loadValuation(ticker) {
    app.showLoading();
    try {
        const [fcffRes, fcfeRes, ddmRes, apvRes] = await Promise.allSettled([
            api.getDcfFcff(ticker),
            api.getDcfFcfe(ticker),
            api.getDdm(ticker),
            api.getApv(ticker),
        ]);

        const company = await api.getCompany(ticker);
        const sym = company.currency_symbol || '$';
        const price = company.current_price || 0;

        // ── DCF FCFF ────────────────────────────────────────
        if (fcffRes.status === 'fulfilled') {
            const d = fcffRes.value;
            setText('fcffValue',   sym + app.fmt(d.intrinsic_value_per_share));
            setText('fcffCurrentPrice', sym + app.fmt(price));
            const upside = price > 0 ? ((d.intrinsic_value_per_share / price) - 1) * 100 : 0;
            setUpsideEl('fcffUpside', upside);
            setText('fcffEV',      app.fmtLarge(d.enterprise_value));
            setText('fcffEqV',     app.fmtLarge(d.equity_value));
            setText('fcffWACC',    d.wacc_components?.wacc ? app.fmt(d.wacc_components.wacc * 100) + '%' : '–');
            setText('fcffTVpct',   d.tv_as_pct_of_ev ? app.fmt(d.tv_as_pct_of_ev) + '%' : '–');

            if (d.projected_fcf?.length) renderFCFFChart(d, sym);
            if (d.sensitivity_table) renderSensitivityTable(d.sensitivity_table);
        } else {
            setError('fcffSection', fcffRes.reason?.message);
        }

        // ── DCF FCFE ────────────────────────────────────────
        if (fcfeRes.status === 'fulfilled') {
            const d = fcfeRes.value;
            setText('fcfeValue',   sym + app.fmt(d.intrinsic_value_per_share));
            const upside = price > 0 ? ((d.intrinsic_value_per_share / price) - 1) * 100 : 0;
            setUpsideEl('fcfeUpside', upside);
        }

        // ── DDM ─────────────────────────────────────────────
        if (ddmRes.status === 'fulfilled') {
            const d = ddmRes.value;
            if (d.applicable === false) {
                setText('ddmNotice', d.reason || 'DDM not applicable - company does not pay dividends.');
                showEl('ddmNoticeBox');
                hideEl('ddmResults');
            } else {
                hideEl('ddmNoticeBox');
                showEl('ddmResults');
                setText('ddmGordon',   sym + app.fmt(d.gordon_growth_value));
                setText('ddmTwoStage', sym + app.fmt(d.two_stage_value));
                setText('ddmHModel',   sym + app.fmt(d.h_model_value));
                setText('ddmYears',    d.years_of_consecutive_dividends ?? '–');
                setText('ddmPayout',   d.payout_ratio ? app.fmt(d.payout_ratio * 100) + '%' : '–');
                setText('ddmCAGR5',    d['5yr_dividend_cagr'] ? app.fmt(d['5yr_dividend_cagr'] * 100) + '%' : '–');
            }
        }

        // ── APV ─────────────────────────────────────────────
        if (apvRes.status === 'fulfilled') {
            const d = apvRes.value;
            setText('apvValue',         sym + app.fmt(d.intrinsic_value_per_share));
            setText('apvUnleveredFirm', app.fmtLarge(d.unlevered_firm_value));
            setText('apvTaxShield',     app.fmtLarge(d.pv_tax_shield));
            setText('apvEV',            app.fmtLarge(d.enterprise_value));
            const upside = price > 0 ? ((d.intrinsic_value_per_share / price) - 1) * 100 : 0;
            setUpsideEl('apvUpside', upside);
        }

    } catch (err) {
        console.error(err);
        app.showError('Failed to load valuation data: ' + err.message);
    } finally {
        app.hideLoading();
    }
}

function renderFCFFChart(data, sym) {
    const ctx = document.getElementById('fcffChart')?.getContext('2d');
    if (!ctx) return;
    app.destroyChart('fcff');
    const years = data.projected_fcf.map((_, i) => 'Y' + (i + 1));
    app.saveChart('fcff', new Chart(ctx, {
        type: 'bar',
        data: {
            labels: years,
            datasets: [{
                label: 'Projected FCF',
                data: data.projected_fcf,
                backgroundColor: '#f0b429',
                borderRadius: 4,
            }, {
                label: 'PV of FCF',
                data: data.pv_fcf || [],
                backgroundColor: 'rgba(59,130,246,0.6)',
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#9ca3af' } } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#9ca3af' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', callback: v => app.fmtLarge(v) } }
            }
        }
    }));
}

function renderSensitivityTable(table) {
    const el = document.getElementById('sensitivityTable');
    if (!el || !table) return;
    const rows = table.rows || table;
    const colLabels = table.col_labels || [];
    const rowLabels = table.row_labels || [];
    let html = '<table class="data-table"><thead><tr><th>WACC \\ TGR</th>';
    colLabels.forEach(c => html += `<th>${(c * 100).toFixed(1)}%</th>`);
    html += '</tr></thead><tbody>';
    (rows.matrix || rows).forEach((row, i) => {
        html += `<tr><td><strong>${(rowLabels[i] * 100)?.toFixed(1)}%</strong></td>`;
        row.forEach(v => {
            const color = v > 100 ? '#10b981' : (v < 50 ? '#ef4444' : '#f0b429');
            html += `<td style="color:${color}">${app.fmt(v)}</td>`;
        });
        html += '</tr>';
    });
    el.innerHTML = html + '</tbody></table>';
}

function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val ?? '–'; }
function setError(id, msg) { const e = document.getElementById(id); if (e && msg) e.innerHTML += `<p style="color:#ef4444;margin-top:1rem;">⚠️ ${msg}</p>`; }
function showEl(id) { const e = document.getElementById(id); if (e) e.style.display = ''; }
function hideEl(id) { const e = document.getElementById(id); if (e) e.style.display = 'none'; }
function setUpsideEl(id, upside) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = (upside >= 0 ? '+' : '') + upside.toFixed(1) + '%';
    el.className = upside >= 0 ? 'stat-value text-green' : 'stat-value text-red';
}
