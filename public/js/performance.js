/* performance.js — stock price history, stats, returns heatmap */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected.</p>'; return; }

    document.querySelectorAll('.currentTickerDisplay').forEach(el => el.textContent = ticker);

    // Period filter buttons
    document.querySelectorAll('.time-filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.time-filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
        });
    });

    await loadPerformance(ticker);
});

async function loadPerformance(ticker) {
    app.showLoading();
    try {
        const data = await api.getPerformance(ticker);

        const company = await api.getCompany(ticker);
        const sym = company.currency_symbol || '$';

        const bm = data.benchmark || { name: 'S&P 500', symbol: '^GSPC', full_name: 'S&P 500 Index', country: 'United States' };
        const rel = data.relative_metrics || {};
        const bStats = data.benchmark_stats || {};

        // ── Update Benchmark Badges and Labels ───────────────
        const badge = document.getElementById('benchmarkBadge');
        if (badge) {
            badge.innerHTML = `🏛️ Benchmark: <strong>${bm.name}</strong> (${bm.market || bm.country})`;
        }
        const subtitle = document.getElementById('perfSubtitle');
        if (subtitle) {
            subtitle.textContent = `Performance against primary sovereign benchmark: ${bm.full_name || bm.name}`;
        }
        const chartHeader = document.getElementById('perfChartHeader');
        if (chartHeader) {
            chartHeader.childNodes[0].nodeValue = `Price Performance vs ${bm.name} (Normalised to 100) `;
        }
        const bLabel = document.getElementById('benchReturnLabel');
        if (bLabel) bLabel.textContent = `${bm.name} Return (5Y)`;
        const betaLabel = document.getElementById('perfBetaLabel');
        if (betaLabel) betaLabel.textContent = `Beta vs ${bm.name}`;

        // ── Stats ────────────────────────────────────────────
        const stats = data.stats || {};
        setText('totalReturn',  pctStr(stats.total_return));
        setText('cagr',         pctStr(stats.annualized_return ?? stats.cagr));
        setText('benchReturn',  pctStr(rel.benchmark_total_return ?? bStats.total_return));
        setText('perfBeta',     rel.beta_vs_benchmark != null ? app.fmt(rel.beta_vs_benchmark, 2) : (company.beta ? app.fmt(company.beta, 2) : '–'));
        setText('perfAlpha',    rel.alpha_vs_benchmark != null ? pctStr(rel.alpha_vs_benchmark) : '–');
        setText('perfCorr',     rel.correlation != null ? app.fmt(rel.correlation, 2) : '–');
        setText('volatility',   pctStr(stats.volatility));
        setText('sharpeRatio',  stats.sharpe_ratio != null ? app.fmt(stats.sharpe_ratio, 2) : (stats.sharpe != null ? app.fmt(stats.sharpe, 2) : '–'));

        colorEl('totalReturn', stats.total_return);
        colorEl('cagr',        stats.annualized_return ?? stats.cagr);
        colorEl('benchReturn', rel.benchmark_total_return ?? bStats.total_return);
        colorEl('perfAlpha',   rel.alpha_vs_benchmark);

        // ── Price Chart ─────────────────────────────────────
        if (data.dates?.length) {
            renderPerfChart(data.dates, data.prices, data.benchmark_prices || [], ticker, sym, bm.name);
        }

        // ── Monthly Returns Heatmap ──────────────────────────
        if (data.monthly_returns?.length) {
            // Convert flat [{month,year,return_pct}] → grouped by year
            const grouped = {};
            data.monthly_returns.forEach(r => {
                if (!grouped[r.year]) grouped[r.year] = Array(12).fill(null);
                grouped[r.year][r.month - 1] = r.return_pct;
            });
            const heatmapData = Object.entries(grouped).sort(([a],[b])=>a-b).map(([year, months]) => ({
                year: parseInt(year),
                months,
                ytd: months.reduce((acc, m) => m != null ? (acc === null ? m : (1+acc)*(1+m)-1) : acc, null)
            }));
            renderHeatmap(heatmapData);
        }

    } catch (err) {
        console.error(err);
        app.showError('Failed to load performance data: ' + err.message);
    } finally {
        app.hideLoading();
    }
}

function renderPerfChart(dates, prices, benchmark, ticker, sym, benchName = 'Benchmark') {
    const ctx = document.getElementById('perfChart')?.getContext('2d');
    if (!ctx) return;
    app.destroyChart('perf');

    // Normalise to 100 at start for comparison
    const norm  = prices.map(p => p / prices[0] * 100);
    const bNorm = benchmark.length ? benchmark.map(p => p / benchmark[0] * 100) : [];

    const datasets = [{
        label: ticker,
        data: norm,
        borderColor: '#f0b429',
        borderWidth: 2,
        pointRadius: 0,
        fill: false,
        tension: 0.1,
    }];

    if (bNorm.length) {
        datasets.push({
            label: benchName,
            data: bNorm,
            borderColor: '#3b82f6',
            borderWidth: 1.5,
            pointRadius: 0,
            borderDash: [5, 5],
            fill: false,
            tension: 0.1,
        });
    }


    app.saveChart('perf', new Chart(ctx, {
        type: 'line',
        data: { labels: dates, datasets },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { labels: { color: '#9ca3af' } },
                tooltip: {
                    callbacks: {
                        label: ctx => `${ctx.dataset.label}: ${ctx.raw?.toFixed(1)} (base 100)`,
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#6b7280', maxTicksLimit: 12 },
                },
                y: {
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#6b7280' },
                }
            }
        }
    }));
}

function renderHeatmap(monthlyReturns) {
    const el = document.getElementById('heatmapContainer');
    if (!el) return;
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    let html = '<table class="data-table"><thead><tr><th>Year</th>';
    months.forEach(m => html += `<th>${m}</th>`);
    html += '<th>Full Year</th></tr></thead><tbody>';

    monthlyReturns.forEach(row => {
        html += `<tr><td><strong>${row.year}</strong></td>`;
        (row.months || []).forEach(v => {
            if (v == null) { html += '<td style="color:#374151">–</td>'; return; }
            const color = v > 0 ? '#10b981' : (v < 0 ? '#ef4444' : '#9ca3af');
            const bg    = v > 0 ? 'rgba(16,185,129,.1)' : (v < 0 ? 'rgba(239,68,68,.1)' : '');
            html += `<td style="color:${color};background:${bg}">${(v * 100).toFixed(1)}%</td>`;
        });
        const ytd = row.ytd ?? row.full_year;
        const ytdColor = ytd > 0 ? '#10b981' : (ytd < 0 ? '#ef4444' : '#9ca3af');
        html += `<td style="color:${ytdColor};font-weight:600">${ytd != null ? (ytd*100).toFixed(1)+'%' : '–'}</td></tr>`;
    });
    el.innerHTML = html + '</tbody></table>';
}

function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val ?? '–'; }
function pctStr(v) { if (v == null) return '–'; const pct = v > 1.5 ? v : v * 100; return (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%'; }
function colorEl(id, v) {
    const e = document.getElementById(id);
    if (!e || v == null) return;
    e.style.color = v >= 0 ? '#10b981' : '#ef4444';
}
