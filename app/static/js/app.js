function getToken() {
    return localStorage.getItem('token');
}

function getUser() {
    const u = localStorage.getItem('user');
    return u ? JSON.parse(u) : null;
}

function logout() {
    fetch('/auth/api/logout', { method: 'POST' }).then(() => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/auth/login';
    });
}

async function fetchWithAuth(url, options = {}) {
    const token = getToken();
    if (!token) {
        window.location.href = '/auth/login';
        return null;
    }
    const headers = {
        'Authorization': 'Bearer ' + token,
        ...options.headers
    };
    const res = await fetch(url, { ...options, headers });
    if (res.status === 401) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/auth/login';
        return null;
    }
    return res;
}

async function apiGet(url) {
    const res = await fetchWithAuth(url);
    if (!res) return null;
    return await res.json();
}

async function apiPost(url, data) {
    const res = await fetchWithAuth(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res) return null;
    const json = await res.json();
    return { ok: res.ok, status: res.status, data: json };
}

async function apiPut(url, data) {
    const res = await fetchWithAuth(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    if (!res) return null;
    const json = await res.json();
    return { ok: res.ok, status: res.status, data: json };
}

async function apiDelete(url) {
    const res = await fetchWithAuth(url, { method: 'DELETE' });
    if (!res) return null;
    return { ok: res.ok, status: res.status };
}

function formatDate(d) {
    if (!d) return '-';
    const dt = new Date(d);
    return dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatDateTime(d) {
    if (!d) return '-';
    const dt = new Date(d);
    return dt.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function statusBadge(status) {
    const map = {
        'registered': 'bg-info text-dark',
        'triaged': 'bg-primary',
        'analysis': 'bg-warning text-dark',
        'review': 'bg-purple text-white',
        'approved': 'bg-success',
        'reported': 'bg-dark',
        'cancelled': 'bg-danger',
        'pending': 'bg-secondary',
        'in_progress': 'bg-warning text-dark',
        'completed': 'bg-success'
    };
    return `<span class="badge ${map[status] || 'bg-secondary'}">${status.charAt(0).toUpperCase() + status.slice(1)}</span>`;
}

function priorityBadge(priority) {
    if (priority === 'urgent') return '<span class="badge bg-danger">Urgent</span>';
    return '<span class="badge bg-secondary">Routine</span>';
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer') || createToastContainer();
    const id = 'toast-' + Date.now();
    const icon = type === 'success' ? 'check-circle' : type === 'danger' ? 'exclamation-circle' : 'info-circle';
    const html = `
        <div id="${id}" class="toast align-items-center text-bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body"><i class="bi bi-${icon} me-2"></i>${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', html);
    const toastEl = document.getElementById(id);
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

function createToastContainer() {
    const div = document.createElement('div');
    div.id = 'toastContainer';
    div.className = 'toast-container position-fixed top-0 end-0 p-3';
    div.style.zIndex = '9999';
    document.body.appendChild(div);
    return div;
}

function showModal(title, bodyHtml, footerHtml) {
    let modal = document.getElementById('appModal');
    if (!modal) {
        const html = `
        <div class="modal fade" id="appModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"></h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body"></div>
                    <div class="modal-footer"></div>
                </div>
            </div>
        </div>`;
        document.body.insertAdjacentHTML('beforeend', html);
        modal = document.getElementById('appModal');
    }
    modal.querySelector('.modal-title').textContent = title;
    modal.querySelector('.modal-body').innerHTML = bodyHtml;
    modal.querySelector('.modal-footer').innerHTML = footerHtml || '<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>';
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
    return bsModal;
}

function confirmAction(message) {
    return new Promise(resolve => {
        const body = `<p class="mb-0">${message}</p>`;
        const footer = `
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
            <button type="button" class="btn btn-danger" id="confirmBtn">Confirm</button>
        `;
        const bsModal = showModal('Confirm', body, footer);
        document.getElementById('confirmBtn').addEventListener('click', () => {
            bsModal.hide();
            resolve(true);
        });
    });
}
