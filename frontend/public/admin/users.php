<?php
declare(strict_types=1);
require_once __DIR__ . '/../../src/Auth.php';
Auth::requireLogin();
if (($_SESSION['role'] ?? 'user') !== 'admin') {
    header('Location: /chat.php'); exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>User Management — Admin</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
<link rel="stylesheet" href="/assets/css/admin.css?v=3">
</head>
<body>

<nav class="admin-nav">
  <div class="admin-brand"><i class="bi bi-shield-check me-2"></i>Admin Panel</div>
  <div class="admin-nav-links">
    <a href="/admin/knowledge.php"><i class="bi bi-book-half me-1"></i>Knowledge Base</a>
    <a href="/admin/users.php" class="active"><i class="bi bi-people me-1"></i>Users</a>
    <a href="/admin/quiz_config.php"><i class="bi bi-gear me-1"></i>Quiz Config</a>
    <a href="/chat.php"><i class="bi bi-arrow-left me-1"></i>Back to Chat</a>
  </div>
</nav>

<div class="admin-container">

  <div class="admin-page-header">
    <div>
      <h1 class="admin-page-title"><i class="bi bi-people me-2"></i>User Management</h1>
      <p class="admin-page-sub">View, edit credits, and manage user access.</p>
    </div>
    <div class="d-flex gap-2">
      <button class="btn-admin-outline" id="reset-credits-btn" onclick="openResetCreditsModal()">
        <i class="bi bi-arrow-counterclockwise me-1"></i>Reset All Credits
      </button>
      <button class="btn-admin-primary" id="create-user-btn" onclick="openCreateUserModal()">
        <i class="bi bi-person-plus me-1"></i>Create User
      </button>
    </div>
  </div>

  <!-- Search + Filter -->
  <div class="admin-card mb-4">
    <div class="admin-card-body d-flex gap-3 align-items-center flex-wrap">
      <input type="text" id="search-input" class="admin-input" placeholder="Search by name, email, username…"
        oninput="debounceSearch()" style="max-width:320px;">
      <span id="user-count" class="text-muted small"></span>
    </div>
  </div>

  <!-- Users Table -->
  <div class="admin-card">
    <div class="admin-card-body p-0">
      <div class="table-wrapper">
        <table class="admin-table">
          <thead>
            <tr>
              <th>User</th><th>Email</th><th>Language</th>
              <th>Total Credits</th><th>Used Credits</th><th>Balance</th>
              <th>Best Quiz</th><th>Status</th><th>Role</th><th>Actions</th>
            </tr>
          </thead>
          <tbody id="users-tbody">
            <tr><td colspan="10" class="text-center text-muted py-4">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- Pagination -->
  <div class="d-flex justify-content-center gap-2 mt-3" id="pagination"></div>
</div>

<!-- Edit Credits Modal -->
<div class="admin-modal-overlay d-none" id="credits-modal">
  <div class="admin-modal" style="max-width:420px">
    <div class="admin-modal-header">
      <span>Edit Credits — <span id="credits-username"></span></span>
      <button onclick="closeCreditsModal()"><i class="bi bi-x-lg"></i></button>
    </div>
    <div class="admin-modal-body">
      <input type="hidden" id="credits-user-id">
      <label class="admin-label">New Balance Credits:</label>
      <input type="number" id="credits-input" class="admin-input" min="0" max="99999">
    </div>
    <div class="admin-modal-footer">
      <button class="btn-admin-outline" onclick="closeCreditsModal()">Cancel</button>
      <button class="btn-admin-primary" onclick="saveCredits()">
        <i class="bi bi-save me-1"></i>Save
      </button>
    </div>
  </div>
</div>

<!-- Chat History Modal -->
<div class="admin-modal-overlay d-none" id="history-modal">
  <div class="admin-modal" style="max-width:700px">
    <div class="admin-modal-header">
      <span>Chat History — <span id="history-username"></span></span>
      <button onclick="closeHistoryModal()"><i class="bi bi-x-lg"></i></button>
    </div>
    <div class="admin-modal-body" style="max-height:500px;overflow-y:auto">
      <div id="history-content" class="text-muted small">Loading...</div>
    </div>
  </div>
</div>

<!-- Create User Modal -->
<div class="admin-modal-overlay d-none" id="create-user-modal">
  <div class="admin-modal" style="max-width:480px">
    <div class="admin-modal-header">
      <span><i class="bi bi-person-plus me-2"></i>Create New User</span>
      <button onclick="closeCreateUserModal()"><i class="bi bi-x-lg"></i></button>
    </div>
    <div class="admin-modal-body">
      <div id="create-user-error" class="admin-alert-error d-none mb-3"></div>
      <div class="row g-3">
        <div class="col-6">
          <label class="admin-label">Full Name *</label>
          <input type="text" id="cu-fullname" class="admin-input" placeholder="John Doe">
        </div>
        <div class="col-6">
          <label class="admin-label">Username *</label>
          <input type="text" id="cu-username" class="admin-input" placeholder="johndoe">
        </div>
        <div class="col-12">
          <label class="admin-label">Email *</label>
          <input type="email" id="cu-email" class="admin-input" placeholder="john@example.com">
        </div>
        <div class="col-12">
          <label class="admin-label">Password *</label>
          <input type="password" id="cu-password" class="admin-input" placeholder="Min 6 characters">
        </div>
        <div class="col-6">
          <label class="admin-label">Role</label>
          <select id="cu-role" class="admin-input">
            <option value="user">User</option>
            <option value="admin">Admin</option>
          </select>
        </div>
        <div class="col-6">
          <label class="admin-label">Starting Credits</label>
          <input type="number" id="cu-credits" class="admin-input" value="100" min="0" max="99999">
        </div>
      </div>
    </div>
    <div class="admin-modal-footer">
      <button class="btn-admin-outline" onclick="closeCreateUserModal()">Cancel</button>
      <button class="btn-admin-primary" id="cu-submit-btn" onclick="submitCreateUser()">
        <i class="bi bi-person-check me-1"></i>Create User
      </button>
    </div>
  </div>
</div>

<!-- Reset Credits Modal -->
<div class="admin-modal-overlay d-none" id="reset-credits-modal">
  <div class="admin-modal" style="max-width:400px">
    <div class="admin-modal-header">
      <span><i class="bi bi-arrow-counterclockwise me-2"></i>Reset All Credits</span>
      <button onclick="closeResetCreditsModal()"><i class="bi bi-x-lg"></i></button>
    </div>
    <div class="admin-modal-body">
      <p class="text-muted small mb-3">This will reset credits for <strong>all regular users</strong> to the specified amount. Admin accounts are not affected.</p>
      <label class="admin-label">Reset Credits To:</label>
      <input type="number" id="reset-credits-input" class="admin-input" value="100" min="0" max="99999">
    </div>
    <div class="admin-modal-footer">
      <button class="btn-admin-outline" onclick="closeResetCreditsModal()">Cancel</button>
      <button class="btn-admin-primary" style="background:linear-gradient(135deg,#f59e0b,#d97706)" onclick="submitResetCredits()">
        <i class="bi bi-arrow-counterclockwise me-1"></i>Reset Credits
      </button>
    </div>
  </div>
</div>

<!-- Edit User Modal -->
<div class="admin-modal-overlay d-none" id="edit-user-modal">
  <div class="admin-modal" style="max-width:480px">
    <div class="admin-modal-header">
      <span><i class="bi bi-pencil me-2"></i>Edit User</span>
      <button onclick="closeEditUserModal()"><i class="bi bi-x-lg"></i></button>
    </div>
    <div class="admin-modal-body">
      <div id="edit-user-error" class="admin-alert-error d-none mb-3"></div>
      <input type="hidden" id="eu-id">
      <div class="row g-3">
        <div class="col-6">
          <label class="admin-label">Full Name *</label>
          <input type="text" id="eu-fullname" class="admin-input" placeholder="John Doe">
        </div>
        <div class="col-6">
          <label class="admin-label">Username *</label>
          <input type="text" id="eu-username" class="admin-input" placeholder="johndoe">
        </div>
        <div class="col-12">
          <label class="admin-label">Email *</label>
          <input type="email" id="eu-email" class="admin-input" placeholder="john@example.com">
        </div>
        <div class="col-12">
          <label class="admin-label">New Password <span class="text-muted">(leave blank to keep)</span></label>
          <input type="password" id="eu-password" class="admin-input" placeholder="Optional">
        </div>
      </div>
    </div>
    <div class="admin-modal-footer">
      <button class="btn-admin-outline" onclick="closeEditUserModal()">Cancel</button>
      <button class="btn-admin-primary" id="eu-submit-btn" onclick="submitEditUser()">
        <i class="bi bi-check2 me-1"></i>Save Changes
      </button>
    </div>
  </div>
</div>

<script>
const API  = 'http://localhost:8100/api/admin';
const KEY  = 'admin123';
const H    = { 'Content-Type': 'application/json', 'X-Admin-Key': KEY };
let currentPage = 1;
let searchTimer = null;

const langFlag = { en: '🇬🇧', ta: '🇮🇳 Ta', hi: '🇮🇳 Hi' };

async function loadUsers(page = 1, search = '') {
  currentPage = page;
  const tbody = document.getElementById('users-tbody');
  tbody.innerHTML = '<tr><td colspan="10" class="text-center py-4"><div class="spinner"></div></td></tr>';
  const r = await fetch(`${API}/users/list?page=${page}&per_page=15&search=${encodeURIComponent(search)}`, { headers: H });
  const rows = await r.json();
  document.getElementById('user-count').textContent = `${rows.length} users`;

  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="text-center text-muted py-4">No users found.</td></tr>';
    return;
  }

  tbody.innerHTML = rows.map(u => {
    const activeClass = u.is_active ? '' : 'row-inactive';
    const statusBadge = u.is_active
      ? '<span class="badge-success">Active</span>'
      : '<span class="badge-danger">Blocked</span>';
    const roleBadge = u.role === 'admin'
      ? '<span class="badge-info">Admin</span>'
      : '<span class="badge-outline">User</span>';
    const toggleTitle  = u.is_active ? 'Block User' : 'Unblock User';
    const toggleIcon   = u.is_active ? 'bi-slash-circle' : 'bi-check-circle';
    const toggleClass  = u.is_active ? 'btn-icon-danger' : 'btn-icon-success';
    const bestQuiz     = u.best_quiz_score !== null ? u.best_quiz_score : '—';
    return `<tr class="${activeClass}">
      <td><strong>${u.full_name}</strong><br><small class="text-muted">@${u.username}</small></td>
      <td class="small">${u.email}</td>
      <td>${langFlag[u.language] || u.language}</td>
      <td class="text-center">${u.total_credits}</td>
      <td class="text-center">${u.used_credits}</td>
      <td class="text-center"><strong>${u.balance_credits}</strong></td>
      <td class="text-center">${bestQuiz}</td>
      <td>${statusBadge}</td>
      <td>${roleBadge}</td>
      <td>
        <button class="btn-icon" title="Edit Credits"
          onclick='openCreditsModal(${u.id}, ${JSON.stringify(u.full_name)}, ${u.balance_credits})'>
          <i class="bi bi-lightning-charge"></i>
        </button>
        <button class="btn-icon" title="Edit User"
          onclick='openEditUserModal(${JSON.stringify(u)})'>
          <i class="bi bi-pencil"></i>
        </button>
        <button class="btn-icon ${toggleClass}" title="${toggleTitle}"
          onclick='toggleUser(${u.id}, ${u.is_active ? 0 : 1})'>
          <i class="bi ${toggleIcon}"></i>
        </button>
        <button class="btn-icon" title="Chat History" onclick='openHistoryModal(${u.id}, ${JSON.stringify(u.full_name)})'>
          <i class="bi bi-chat-left-dots"></i>
        </button>
        <button class="btn-icon btn-icon-danger" title="Delete User"
          onclick='deleteUser(${u.id}, ${JSON.stringify(u.full_name)})'>
          <i class="bi bi-trash"></i>
        </button>
      </td>
    </tr>`;
  }).join('');
}

function debounceSearch() {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    loadUsers(1, document.getElementById('search-input').value);
  }, 400);
}

// ── Credits Modal ─────────────────────────────────────────────
function openCreditsModal(id, name, current) {
  document.getElementById('credits-user-id').value = id;
  document.getElementById('credits-username').textContent = name;
  document.getElementById('credits-input').value = current;
  document.getElementById('credits-modal').classList.remove('d-none');
}
function closeCreditsModal() { document.getElementById('credits-modal').classList.add('d-none'); }
async function saveCredits() {
  const uid  = parseInt(document.getElementById('credits-user-id').value);
  const cred = parseInt(document.getElementById('credits-input').value);
  await fetch(`${API}/users/credits`, { method: 'PUT', headers: H, body: JSON.stringify({ user_id: uid, credits: cred }) });
  closeCreditsModal();
  loadUsers(currentPage, document.getElementById('search-input').value);
}

// ── Toggle User ───────────────────────────────────────────────
async function toggleUser(uid, newState) {
  if (!confirm(newState ? 'Unblock this user?' : 'Block this user?')) return;
  await fetch(`${API}/users/toggle`, { method: 'PUT', headers: H, body: JSON.stringify({ user_id: uid, is_active: newState }) });
  loadUsers(currentPage, document.getElementById('search-input').value);
}

// ── Chat History Modal ────────────────────────────────────────
async function openHistoryModal(uid, name) {
  document.getElementById('history-username').textContent = name;
  document.getElementById('history-content').innerHTML = '<div class="spinner"></div>';
  document.getElementById('history-modal').classList.remove('d-none');
  const r    = await fetch(`${API}/users/${uid}/chat-history`, { headers: H });
  const rows = await r.json();
  if (!rows.length) {
    document.getElementById('history-content').innerHTML = '<em>No chat history yet.</em>';
    return;
  }
  document.getElementById('history-content').innerHTML = rows.map(r => `
    <div class="history-row history-${r.role}">
      <span class="history-role">${r.role === 'user' ? '👤' : '🤖'}</span>
      <span class="history-msg">${r.message.substring(0,200)}</span>
      <span class="history-time">${r.created_at.substring(0,16)}</span>
    </div>
  `).join('');
}
function closeHistoryModal() { document.getElementById('history-modal').classList.add('d-none'); }

// ── Edit User ─────────────────────────────────────────────
function openEditUserModal(u) {
  document.getElementById('edit-user-error').classList.add('d-none');
  document.getElementById('eu-id').value       = u.id;
  document.getElementById('eu-fullname').value = u.full_name;
  document.getElementById('eu-username').value = u.username;
  document.getElementById('eu-email').value    = u.email;
  document.getElementById('eu-password').value = '';
  document.getElementById('edit-user-modal').classList.remove('d-none');
}
function closeEditUserModal() { document.getElementById('edit-user-modal').classList.add('d-none'); }

async function submitEditUser() {
  const id       = parseInt(document.getElementById('eu-id').value);
  const fullName = document.getElementById('eu-fullname').value.trim();
  const username = document.getElementById('eu-username').value.trim();
  const email    = document.getElementById('eu-email').value.trim();
  const password = document.getElementById('eu-password').value;
  const errBox   = document.getElementById('edit-user-error');

  if (!fullName || !username || !email) {
    errBox.textContent = 'Full name, username and email are required.';
    errBox.classList.remove('d-none');
    return;
  }
  if (password && password.length < 6) {
    errBox.textContent = 'New password must be at least 6 characters.';
    errBox.classList.remove('d-none');
    return;
  }

  const btn = document.getElementById('eu-submit-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Saving...';

  const payload = { user_id: id, full_name: fullName, username, email };
  if (password) payload.password = password;

  try {
    const r = await fetch(`${API}/users/update`, {
      method: 'PUT', headers: H, body: JSON.stringify(payload)
    });
    const data = await r.json();
    if (!r.ok) {
      errBox.textContent = data.detail || 'Failed to update user.';
      errBox.classList.remove('d-none');
      return;
    }
    closeEditUserModal();
    loadUsers(currentPage, document.getElementById('search-input').value);
  } catch(e) {
    errBox.textContent = `Error: ${e.message}`;
    errBox.classList.remove('d-none');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Save Changes';
  }
}

// ── Delete User ──────────────────────────────────────────
function deleteUser(id, name) {
  if (!confirm(`Permanently delete "${name}"? This cannot be undone.`)) return;
  fetch(`${API}/users/${id}`, { method: 'DELETE', headers: H })
    .then(r => r.json())
    .then(() => loadUsers(currentPage, document.getElementById('search-input').value))
    .catch(e => alert('Delete failed: ' + e.message));
}

// ── Create User ───────────────────────────────────────────────
function openCreateUserModal() {
  document.getElementById('create-user-error').classList.add('d-none');
  document.getElementById('cu-fullname').value = '';
  document.getElementById('cu-username').value = '';
  document.getElementById('cu-email').value = '';
  document.getElementById('cu-password').value = '';
  document.getElementById('cu-role').value = 'user';
  document.getElementById('cu-credits').value = 100;
  document.getElementById('create-user-modal').classList.remove('d-none');
}
function closeCreateUserModal() { document.getElementById('create-user-modal').classList.add('d-none'); }

async function submitCreateUser() {
  const fullName = document.getElementById('cu-fullname').value.trim();
  const username = document.getElementById('cu-username').value.trim();
  const email    = document.getElementById('cu-email').value.trim();
  const password = document.getElementById('cu-password').value;
  const role     = document.getElementById('cu-role').value;
  const credits  = parseInt(document.getElementById('cu-credits').value) || 100;
  const errBox   = document.getElementById('create-user-error');

  // Client-side validation
  if (!fullName || !username || !email || !password) {
    errBox.textContent = 'Please fill in all required fields.';
    errBox.classList.remove('d-none');
    return;
  }
  if (password.length < 6) {
    errBox.textContent = 'Password must be at least 6 characters.';
    errBox.classList.remove('d-none');
    return;
  }

  const btn = document.getElementById('cu-submit-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Creating...';

  try {
    const r = await fetch(`${API}/users/create`, {
      method: 'POST', headers: H,
      body: JSON.stringify({ username, email, password, full_name: fullName, role, credits })
    });
    const data = await r.json();
    if (!r.ok) {
      errBox.textContent = data.detail || 'Failed to create user.';
      errBox.classList.remove('d-none');
      return;
    }
    closeCreateUserModal();
    loadUsers(currentPage, document.getElementById('search-input').value);
  } catch(e) {
    errBox.textContent = `Error: ${e.message}`;
    errBox.classList.remove('d-none');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-person-check me-1"></i>Create User';
  }
}

// ── Reset All Credits ─────────────────────────────────────────
function openResetCreditsModal() {
  document.getElementById('reset-credits-input').value = 100;
  document.getElementById('reset-credits-modal').classList.remove('d-none');
}
function closeResetCreditsModal() { document.getElementById('reset-credits-modal').classList.add('d-none'); }

async function submitResetCredits() {
  const credits = parseInt(document.getElementById('reset-credits-input').value);
  if (isNaN(credits) || credits < 0) {
    alert('Please enter a valid credit amount (0 or more).');
    return;
  }
  if (!confirm(`Reset ALL user credits to ${credits}? This cannot be undone.`)) return;

  const r = await fetch(`${API}/users/reset-credits`, {
    method: 'POST', headers: H,
    body: JSON.stringify({ credits })
  });
  const data = await r.json();
  closeResetCreditsModal();
  loadUsers(currentPage, document.getElementById('search-input').value);
  alert(data.message || 'Credits reset successfully.');
}

// ── Init ──────────────────────────────────────────────────────
loadUsers();
</script>
</body>
</html>
