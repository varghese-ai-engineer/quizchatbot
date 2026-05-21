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
<title>Quiz Config — Admin</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
<link rel="stylesheet" href="/assets/css/admin.css?v=3">
<style>
.config-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 14px; padding: 2rem; }
.preview-box { background: var(--color-surface2); border: 1px solid var(--color-border); border-radius: 12px; padding: 1.25rem; }
.preview-row { display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid var(--color-border); }
.preview-row:last-child { border-bottom: none; }
.preview-label { color: var(--color-muted); font-size: 0.82rem; }
.preview-val   { font-weight: 600; font-size: 0.9rem; }
.pass-preview  { background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); border-radius: 10px; padding: 1rem; text-align: center; margin-top: 1rem; }
.pass-preview .big { font-size: 1.8rem; font-weight: 700; color: var(--color-success); }
.type-cards { display: flex; gap: 0.75rem; flex-wrap: wrap; }
.type-card { flex: 1; min-width: 130px; background: var(--color-surface2); border: 2px solid var(--color-border); border-radius: 12px; padding: 1rem; cursor: pointer; text-align: center; transition: all 0.2s; }
.type-card:hover { border-color: var(--color-primary); }
.type-card.selected { border-color: var(--color-primary); background: rgba(108,99,255,0.1); }
.type-card i { font-size: 1.5rem; display: block; margin-bottom: 0.4rem; }
.type-card span { font-size: 0.8rem; font-weight: 600; }
.save-success { color: var(--color-success); font-size: 0.85rem; }

/* ── Leniency Slider ── */
.leniency-wrap { padding: 0.25rem 0 0.5rem; }
.leniency-track {
  position: relative;
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 8px;
  border-radius: 99px;
  background: linear-gradient(to right, #ef4444 0%, #f59e0b 40%, #22c55e 100%);
  outline: none;
  cursor: pointer;
}
.leniency-track::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 22px; height: 22px;
  border-radius: 50%;
  background: #fff;
  border: 3px solid var(--color-primary);
  box-shadow: 0 2px 8px rgba(0,0,0,0.35);
  cursor: grab;
  transition: transform 0.15s;
}
.leniency-track::-webkit-slider-thumb:active { transform: scale(1.2); cursor: grabbing; }
.leniency-labels { display: flex; justify-content: space-between; font-size: 0.75rem; color: var(--color-muted); margin-top: 0.35rem; }
.leniency-badge {
  display: inline-flex; align-items: center; gap: 0.4rem;
  background: rgba(108,99,255,0.12); border: 1px solid rgba(108,99,255,0.25);
  border-radius: 99px; padding: 0.25rem 0.75rem;
  font-size: 0.78rem; font-weight: 600; color: var(--color-primary);
  margin-top: 0.75rem;
}
.threshold-row { display: flex; gap: 0.75rem; margin-top: 0.75rem; flex-wrap: wrap; }
.threshold-chip {
  flex: 1; min-width: 130px;
  background: var(--color-surface2); border: 1px solid var(--color-border);
  border-radius: 10px; padding: 0.6rem 0.9rem; font-size: 0.8rem;
}
.threshold-chip .tc-label { color: var(--color-muted); font-size: 0.72rem; margin-bottom: 0.2rem; }
.threshold-chip .tc-val   { font-weight: 700; font-size: 1rem; }
.tc-accept .tc-val { color: #22c55e; }
.tc-reject .tc-val { color: #ef4444; }
.tc-llm    .tc-val { color: #f59e0b; }

/* ── Debug Toggle ── */
.debug-card { background: rgba(108,99,255,0.06); border: 1px solid rgba(108,99,255,0.2); border-radius: 14px; padding: 1.5rem 2rem; }
.toggle-row  { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
.toggle-label h6 { font-weight: 600; margin-bottom: 0.2rem; font-size: 0.95rem; }
.toggle-label p  { font-size: 0.78rem; color: var(--color-muted); margin: 0; }
.toggle-pill {
  position: relative; width: 52px; height: 28px; flex-shrink: 0; cursor: pointer;
  background: var(--color-surface2); border: 1px solid var(--color-border);
  border-radius: 99px; transition: background 0.25s, border-color 0.25s;
}
.toggle-pill.on { background: var(--color-primary); border-color: var(--color-primary); }
.toggle-pill::after {
  content:''; position:absolute; top:3px; left:3px;
  width:20px; height:20px; border-radius:50%; background:#fff;
  transition: transform 0.25s; box-shadow: 0 1px 4px rgba(0,0,0,0.3);
}
.toggle-pill.on::after { transform: translateX(24px); }
.toggle-status { font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em; margin-top: 0.35rem; text-align:center; }
.toggle-status.on  { color: var(--color-primary); }
.toggle-status.off { color: var(--color-muted); }
</style>
</head>
<body>

<nav class="admin-nav">
  <div class="admin-brand"><i class="bi bi-shield-check me-2"></i>Admin Panel</div>
  <div class="admin-nav-links">
    <a href="/admin/knowledge.php"><i class="bi bi-book-half me-1"></i>Knowledge Base</a>
    <a href="/admin/users.php"><i class="bi bi-people me-1"></i>Users</a>
    <a href="/admin/quiz_config.php" class="active"><i class="bi bi-gear me-1"></i>Quiz Config</a>
    <a href="/chat.php"><i class="bi bi-arrow-left me-1"></i>Back to Chat</a>
  </div>
</nav>

<div class="admin-container">
  <div class="admin-page-header">
    <div>
      <h1 class="admin-page-title"><i class="bi bi-gear me-2"></i>Quiz Configuration</h1>
      <p class="admin-page-sub">Configure quiz rules, scoring, and intro message shown to users.</p>
    </div>
    <button class="btn-admin-primary" id="save-btn" onclick="saveConfig()">
      <i class="bi bi-save me-1"></i>Save Configuration
    </button>
  </div>

  <div class="row g-4">

    <!-- ── Left: Config Form ─────────────────────────────── -->
    <div class="col-lg-7">

      <!-- Question Type -->
      <div class="config-card mb-4">
        <h5 class="mb-3"><i class="bi bi-list-check me-2"></i>Question Type</h5>
        <div class="type-cards" id="type-cards">
          <div class="type-card selected" data-type="mcq" id="type-mcq" onclick="selectType('mcq')">
            <i class="bi bi-ui-radios text-primary"></i>
            <span>MCQ Only</span>
            <div class="text-muted" style="font-size:0.72rem;margin-top:0.3rem">Multiple choice — user picks A/B/C/D</div>
          </div>
          <div class="type-card" data-type="open" id="type-open" onclick="selectType('open')">
            <i class="bi bi-keyboard text-accent" style="color:var(--color-accent)"></i>
            <span>Open-Ended Only</span>
            <div class="text-muted" style="font-size:0.72rem;margin-top:0.3rem">User types answer — AI evaluates</div>
          </div>
          <div class="type-card" data-type="both" id="type-both" onclick="selectType('both')">
            <i class="bi bi-layers" style="color:var(--color-warn)"></i>
            <span>Both Types</span>
            <div class="text-muted" style="font-size:0.72rem;margin-top:0.3rem">Mix of MCQ and open questions</div>
          </div>
        </div>
        <input type="hidden" id="question-type" value="mcq">
      </div>

      <!-- Scoring Settings -->
      <div class="config-card mb-4">
        <h5 class="mb-3"><i class="bi bi-calculator me-2"></i>Scoring Settings</h5>
        <div class="row g-3">
          <div class="col-4">
            <label class="admin-label">Number of Questions</label>
            <input type="number" id="num-questions" class="admin-input" value="10" min="1" max="100" oninput="updatePreview()">
          </div>
          <div class="col-4">
            <label class="admin-label">Marks per Question</label>
            <input type="number" id="marks-per-q" class="admin-input" value="1" min="1" max="100" oninput="updatePreview()">
          </div>
          <div class="col-4">
            <label class="admin-label">Pass Mark (%)</label>
            <div style="position:relative">
              <input type="number" id="pass-mark-pct" class="admin-input" value="60" min="1" max="100" oninput="updatePreview()">
            </div>
          </div>
        </div>
      </div>

      <!-- Intro Text -->
      <div class="config-card">
        <h5 class="mb-2"><i class="bi bi-card-text me-2"></i>Intro Message</h5>
        <p class="text-muted small mb-3">This text is shown to users on the quiz introduction screen before they start.</p>
        <textarea id="intro-text" class="admin-textarea" rows="4"
          placeholder="Welcome to the quiz! Here's what you need to know..."></textarea>
      </div>

      <!-- Answer Leniency -->
      <div class="config-card mt-4">
        <h5 class="mb-1"><i class="bi bi-sliders me-2"></i>Answer Leniency</h5>
        <p class="text-muted small mb-3">
          Controls how strictly open-ended answers are evaluated.
          <strong>0 = exact answers only</strong>, <strong>100 = very flexible</strong> (abbreviations, nicknames, partials all accepted).
        </p>
        <div class="leniency-wrap">
          <input type="range" id="leniency-slider" class="leniency-track"
            min="0" max="100" step="1" value="50"
            oninput="updateLeniency(this.value)">
          <div class="leniency-labels">
            <span>🔒 Strict (0)</span>
            <span id="leniency-val-label">Balanced (50)</span>
            <span>🎯 Very Easy (100)</span>
          </div>
        </div>
        <div class="leniency-badge">
          <i class="bi bi-activity"></i>
          <span id="leniency-mode-text">Balanced — abbreviations &amp; nicknames accepted</span>
        </div>
        <div class="threshold-row">
          <div class="threshold-chip tc-accept">
            <div class="tc-label">✅ Auto CORRECT if score ≥</div>
            <div class="tc-val" id="tc-accept">85</div>
          </div>
          <div class="threshold-chip tc-llm">
            <div class="tc-label">🤖 LLM evaluates score</div>
            <div class="tc-val" id="tc-llm-zone">55 – 84</div>
          </div>
          <div class="threshold-chip tc-reject">
            <div class="tc-label">❌ Auto WRONG if score &lt;</div>
            <div class="tc-val" id="tc-reject">55</div>
          </div>
        </div>
      </div>

      <!-- Developer Settings -->
      <div class="debug-card mt-4" id="debug-section">
        <div class="d-flex align-items-center gap-2 mb-3">
          <i class="bi bi-bug text-primary" style="font-size:1.1rem"></i>
          <h5 class="mb-0">Developer Settings</h5>
          <span class="badge" style="background:rgba(108,99,255,0.15);color:var(--color-primary);font-size:0.7rem">Admin Only</span>
        </div>
        <div class="toggle-row">
          <div class="toggle-label">
            <h6><i class="bi bi-terminal me-1"></i>Show LLM Prompt Inspector</h6>
            <p>When ON, the exact prompt sent to the AI model appears in a popup each time the LLM is called — in both Chat and Quiz. Visible to admins only.</p>
          </div>
          <div style="text-align:center">
            <div class="toggle-pill" id="debug-toggle" onclick="togglePromptDebug()"></div>
            <div class="toggle-status off" id="debug-status">OFF</div>
          </div>
        </div>
      </div>

    </div>

    <!-- ── Right: Live Preview ───────────────────────────── -->
    <div class="col-lg-5">
      <div class="config-card" style="position:sticky;top:80px">
        <h5 class="mb-3"><i class="bi bi-eye me-2"></i>Live Preview</h5>
        <p class="text-muted small mb-3">This is what users will see on the quiz intro screen.</p>

        <!-- Preview card mimicking quiz intro -->
        <div style="background:var(--color-bg);border-radius:14px;padding:1.5rem;border:1px solid var(--color-border)">
          <div style="text-align:center;margin-bottom:1rem">
            <div style="width:56px;height:56px;background:rgba(108,99,255,0.15);border-radius:50%;display:flex;align-items:center;justify-content:center;margin:0 auto 0.75rem">
              <i class="bi bi-patch-question" style="font-size:1.5rem;color:var(--color-primary)"></i>
            </div>
            <h6 style="font-weight:700">IPL Cricket Quiz</h6>
          </div>

          <div class="preview-box mb-3">
            <div class="preview-row">
              <span class="preview-label">📝 Questions</span>
              <span class="preview-val" id="pv-questions">10</span>
            </div>
            <div class="preview-row">
              <span class="preview-label">⭐ Marks per Question</span>
              <span class="preview-val" id="pv-marks">1</span>
            </div>
            <div class="preview-row">
              <span class="preview-label">🏆 Total Marks</span>
              <span class="preview-val" id="pv-total">10</span>
            </div>
            <div class="preview-row">
              <span class="preview-label">🎯 Pass Mark</span>
              <span class="preview-val" id="pv-pass">6 marks (60%)</span>
            </div>
            <div class="preview-row">
              <span class="preview-label">🖊️ Question Type</span>
              <span class="preview-val" id="pv-type">Both MCQ & Open</span>
            </div>
          </div>

          <div class="pass-preview">
            <div class="big" id="pv-pass-big">6 / 10</div>
            <div class="text-muted small">marks needed to pass</div>
          </div>
        </div>
      </div>
    </div>

  </div>
</div>

<script>
const API = 'http://localhost:8100/api/admin';
const KEY = 'admin123';
const H   = { 'Content-Type': 'application/json', 'X-Admin-Key': KEY };

let selectedType = 'mcq';

function selectType(type) {
  selectedType = type;
  document.getElementById('question-type').value = type;
  document.querySelectorAll('.type-card').forEach(c => c.classList.remove('selected'));
  document.getElementById(`type-${type}`).classList.add('selected');
  updatePreview();
}

function updatePreview() {
  const n   = parseInt(document.getElementById('num-questions').value)   || 0;
  const m   = parseInt(document.getElementById('marks-per-q').value)     || 0;
  const pct = parseInt(document.getElementById('pass-mark-pct').value)   || 0;
  const total = n * m;
  const pass  = Math.ceil(total * pct / 100);

  document.getElementById('pv-questions').textContent = n;
  document.getElementById('pv-marks').textContent     = m;
  document.getElementById('pv-total').textContent     = total;
  document.getElementById('pv-pass').textContent      = `${pass} marks (${pct}%)`;
  document.getElementById('pv-pass-big').textContent  = `${pass} / ${total}`;

  const typeLabels = { mcq: 'MCQ Only', open: 'Open-Ended Only', both: 'Both MCQ & Open' };
  document.getElementById('pv-type').textContent = typeLabels[selectedType] || selectedType;
}

async function loadConfig() {
  const r = await fetch(`${API}/quiz-config`, { headers: H });
  const d = await r.json();
  if (!d || !d.num_questions) return;

  document.getElementById('num-questions').value  = d.num_questions;
  document.getElementById('marks-per-q').value    = d.marks_per_q;
  document.getElementById('pass-mark-pct').value  = d.pass_mark_pct;
  document.getElementById('intro-text').value     = d.intro_text || '';
  selectType(d.question_type || 'both');

  const leniency = d.leniency_score ?? 50;
  document.getElementById('leniency-slider').value = leniency;
  updateLeniency(leniency);

  updatePreview();
}

async function saveConfig() {
  const btn = document.getElementById('save-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Saving...';

  try {
    const r = await fetch(`${API}/quiz-config`, {
      method: 'PUT', headers: H,
      body: JSON.stringify({
        num_questions:  parseInt(document.getElementById('num-questions').value),
        marks_per_q:    parseInt(document.getElementById('marks-per-q').value),
        pass_mark_pct:  parseInt(document.getElementById('pass-mark-pct').value),
        question_type:  selectedType,
        intro_text:     document.getElementById('intro-text').value,
        leniency_score: parseInt(document.getElementById('leniency-slider').value),
      })
    });
    const d = await r.json();
    if (r.ok) {
      btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Saved!';
      btn.style.background = 'var(--color-success)';
      setTimeout(() => {
        btn.innerHTML = '<i class="bi bi-save me-1"></i>Save Configuration';
        btn.style.background = '';
        btn.disabled = false;
      }, 2000);
    } else {
      alert(d.detail || 'Save failed.');
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-save me-1"></i>Save Configuration';
    }
  } catch(e) {
    alert('Error: ' + e.message);
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-save me-1"></i>Save Configuration';
  }
}

loadConfig();
loadDebugToggle();

// ── Leniency slider logic ─────────────────────────────────────
function leniencyToThresholds(l) {
  // Mirror of backend _leniency_to_thresholds()
  l = Math.max(0, Math.min(100, l));
  let accept, reject;
  if (l <= 50) {
    accept = Math.round(100 - l * 0.30);
    reject = Math.round(75  - l * 0.40);
  } else {
    accept = Math.round(85 - (l - 50) * 0.60);
    reject = Math.round(55 - (l - 50) * 0.70);
  }
  return { accept: Math.max(55, accept), reject: Math.max(5, reject) };
}

function updateLeniency(val) {
  val = parseInt(val);
  const { accept, reject } = leniencyToThresholds(val);

  // Label
  let label, mode;
  if      (val <= 10)  { label = `Strict (${val})`;       mode = '🔒 Very strict — only exact answers accepted'; }
  else if (val <= 35)  { label = `Strict (${val})`;       mode = '🔒 Strict — minor variations accepted'; }
  else if (val <= 65)  { label = `Balanced (${val})`;     mode = '⚖️ Balanced — abbreviations & nicknames accepted'; }
  else if (val <= 85)  { label = `Lenient (${val})`;      mode = '🎯 Lenient — partial answers accepted'; }
  else                 { label = `Very Easy (${val})`;    mode = '🎯 Very easy — almost any relevant answer accepted'; }

  document.getElementById('leniency-val-label').textContent  = label;
  document.getElementById('leniency-mode-text').textContent  = mode;
  document.getElementById('tc-accept').textContent           = accept;
  document.getElementById('tc-reject').textContent           = reject;
  document.getElementById('tc-llm-zone').textContent         = `${reject} – ${accept - 1}`;
}

async function loadDebugToggle() {
  try {
    const r = await fetch(`${API}/prompt-debug`, { headers: H });
    const d = await r.json();
    setDebugUI(d.show_prompt_debug);
  } catch(e) { console.warn('Could not load debug toggle', e); }
}

async function togglePromptDebug() {
  const pill = document.getElementById('debug-toggle');
  pill.style.opacity = '0.5';
  pill.style.pointerEvents = 'none';
  try {
    const r = await fetch(`${API}/prompt-debug`, { method: 'POST', headers: H });
    const d = await r.json();
    setDebugUI(d.show_prompt_debug);
  } catch(e) { alert('Toggle failed: ' + e.message); }
  pill.style.opacity = '';
  pill.style.pointerEvents = '';
}

function setDebugUI(isOn) {
  const pill   = document.getElementById('debug-toggle');
  const status = document.getElementById('debug-status');
  if (isOn) {
    pill.classList.add('on');
    status.textContent = 'ON';
    status.className = 'toggle-status on';
  } else {
    pill.classList.remove('on');
    status.textContent = 'OFF';
    status.className = 'toggle-status off';
  }
}
</script>
</body>
</html>
