/* football-field.js - all valuation models side-by-side */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) { document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected.</p>'; return; }

    document.querySelectorAll('.currentTickerDisplay').forEach(el => el.textContent = ticker);
    await loadFootballField(ticker);
});

async function loadFootballField(ticker) {
    app.showLoading();
    try {
        const [ffRes, companyRes] = await Promise.all([
            api.getFootballField(ticker),
            api.getCompany(ticker),
        ]);

        const company      = companyRes;
        const currentPrice = company.current_price || 0;
        const sym          = company.currency_symbol || '$';
        const methods      = ffRes.methods || [];

        if (!methods.length) {
            app.showError('No valuation data could be computed for this ticker.');
            return;
        }

        // ── Summary stats ────────────────────────────────────
        const mids   = methods.map(m => m.mid || (m.low + m.high) / 2).filter(v => v > 0);
        const allLow = methods.map(m => m.low).filter(v => v > 0);
        const allHigh= methods.map(m => m.high).filter(v => v > 0);

        const median     = mids.length ? mids.reduce((a,b)=>a+b,0)/mids.length : 0;
        const rangeMin   = allLow.length  ? Math.min(...allLow)  : 0;
        const rangeMax   = allHigh.length ? Math.max(...allHigh) : 0;
        const upside     = currentPrice > 0 ? ((median / currentPrice) - 1) * 100 : 0;

        setText('currentPriceVal', sym + app.fmt(currentPrice));
        setText('consensusRange',  `${sym}${app.fmt(rangeMin)} – ${sym}${app.fmt(rangeMax)}`);
        setText('medianValue',     sym + app.fmt(median));
        setUpsideEl('priceUpside', upside);

        // ── Table ────────────────────────────────────────────
        const tbody = document.querySelector('#valuationTable tbody');
        if (tbody) {
            tbody.innerHTML = '';
            methods.forEach(item => {
                const mid    = item.mid || (item.low + item.high) / 2;
                const upside = currentPrice > 0 ? ((mid / currentPrice) - 1) * 100 : 0;
                const cl     = upside >= 0 ? 'text-green' : 'text-red';

                // Colour band: green = current in range, blue = undervalued, red = overvalued
                let badge = '🔵';
                if (currentPrice >= item.low && currentPrice <= item.high) badge = '🟢';
                else if (currentPrice > item.high) badge = '🔴';

                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${badge} ${item.method}</td>
                    <td>${sym}${app.fmt(item.low)}</td>
                    <td><strong>${sym}${app.fmt(mid)}</strong></td>
                    <td>${sym}${app.fmt(item.high)}</td>
                    <td class="${cl}">${upside >= 0 ? '+' : ''}${upside.toFixed(1)}%</td>
                    <td style="font-size:.8rem;color:#6b7280">${item.description || ''}</td>
                `;
                tbody.appendChild(tr);
            });
        }

        // ── Chart ────────────────────────────────────────────
        renderChart(methods, currentPrice, sym);

    } catch (err) {
        console.error(err);
        app.showError('Failed to load football field: ' + err.message);
    } finally {
        app.hideLoading();
    }
}

function renderChart(methods, currentPrice, sym) {
    const ctx = document.getElementById('footballFieldChart')?.getContext('2d');
    if (!ctx) return;
    app.destroyChart('ff');

    const labels = methods.map(m => m.method);
    const lows   = methods.map(m => m.low);
    const ranges = methods.map(m => Math.max(0, m.high - m.low));
    const bgColors = methods.map(m => {
        const mid = m.mid || (m.low + m.high) / 2;
        if (currentPrice >= m.low && currentPrice <= m.high) return 'rgba(16,185,129,0.7)';
        return currentPrice < m.low ? 'rgba(59,130,246,0.7)' : 'rgba(239,68,68,0.7)';
    });

    app.saveChart('ff', new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Base offset (hidden)',
                    data: lows,
                    backgroundColor: 'transparent',
                    borderWidth: 0,
                    stack: 'stack',
                },
                {
                    label: 'Valuation Range',
                    data: ranges,
                    backgroundColor: bgColors,
                    borderRadius: 4,
                    stack: 'stack',
                }
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            if (ctx.datasetIndex === 0) return null;
                            const m = methods[ctx.dataIndex];
                            return `Range: ${sym}${app.fmt(m.low)} – ${sym}${app.fmt(m.high)}`;
                        }
                    }
                },
                annotation: {
                    annotations: {
                        currentPrice: {
                            type: 'line',
                            xMin: currentPrice,
                            xMax: currentPrice,
                            borderColor: '#f0b429',
                            borderWidth: 2,
                            borderDash: [6, 4],
                            label: {
                                display: true,
                                content: `${sym}${app.fmt(currentPrice)}`,
                                position: 'start',
                                color: '#0a0e1a',
                                backgroundColor: '#f0b429',
                                padding: { x: 6, y: 3 },
                                borderRadius: 4,
                            }
                        }
                    }
                }
            },
            scales: {
                x: { stacked: true, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                y: { stacked: true, grid: { display: false }, ticks: { color: '#9ca3af' } },
            }
        }
    }));
}

function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val ?? '–'; }
function setUpsideEl(id, upside) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = (upside >= 0 ? '+' : '') + upside.toFixed(1) + '%';
    el.className = 'stat-value ' + (upside >= 0 ? 'text-green' : 'text-red');
}
