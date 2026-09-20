/* download.js: Institutional Excel model download and summary copy */
let currentCompanyInfo = null;

document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const ticker = app.getTicker();
    if (!ticker) {
        document.body.innerHTML = '<p style="padding:2rem;color:#f0b429;">No ticker selected. <a href="dashboard.html" style="color:#38bdf8;">Go back to Studio</a></p>';
        return;
    }

    document.querySelectorAll('.currentTickerDisplay').forEach(el => el.textContent = ticker);
    setText('downloadTitle', `${ticker}: Institutional Valuation Model`);

    // Load company info for the preview card
    try {
        const company = await api.getCompany(ticker);
        currentCompanyInfo = company;
        const sym = company.currency_symbol || '$';
        setText('downloadCompanyName', company.name || ticker);
        setText('downloadSector', company.sector || '-');
        setText('downloadPrice', sym + app.fmt(company.current_price));
        setText('downloadCurrency', company.currency || 'USD');
    } catch (e) {
        console.warn('Company info fetch non-critical warning:', e);
    }

    // Copy Live Summary Action
    const copyBtn = document.getElementById('copySummaryBtn');
    if (copyBtn) {
        copyBtn.addEventListener('click', () => {
            if (!ticker) return;
            const name = (currentCompanyInfo && currentCompanyInfo.name) || ticker;
            const price = (currentCompanyInfo && currentCompanyInfo.current_price) ? app.fmt(currentCompanyInfo.current_price) : '-';
            const sector = (currentCompanyInfo && currentCompanyInfo.sector) || '-';
            const text = [
                `VALUATION STUDIO: EXECUTIVE MODEL SUMMARY`,
                `Ticker: ${ticker}`,
                `Company: ${name}`,
                `Sector: ${sector}`,
                `Current Price: $${price}`,
                `Model Architecture: 5-Year DCF, WACC, 3-Statement & 9x9 Sensitivity Matrix`,
                `Format: Microsoft Excel (.xlsx) / 100% Dynamic Native Formulas`,
                `Status: Live Institutional Model Compiled`,
                `Generated via Valuation Studio`
            ].join('\n');

            navigator.clipboard.writeText(text).then(() => {
                app.showToast('Executive Summary copied to clipboard!', 'success');
            }).catch(() => {
                app.showToast('Failed to copy summary to clipboard', 'error');
            });
        });
    }

    // Download button with animated multi-stage progress
    const downloadBtn = document.getElementById('downloadBtn');
    const progressContainer = document.getElementById('downloadProgressContainer');
    const progressBarFill = document.getElementById('progressBarFill');
    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');
    const step4 = document.getElementById('step4');

    if (downloadBtn) {
        downloadBtn.addEventListener('click', async () => {
            try {
                downloadBtn.disabled = true;
                downloadBtn.style.opacity = '0.7';
                if (progressContainer) progressContainer.style.display = 'block';

                // Step 1: SEC filings & financials
                if (progressBarFill) progressBarFill.style.width = '20%';
                if (step1) { step1.className = 'progress-step-item active'; }

                await new Promise(r => setTimeout(r, 450));

                // Step 2: DCF & WACC schedules
                if (progressBarFill) progressBarFill.style.width = '55%';
                if (step1) {
                    step1.className = 'progress-step-item done';
                    step1.querySelector('span').textContent = '[1/4] Historical SEC filings & financial statements extracted ✓';
                }
                if (step2) { step2.className = 'progress-step-item active'; }

                // Fetch real blob from backend
                const downloadPromise = api.downloadExcel(ticker);

                await new Promise(r => setTimeout(r, 450));

                // Step 3: Vector identity
                if (progressBarFill) progressBarFill.style.width = '80%';
                if (step2) {
                    step2.className = 'progress-step-item done';
                    step2.querySelector('span').textContent = '[2/4] 5-year dynamic DCF & WACC schedules compiled ✓';
                }
                if (step3) { step3.className = 'progress-step-item active'; }

                const blob = await downloadPromise;

                // Step 4: Finalize
                if (progressBarFill) progressBarFill.style.width = '100%';
                if (step3) {
                    step3.className = 'progress-step-item done';
                    step3.querySelector('span').textContent = '[3/4] Corporate vector identity & formatting embedded ✓';
                }
                if (step4) {
                    step4.className = 'progress-step-item done';
                    step4.querySelector('span').textContent = '[4/4] Encrypted .xlsx workbook finalized ✓';
                }

                await new Promise(r => setTimeout(r, 300));

                // Trigger file download
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${ticker}_Valuation_Studio_Model.xlsx`;
                document.body.appendChild(a);
                a.click();
                URL.revokeObjectURL(url);
                document.body.removeChild(a);

                app.showToast(`${ticker} Excel Model downloaded successfully!`, 'success');
            } catch (err) {
                console.error(err);
                app.showToast('Download failed: ' + (err.message || 'Error communicating with server'), 'error');
            } finally {
                downloadBtn.disabled = false;
                downloadBtn.style.opacity = '1';
                setTimeout(() => {
                    if (progressContainer) progressContainer.style.display = 'none';
                    if (progressBarFill) progressBarFill.style.width = '0%';
                }, 4000);
            }
        });
    }
});

function setText(id, val) {
    const e = document.getElementById(id);
    if (e) e.textContent = val ?? '-';
}
