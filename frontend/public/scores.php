<?php
declare(strict_types=1);
require_once __DIR__ . '/../src/Auth.php';
Auth::requireLogin();
$userId   = (int) $_SESSION['user_id'];
$fullName = $_SESSION['full_name'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="description" content="My Quiz Scores — View your quiz history and performance.">
<title>My Scores — <?= APP_NAME ?></title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
<link rel="stylesheet" href="/assets/css/quiz.css">
<style>
.scores-wrapper { max-width: 720px; margin: 0 auto; padding: calc(var(--nav-h) + 2rem) 1rem 3rem; }
.scores-header  { margin-bottom: 2rem; }
.scores-title   { font-size: 1.6rem; font-weight: 700; margin-bottom: 0.3rem; }
.scores-sub     { color: var(--color-muted); font-size: 0.88rem; }

/* Summary cards */
.summary-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 0.75rem; margin-bottom: 2rem; }
.summary-card {
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: 14px; padding: 1.1rem; text-align: center;
}
.summary-icon { font-size: 1.4rem; margin-bottom: 0.3rem; }
.summary-val  { font-size: 1.5rem; font-weight: 700; color: var(--color-text); }
.summary-label{ font-size: 0.72rem; color: var(--color-muted); margin-top: 0.1rem; }

/* History list */
.session-card {
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: 14px; padding: 1.25rem 1.5rem; margin-bottom: 0.75rem;
  display: flex; align-items: center; gap: 1rem;
  transition: border-color 0.2s;
}
.session-card:hover { border-color: var(--color-primary); }
.session-icon {
  width: 44px; height: 44px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 1.2rem;
}
.session-icon.passed { background: rgba(34,197,94,0.15);  color: var(--color-success); }
.session-icon.failed { background: rgba(239,68,68,0.12);  color: var(--color-danger); }
.session-info { flex: 1; }
.session-topic { font-weight: 600; font-size: 0.9rem; margin-bottom: 0.2rem; }
.session-meta  { font-size: 0.75rem; color: var(--color-muted); }
.session-score { text-align: right; }
.session-marks { font-size: 1.2rem; font-weight: 700; }
.session-marks.passed { color: var(--color-success); }
.session-marks.failed { color: var(--color-danger); }
.session-pct   { font-size: 0.75rem; color: var(--color-muted); }
.badge-pass { background: rgba(34,197,94,0.15); color: var(--color-success); border-radius: 99px; padding: 0.15rem 0.6rem; font-size: 0.7rem; font-weight: 700; }
.badge-fail { background: rgba(239,68,68,0.12); color: var(--color-danger);  border-radius: 99px; padding: 0.15rem 0.6rem; font-size: 0.7rem; font-weight: 700; }

.empty-state { text-align: center; padding: 3rem 1rem; color: var(--color-muted); }
.empty-state i { font-size: 3rem; display: block; margin-bottom: 1rem; opacity: 0.4; }

.btn-take-quiz {
  display: inline-flex; align-items: center; gap: 0.5rem;
  background: linear-gradient(135deg, var(--color-primary), #8b85ff);
  color: #fff; border: none; border-radius: 10px; padding: 0.65rem 1.25rem;
  font-family: var(--font); font-size: 0.88rem; font-weight: 600;
  cursor: pointer; text-decoration: none; transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 16px rgba(108,99,255,0.35);
}
.btn-take-quiz:hover { color:#fff; transform: translateY(-1px); box-shadow: 0 6px 22px rgba(108,99,255,0.45); }
.skeleton { background: var(--color-surface2); border-radius: 8px; animation: shimmer 1.5s infinite; height: 70px; margin-bottom: 0.75rem; }
@keyframes shimmer { 0%,100%{opacity:0.5} 50%{opacity:1} }
</style>
</head>
<body>

<nav class="quiz-nav">
  <a href="/chat.php" class="quiz-nav-back"><i class="bi bi-arrow-left me-1"></i>Back to Chat</a>
  <div class="quiz-nav-brand"><i class="bi bi-bar-chart-line me-2"></i>My Scores</div>
  <div class="quiz-nav-user"><?= htmlspecialchars($fullName) ?></div>
</nav>

<div class="scores-wrapper">

  <div class="scores-header d-flex justify-content-between align-items-start flex-wrap gap-3">
    <div>
      <h1 class="scores-title"><i class="bi bi-bar-chart-line me-2 text-primary"></i>My Quiz History</h1>
      <p class="scores-sub">Your completed quiz sessions and performance.</p>
    </div>
    <a href="/quiz.php" class="btn-take-quiz">
      <i class="bi bi-play-fill"></i>Take a Quiz
    </a>
  </div>

  <!-- Summary -->
  <div class="summary-grid" id="summary-grid">
    <div class="summary-card">
      <div class="summary-icon">🎯</div>
      <div class="summary-val" id="sum-total">—</div>
      <div class="summary-label">Quizzes Taken</div>
    </div>
    <div class="summary-card">
      <div class="summary-icon">🏆</div>
      <div class="summary-val" id="sum-passed" style="color:var(--color-success)">—</div>
      <div class="summary-label">Passed</div>
    </div>
    <div class="summary-card">
      <div class="summary-icon">📊</div>
      <div class="summary-val" id="sum-avg">—</div>
      <div class="summary-label">Avg Score %</div>
    </div>
  </div>

  <!-- Session list -->
  <div id="session-list">
    <div class="skeleton"></div>
    <div class="skeleton" style="opacity:0.7"></div>
    <div class="skeleton" style="opacity:0.4"></div>
  </div>

</div>

<script>
const API     = '<?= API_PUBLIC_URL ?>/api';
const USER_ID = <?= $userId ?>;

async function loadScores() {
  const r = await fetch(`${API}/quiz/history/${USER_ID}`);
  const data = await r.json();

  const list = document.getElementById('session-list');

  if (!r.ok || !data.sessions || data.sessions.length === 0) {
    list.innerHTML = `
      <div class="empty-state">
        <i class="bi bi-clipboard-x"></i>
        <p>No quiz sessions yet.</p>
        <a href="/quiz.php" class="btn-take-quiz mt-3"><i class="bi bi-play-fill"></i>Take your first quiz</a>
      </div>`;
    document.getElementById('sum-total').textContent  = '0';
    document.getElementById('sum-passed').textContent = '0';
    document.getElementById('sum-avg').textContent    = '—';
    return;
  }

  const sessions = data.sessions;
  const total    = sessions.length;
  const passed   = sessions.filter(s => s.passed).length;
  const avgPct   = Math.round(sessions.reduce((sum, s) => sum + s.percentage, 0) / total);

  document.getElementById('sum-total').textContent  = total;
  document.getElementById('sum-passed').textContent = passed;
  document.getElementById('sum-avg').textContent    = `${avgPct}%`;

  list.innerHTML = sessions.map(s => {
    const cls     = s.passed ? 'passed' : 'failed';
    const icon    = s.passed ? 'bi-trophy-fill' : 'bi-x-circle-fill';
    const badge   = s.passed
      ? '<span class="badge-pass">PASSED</span>'
      : '<span class="badge-fail">FAILED</span>';
    const date    = new Date(s.started_at).toLocaleString('en-IN', {
      day:'numeric', month:'short', year:'numeric', hour:'2-digit', minute:'2-digit'
    });
    return `
      <div class="session-card">
        <div class="session-icon ${cls}"><i class="bi ${icon}"></i></div>
        <div class="session-info">
          <div class="session-topic">${s.topic_name || 'All Topics'} ${badge}</div>
          <div class="session-meta">
            ${s.score}/${s.total_questions} correct &nbsp;·&nbsp;
            ${s.earned_marks}/${s.total_marks} marks &nbsp;·&nbsp;
            ${date}
          </div>
        </div>
        <div class="session-score">
          <div class="session-marks ${cls}">${s.percentage}%</div>
          <div class="session-pct">Pass: ${s.pass_mark_pct}%</div>
        </div>
      </div>`;
  }).join('');
}

loadScores();
</script>
</body>
</html>
