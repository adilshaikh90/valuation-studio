/* dashboard.js — uses api.getCompany() and api.getSummary() */
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
        setText('tickerBadge',   ticker);
        setText('sectorBadge',   company.sector || '');
        setText('currentPrice',  sym + app.fmt(company.current_price));

        const changeEl = document.getElementById('priceChange');
        if (changeEl) {
            const pct = company.price_change_pct || 0;
            changeEl.textContent = (pct >= 0 ? '+' : '') + app.fmt(pct, 2) + '%';
            changeEl.className = pct >= 0 ? 'badge text-green' : 'badge text-red';
        }
        setText('currencyLabel', company.currency || 'USD');

        // ── Key metrics ─────────────────────────────────────
        setText('marketCap',    app.fmtLarge(company.market_cap));
        setText('peRatio',      company.pe_ratio ? app.fmt(company.pe_ratio) + 'x' : 'N/A');
        setText('epsVal',       sym + app.fmt(company.eps));
        setText('betaVal',      company.beta ? app.fmt(company.beta) : 'N/A');
        setText('divYield',     company.dividend_yield ? app.fmt(company.dividend_yield * 100) + '%' : 'N/A');
        setText('fwdPE',        company.forward_pe ? app.fmt(company.forward_pe) + 'x' : 'N/A');
        setText('employees',    company.employees ? Number(company.employees).toLocaleString() : 'N/A');
        setText('country',      company.country || '–');

        // 52-week range bar
        const low52  = company['52_week_low']  || company.week52_low;
        const high52 = company['52_week_high'] || company.week52_high;
        setText('week52Low',  sym + app.fmt(low52));
        setText('week52High', sym + app.fmt(high52));
        if (low52 && high52 && company.current_price) {
            const pct = Math.min(100, Math.max(0, ((company.current_price - low52) / (high52 - low52)) * 100));
            const bar = document.getElementById('week52Bar');
            if (bar) bar.style.width = pct + '%';
        }

        // ── Description ─────────────────────────────────────
        setText('companyDesc', company.description || 'No description available.');

        // ── AI Summary ──────────────────────────────────────
        if (sum) {
            setText('aiSummaryText', sum.summary_text || '');
            renderStrengthsRisks(sum.strengths || [], sum.risks || []);
            setText('aiDisclaimer', sum.disclaimer || '');
        }

        // ── Quick nav links with current ticker ─────────────
        document.querySelectorAll('[data-nav-page]').forEach(link => {
            link.href = link.dataset.navPage + '?ticker=' + ticker;
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
