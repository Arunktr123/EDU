/**
 * SUPERNATURAL — Main Frontend JavaScript
 * Handles: chip selection, auth state, shared utilities
 */

// ── Chip Selector Initialization ─────────────────────────────────────────────
document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => chip.classList.toggle('active'));
});

// ── Auth State Management ─────────────────────────────────────────────────────
const token = localStorage.getItem('token');
const role  = localStorage.getItem('role');

if (token) {
    // Hide login/register, show logout
    const navAuth = document.getElementById('nav-auth');
    const logoutBtn = document.getElementById('logout-btn');
    if (navAuth)   navAuth.style.display = 'none';
    if (logoutBtn) logoutBtn.style.display = 'inline';
}

document.getElementById('logout-btn')?.addEventListener('click', () => {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    window.location.href = '/';
});

// ── Register Page Role Detection ──────────────────────────────────────────────
const urlRole = new URLSearchParams(window.location.search).get('role');
if (urlRole === 'mentor') {
    window.location.href = '/register/mentor';
} else if (urlRole === 'student') {
    window.location.href = '/register/student';
}

// ── Shared API Utility ─────────────────────────────────────────────────────────
window.apiFetch = async function(url, method = 'GET', body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const storedToken = localStorage.getItem('token');
    if (storedToken) headers['Authorization'] = `Bearer ${storedToken}`;
    
    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);
    
    const res = await fetch(url, options);
    if (res.status === 401) {
        localStorage.clear();
        window.location.href = '/login';
    }
    return res;
};

// ── Toast Notifications ────────────────────────────────────────────────────────
window.showToast = function(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position:fixed; bottom:24px; right:24px;
        background:${type === 'success' ? '#28c76f' : '#ea5455'};
        color:white; padding:12px 20px;
        border-radius:12px; font-size:.9rem;
        font-family:Inter,sans-serif;
        box-shadow:0 4px 20px rgba(0,0,0,.3);
        z-index:9999; animation:slideIn .3s ease;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
};
