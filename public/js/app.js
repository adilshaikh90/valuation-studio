class App {
    constructor() {
        this.currentTicker = this.getTicker();
        this.currentCompany = null;
        this.user = null;
        this._charts = {};
    }

    async init() {
        // Anti-stale cache guard: If browser served an ancient cached HTML file lacking the sidebar
        const isAuthPage = window.location.pathname.includes('login')
            || window.location.pathname.includes('signup')
            || window.location.pathname === '/'
            || window.location.pathname.endsWith('index.html');
        if (!isAuthPage && !document.querySelector('.layout-with-sidebar')) {
            const url = new URL(window.location.href);
            url.searchParams.set('v', '2.1_' + Date.now());
            window.location.replace(url.toString());
            return;
        }

        await this.checkAuth();
        this.setupEventListeners();
    }

    isAuthenticated() {
        return !!api.token;
    }

    async checkAuth() {
        const isAuthPage = window.location.pathname.includes('login')
            || window.location.pathname.includes('signup')
            || window.location.pathname === '/'
            || window.location.pathname.endsWith('index.html');

        if (api.token) {
            try {
                this.user = await api.getMe();
                localStorage.setItem('vs_user', JSON.stringify(this.user));
                const userEl = document.getElementById('user-menu-name');
                if (userEl) userEl.textContent = this.user.email;
                // Sidebar user email
                const sidebarEmail = document.getElementById('sidebarUserEmail');
                if (sidebarEmail) sidebarEmail.textContent = this.user.email;
            } catch (err) {
                api.clearToken();
                if (!isAuthPage) window.location.href = 'login.html';
            }
        } else if (!isAuthPage) {
            window.location.href = 'login.html';
        }

        // Populate sidebar ticker info
        this._populateSidebar();

        // Mark active sidebar item
        const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';
        document.querySelectorAll('.sidebar-item').forEach(item => {
            item.classList.remove('active');
            const href = item.getAttribute('href') || '';
            if (href === currentPage || href.split('?')[0] === currentPage) {
                item.classList.add('active');
            }
        });
    }

    async _populatSidebar() { this._populateSidebar(); }

    _populateSidebar() {
        const ticker = this.getTicker();
        const tickerEl = document.getElementById('sidebarTicker');
        if (tickerEl && ticker) tickerEl.textContent = ticker;

        // Fetch price for sidebar if ticker exists
        if (ticker && api.token) {
            api.getCompany(ticker).then(info => {
                const priceEl = document.getElementById('sidebarPrice');
                if (priceEl && info.current_price) {
                    const sym = info.currency_symbol || '$';
                    priceEl.textContent = sym + this.fmt(info.current_price);
                    const pct = info.price_change_pct || 0;
                    priceEl.className = 'sidebar-ticker-price ' + (pct >= 0 ? 'text-green' : 'text-red');
                }
            }).catch(() => {});
        }
    }


    getUser() {
        try { return JSON.parse(localStorage.getItem('vs_user') || '{}'); } catch { return {}; }
    }

    setupEventListeners() {
        // Global ticker search (landing page)
        const searchForm = document.getElementById('global-search');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const input = searchForm.querySelector('input');
                if (input && input.value.trim()) {
                    this.setTicker(input.value.trim());
                    window.location.href = api.token ? 'dashboard.html' : 'login.html';
                }
            });
        }

        // Nav search bar (authenticated pages)
        const navSearchBtn = document.getElementById('navSearchBtn');
        if (navSearchBtn) {
            navSearchBtn.addEventListener('click', () => {
                const inp = document.getElementById('navTickerInput');
                if (inp && inp.value.trim()) {
                    this.setTicker(inp.value.trim().toUpperCase());
                    window.location.href = 'dashboard.html';
                }
            });
        }
        const navInput = document.getElementById('navTickerInput');
        if (navInput) {
            navInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') navSearchBtn && navSearchBtn.click();
            });
        }

        // Logout
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', (e) => {
                e.preventDefault();
                api.clearToken();
                localStorage.removeItem('vs_user');
                window.location.href = 'index.html';
            });
        }
    }

    setTicker(ticker) {
        this.currentTicker = ticker.toUpperCase();
        localStorage.setItem('vs_ticker', this.currentTicker);
    }

    getTicker() {
        // Also check URL param
        const params = new URLSearchParams(window.location.search);
        const urlTicker = params.get('ticker');
        if (urlTicker) {
            localStorage.setItem('vs_ticker', urlTicker.toUpperCase());
            return urlTicker.toUpperCase();
        }
        return localStorage.getItem('vs_ticker') || '';
    }

    navigateTo(page) { window.location.href = page; }

    // ── Loading overlay ──────────────────────────────────
    showLoading(containerId) {
        if (containerId) {
            const el = document.getElementById(containerId);
            if (el) el.innerHTML = `<div class="flex-center" style="min-height:200px;"><div class="loading"></div></div>`;
        } else {
            let ov = document.getElementById('_globalLoadingOverlay');
            if (!ov) {
                ov = document.createElement('div');
                ov.id = '_globalLoadingOverlay';
                ov.style.cssText = 'position:fixed;inset:0;background:rgba(10,14,26,.7);display:flex;align-items:center;justify-content:center;z-index:9999;';
                ov.innerHTML = '<div class="loading" style="width:48px;height:48px;border-width:4px;"></div>';
                document.body.appendChild(ov);
            }
        }
    }

    hideLoading(containerId, html) {
        if (containerId) {
            const el = document.getElementById(containerId);
            if (el && html !== undefined) el.innerHTML = html;
        } else {
            const ov = document.getElementById('_globalLoadingOverlay');
            if (ov) ov.remove();
        }
    }

    // ── Toast notifications ───────────────────────────────
    showToast(message, type = 'info') {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
        toast.innerHTML = `<div>${icons[type] || 'ℹ️'}</div><div>${message}</div>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(20px)';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    showError(message, containerId) {
        const html = `<div style="color:#ef4444;padding:1.5rem;border:1px solid #ef4444;border-radius:8px;background:rgba(239,68,68,.1);text-align:center;">⚠️ ${message}</div>`;
        if (containerId) {
            const el = document.getElementById(containerId);
            if (el) el.innerHTML = html;
        } else {
            this.showToast(message, 'error');
        }
    }

    // ── Formatters ────────────────────────────────────────
    fmt(num, decimals = 2) {
        if (num == null || isNaN(num)) return '–';
        return Number(num).toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
    }

    fmtPct(num, decimals = 1) {
        if (num == null || isNaN(num)) return '–';
        const pct = num > 1.5 ? num : num * 100; // accept both 0.05 and 5.0
        return (pct >= 0 ? '+' : '') + pct.toFixed(decimals) + '%';
    }

    fmtLarge(num) {
        if (num == null || isNaN(num)) return '–';
        const abs = Math.abs(num);
        const sign = num < 0 ? '-' : '';
        if (abs >= 1e12) return sign + (abs / 1e12).toFixed(2) + 'T';
        if (abs >= 1e9)  return sign + (abs / 1e9).toFixed(2) + 'B';
        if (abs >= 1e6)  return sign + (abs / 1e6).toFixed(2) + 'M';
        if (abs >= 1e3)  return sign + (abs / 1e3).toFixed(2) + 'K';
        return sign + this.fmt(abs);
    }

    formatNumber(num, large = false) {
        return large ? this.fmtLarge(num) : this.fmt(num);
    }

    formatPercent(num) { return this.fmtPct(num); }

    formatCurrency(value, symbol) {
        if (value == null || isNaN(value)) return '–';
        const s = symbol || '$';
        const isNeg = value < 0;
        return (isNeg ? '-' : '') + s + this.fmt(Math.abs(value));
    }

    // ── Chart helpers ────────────────────────────────────
    destroyChart(id) {
        if (this._charts[id]) { this._charts[id].destroy(); delete this._charts[id]; }
    }

    saveChart(id, instance) { this._charts[id] = instance; }
}

const app = new App();
document.addEventListener('DOMContentLoaded', () => app.init());
