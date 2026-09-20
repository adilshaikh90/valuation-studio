/**
 * Valuation Studio - API Client
 * Handles all communication with the FastAPI backend.
 */
const API_BASE = window.location.origin + '/api';

class ApiClient {
    constructor() {
        this.token = localStorage.getItem('vs_token');
    }

    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem('vs_token', token);
        } else {
            localStorage.removeItem('vs_token');
        }
    }

    clearToken() {
        this.token = null;
        try {
            localStorage.removeItem('vs_token');
            localStorage.removeItem('vs_user');
            localStorage.removeItem('vs_ticker');
            sessionStorage.clear();
        } catch (e) {}
    }

    getHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        return headers;
    }

    async request(method, path, body = null) {
        try {
            const options = {
                method,
                headers: this.getHeaders()
            };
            if (body) {
                options.body = JSON.stringify(body);
            }

            const response = await fetch(`${API_BASE}${path}`, options);

            if (response.status === 401) {
                this.clearToken();
                window.location.replace('login.html');
                throw new Error('Unauthorized');
            }

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || data.error || data.message || 'API request failed');
            }

            return data;
        } catch (error) {
            console.error(`API Error (${method} ${path}):`, error);
            throw error;
        }
    }

    // ── Auth ─────────────────────────────────────────────
    async signup(email, password) { return this.request('POST', '/auth/signup', { email, password }); }
    async login(email, password) { return this.request('POST', '/auth/login', { email, password }); }
    async getMe() { return this.request('GET', '/auth/me'); }

    // ── Company ──────────────────────────────────────────
    async getCompany(ticker) { return this.request('GET', `/company/${ticker}`); }
    async getFinancials(ticker) { return this.request('GET', `/company/${ticker}/financials`); }

    // ── Valuation ────────────────────────────────────────
    async getDcfFcff(ticker, params = {}) {
        const qs = new URLSearchParams(params).toString();
        return this.request('GET', `/valuation/${ticker}/dcf-fcff${qs ? '?' + qs : ''}`);
    }
    async getDcfFcfe(ticker) { return this.request('GET', `/valuation/${ticker}/dcf-fcfe`); }
    async getDdm(ticker) { return this.request('GET', `/valuation/${ticker}/ddm`); }
    async getApv(ticker) { return this.request('GET', `/valuation/${ticker}/apv`); }
    async getComps(ticker, customPeers = []) {
        const qs = customPeers.length ? `?custom_peers=${customPeers.join('&custom_peers=')}` : '';
        return this.request('GET', `/valuation/${ticker}/comps${qs}`);
    }
    async getNav(ticker) { return this.request('GET', `/valuation/${ticker}/nav`); }
    async getLbo(ticker, params = {}) {
        const qs = new URLSearchParams(params).toString();
        return this.request('GET', `/valuation/${ticker}/lbo${qs ? '?' + qs : ''}`);
    }
    async getFootballField(ticker) { return this.request('GET', `/valuation/${ticker}/football-field`); }

    // ── Quant ────────────────────────────────────────────
    async getMonteCarlo(ticker, iterations = 10000) {
        return this.request('GET', `/quant/${ticker}/monte-carlo?iterations=${iterations}`);
    }
    async getSensitivity(ticker) { return this.request('GET', `/quant/${ticker}/sensitivity`); }
    async getTornado(ticker) { return this.request('GET', `/quant/${ticker}/tornado`); }
    async getScenarios(ticker) { return this.request('GET', `/quant/${ticker}/scenarios`); }
    async getScenarioWeighting(ticker) { return this.request('GET', `/quant/${ticker}/scenario-weighting`); }
    async getRegressionMultiples(ticker) { return this.request('GET', `/quant/${ticker}/regression-multiples`); }

    // ── Performance ──────────────────────────────────────
    async getPerformance(ticker) { return this.request('GET', `/performance/${ticker}`); }

    // ── News ─────────────────────────────────────────────
    async getNews(ticker) { return this.request('GET', `/news/${ticker}`); }

    // ── Summary ──────────────────────────────────────────
    async getSummary(ticker) { return this.request('GET', `/summary/${ticker}`); }

    // ── Excel Download ───────────────────────────────────
    async downloadExcel(ticker) {
        const response = await fetch(`${API_BASE}/excel/${ticker}/download`, {
            headers: { 'Authorization': `Bearer ${this.token}` }
        });
        if (!response.ok) throw new Error('Download failed');
        return response.blob();
    }

    // ── Admin ────────────────────────────────────────────
    async getUsers(page = 1, limit = 50) { return this.request('GET', `/admin/users?page=${page}&limit=${limit}`); }
    async toggleUser(userId) { return this.request('PATCH', `/admin/users/${userId}`); }
    async updateUserRole(userId, role) { return this.request('PATCH', `/admin/users/${userId}/role`, { role }); }
    async deleteUser(userId) { return this.request('DELETE', `/admin/users/${userId}`); }
    async getAdminLogs(limit = 50) { return this.request('GET', `/admin/logs?limit=${limit}`); }
    async getAnalytics() { return this.request('GET', '/admin/analytics'); }
}

const api = new ApiClient();
window.api = api;
