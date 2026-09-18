/* admin.js — comprehensive admin dashboard with user controls & audit trail */
let allUsers = [];

document.addEventListener('DOMContentLoaded', async () => {
    if (!app.isAuthenticated()) { window.location.href = 'login.html'; return; }

    const user = app.getUser();
    if (user.role !== 'admin') {
        document.body.innerHTML = `
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:1rem;background:#0f0f0f;color:#fff;">
                <h1 style="color:#f59e0b;font-size:2rem;">🔒 Access Denied</h1>
                <p style="color:#94a3b8;">Administrator privileges required to access the control center.</p>
                <a href="dashboard.html?v=2.1" class="btn btn-primary" style="margin-top:1rem;">Return to Dashboard</a>
            </div>`;
        return;
    }

    const emailEl = document.getElementById('sidebarUserEmail');
    if (emailEl) emailEl.textContent = user.email || 'Admin';

    // Search input filter
    const searchInput = document.getElementById('userSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterUsers(e.target.value.toLowerCase());
        });
    }

    await loadAdminData();
});

async function loadAdminData() {
    app.showLoading();
    try {
        const [analytics, usersRes, logsRes] = await Promise.all([
            api.getAnalytics(),
            api.getUsers(1, 100),
            api.getAdminLogs(50).catch(() => []),
        ]);

        // Stats
        setText('totalUsers', analytics.total_users ?? 0);
        setText('totalSearches', analytics.total_searches ?? 0);

        const today = new Date().toISOString().slice(0, 10);
        const todayEntry = analytics.searches_by_day?.find(d => d.date === today);
        setText('searchesToday', todayEntry?.count ?? 0);

        const topTicker = analytics.top_tickers?.[0];
        setText('topTicker', topTicker ? topTicker.ticker : '—');
        setText('topTickerCount', topTicker ? `${topTicker.count} requests` : 'No searches recorded');

        // Charts
        if (analytics.searches_by_day?.length) renderSearchesChart(analytics.searches_by_day);
        if (analytics.top_tickers?.length)     renderTopTickersChart(analytics.top_tickers);

        // Users
        allUsers = usersRes.users || [];
        const activeCount = allUsers.filter(u => u.is_active !== false).length;
        setText('activeUsersCount', `${activeCount} active / ${allUsers.length} total`);
        renderUsersTable(allUsers);

        // Logs
        renderAuditLogs(logsRes || []);

    } catch (err) {
        console.error(err);
        app.showToast('Failed to load admin data: ' + err.message, 'error');
    } finally {
        app.hideLoading();
    }
}

function filterUsers(query) {
    if (!query) {
        renderUsersTable(allUsers);
        return;
    }
    const filtered = allUsers.filter(u => 
        (u.email || '').toLowerCase().includes(query) ||
        (u.role || '').toLowerCase().includes(query)
    );
    renderUsersTable(filtered);
}

function renderUsersTable(users) {
    const tbody = document.querySelector('#usersTable tbody');
    if (!tbody) return;
    if (!users.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center py-4 text-muted">No users found.</td></tr>';
        return;
    }

    const currentAdmin = app.getUser();

    tbody.innerHTML = users.map(u => {
        const created = u.created_at ? new Date(u.created_at).toLocaleDateString() : '—';
        const lastLogin = u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never';
        const isActive = u.is_active !== false;
        const isAdmin = u.role === 'admin';
        const isSelf = u.id === currentAdmin.id;

        return `
            <tr>
                <td style="font-family:monospace;color:var(--text-muted);">#${u.id}</td>
                <td style="font-weight:600;">
                    ${u.email}
                    ${isSelf ? '<span class="badge" style="margin-left:6px;font-size:0.7rem;background:rgba(59,130,246,0.15);color:#60a5fa;">You</span>' : ''}
                </td>
                <td>
                    <span class="admin-badge ${isAdmin ? 'badge-admin' : 'badge-user'}">${u.role ? u.role.toUpperCase() : 'USER'}</span>
                </td>
                <td>
                    <span class="status-dot ${isActive ? 'status-active' : 'status-inactive'}"></span>
                    <span style="color:${isActive ? '#22c55e' : '#ef4444'};font-size:0.85rem;">${isActive ? 'Active' : 'Suspended'}</span>
                </td>
                <td class="text-muted text-sm">${created}</td>
                <td class="text-muted text-sm">${lastLogin}</td>
                <td style="text-align: right;">
                    <div class="flex gap-1 justify-end">
                        <button class="action-btn action-btn-gold" onclick="toggleRole(${u.id}, '${u.role}', '${u.email}')" ${isSelf ? 'disabled title="Cannot change own role"' : ''}>
                            ${isAdmin ? 'Make User' : 'Make Admin'}
                        </button>
                        <button class="action-btn" onclick="toggleActive(${u.id}, '${u.email}')" ${isSelf ? 'disabled title="Cannot suspend own account"' : ''}>
                            ${isActive ? 'Suspend' : 'Activate'}
                        </button>
                        <button class="action-btn action-btn-danger" onclick="deleteUserAccount(${u.id}, '${u.email}')" ${isSelf ? 'disabled title="Cannot delete own account"' : ''}>
                            Delete
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function renderAuditLogs(logs) {
    const tbody = document.querySelector('#logsTable tbody');
    if (!tbody) return;
    if (!logs.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No recent queries recorded.</td></tr>';
        return;
    }

    tbody.innerHTML = logs.map(l => {
        const time = l.timestamp ? new Date(l.timestamp).toLocaleString() : '—';
        return `
            <tr>
                <td class="text-muted text-sm">${time}</td>
                <td style="font-weight:500;">${l.user_email || 'Anonymous'}</td>
                <td><span class="badge" style="font-weight:700;color:var(--text-primary);background:var(--surface-3);">${l.ticker || '—'}</span></td>
                <td>${l.company || '—'}</td>
                <td><span style="color:#f59e0b;font-weight:600;">${l.currency || 'USD'}</span></td>
                <td class="text-muted">${l.country || '—'}</td>
            </tr>
        `;
    }).join('');
}

window.toggleActive = async function(userId, email) {
    if (!confirm(`Toggle active status for ${email}?`)) return;
    try {
        await api.toggleUser(userId);
        app.showToast(`User status updated for ${email}`, 'success');
        await loadAdminData();
    } catch (e) {
        app.showToast('Failed: ' + e.message, 'error');
    }
};

window.toggleRole = async function(userId, currentRole, email) {
    const newRole = currentRole === 'admin' ? 'user' : 'admin';
    if (!confirm(`Change role for ${email} from ${currentRole.toUpperCase()} to ${newRole.toUpperCase()}?`)) return;
    try {
        await api.updateUserRole(userId, newRole);
        app.showToast(`User ${email} is now ${newRole.toUpperCase()}`, 'success');
        await loadAdminData();
    } catch (e) {
        app.showToast('Failed to change role: ' + e.message, 'error');
    }
};

window.deleteUserAccount = async function(userId, email) {
    if (!confirm(`Are you sure you want to permanently delete user account ${email}? This action cannot be undone.`)) return;
    try {
        await api.deleteUser(userId);
        app.showToast(`User ${email} deleted`, 'success');
        await loadAdminData();
    } catch (e) {
        app.showToast('Failed to delete: ' + e.message, 'error');
    }
};

function renderSearchesChart(data) {
    const ctx = document.getElementById('searchesChart')?.getContext('2d');
    if (!ctx) return;
    app.destroyChart('searches');
    app.saveChart('searches', new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => d.date ? d.date.slice(5) : ''),
            datasets: [{
                label: 'Searches',
                data: data.map(d => d.count),
                borderColor: '#f59e0b',
                backgroundColor: 'rgba(245,158,11,.1)',
                fill: true,
                tension: 0.3,
                pointRadius: 3,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#71717a' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#71717a' } },
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
                label: 'Queries',
                data: data.map(d => d.count),
                backgroundColor: '#3b82f6',
                borderRadius: 4,
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#71717a' } },
                y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#71717a' } },
            }
        }
    }));
}

function setText(id, val) { 
    const e = document.getElementById(id); 
    if (e) e.textContent = val ?? '—'; 
}
