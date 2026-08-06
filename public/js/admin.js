/* admin.js — admin dashboard: users, analytics, charts */
document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    // Check admin role from stored user
    const user = app.getUser();
    if (user.role !== 'admin') {
        document.body.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:1rem;">
                <h1 style="color:#f0b429;font-size:2rem;">🔒 Access Denied</h1>
                <p style="color:#9ca3af;">Admin privileges required.</p>
                <a href="dashboard.html" style="color:#3b82f6;">← Back to Dashboard</a>
            </div>`;
        return;
    }

    setText('adminEmail', user.email || 'Admin');
    await loadAdminData();
});

async function loadAdminData() {
    app.showLoading();
    try {
        const [analytics, usersRes] = await Promise.all([
            api.getAnalytics(),
            api.getUsers(),
        ]);

        // Compute derived stats
        const today = new Date().toISOString().slice(0, 10);
        const todayEntry = analytics.searches_by_day?.find(d => d.date === today);
        const searchesToday = todayEntry?.count ?? 0;
        const topTickerEntry = analytics.top_tickers?.[0];
        const topTicker = topTickerEntry?.ticker ?? '–';

        // ── Stats ──────────────────────────────────
        setText('totalUsers',    analytics.total_users ?? '–');
        setText('totalSearches', analytics.total_searches ?? '–');
        setText('searchesToday', searchesToday);
        setText('topTicker',     topTicker);
        setText('activeUsers',   analytics.top_users?.length ?? '–');

        // ── Charts ───────────────────────────────────────────
        if (analytics.searches_by_day?.length) renderSearchesChart(analytics.searches_by_day);
        if (analytics.top_tickers?.length)     renderTopTickersChart(analytics.top_tickers);

        // ── Users table ──────────────────────────────────────
        const users = usersRes.users || usersRes || [];
        renderUsersTable(users);

    } catch (err) {
        console.error(err);
        app.showError('Failed to load admin data: ' + err.message);
    } finally {
        app.hideLoading();
    }
}

function renderSearchesChart(data) {
    const ctx = document.getElementById('searchesChart')?.getContext('2d');
    if (!ctx) return;
    app.destroyChart('searches');
    app.saveChart('searches', new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.date || d.day),
            datasets: [{
                label: 'Searches',
                data: data.map(d => d.count),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59,130,246,.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 3,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#9ca3af' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
            }
        }
    }));
}

function renderTopTickersChart(data) {
    const ctx = document.getElementById('topTickersChart')?.getContext('2d');
    if (!ctx) return;
    app.destroyChart('tickers');
    app.saveChart('tickers', new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => d.ticker),
            datasets: [{
                label: 'Searches',
                data: data.map(d => d.count),
                backgroundColor: '#f0b429',
                borderRadius: 4,
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af' } },
                y: { grid: { display: false }, ticks: { color: '#9ca3af' } },
            }
        }
    }));
}

function renderUsersTable(users) {
    const tbody = document.querySelector('#usersTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';
    users.forEach(u => {
        const created   = u.created_at  ? new Date(u.created_at).toLocaleDateString()  : '–';
        const lastLogin = u.last_login  ? new Date(u.last_login).toLocaleDateString()  : 'Never';
        const isActive  = u.is_active !== false;
        const roleColor = u.role === 'admin' ? '#f0b429' : '#6b7280';
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${u.email}</td>
            <td><span class="badge" style="color:${roleColor};border-color:${roleColor}">${u.role || 'user'}</span></td>
            <td><span style="color:${isActive ? '#10b981' : '#ef4444'}">${isActive ? '● Active' : '○ Inactive'}</span></td>
            <td style="color:#6b7280">${created}</td>
            <td style="color:#6b7280">${lastLogin}</td>
            <td>
                <button class="btn btn-ghost" style="font-size:.8rem;padding:.25rem .75rem;" onclick="toggleUser(${u.id}, '${u.email}')">
                    ${isActive ? 'Deactivate' : 'Activate'}
                </button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

window.toggleUser = async function(userId, email) {
    if (!confirm(`Change status for ${email}?`)) return;
    try {
        await api.toggleUser(userId);
        app.showToast('User updated', 'success');
        await loadAdminData();
    } catch (e) {
        app.showToast('Failed: ' + e.message, 'error');
    }
};

function setText(id, val) { const e = document.getElementById(id); if (e) e.textContent = val ?? '–'; }
