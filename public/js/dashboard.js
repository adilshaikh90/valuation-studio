/* dashboard.js - uses api.getCompany() and api.getSummary() */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { showNoTicker(); return; }

    document.querySelectorAll('.currentTickerDisplay').forEach(el => el.textContent = ticker);

    // Wire nav search
    const searchBtn = document.getElementById('navSearchBtn');
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            const v = document.getElementById('navTickerInput')?.value.trim().toUpperCase();
            if (v) { app.setTicker(v); window.location.reload(); }
        });
    }

    await loadDashboard(ticker);
});

function showNoTicker() {
    const hero = document.getElementById('dashboardHero');
    if (hero) hero.innerHTML = `
        <div style="text-align:center;padding:4rem;">
            <h2 style="color:var(--accent-gold)">No company selected</h2>
            <p style="color:var(--text-secondary);margin-top:1rem;">Enter a ticker symbol to get started.</p>
        </div>`;
}

async function loadDashboard(ticker) {
    app.showLoading();
    try {
        // Fetch company info and summary in parallel
        const [info, summary] = await Promise.allSettled([
            api.getCompany(ticker),
            api.getSummary(ticker),
        ]);

        const company = info.status === 'fulfilled' ? info.value : null;
        const sum     = summary.status === 'fulfilled' ? summary.value : null;

        if (!company) {
            setText('companyName', `Symbol "${ticker}" Not Found`);
            setText('companyDesc', `Could not find active market data for ticker "${ticker}". Please verify the symbol (e.g. AAPL, MSFT, NVDA, TSLA, ASML).`);
            app.showError(`Could not load data for "${ticker}". Check the ticker symbol.`);
            app.hideLoading();
            return;
        }


        const sym = company.currency_symbol || '$';

        // ── Header ─────────────────────────────────────────
        setText('companyName',   company.name || ticker);
        setText('tickerBadge',   `[${ticker}]`);
        setText('sectorBadge',   company.sector ? `[${company.sector.toUpperCase()}]` : '[SECTOR: N/A]');
        
        const countryDisplay = (company.country && company.country !== 'Global') ? company.country.toUpperCase() : 'UNITED STATES';
        setText('countryBadge',  `[${countryDisplay}]`);
        
        // Currency badge formatting
        let currDisplay = company.currency || 'USD';
        if (currDisplay.toUpperCase() === 'GBX' || ticker.endsWith('.L')) {
            currDisplay = 'GBX (PENCE)';
        }
        setText('currencyLabel', `[${currDisplay}]`);

        setText('currentPrice',  sym + app.fmt(company.current_price));

        const changeEl = document.getElementById('priceChange');
        if (changeEl) {
            const pct = company.price_change_pct || 0;
            changeEl.textContent = (pct >= 0 ? '+' : '') + app.fmt(pct, 2) + '%';
            changeEl.className = pct >= 0 ? 'price-change text-green' : 'price-change text-red';
            changeEl.style.cssText = pct >= 0 
                ? 'background: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3);' 
                : 'background: rgba(239, 68, 68, 0.12); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3);';
        }

        // Action buttons
        const btnFin = document.getElementById('btnLaunchFinancials');
        if (btnFin) btnFin.href = `financials.html?ticker=${encodeURIComponent(ticker)}`;
        const btnExp = document.getElementById('btnExportModel');
        if (btnExp) btnExp.href = `download.html?ticker=${encodeURIComponent(ticker)}`;

        // ── Key metrics ─────────────────────────────────────
        setText('marketCap',    app.fmtLarge(company.market_cap));
        setText('peRatio',      (company.pe_ratio != null && !isNaN(company.pe_ratio)) ? app.fmt(company.pe_ratio, 2) + 'x' : 'N/A');
        setText('epsVal',       (company.eps != null && !isNaN(company.eps)) ? sym + app.fmt(company.eps, 2) : 'N/A');
        setText('betaVal',      (company.beta != null && !isNaN(company.beta)) ? app.fmt(company.beta, 2) : 'N/A');

        let divDisplay = 'N/A';
        if (company.dividend_yield != null && !isNaN(company.dividend_yield)) {
            const rawYield = Number(company.dividend_yield);
            const yPct = rawYield > 0.15 ? rawYield : rawYield * 100;
            divDisplay = app.fmt(yPct, 2) + '%';
        }
        setText('divYield',     divDisplay);

        setText('fwdPE',        (company.forward_pe != null && !isNaN(company.forward_pe)) ? app.fmt(company.forward_pe, 2) + 'x' : 'N/A');
        setText('employees',    (company.employees != null && !isNaN(company.employees) && company.employees > 0) ? Number(company.employees).toLocaleString() : 'N/A');
        setText('country',      (company.country && company.country !== 'Global') ? company.country : (company.country || '–'));

        // 52-week range bar
        const low52  = company['52_week_low']  || company.week52_low;
        const high52 = company['52_week_high'] || company.week52_high;
        setText('week52Low',  sym + app.fmt(low52));
        setText('week52High', sym + app.fmt(high52));
        if (low52 && high52 && company.current_price) {
            const pct = Math.min(100, Math.max(0, ((company.current_price - low52) / (high52 - low52)) * 100));
            const bar = document.getElementById('week52Bar');
            if (bar) bar.style.width = pct + '%';
            setText('rangeSpreadPct', `${app.fmt(pct, 1)}% OF 52W RANGE`);
        }

        // ── Description & Website ───────────────────────────
        setText('companyDesc', company.description || 'No business description available.');
        const webEl = document.getElementById('companyWebsiteLink');
        if (webEl && company.website) {
            webEl.innerHTML = `<a href="${company.website}" target="_blank" rel="noopener" style="font-family:var(--font-mono); font-size:0.75rem; color:var(--gold); text-decoration:none; display:inline-flex; align-items:center; gap:4px; border:1px solid rgba(245,158,11,0.3); padding:3px 10px; border-radius:9999px; background:rgba(245,158,11,0.06);">WEBSITE ↗</a>`;
        }

        // ── AI Summary ──────────────────────────────────────
        if (sum) {
            setText('aiSummaryText', sum.summary_text || '');
            renderStrengthsRisks(sum.strengths || [], sum.risks || []);
            setText('aiDisclaimer', sum.disclaimer || '');
        }

        // ── Quick nav links with current ticker ─────────────
        document.querySelectorAll('[data-nav-page]').forEach(link => {
            link.href = link.dataset.navPage + '?ticker=' + encodeURIComponent(ticker);
        });

    } catch (err) {
        console.error(err);
        app.showError('Failed to load dashboard: ' + err.message);
    } finally {
        app.hideLoading();
    }
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value ?? '–';
}

function renderStrengthsRisks(strengths, risks) {
    const sEl = document.getElementById('strengthsList');
    const rEl = document.getElementById('risksList');
    if (sEl) {
        if (strengths.length) {
            sEl.innerHTML = strengths.map(s => `<li class="sr-item sr-item-green">${s}</li>`).join('');
        } else {
            sEl.innerHTML = '<li class="sr-item sr-empty">No specific strengths identified.</li>';
        }
    }
    if (rEl) {
        if (risks.length) {
            rEl.innerHTML = risks.map(r => `<li class="sr-item sr-item-red">${r}</li>`).join('');
        } else {
            rEl.innerHTML = '<li class="sr-item sr-empty">No elevated risks identified.</li>';
        }
    }
}
