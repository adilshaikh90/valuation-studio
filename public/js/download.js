/* download.js — Excel model download */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) {
        document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected. <a href="dashboard.html" style="color:#3b82f6;">Go back</a></p>';
        return;
    }

    document.querySelectorAll('.currentTickerDisplay').forEach(el => el.textContent = ticker);
    setText('downloadTitle', `${ticker} — Complete Financial Model`);

    // Load company info for the preview card
    try {
        const company = await api.getCompany(ticker);
        const sym = company.currency_symbol || '$';
        setText('downloadCompanyName', company.name || ticker);
        setText('downloadSector',      company.sector || '–');
        setText('downloadPrice',       sym + app.fmt(company.current_price));
        setText('downloadCurrency',    company.currency || 'USD');
    } catch (e) { /* non-critical */ }

    // ── Download button ───────────────────────────────────
    const downloadBtn = document.getElementById('downloadBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', async () => {
            try {
                downloadBtn.disabled = true;
                downloadBtn.innerHTML = '<span class="loading" style="display:inline-block;width:16px;height:16px;margin-right:8px;border-width:2px;vertical-align:middle;"></span> Generating…';

                const blob = await api.downloadExcel(ticker);
                const url  = URL.createObjectURL(blob);
                const a    = document.createElement('a');
                a.href     = url;
                a.download = `${ticker}_Valuation_Studio_Model.xlsx`;
                document.body.appendChild(a);
                a.click();
                URL.revokeObjectURL(url);
                document.body.removeChild(a);

                app.showToast('Model downloaded!', 'success');
            } catch (err) {
                console.error(err);
                app.showToast('Download failed: ' + err.message, 'error');
            } finally {
                downloadBtn.disabled = false;
                downloadBtn.innerHTML = '⬇ Download Excel Model';
            }
        });
    }
});

function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val ?? '–'; }
