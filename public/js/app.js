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

                // Admin Control & Badge
                if (this.user && this.user.role === 'admin') {
                    const sidebarFooter = document.querySelector('.sidebar-footer');
                    if (sidebarFooter && !document.getElementById('sidebarAdminBadge')) {
                        const badge = document.createElement('span');
                        badge.id = 'sidebarAdminBadge';
                        badge.style.cssText = 'background: rgba(245, 158, 11, 0.18); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4); padding: 2px 7px; font-size: 0.7rem; border-radius: 4px; font-weight: 700; margin-bottom: 5px; display: inline-block; letter-spacing: 0.05em;';
                        badge.textContent = 'ADMIN';
                        sidebarFooter.insertBefore(badge, sidebarFooter.firstChild);
                    }

                    const sidebarNav = document.querySelector('.sidebar-nav');
                    if (sidebarNav && !document.getElementById('adminControlNavItem')) {
                        const adminLink = document.createElement('a');
                        adminLink.id = 'adminControlNavItem';
                        adminLink.href = 'admin.html?v=2.1';
                        adminLink.className = 'sidebar-item' + (window.location.pathname.includes('admin') ? ' active' : '');
                        adminLink.style.cssText = 'color: #f59e0b; font-weight: 600; border: 1px solid rgba(245, 158, 11, 0.25); background: rgba(245, 158, 11, 0.06); margin-top: 0.6rem;';
                        adminLink.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Admin Control';
                        sidebarNav.appendChild(adminLink);
                    }
                }
            } catch (err) {
                api.clearToken();
                if (!isAuthPage) window.location.href = 'login.html';
            }
        } else if (!isAuthPage) {
            window.location.href = 'login.html';
        }

        // Initialize global cookie notice
        this._initCookieBanner();

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

    // ── Cookie & Analytics Banner ────────────────────────
    _initCookieBanner() {
        const consent = localStorage.getItem('vs_cookie_consent');
        const existingBanner = document.getElementById('cookieNoticeBanner');
        if (consent) {
            if (existingBanner) existingBanner.classList.add('hidden');
            return;
        }
        if (existingBanner) return;

        const banner = document.createElement('div');
        banner.id = 'cookieNoticeBanner';
        banner.className = 'cookie-banner';
        banner.style.cssText = `
            position: fixed; bottom: 0; left: 0; right: 0;
            background: rgba(8, 14, 24, 0.96); backdrop-filter: blur(12px);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            padding: 1rem 2rem; z-index: 9999;
            display: flex; justify-content: center; align-items: center;
            box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.4);
            font-family: 'Inter', -apple-system, sans-serif;
        `;
        banner.innerHTML = `
            <div style="width: 100%; max-width: 1200px; display: flex; justify-content: space-between; align-items: center; gap: 2rem; flex-wrap: wrap;">
                <div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.45; flex: 1; min-width: 280px;">
                    <strong style="color: #ffffff; font-weight: 600;">Cookie &amp; Analytics Notice</strong> — We use Google Analytics to understand how the tool is used. No personal financial data is included in analytics events. You can opt out at any time. <a href="#" id="cookieGlobalPrivacyLink" style="color: #94a3b8; text-decoration: underline; margin-left: 0.35rem;">Privacy Policy</a>
                </div>
                <div style="display: flex; gap: 0.75rem; align-items: center;">
                    <button type="button" id="cookieGlobalDecline" style="background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255, 255, 255, 0.15); color: #e2e8f0; border-radius: 6px; padding: 0.55rem 1.25rem; font-size: 0.88rem; font-weight: 500; cursor: pointer; transition: all 0.2s;">Decline</button>
                    <button type="button" id="cookieGlobalAccept" style="background: #d97706; border: none; color: #0f172a; border-radius: 6px; padding: 0.55rem 1.35rem; font-size: 0.88rem; font-weight: 600; cursor: pointer; transition: all 0.2s; box-shadow: 0 2px 8px rgba(217, 119, 6, 0.3);">Accept Analytics</button>
                </div>
            </div>
        `;
        document.body.appendChild(banner);

        document.getElementById('cookieGlobalPrivacyLink')?.addEventListener('click', (e) => {
            e.preventDefault();
            alert('Valuation Studio Privacy Policy: We do not sell or store personal financial search data without consent.');
        });
        document.getElementById('cookieGlobalDecline')?.addEventListener('click', () => {
            localStorage.setItem('vs_cookie_consent', 'declined');
            banner.remove();
        });
        document.getElementById('cookieGlobalAccept')?.addEventListener('click', () => {
            localStorage.setItem('vs_cookie_consent', 'accepted');
            banner.remove();
        });
    }

    // ── Chart helpers ────────────────────────────────────
    destroyChart(id) {
        if (this._charts[id]) { this._charts[id].destroy(); delete this._charts[id]; }
    }

    saveChart(id, instance) { this._charts[id] = instance; }
}

const app = new App();
document.addEventListener('DOMContentLoaded', () => app.init());

