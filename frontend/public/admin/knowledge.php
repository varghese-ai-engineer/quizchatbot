<?php
declare(strict_types=1);
require_once __DIR__ . '/../../src/Auth.php';
require_once __DIR__ . '/../../src/Database.php';
Auth::requireLogin();
// Simple admin check
if (($_SESSION['role'] ?? 'user') !== 'admin') {
    header('Location: /chat.php'); exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Knowledge Base — Admin</title>
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
    <a href="/admin/knowledge.php" class="active"><i class="bi bi-book-half me-1"></i>Knowledge Base</a>
    <a href="/admin/users.php"><i class="bi bi-people me-1"></i>Users</a>
    <a href="/admin/quiz_config.php"><i class="bi bi-gear me-1"></i>Quiz Config</a>
    <a href="/chat.php"><i class="bi bi-arrow-left me-1"></i>Back to Chat</a>
  </div>
</nav>

<div class="admin-container">

  <!-- Header + Actions -->
  <div class="admin-page-header">
    <div>
      <h1 class="admin-page-title"><i class="bi bi-book-half me-2"></i>Knowledge Base</h1>
      <p class="admin-page-sub">Manage AI knowledge files, domains, and per-file language rules.</p>
    </div>
    <div class="d-flex gap-2">
      <button class="btn-admin-primary" onclick="document.getElementById('upload-input').click()">
        <i class="bi bi-cloud-upload me-1"></i>Upload .md File
      </button>
      <input type="file" id="upload-input" style="display:none" onchange="handleFileSelect(this)">
    </div>
  </div>

  <!-- Upload Progress -->
  <div id="upload-progress" class="upload-progress d-none">
    <div class="upload-bar"><div class="upload-fill" id="upload-fill"></div></div>
    <span id="upload-status">Uploading...</span>
  </div>

  <!-- Global AI Instructions -->
  <div class="admin-card mb-4">
    <div class="admin-card-header">
      <i class="bi bi-globe2 me-2"></i>Global AI Instructions
      <span class="badge-info ms-2">Applies to all chats</span>
    </div>
    <div class="admin-card-body">
      <textarea id="global-instruction" class="admin-textarea" rows="4"
        placeholder="Enter global AI behavior rules..."></textarea>
      <button class="btn-admin-primary mt-2" onclick="saveGlobalInstructions()">
        <i class="bi bi-save me-1"></i>Save
      </button>
      <span id="global-save-status" class="ms-2 text-success d-none">✓ Saved</span>
    </div>
  </div>

  <!-- Knowledge Files Table -->
  <div class="admin-card">
    <div class="admin-card-header"><i class="bi bi-table me-2"></i>Indexed Files</div>
    <div class="admin-card-body p-0">
      <div class="table-wrapper">
        <table class="admin-table" id="knowledge-table">
          <thead>
            <tr>
              <th>File</th><th>Domain</th><th>Topics</th><th>Keywords</th>
              <th>AI Language Rules</th><th>Chunks</th><th>Indexed At</th>
              <th>Status</th><th>Actions</th>
            </tr>
          </thead>
          <tbody id="knowledge-tbody">
            <tr><td colspan="9" class="text-center text-muted py-4">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>

<!-- Edit Rules Modal -->
<div class="admin-modal-overlay d-none" id="rules-modal">
  <div class="admin-modal">
    <div class="admin-modal-header">
      <span id="rules-modal-title">Edit AI Language Rules</span>
      <button onclick="closeRulesModal()"><i class="bi bi-x-lg"></i></button>
    </div>
    <div class="admin-modal-body">
      <input type="hidden" id="rules-filename">
      <label class="admin-label">AI Language Rules (one rule per line):</label>
      <textarea id="rules-textarea" class="admin-textarea" rows="10"
        placeholder="e.g. Keep player names in English&#10;Use Tamil cricket terms naturally"></textarea>
    </div>
    <div class="admin-modal-footer">
      <button class="btn-admin-outline" onclick="closeRulesModal()">Cancel</button>
      <button class="btn-admin-primary" onclick="saveRules()">
        <i class="bi bi-save me-1"></i>Save Rules
      </button>
    </div>
  </div>
</div>

<script>
const API = 'http://localhost:8100/api/admin';
const KEY = 'admin123';
const H   = { 'Content-Type': 'application/json', 'X-Admin-Key': KEY };

// ── Load knowledge files ──────────────────────────────────────
async function loadKnowledge() {
  const tbody = document.getElementById('knowledge-tbody');
  try {
    const r = await fetch(`${API}/knowledge/list`, { headers: H });
    const rows = await r.json();
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted py-4">No files indexed yet.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(row => {
      const topics   = tryParse(row.topics_json, []).slice(0,3).join(', ') || '—';
      const keywords = tryParse(row.keywords_json, []).slice(0,5).join(', ') || '—';
      const rules    = row.ai_language_rules ? row.ai_language_rules.substring(0,60)+'…' : '—';
      const status   = row.status === 'indexed'
        ? '<span class="badge-success">indexed</span>'
        : row.status === 'pending'
          ? '<span class="badge-warning">pending</span>'
          : '<span class="badge-danger">error</span>';
      return `<tr>
        <td><strong>${row.filename}</strong></td>
        <td><span class="domain-badge">${row.domain_name}</span></td>
        <td class="text-muted small">${topics}</td>
        <td class="text-muted small">${keywords}</td>
        <td class="text-muted small" title="${row.ai_language_rules || ''}">${rules}</td>
        <td class="text-center">${row.chunk_count}</td>
        <td class="text-muted small">${row.indexed_at ? row.indexed_at.substring(0,16) : '—'}</td>
        <td>${status}</td>
        <td>
          <button class="btn-icon" title="Edit Rules" onclick='openRulesModal(${JSON.stringify(row.filename)}, ${JSON.stringify(row.ai_language_rules||"")})'>
            <i class="bi bi-pencil"></i>
          </button>
          <button class="btn-icon btn-icon-warn" title="Re-index" onclick='reindex(${JSON.stringify(row.filename)})'>
            <i class="bi bi-arrow-repeat"></i>
          </button>
          <button class="btn-icon btn-icon-danger" title="Delete" onclick='deleteFile(${JSON.stringify(row.filename)})'>
            <i class="bi bi-trash"></i>
          </button>
        </td>
      </tr>`;
    }).join('');
  } catch(e) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger py-4">${e.message}</td></tr>`;
  }
}

function tryParse(s, fallback) {
  try { return JSON.parse(s) || fallback; } catch { return fallback; }
}

// ── File Select — validate before upload ─────────────────────
function handleFileSelect(input) {
  const file = input.files[0];
  if (!file) return;

  // Validate .md extension immediately at select time
  if (!file.name.toLowerCase().endsWith('.md')) {
    showUploadError(`"${file.name}" is not a .md file. Please select a Markdown (.md) file.`);
    input.value = '';
    return;
  }

  // Valid — proceed to upload
  uploadFile(input, file);
}

function showUploadError(msg) {
  const progress = document.getElementById('upload-progress');
  const fill     = document.getElementById('upload-fill');
  const status   = document.getElementById('upload-status');
  progress.classList.remove('d-none');
  fill.style.width = '100%';
  fill.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
  status.textContent = '✗ ' + msg;
  status.style.color = '#ef4444';
  setTimeout(() => {
    progress.classList.add('d-none');
    fill.style.background = '';
    status.style.color = '';
  }, 4000);
}

// ── Upload ────────────────────────────────────────────────────
async function uploadFile(input, file) {
  if (!file) return;
  const progress = document.getElementById('upload-progress');
  const fill     = document.getElementById('upload-fill');
  const status   = document.getElementById('upload-status');
  progress.classList.remove('d-none');
  fill.style.width = '30%';
  status.textContent = `Uploading ${file.name}...`;

  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await fetch(`${API}/knowledge/upload`, {
      method: 'POST', headers: { 'X-Admin-Key': KEY }, body: fd
    });
    fill.style.width = '70%';
    status.textContent = 'Indexing in background...';
    setTimeout(() => {
      fill.style.width = '100%';
      status.textContent = '✓ Done!';
      setTimeout(() => progress.classList.add('d-none'), 2000);
      loadKnowledge();
    }, 3000);
  } catch(e) {
    showUploadError(e.message);
  }
  input.value = '';
}

// ── Delete ────────────────────────────────────────────────────
async function deleteFile(filename) {
  if (!confirm(`Delete "${filename}" and all its vectors?`)) return;
  await fetch(`${API}/knowledge/${encodeURIComponent(filename)}`,
    { method: 'DELETE', headers: H });
  loadKnowledge();
}

// ── Re-index ─────────────────────────────────────────────────
async function reindex(filename) {
  if (!confirm(`Re-index "${filename}"?`)) return;
  await fetch(`${API}/knowledge/reindex/${encodeURIComponent(filename)}`,
    { method: 'POST', headers: H });
  alert('Re-indexing started in background.');
  setTimeout(loadKnowledge, 5000);
}

// ── Rules modal ───────────────────────────────────────────────
function openRulesModal(filename, rules) {
  document.getElementById('rules-filename').value = filename;
  document.getElementById('rules-textarea').value = rules;
  document.getElementById('rules-modal-title').textContent = `Edit AI Rules — ${filename}`;
  document.getElementById('rules-modal').classList.remove('d-none');
}
function closeRulesModal() {
  document.getElementById('rules-modal').classList.add('d-none');
}
async function saveRules() {
  const filename = document.getElementById('rules-filename').value;
  const rules    = document.getElementById('rules-textarea').value;
  await fetch(`${API}/knowledge/rules`, {
    method: 'PUT', headers: H,
    body: JSON.stringify({ filename, ai_language_rules: rules })
  });
  closeRulesModal();
  loadKnowledge();
}

// ── Global instructions ───────────────────────────────────────
async function loadGlobalInstructions() {
  const r = await fetch(`${API}/settings/global`, { headers: H });
  const d = await r.json();
  document.getElementById('global-instruction').value = d.global_special_instruction || '';
}
async function saveGlobalInstructions() {
  const inst = document.getElementById('global-instruction').value;
  await fetch(`${API}/settings/global`, {
    method: 'PUT', headers: H,
    body: JSON.stringify({ global_special_instruction: inst })
  });
  const s = document.getElementById('global-save-status');
  s.classList.remove('d-none');
  setTimeout(() => s.classList.add('d-none'), 2000);
}

// ── Init ──────────────────────────────────────────────────────
loadKnowledge();
loadGlobalInstructions();
</script>
</body>
</html>
