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
            renderFcffData(d, sym, price);
            setupDcfControls(ticker, sym, price);
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

function renderFcffData(d, sym, price) {
    if (!d) return;
    setText('fcffValue',   sym + app.fmt(d.intrinsic_value_per_share));
    setText('fcffCurrentPrice', sym + app.fmt(price));
    const upside = price > 0 ? ((d.intrinsic_value_per_share / price) - 1) * 100 : 0;
    setUpsideEl('fcffUpside', upside);
    setText('fcffEV',      app.fmtLarge(d.enterprise_value));
    setText('fcffEqV',     app.fmtLarge(d.equity_value));
    setText('fcffWACC',    d.wacc_components?.wacc ? app.fmt(d.wacc_components.wacc * 100) + '%' : '–');
    setText('fcffTVpct',   d.tv_as_pct_of_ev ? app.fmt(d.tv_as_pct_of_ev) + '%' : '–');

    if (d.projected_fcf?.length) renderFCFFChart(d, sym);
    renderEvBridgeChart(d, sym);
    if (d.wacc_components) renderWaccTable(d.wacc_components);
    if (d.sensitivity_table) renderSensitivityTable(d.sensitivity_table);
}

function renderEvBridgeChart(data, sym) {
    const canvas = document.getElementById('evBridgeChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    app.destroyChart('evBridge');

    const ev = Number(data.enterprise_value || 0);
    const bridge = data.bridge || {};
    const debt = Number(bridge.total_debt || 0);
    const cash = Number(bridge.cash || 0);
    const minority = Number(bridge.minority_interest || 0);
    const preferred = Number(bridge.preferred_equity || 0);
    const eqInvest = Number(bridge.equity_investments || 0);
    const otherNet = minority + preferred - eqInvest;
    const eqVal = Number(data.equity_value || (ev - debt + cash - otherNet));

    const labels = ['Enterprise Value', 'Less: Total Debt', 'Plus: Cash'];
    const values = [ev, -debt, cash];
    const colors = ['#38bdf8', '#ef4444', '#10b981'];

    if (Math.abs(otherNet) > 0) {
        labels.push(otherNet > 0 ? 'Less: Other Liab' : 'Plus: Other Assets');
        values.push(-otherNet);
        colors.push('#818cf8');
    }
    labels.push('Equity Value');
    values.push(eqVal);
    colors.push('#f59e0b');

    app.saveChart('evBridge', new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderRadius: 4,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (c) => {
                            const val = c.raw;
                            const sign = val < 0 ? '-' : '';
                            return `${c.label}: ${sign}${sym}${app.fmtLarge(Math.abs(val))}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#9ca3af', font: { size: 10 } }
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: {
                        color: '#9ca3af',
                        callback: (v) => app.fmtLarge(v)
                    }
                }
            }
        }
    }));
}

function renderWaccTable(wacc) {
    const table = document.getElementById('waccTable');
    if (!table || !wacc) return;

    const rf = wacc.risk_free_rate != null ? (wacc.risk_free_rate * 100).toFixed(2) + '%' : '–';
    const beta = wacc.beta_used != null ? Number(wacc.beta_used).toFixed(2) : (wacc.beta_raw != null ? Number(wacc.beta_raw).toFixed(2) : '1.00');
    const erp = wacc.equity_risk_premium != null ? (wacc.equity_risk_premium * 100).toFixed(2) + '%' : '5.50%';
    const ke = wacc.cost_of_equity != null ? (wacc.cost_of_equity * 100).toFixed(2) + '%' : '–';
    const kd = wacc.cost_of_debt != null ? (wacc.cost_of_debt * 100).toFixed(2) + '%' : '–';
    const tax = wacc.tax_rate != null ? (wacc.tax_rate * 100).toFixed(1) + '%' : '–';
    const afterTaxKd = (wacc.cost_of_debt != null && wacc.tax_rate != null) 
        ? (wacc.cost_of_debt * (1 - wacc.tax_rate) * 100).toFixed(2) + '%' 
        : '–';
    const we = wacc.weight_equity != null ? (wacc.weight_equity * 100).toFixed(1) + '%' : '–';
    const wd = wacc.weight_debt != null ? (wacc.weight_debt * 100).toFixed(1) + '%' : '–';
    const finalWacc = wacc.wacc != null ? (wacc.wacc * 100).toFixed(2) + '%' : '–';

    table.innerHTML = `
        <thead>
            <tr>
                <th style="text-align:left;">Component</th>
                <th style="text-align:right;">Value / Weight</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>Risk-Free Rate (Rf – 10Y Treasury)</td><td style="text-align:right; font-family:var(--font-mono);">${rf}</td></tr>
            <tr><td>Beta (Levered)</td><td style="text-align:right; font-family:var(--font-mono);">${beta}</td></tr>
            <tr><td>Equity Risk Premium (ERP)</td><td style="text-align:right; font-family:var(--font-mono);">${erp}</td></tr>
            <tr><td>Cost of Equity (CAPM Ke)</td><td style="text-align:right; font-family:var(--font-mono); color:#10b981; font-weight:600;">${ke}</td></tr>
            <tr><td>Pre-Tax Cost of Debt (Kd)</td><td style="text-align:right; font-family:var(--font-mono);">${kd}</td></tr>
            <tr><td>Effective Tax Rate (t)</td><td style="text-align:right; font-family:var(--font-mono);">${tax}</td></tr>
            <tr><td>After-Tax Cost of Debt [Kd*(1-t)]</td><td style="text-align:right; font-family:var(--font-mono);">${afterTaxKd}</td></tr>
            <tr><td>Weight of Equity (We = E / V)</td><td style="text-align:right; font-family:var(--font-mono);">${we}</td></tr>
            <tr><td>Weight of Debt (Wd = D / V)</td><td style="text-align:right; font-family:var(--font-mono);">${wd}</td></tr>
            <tr style="background:rgba(245, 158, 11, 0.1); border-top:2px solid rgba(245, 158, 11, 0.3);">
                <td><strong style="color:#f59e0b;">Weighted Average Cost of Capital (WACC)</strong></td>
                <td style="text-align:right; font-family:var(--font-mono); font-weight:700; color:#f59e0b; font-size:1.05rem;">${finalWacc}</td>
            </tr>
        </tbody>
    `;
}

let dcfControlsBound = false;
function setupDcfControls(ticker, sym, price) {
    if (dcfControlsBound) return;
    dcfControlsBound = true;

    const tgrSlider = document.getElementById('tgrSlider');
    const tgrInput = document.getElementById('tgrInput');
    const recalcBtn = document.getElementById('recalcFcff');

    if (tgrSlider && tgrInput) {
        tgrSlider.addEventListener('input', () => {
            tgrInput.value = tgrSlider.value;
        });
        tgrInput.addEventListener('input', () => {
            tgrSlider.value = tgrInput.value;
        });
    }

    if (recalcBtn) {
        recalcBtn.addEventListener('click', async () => {
            recalcBtn.disabled = true;
            const origText = recalcBtn.textContent;
            recalcBtn.textContent = 'Calculating...';
            try {
                const params = {
                    terminal_growth: (parseFloat(tgrInput?.value || 2.5) / 100).toString(),
                    projection_years: (document.getElementById('projYears')?.value || 5).toString(),
                    mid_year_convention: (document.getElementById('midYearCheck')?.checked ?? true).toString(),
                    sbc_as_cost: (document.getElementById('sbcCheck')?.checked ?? true).toString(),
                };
                const waccOverride = document.getElementById('waccOverride')?.value;
                if (waccOverride) {
                    params.wacc_override = (parseFloat(waccOverride) / 100).toString();
                }
                const exitMultiple = document.getElementById('exitMultiple')?.value;
                if (exitMultiple) {
                    params.exit_multiple = parseFloat(exitMultiple).toString();
                }

                const updated = await api.getDcfFcff(ticker, params);
                renderFcffData(updated, sym, price);
            } catch (err) {
                app.showError('Recalculation error: ' + err.message);
            } finally {
                recalcBtn.disabled = false;
                recalcBtn.textContent = origText;
            }
        });
    }
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
