/* lbo-nav.js - LBO analysis and NAV calculation */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected.</p>'; return; }

    document.querySelectorAll('.currentTickerDisplay').forEach(el => el.textContent = ticker);

    setupSliders();

    const calcBtn = document.getElementById('calcLboBtn');
    if (calcBtn) calcBtn.addEventListener('click', () => loadLboNav(ticker));

    await loadLboNav(ticker);
});

function setupSliders() {
    [['leverage', 'leverageVal', v => parseFloat(v).toFixed(1) + 'x'],
     ['targetIrr', 'targetIrrVal', v => v + '%'],
     ['holdPeriod', 'holdPeriodVal', v => v + ' yrs'],
    ].forEach(([sliderId, valId, fmt]) => {
        const slider = document.getElementById(sliderId);
        const valEl  = document.getElementById(valId);
        if (slider && valEl) {
            valEl.textContent = fmt(slider.value);
            slider.addEventListener('input', () => { valEl.textContent = fmt(slider.value); });
        }
    });
}

async function loadLboNav(ticker) {
    app.showLoading();
    try {
        const leverage   = parseFloat(document.getElementById('leverage')?.value || '5');
        const targetIrr  = parseFloat(document.getElementById('targetIrr')?.value || '20') / 100;
        const holdPeriod = parseInt(document.getElementById('holdPeriod')?.value || '5', 10);

        const [lboRes, navRes, companyRes] = await Promise.all([
            api.getLbo(ticker, { leverage, target_irr: targetIrr, hold_period: holdPeriod }),
            api.getNav(ticker),
            api.getCompany(ticker),
        ]);

        const sym   = companyRes.currency_symbol || '$';
        const price = companyRes.current_price || 0;

        // ── LBO Results ──────────────────────────────────────
        setText('lboMoic',       lboRes.moic != null ? app.fmt(lboRes.moic) + 'x' : '–');
        setText('lboIrr',        lboRes.irr  != null ? (lboRes.irr * 100).toFixed(1) + '%' : '–');
        setText('lboFloorPrice', lboRes.lbo_floor_price ? sym + app.fmt(lboRes.lbo_floor_price) : '–');
        setText('lboEntryEV',    lboRes.entry_ev ? sym + app.fmtLarge(lboRes.entry_ev) : '–');
        setText('lboDebt',       lboRes.debt ? sym + app.fmtLarge(lboRes.debt) : '–');
        setText('lboEntryEq',    lboRes.entry_equity ? sym + app.fmtLarge(lboRes.entry_equity) : '–');
        setText('lboExitEV',     lboRes.exit_ev ? sym + app.fmtLarge(lboRes.exit_ev) : '–');

        // Color MOIC/IRR
        const irrGood = lboRes.irr >= targetIrr;
        colorEl('lboIrr',  irrGood ? 1 : -1);
        colorEl('lboMoic', (lboRes.moic || 0) >= 2.0 ? 1 : -1);

        // Debt schedule table
        if (lboRes.debt_schedule?.length) renderDebtSchedule(lboRes.debt_schedule, sym);

        // ── NAV Results ─────────────────────────────────────
        setText('navAssets',        sym + app.fmtLarge(navRes.nav || 0));
        setText('navLiab',          '–');
        setText('navPerShare',      sym + app.fmt(navRes.nav_per_share));
        setText('tangibleNavPerShare', sym + app.fmt(navRes.tangible_nav_per_share));
        setText('navPriceRatio',    navRes.price_nav_ratio ? app.fmt(navRes.price_nav_ratio) + 'x' : '–');
        setText('tangNavPriceRatio',navRes.price_tangible_nav_ratio ? app.fmt(navRes.price_tangible_nav_ratio) + 'x' : '–');

        renderNavChart(navRes, price, sym);

    } catch (err) {
        console.error(err);
        app.showError('Failed to load analysis: ' + err.message);
    } finally {
        app.hideLoading();
    }
}

function renderDebtSchedule(schedule, sym) {
    const tbody = document.querySelector('#debtTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    schedule.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.year || '–'}</td>
            <td>${row.beg_debt != null ? sym + app.fmtLarge(row.beg_debt) : '–'}</td>
            <td>${row.interest != null ? sym + app.fmtLarge(row.interest) : '–'}</td>
            <td>${row.fcf != null ? sym + app.fmtLarge(row.fcf) : '–'}</td>
            <td>${row.paydown != null ? sym + app.fmtLarge(row.paydown) : '–'}</td>
            <td>${row.end_debt != null ? sym + app.fmtLarge(row.end_debt) : '–'}</td>
        `;
        tbody.appendChild(tr);
    });
}

function renderNavChart(nav, price, sym) {
    const ctx = document.getElementById('navChart')?.getContext('2d');
    if (!ctx) return;
    app.destroyChart('nav');
    app.saveChart('nav', new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Current Price', 'NAV / Share', 'Tangible NAV'],
            datasets: [{
                label: 'Value per Share',
                data: [price, nav.nav_per_share, nav.tangible_nav_per_share],
                backgroundColor: ['#f0b429', '#3b82f6', '#10b981'],
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#9ca3af' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', callback: v => sym + app.fmt(v) } }
            }
        }
    }));
}

function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val ?? '–'; }
function colorEl(id, sign) {
    const e = document.getElementById(id);
    if (e) e.style.color = sign >= 0 ? '#10b981' : '#ef4444';
}
function app_fmtLarge(n) { return app.fmtLarge(n); }
