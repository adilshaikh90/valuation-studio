document.addEventListener('DOMContentLoaded', () => {
    // ── Login form ────────────────────────────────────────
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email    = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const btn      = loginForm.querySelector('button[type="submit"]');
            const errEl    = document.getElementById('auth-error');

            try {
                btn.disabled = true;
                btn.innerHTML = '<span class="loading" style="display:inline-block;width:16px;height:16px;margin-right:8px;border-width:2px;vertical-align:middle;"></span> Logging in…';
                if (errEl) errEl.style.display = 'none';

                const res = await api.login(email, password);
                api.setToken(res.access_token);               // ← correct field
                localStorage.setItem('vs_user', JSON.stringify(res.user));

                app.showToast('Login successful!', 'success');
                setTimeout(() => { window.location.href = 'dashboard.html'; }, 400);

            } catch (err) {
                if (errEl) { errEl.textContent = err.message; errEl.style.display = 'block'; }
            } finally {
                btn.disabled = false;
                btn.innerHTML = 'Log In';
            }
        });
    }

    // ── Signup form ───────────────────────────────────────
    const signupForm = document.getElementById('signup-form');
    if (signupForm) {
        signupForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email    = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value;
            const confirm  = document.getElementById('confirm-password')?.value;
            const btn      = signupForm.querySelector('button[type="submit"]');
            const errEl    = document.getElementById('auth-error');

            if (confirm !== undefined && password !== confirm) {
                if (errEl) { errEl.textContent = 'Passwords do not match'; errEl.style.display = 'block'; }
                return;
            }

            try {
                btn.disabled = true;
                btn.innerHTML = '<span class="loading" style="display:inline-block;width:16px;height:16px;margin-right:8px;border-width:2px;vertical-align:middle;"></span> Creating account…';
                if (errEl) errEl.style.display = 'none';

                const res = await api.signup(email, password);
                api.setToken(res.access_token);               // ← correct field
                localStorage.setItem('vs_user', JSON.stringify(res.user));

                app.showToast('Account created!', 'success');
                setTimeout(() => { window.location.href = 'dashboard.html'; }, 400);

            } catch (err) {
                if (errEl) { errEl.textContent = err.message; errEl.style.display = 'block'; }
            } finally {
                btn.disabled = false;
                btn.innerHTML = 'Sign Up';
            }
        });
    }
});
