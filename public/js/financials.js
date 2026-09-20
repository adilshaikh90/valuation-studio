/**
 * Valuation Studio - 3-Statement Financial Model
 * Institutional Income Statement, Balance Sheet, Cash Flow, and Key Ratios.
 */

document.addEventListener('DOMContentLoaded', async () => {
  if (!app.isAuthenticated()) {
    window.location.href = 'login.html';
    return;
  }

  const ticker = app.getTicker();
  if (!ticker) {
    showNoTickerState();
    return;
  }

  // Update sidebar ticker display
  document.querySelectorAll('#sidebarTicker').forEach(el => el.textContent = ticker);

  // Nav search bar
  const navSearchBtn = document.getElementById('navSearchBtn');
  if (navSearchBtn) {
    navSearchBtn.addEventListener('click', () => {
      const v = document.getElementById('navTickerInput')?.value.trim().toUpperCase();
      if (v) {
        app.setTicker(v);
        window.location.reload();
      }
    });
  }
  const navTickerInput = document.getElementById('navTickerInput');
  if (navTickerInput) {
    navTickerInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') navSearchBtn && navSearchBtn.click();
    });
  }

  // Set up tabs
  initTabSwitching();

  // Set up live search filter
  initLineItemFilter();

  // Load statements
  await loadFinancialStatements(ticker);
});

function showNoTickerState() {
  const container = document.querySelector('.main-content');
  if (container) {
    container.innerHTML = `
      <div style="text-align:center; padding: 5rem 1rem;">
        <h2 style="color:#f59e0b; font-size: 1.75rem; margin-bottom: 1rem;">No Company Selected</h2>
        <p style="color:#94a3b8; margin-bottom: 2rem;">Please enter a ticker symbol in the search bar above to view 3-statement financials.</p>
        <a href="dashboard.html" class="btn btn-primary" style="display:inline-flex; align-items:center; gap:0.5rem;">
          Return to Dashboard
        </a>
      </div>`;
  }
}

function initTabSwitching() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));

      btn.classList.add('active');
      const tabKey = btn.getAttribute('data-tab');
      const target = document.getElementById(`tab-${tabKey}`);
      if (target) {
        target.classList.add('active');
      }

      // Re-trigger live search filter on active tab
      const searchInput = document.getElementById('finSearchInput');
      if (searchInput && searchInput.value) {
        applyFilter(searchInput.value.toLowerCase());
      }
    });
  });
}

function initLineItemFilter() {
  const input = document.getElementById('finSearchInput');
  if (!input) return;

  input.addEventListener('input', (e) => {
    applyFilter(e.target.value.trim().toLowerCase());
  });
}

function applyFilter(query) {
  const activeTabContent = document.querySelector('.tab-content.active');
  if (!activeTabContent) return;

  const rows = activeTabContent.querySelectorAll('tbody tr');
  rows.forEach(row => {
    if (!query) {
      row.style.display = '';
      return;
    }

    if (row.classList.contains('fin-section-row')) {
      // Keep section row visible if any upcoming rows match
      row.style.display = '';
    } else {
      const text = row.querySelector('td:first-child')?.textContent.toLowerCase() || '';
      row.style.display = text.includes(query) ? '' : 'none';
    }
  });
}

// ── Financial Data Loading & Processing ─────────────────────────────────────
async function loadFinancialStatements(ticker) {
  const loadingEl = document.getElementById('finLoading');
  const tabsEl = document.querySelector('.tabs');
  if (loadingEl) loadingEl.style.display = 'block';

  try {
    const [finRes, compRes] = await Promise.allSettled([
      api.getFinancials(ticker),
      api.getCompany(ticker)
    ]);

    const financials = finRes.status === 'fulfilled' ? finRes.value : null;
    const company = compRes.status === 'fulfilled' ? compRes.value : {};

    if (loadingEl) loadingEl.style.display = 'none';

    if (!financials || financials.error) {
      showErrorState(financials?.error || 'Unable to retrieve financial statement data from exchange.');
      return;
    }

    const curr = company.currency || 'USD';
    const sym = company.currency_symbol || (curr === 'GBP' ? '£' : '$');

    // Update Header Badges
    const subtitle = document.getElementById('finSubtitle');
    if (subtitle) {
      subtitle.textContent = `${company.name || ticker} [${ticker}] - 5-Year Consolidated Statements (${curr})`;
    }

    const tagText = `All figures in Millions ${curr} (${sym}M), except per-share data`;
    ['isCurrencyTag', 'bsCurrencyTag', 'cfCurrencyTag'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.textContent = tagText;
    });

    // Extract records & dates chronologically (oldest to newest)
    const isRecords = (financials.income_statement || []).slice().reverse();
    const bsRecords = (financials.balance_sheet || []).slice().reverse();
    const cfRecords = (financials.cash_flow || []).slice().reverse();

    // Map column headers
    const dates = isRecords.map(r => r.date).filter(Boolean);
    const colYears = dates.map(d => {
      const yr = new Date(d).getFullYear();
      return isNaN(yr) ? d : `FY ${yr}`;
    });

    // Render each statement
    renderIncomeStatement(isRecords, colYears, sym);
    renderBalanceSheet(bsRecords, colYears, sym);
    renderCashFlow(cfRecords, colYears, sym);
    renderKeyRatios(isRecords, bsRecords, cfRecords, colYears, sym);

  } catch (err) {
    if (loadingEl) loadingEl.style.display = 'none';
    showErrorState(err.message || 'Error occurred while processing statements.');
  }
}

function showErrorState(msg) {
  const container = document.querySelector('.main-content');
  if (container) {
    const errDiv = document.createElement('div');
    errDiv.style.cssText = 'background: rgba(239, 68, 68, 0.1); border: 1px solid #ef4444; border-radius: 8px; padding: 2rem; text-align: center; margin: 2rem 0;';
    errDiv.innerHTML = `
      <h3 style="color:#ef4444; margin-bottom: 0.5rem;">Failed to Load Financial Statements</h3>
      <p style="color:#cbd5e1;">${msg}</p>
    `;
    container.insertBefore(errDiv, container.firstChild);
  }
}

// ── Helpers ─────────────────────────────────────────────────────────────────
function getVal(row, keys, def = 0) {
  if (!row) return def;
  for (const k of keys) {
    if (row[k] !== undefined && row[k] !== null && !isNaN(row[k])) {
      return Number(row[k]);
    }
  }
  return def;
}

function fmtM(val, decimals = 1, showDash = true) {
  if (val === null || val === undefined || isNaN(val)) return showDash ? '-' : '0.0';
  if (val === 0 && showDash) return '-';
  const m = val / 1e6;
  const isNeg = m < 0;
  const str = Math.abs(m).toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
  return isNeg ? `(${str})` : str;
}

function fmtEPS(val, sym = '$') {
  if (val === null || val === undefined || isNaN(val) || val === 0) return '-';
  const isNeg = val < 0;
  const str = Math.abs(val).toFixed(2);
  return isNeg ? `(${sym}${str})` : `${sym}${str}`;
}

function fmtPct(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val) || !isFinite(val)) return '-';
  const isNeg = val < 0;
  const pct = (val * 100).toFixed(decimals);
  const cls = isNeg ? 'text-red' : (val > 0 ? 'text-green' : '');
  return `<span class="${cls}">${val > 0 ? '+' : ''}${pct}%</span>`;
}

function fmtMargin(val, decimals = 1) {
  if (val === null || val === undefined || isNaN(val) || !isFinite(val)) return '-';
  return (val * 100).toFixed(decimals) + '%';
}

function fmtMult(val, decimals = 2) {
  if (val === null || val === undefined || isNaN(val) || !isFinite(val)) return '-';
  return val.toFixed(decimals) + 'x';
}

function calcYoY(curr, prev) {
  if (!prev || prev === 0 || !curr) return null;
  return (curr - prev) / Math.abs(prev);
}

function calcCagr(first, last, nYears) {
  if (!first || first <= 0 || !last || last <= 0 || nYears <= 0) return null;
  return Math.pow(last / first, 1 / nYears) - 1;
}

// ── Table Builders ──────────────────────────────────────────────────────────
function buildTableHeader(tableId, colYears, extraCol = 'CAGR / YoY') {
  const table = document.getElementById(tableId);
  if (!table) return;

  const thead = table.querySelector('thead');
  let ths = colYears.map(yr => `<th>${yr}</th>`).join('');
  if (extraCol) {
    ths += `<th style="color:#f59e0b;">${extraCol}</th>`;
  }
  thead.innerHTML = `<tr><th>Line Item</th>${ths}</tr>`;
}

function rowHTML(label, vals, opts = {}) {
  const { indent = 0, bold = false, isSubtotal = false, isTotal = false, isSection = false, extraVal = '' } = opts;

  if (isSection) {
    return `<tr class="fin-section-row"><td colspan="10">${label}</td></tr>`;
  }

  let trClass = '';
  if (isTotal) trClass = 'fin-total-row';
  else if (isSubtotal) trClass = 'fin-subtotal-row';

  let tdClass = '';
  if (indent === 1) tdClass = 'indent-1';
  else if (indent === 2) tdClass = 'indent-2';

  const cells = vals.map(v => `<td>${v}</td>`).join('');
  const extraCell = extraVal !== undefined ? `<td>${extraVal}</td>` : '';

  return `<tr class="${trClass}"><td class="${tdClass}">${label}</td>${cells}${extraCell}</tr>`;
}

// ── 1. Income Statement ─────────────────────────────────────────────────────
function renderIncomeStatement(records, colYears, sym) {
  buildTableHeader('isTable', colYears, 'YoY Growth');
  const tbody = document.querySelector('#isTable tbody');
  if (!tbody || !records.length) return;

  let html = '';

  // Data series extraction
  const rev = records.map(r => getVal(r, ['Total Revenue', 'Operating Revenue']));
  const cogs = records.map(r => getVal(r, ['Cost Of Revenue', 'Reconciled Cost Of Revenue', 'Net Policyholder Benefits And Claims']));
  const gp = records.map((r, i) => {
    const rawGp = getVal(r, ['Gross Profit']);
    return rawGp !== 0 ? rawGp : (rev[i] - cogs[i]);
  });
  const rd = records.map(r => getVal(r, ['Research And Development']));
  const sga = records.map(r => getVal(r, ['Selling General And Administration', 'General And Administrative Expense']));
  const otherOpex = records.map(r => getVal(r, ['Other Operating Expenses']));
  const totalOpex = records.map(r => getVal(r, ['Operating Expense', 'Total Expenses']));
  const ebit = records.map(r => getVal(r, ['Operating Income', 'EBIT']));
  const da = records.map(r => getVal(r, ['Depreciation And Amortization', 'Reconciled Depreciation', 'Depreciation Amortization Depletion']));
  const ebitda = records.map((r, i) => {
    const raw = getVal(r, ['EBITDA', 'Normalized EBITDA']);
    return raw !== 0 ? raw : (ebit[i] + da[i]);
  });
  const intExp = records.map(r => getVal(r, ['Interest Expense', 'Net Interest Income']));
  const nonOp = records.map(r => getVal(r, ['Other Income Expense', 'Special Income Charges', 'Other Non Operating Income Expenses']));
  const ebt = records.map(r => getVal(r, ['Pretax Income']));
  const tax = records.map(r => getVal(r, ['Tax Provision']));
  const ni = records.map(r => getVal(r, ['Net Income Common Stockholders', 'Net Income', 'Net Income Continuous Operations']));
  const eps = records.map(r => getVal(r, ['Diluted EPS', 'Basic EPS']));
  const shares = records.map(r => getVal(r, ['Diluted Average Shares', 'Basic Average Shares']));

  const n = records.length;
  const lastIdx = n - 1;
  const prevIdx = Math.max(0, n - 2);

  // 1. REVENUE & GROSS PROFIT
  html += rowHTML('REVENUE &amp; GROSS PROFIT', [], { isSection: true });
  html += rowHTML('Total Revenue', rev.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(rev[lastIdx], rev[prevIdx]))
  });
  html += rowHTML('YoY Revenue Growth', rev.map((v, i) => i === 0 ? '-' : fmtPct(calcYoY(v, rev[i - 1]))), {
    indent: 1
  });
  html += rowHTML('Cost of Goods Sold / Policy Claims', cogs.map(v => fmtM(-Math.abs(v))), {
    indent: 1,
    extraVal: fmtPct(calcYoY(cogs[lastIdx], cogs[prevIdx]))
  });
  html += rowHTML('Gross Profit', gp.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(gp[lastIdx], gp[prevIdx]))
  });
  html += rowHTML('Gross Margin %', gp.map((v, i) => rev[i] ? fmtMargin(v / rev[i]) : '-'), {
    indent: 1
  });

  // 2. OPERATING EXPENSES
  html += rowHTML('OPERATING EXPENSES', [], { isSection: true });
  if (rd.some(v => v > 0)) {
    html += rowHTML('Research &amp; Development (R&amp;D)', rd.map(v => fmtM(-Math.abs(v))), { indent: 1 });
  }
  html += rowHTML('Selling, General &amp; Administrative (SG&amp;A)', sga.map(v => fmtM(-Math.abs(v))), { indent: 1 });
  if (otherOpex.some(v => v > 0)) {
    html += rowHTML('Other Operating Expenses', otherOpex.map(v => fmtM(-Math.abs(v))), { indent: 1 });
  }
  html += rowHTML('Total Operating Expenses', totalOpex.map(v => fmtM(-Math.abs(v))), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(totalOpex[lastIdx], totalOpex[prevIdx]))
  });

  // 3. OPERATING INCOME & EBITDA
  html += rowHTML('OPERATING PROFIT &amp; EBITDA', [], { isSection: true });
  html += rowHTML('Operating Income (EBIT)', ebit.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(ebit[lastIdx], ebit[prevIdx]))
  });
  html += rowHTML('Operating Margin %', ebit.map((v, i) => rev[i] ? fmtMargin(v / rev[i]) : '-'), { indent: 1 });
  html += rowHTML('Depreciation &amp; Amortization', da.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('EBITDA', ebitda.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(ebitda[lastIdx], ebitda[prevIdx]))
  });
  html += rowHTML('EBITDA Margin %', ebitda.map((v, i) => rev[i] ? fmtMargin(v / rev[i]) : '-'), { indent: 1 });

  // 4. NON-OPERATING & TAX
  html += rowHTML('NON-OPERATING ITEMS &amp; PRE-TAX', [], { isSection: true });
  html += rowHTML('Net Interest Expense / (Income)', intExp.map(v => fmtM(-Math.abs(v))), { indent: 1 });
  if (nonOp.some(v => v !== 0)) {
    html += rowHTML('Other Non-Operating Income / (Expense)', nonOp.map(v => fmtM(v)), { indent: 1 });
  }
  html += rowHTML('Pre-Tax Income (EBT)', ebt.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(ebt[lastIdx], ebt[prevIdx]))
  });
  html += rowHTML('Income Tax Provision', tax.map(v => fmtM(-Math.abs(v))), { indent: 1 });
  html += rowHTML('Effective Tax Rate %', tax.map((v, i) => ebt[i] > 0 ? fmtMargin(v / ebt[i]) : '-'), { indent: 1 });

  // 5. NET INCOME & EPS
  html += rowHTML('NET INCOME &amp; PER SHARE', [], { isSection: true });
  html += rowHTML('Consolidated Net Income', ni.map(v => fmtM(v)), {
    isTotal: true,
    extraVal: fmtPct(calcYoY(ni[lastIdx], ni[prevIdx]))
  });
  html += rowHTML('Net Profit Margin %', ni.map((v, i) => rev[i] ? fmtMargin(v / rev[i]) : '-'), { indent: 1 });
  html += rowHTML('Diluted Earnings Per Share (EPS)', eps.map(v => fmtEPS(v, sym)), {
    bold: true,
    extraVal: fmtPct(calcYoY(eps[lastIdx], eps[prevIdx]))
  });
  html += rowHTML('Weighted Diluted Shares (M)', shares.map(v => v ? (v / 1e6).toFixed(1) : '-'), { indent: 1 });

  tbody.innerHTML = html;
}

// ── 2. Balance Sheet ────────────────────────────────────────────────────────
function renderBalanceSheet(records, colYears, sym) {
  buildTableHeader('bsTable', colYears, 'YoY Change');
  const tbody = document.querySelector('#bsTable tbody');
  if (!tbody || !records.length) return;

  let html = '';

  const cash = records.map(r => getVal(r, ['Cash And Cash Equivalents']));
  const stInv = records.map(r => getVal(r, ['Other Short Term Investments', 'Cash Cash Equivalents And Short Term Investments']));
  const ar = records.map(r => getVal(r, ['Accounts Receivable', 'Receivables']));
  const inv = records.map(r => getVal(r, ['Inventory']));
  const otherCa = records.map(r => getVal(r, ['Other Current Assets', 'Prepaid Assets']));
  const totalCa = records.map(r => getVal(r, ['Current Assets', 'Total Current Assets']));

  const nppe = records.map(r => getVal(r, ['Net PPE', 'Gross PPE']));
  const gw = records.map(r => getVal(r, ['Goodwill']));
  const intang = records.map(r => getVal(r, ['Other Intangible Assets', 'Goodwill And Other Intangible Assets']));
  const ltInv = records.map(r => getVal(r, ['Investments And Advances', 'Investmentin Financial Assets', 'Financial Assets']));
  const otherNca = records.map(r => getVal(r, ['Other Non Current Assets']));
  const totalAssets = records.map(r => getVal(r, ['Total Assets']));

  const ap = records.map(r => getVal(r, ['Accounts Payable', 'Payables']));
  const stDebt = records.map(r => getVal(r, ['Current Debt', 'Current Debt And Capital Lease Obligation', 'Other Current Borrowings']));
  const otherCl = records.map(r => getVal(r, ['Other Current Liabilities', 'Current Accrued Expenses']));
  const totalCl = records.map(r => getVal(r, ['Current Liabilities', 'Total Current Liabilities']));

  const ltDebt = records.map(r => getVal(r, ['Long Term Debt', 'Long Term Debt And Capital Lease Obligation']));
  const otherNcl = records.map(r => getVal(r, ['Other Non Current Liabilities', 'Non Current Deferred Taxes Liabilities']));
  const totalLiab = records.map(r => getVal(r, ['Total Liabilities Net Minority Interest', 'Total Liabilities']));

  const commonStock = records.map(r => getVal(r, ['Common Stock', 'Capital Stock']));
  const re = records.map(r => getVal(r, ['Retained Earnings']));
  const apic = records.map(r => getVal(r, ['Additional Paid In Capital', 'Other Equity Adjustments']));
  const equity = records.map(r => getVal(r, ['Stockholders Equity', 'Common Stock Equity']));

  const lastIdx = records.length - 1;
  const prevIdx = Math.max(0, records.length - 2);

  // ASSETS: Current
  html += rowHTML('CURRENT ASSETS', [], { isSection: true });
  html += rowHTML('Cash &amp; Cash Equivalents', cash.map(v => fmtM(v)), { indent: 1 });
  if (stInv.some(v => v > 0)) {
    html += rowHTML('Short-Term Investments', stInv.map(v => fmtM(v)), { indent: 1 });
  }
  html += rowHTML('Accounts Receivable', ar.map(v => fmtM(v)), { indent: 1 });
  if (inv.some(v => v > 0)) {
    html += rowHTML('Inventory', inv.map(v => fmtM(v)), { indent: 1 });
  }
  html += rowHTML('Other Current Assets / Prepaids', otherCa.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Total Current Assets', totalCa.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(totalCa[lastIdx], totalCa[prevIdx]))
  });

  // ASSETS: Non-Current
  html += rowHTML('NON-CURRENT ASSETS', [], { isSection: true });
  html += rowHTML('Property, Plant &amp; Equipment (Net PPE)', nppe.map(v => fmtM(v)), { indent: 1 });
  if (gw.some(v => v > 0)) html += rowHTML('Goodwill', gw.map(v => fmtM(v)), { indent: 1 });
  if (intang.some(v => v > 0)) html += rowHTML('Intangible Assets', intang.map(v => fmtM(v)), { indent: 1 });
  if (ltInv.some(v => v > 0)) html += rowHTML('Long-Term Financial Investments', ltInv.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Other Non-Current Assets', otherNca.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('TOTAL ASSETS', totalAssets.map(v => fmtM(v)), {
    isTotal: true,
    extraVal: fmtPct(calcYoY(totalAssets[lastIdx], totalAssets[prevIdx]))
  });

  // LIABILITIES: Current
  html += rowHTML('CURRENT LIABILITIES', [], { isSection: true });
  html += rowHTML('Accounts Payable', ap.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Short-Term Debt &amp; Borrowings', stDebt.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Other Current Liabilities', otherCl.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Total Current Liabilities', totalCl.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(totalCl[lastIdx], totalCl[prevIdx]))
  });

  // LIABILITIES: Non-Current
  html += rowHTML('NON-CURRENT LIABILITIES', [], { isSection: true });
  html += rowHTML('Long-Term Debt', ltDebt.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Other Non-Current Liabilities', otherNcl.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('TOTAL LIABILITIES', totalLiab.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(totalLiab[lastIdx], totalLiab[prevIdx]))
  });

  // STOCKHOLDERS' EQUITY
  html += rowHTML("STOCKHOLDERS' EQUITY", [], { isSection: true });
  html += rowHTML('Common Stock', commonStock.map(v => fmtM(v)), { indent: 1 });
  if (apic.some(v => v > 0)) html += rowHTML('Additional Paid-In Capital', apic.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Retained Earnings', re.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML("TOTAL STOCKHOLDERS' EQUITY", equity.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(equity[lastIdx], equity[prevIdx]))
  });

  // TOTAL LIABILITIES & EQUITY
  const totalLiabEq = totalLiab.map((l, i) => l + equity[i]);
  html += rowHTML('TOTAL LIABILITIES &amp; EQUITY', totalLiabEq.map(v => fmtM(v)), {
    isTotal: true,
    extraVal: fmtPct(calcYoY(totalLiabEq[lastIdx], totalLiabEq[prevIdx]))
  });

  // CREDIT & LIQUIDITY BRIDGE
  html += rowHTML('CREDIT &amp; WORKING CAPITAL BRIDGE', [], { isSection: true });
  const totalDebt = stDebt.map((s, i) => s + ltDebt[i]);
  const netDebt = totalDebt.map((d, i) => d - cash[i]);
  const nwc = totalCa.map((ca, i) => ca - totalCl[i]);

  html += rowHTML('Total Debt (ST + LT Debt)', totalDebt.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Net Debt (Total Debt - Cash)', netDebt.map(v => fmtM(v)), {
    bold: true,
    indent: 1,
    extraVal: fmtPct(calcYoY(netDebt[lastIdx], netDebt[prevIdx]))
  });
  html += rowHTML('Net Working Capital (CA - CL)', nwc.map(v => fmtM(v)), {
    bold: true,
    indent: 1,
    extraVal: fmtPct(calcYoY(nwc[lastIdx], nwc[prevIdx]))
  });

  tbody.innerHTML = html;
}

// ── 3. Cash Flow Statement ──────────────────────────────────────────────────
function renderCashFlow(records, colYears, sym) {
  buildTableHeader('cfTable', colYears, 'YoY Trend');
  const tbody = document.querySelector('#cfTable tbody');
  if (!tbody || !records.length) return;

  let html = '';

  const ni = records.map(r => getVal(r, ['Net Income From Continuing Operations', 'Net Income']));
  const da = records.map(r => getVal(r, ['Depreciation And Amortization', 'Depreciation Amortization Depletion']));
  const sbc = records.map(r => getVal(r, ['Stock Based Compensation']));
  const wcChange = records.map(r => getVal(r, ['Change In Working Capital']));
  const defTax = records.map(r => getVal(r, ['Deferred Tax', 'Deferred Income Tax']));
  const otherNonCash = records.map(r => getVal(r, ['Other Non Cash Items']));
  const cfo = records.map(r => getVal(r, ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities']));

  const capex = records.map(r => -Math.abs(getVal(r, ['Capital Expenditure', 'Purchase Of PPE', 'Purchase Of Property Plant And Equipment'])));
  const netInv = records.map(r => getVal(r, ['Net Investment Purchase And Sale', 'Purchase Of Investment', 'Sale Of Investment']));
  const acquisitions = records.map(r => getVal(r, ['Net Business Purchase And Sale', 'Purchase Of Business', 'Sale Of Business']));
  const cfi = records.map(r => getVal(r, ['Investing Cash Flow', 'Cash Flow From Continuing Investing Activities']));

  const debtFlow = records.map(r => getVal(r, ['Net Issuance Payments Of Debt', 'Issuance Of Debt', 'Repayment Of Debt']));
  const stockFlow = records.map(r => getVal(r, ['Repurchase Of Capital Stock', 'Common Stock Issuance']));
  const dividends = records.map(r => -Math.abs(getVal(r, ['Cash Dividends Paid', 'Common Stock Dividend Paid'])));
  const cff = records.map(r => getVal(r, ['Financing Cash Flow', 'Cash Flow From Continuing Financing Activities']));

  const fcf = cfo.map((o, i) => o + capex[i]);

  const lastIdx = records.length - 1;
  const prevIdx = Math.max(0, records.length - 2);

  // 1. OPERATING ACTIVITIES (CFO)
  html += rowHTML('CASH FLOW FROM OPERATING ACTIVITIES (CFO)', [], { isSection: true });
  html += rowHTML('Consolidated Net Income', ni.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Depreciation &amp; Amortization', da.map(v => fmtM(v)), { indent: 1 });
  if (sbc.some(v => v > 0)) html += rowHTML('Stock-Based Compensation', sbc.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Change in Working Capital', wcChange.map(v => fmtM(v)), { indent: 1 });
  if (defTax.some(v => v !== 0)) html += rowHTML('Deferred Income Taxes', defTax.map(v => fmtM(v)), { indent: 1 });
  if (otherNonCash.some(v => v !== 0)) html += rowHTML('Other Non-Cash Operating Items', otherNonCash.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Net Cash Provided by Operating Activities (CFO)', cfo.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(cfo[lastIdx], cfo[prevIdx]))
  });

  // 2. INVESTING ACTIVITIES (CFI)
  html += rowHTML('CASH FLOW FROM INVESTING ACTIVITIES (CFI)', [], { isSection: true });
  html += rowHTML('Capital Expenditures (CapEx)', capex.map(v => fmtM(v)), { indent: 1 });
  if (netInv.some(v => v !== 0)) html += rowHTML('Net Purchase / (Sale) of Marketable Securities', netInv.map(v => fmtM(v)), { indent: 1 });
  if (acquisitions.some(v => v !== 0)) html += rowHTML('Business Acquisitions &amp; Disposals', acquisitions.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Net Cash Used in Investing Activities (CFI)', cfi.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(cfi[lastIdx], cfi[prevIdx]))
  });

  // 3. FINANCING ACTIVITIES (CFF)
  html += rowHTML('CASH FLOW FROM FINANCING ACTIVITIES (CFF)', [], { isSection: true });
  html += rowHTML('Net Issuance / (Repayment) of Debt', debtFlow.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Common Stock Repurchase &amp; Issuance', stockFlow.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Cash Dividends Paid', dividends.map(v => fmtM(v)), { indent: 1 });
  html += rowHTML('Net Cash Used in Financing Activities (CFF)', cff.map(v => fmtM(v)), {
    bold: true,
    isSubtotal: true,
    extraVal: fmtPct(calcYoY(cff[lastIdx], cff[prevIdx]))
  });

  // 4. FREE CASH FLOW & METRICS
  html += rowHTML('FREE CASH FLOW TO FIRM (FCFF)', [], { isSection: true });
  html += rowHTML('Free Cash Flow (CFO - |CapEx|)', fcf.map(v => fmtM(v)), {
    isTotal: true,
    extraVal: fmtPct(calcYoY(fcf[lastIdx], fcf[prevIdx]))
  });
  html += rowHTML('FCF Conversion % (FCF / CFO)', fcf.map((f, i) => cfo[i] ? fmtMargin(f / cfo[i]) : '-'), { indent: 1 });

  tbody.innerHTML = html;
}

// ── 4. Key Ratios ───────────────────────────────────────────────────────────
function renderKeyRatios(isRecords, bsRecords, cfRecords, colYears, sym) {
  buildTableHeader('ratiosTable', colYears, 'Latest');
  const tbody = document.querySelector('#ratiosTable tbody');
  if (!tbody || !isRecords.length) return;

  let html = '';

  const n = isRecords.length;
  const rev = isRecords.map(r => getVal(r, ['Total Revenue', 'Operating Revenue']));
  const gp = isRecords.map(r => getVal(r, ['Gross Profit']));
  const ebit = isRecords.map(r => getVal(r, ['Operating Income', 'EBIT']));
  const da = isRecords.map(r => getVal(r, ['Depreciation And Amortization', 'Reconciled Depreciation']));
  const ebitda = isRecords.map((r, i) => getVal(r, ['EBITDA', 'Normalized EBITDA']) || (ebit[i] + da[i]));
  const ni = isRecords.map(r => getVal(r, ['Net Income Common Stockholders', 'Net Income']));
  const intExp = isRecords.map(r => Math.abs(getVal(r, ['Interest Expense'])));

  const totalAssets = bsRecords.map(r => getVal(r, ['Total Assets']));
  const equity = bsRecords.map(r => getVal(r, ['Stockholders Equity', 'Common Stock Equity']));
  const totalCa = bsRecords.map(r => getVal(r, ['Current Assets', 'Total Current Assets']));
  const totalCl = bsRecords.map(r => getVal(r, ['Current Liabilities', 'Total Current Liabilities']));
  const cash = bsRecords.map(r => getVal(r, ['Cash And Cash Equivalents']));
  const ar = bsRecords.map(r => getVal(r, ['Accounts Receivable', 'Receivables']));
  const stDebt = bsRecords.map(r => getVal(r, ['Current Debt', 'Current Debt And Capital Lease Obligation']));
  const ltDebt = bsRecords.map(r => getVal(r, ['Long Term Debt', 'Long Term Debt And Capital Lease Obligation']));
  const totalDebt = stDebt.map((s, i) => s + (ltDebt[i] || 0));
  const netDebt = totalDebt.map((d, i) => d - (cash[i] || 0));

  const lastIdx = n - 1;

  // 1. PROFITABILITY
  html += rowHTML('PROFITABILITY MULTIPLES', [], { isSection: true });
  html += rowHTML('Gross Profit Margin %', gp.map((v, i) => rev[i] ? fmtMargin(v / rev[i]) : '-'), {
    bold: true,
    extraVal: rev[lastIdx] ? fmtMargin(gp[lastIdx] / rev[lastIdx]) : '-'
  });
  html += rowHTML('Operating (EBIT) Margin %', ebit.map((v, i) => rev[i] ? fmtMargin(v / rev[i]) : '-'), {
    bold: true,
    extraVal: rev[lastIdx] ? fmtMargin(ebit[lastIdx] / rev[lastIdx]) : '-'
  });
  html += rowHTML('EBITDA Margin %', ebitda.map((v, i) => rev[i] ? fmtMargin(v / rev[i]) : '-'), {
    bold: true,
    extraVal: rev[lastIdx] ? fmtMargin(ebitda[lastIdx] / rev[lastIdx]) : '-'
  });
  html += rowHTML('Net Profit Margin %', ni.map((v, i) => rev[i] ? fmtMargin(v / rev[i]) : '-'), {
    bold: true,
    extraVal: rev[lastIdx] ? fmtMargin(ni[lastIdx] / rev[lastIdx]) : '-'
  });
  html += rowHTML('Return on Equity (ROE %)', ni.map((v, i) => equity[i] ? fmtMargin(v / equity[i]) : '-'), {
    bold: true,
    extraVal: equity[lastIdx] ? fmtMargin(ni[lastIdx] / equity[lastIdx]) : '-'
  });
  html += rowHTML('Return on Assets (ROA %)', ni.map((v, i) => totalAssets[i] ? fmtMargin(v / totalAssets[i]) : '-'), {
    indent: 1,
    extraVal: totalAssets[lastIdx] ? fmtMargin(ni[lastIdx] / totalAssets[lastIdx]) : '-'
  });

  // 2. LIQUIDITY
  html += rowHTML('LIQUIDITY &amp; SOLVENCY', [], { isSection: true });
  html += rowHTML('Current Ratio (CA / CL)', totalCa.map((ca, i) => totalCl[i] ? fmtMult(ca / totalCl[i]) : '-'), {
    bold: true,
    extraVal: totalCl[lastIdx] ? fmtMult(totalCa[lastIdx] / totalCl[lastIdx]) : '-'
  });
  html += rowHTML('Quick Ratio ((Cash + AR) / CL)', cash.map((c, i) => totalCl[i] ? fmtMult((c + (ar[i] || 0)) / totalCl[i]) : '-'), {
    indent: 1,
    extraVal: totalCl[lastIdx] ? fmtMult(((cash[lastIdx] || 0) + (ar[lastIdx] || 0)) / totalCl[lastIdx]) : '-'
  });
  html += rowHTML('Cash Ratio (Cash / CL)', cash.map((c, i) => totalCl[i] ? fmtMult(c / totalCl[i]) : '-'), {
    indent: 1
  });

  // 3. LEVERAGE
  html += rowHTML('LEVERAGE &amp; COVERAGE', [], { isSection: true });
  html += rowHTML('Debt-to-Equity Ratio', totalDebt.map((d, i) => equity[i] ? fmtMult(d / equity[i]) : '-'), {
    bold: true,
    extraVal: equity[lastIdx] ? fmtMult(totalDebt[lastIdx] / equity[lastIdx]) : '-'
  });
  html += rowHTML('Net Debt / EBITDA', netDebt.map((nd, i) => ebitda[i] && ebitda[i] > 0 ? fmtMult(nd / ebitda[i]) : '-'), {
    bold: true,
    extraVal: ebitda[lastIdx] && ebitda[lastIdx] > 0 ? fmtMult(netDebt[lastIdx] / ebitda[lastIdx]) : '-'
  });
  html += rowHTML('Interest Coverage (EBIT / Interest)', ebit.map((eb, i) => intExp[i] && intExp[i] > 0 ? fmtMult(eb / intExp[i]) : '-'), {
    indent: 1,
    extraVal: intExp[lastIdx] && intExp[lastIdx] > 0 ? fmtMult(ebit[lastIdx] / intExp[lastIdx]) : '-'
  });

  // 4. DUPONT DECOMPOSITION
  html += rowHTML('DUPONT 3-WAY ROE DECOMPOSITION', [], { isSection: true });
  const netMargin = ni.map((v, i) => rev[i] ? (v / rev[i]) : 0);
  const assetTurn = rev.map((r, i) => totalAssets[i] ? (r / totalAssets[i]) : 0);
  const finLev = totalAssets.map((a, i) => equity[i] ? (a / equity[i]) : 0);
  const dupontRoe = netMargin.map((m, i) => m * assetTurn[i] * finLev[i]);

  html += rowHTML('1. Net Profit Margin', netMargin.map(v => fmtMargin(v)), { indent: 1 });
  html += rowHTML('2. Asset Turnover Ratio', assetTurn.map(v => fmtMult(v)), { indent: 1 });
  html += rowHTML('3. Financial Leverage Multiplier (Assets / Equity)', finLev.map(v => fmtMult(v)), { indent: 1 });
  html += rowHTML('Implied DuPont Return on Equity (ROE)', dupontRoe.map(v => fmtMargin(v)), {
    isTotal: true,
    extraVal: fmtMargin(dupontRoe[lastIdx])
  });

  tbody.innerHTML = html;
}
