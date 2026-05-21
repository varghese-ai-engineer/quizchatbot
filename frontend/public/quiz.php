<?php
declare(strict_types=1);
require_once __DIR__ . '/../src/Auth.php';
Auth::requireLogin();
$userId   = (int) $_SESSION['user_id'];
$fullName = $_SESSION['full_name'];
$language = $_SESSION['language'] ?? 'en';
$isAdmin  = ($_SESSION['role'] ?? 'user') === 'admin';
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta name="description" content="IPL Quiz — Test your cricket knowledge with AI-powered evaluation.">
<title>Quiz — <?= APP_NAME ?></title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
<link rel="stylesheet" href="/assets/css/quiz.css">
</head>
<body>

<!-- Nav -->
<nav class="quiz-nav">
  <a href="/chat.php" class="quiz-nav-back"><i class="bi bi-arrow-left me-1"></i>Back to Chat</a>
  <div class="quiz-nav-brand"><i class="bi bi-patch-question me-2"></i>IPL Quiz</div>
  <div class="quiz-nav-right">
    <select id="lang-select" class="lang-select" aria-label="Language">
      <option value="en" <?= $language === 'en' ? 'selected' : '' ?>>🇬🇧 English</option>
      <option value="ta" <?= $language === 'ta' ? 'selected' : '' ?>>🇮🇳 Tamil</option>
      <option value="hi" <?= $language === 'hi' ? 'selected' : '' ?>>🇮🇳 Hindi</option>
    </select>
    <div class="quiz-nav-user"><?= htmlspecialchars($fullName) ?></div>
  </div>
</nav>

<div class="quiz-wrapper">

  <!-- ── Screen 1: Intro ───────────────────────────────────── -->
  <div id="screen-intro" class="quiz-screen">
    <div class="quiz-card intro-card">
      <div class="quiz-icon-wrap">
        <i class="bi bi-patch-question"></i>
      </div>
      <h1 class="quiz-title">IPL Cricket Quiz</h1>
      <p class="quiz-subtitle" id="intro-text">Loading quiz info...</p>

      <div class="rules-grid" id="rules-grid">
        <div class="rule-item">
          <i class="bi bi-hash"></i>
          <span class="rule-label">Questions</span>
          <span class="rule-val" id="rule-questions">—</span>
        </div>
        <div class="rule-item">
          <i class="bi bi-star-fill"></i>
          <span class="rule-label">Marks / Question</span>
          <span class="rule-val" id="rule-marks">—</span>
        </div>
        <div class="rule-item">
          <i class="bi bi-trophy-fill"></i>
          <span class="rule-label">Total Marks</span>
          <span class="rule-val" id="rule-total">—</span>
        </div>
        <div class="rule-item">
          <i class="bi bi-bullseye"></i>
          <span class="rule-label">Pass Mark</span>
          <span class="rule-val" id="rule-pass">—</span>
        </div>
      </div>

      <div class="topic-select-wrap">
        <label class="quiz-label">Select Topic</label>
        <select id="topic-select" class="quiz-select">
          <option value="">Loading topics...</option>
        </select>
      </div>

      <button class="btn-quiz-start" id="start-btn" onclick="startQuiz()">
        <i class="bi bi-play-fill me-2"></i>Start Quiz
      </button>
    </div>
  </div>

  <!-- ── Screen 2: Question ────────────────────────────────── -->
  <div id="screen-question" class="quiz-screen d-none">
    <div class="quiz-card question-card">

      <!-- Progress -->
      <div class="quiz-progress-wrap">
        <div class="quiz-progress-info">
          <span id="q-current">Q1</span>
          <span id="q-score-live">Score: 0</span>
        </div>
        <div class="quiz-progress-bar">
          <div class="quiz-progress-fill" id="q-progress-fill"></div>
        </div>
      </div>

      <!-- Question -->
      <div class="question-number" id="q-number">Question 1 of 10</div>
      <div class="question-text" id="q-text">Loading...</div>
      <div class="question-difficulty" id="q-difficulty"></div>

      <!-- MCQ Options -->
      <div id="mcq-options" class="mcq-options d-none"></div>

      <!-- Open Answer -->
      <div id="open-answer" class="d-none">
        <label class="quiz-label">Your Answer</label>
        <textarea id="open-input" class="quiz-textarea" rows="3"
          placeholder="Type your answer here..."></textarea>
        <p class="open-hint"><i class="bi bi-robot me-1"></i>Your answer will be evaluated by AI — write in your own words.</p>
      </div>

      <!-- Submit / Feedback -->
      <div id="answer-actions">
        <button class="btn-quiz-submit" id="submit-btn" onclick="submitAnswer()">
          <i class="bi bi-send me-2"></i>Submit Answer
        </button>
      </div>

      <!-- Feedback (shown after submit) -->
      <div id="answer-feedback" class="d-none">
        <div class="feedback-box" id="feedback-box">
          <div class="feedback-verdict" id="feedback-verdict"></div>
          <div class="feedback-text" id="feedback-text"></div>
          <div class="feedback-correct" id="feedback-correct"></div>
        </div>
        <button class="btn-quiz-next" id="next-btn" onclick="nextQuestion()">
          <span id="next-btn-text">Next Question <i class="bi bi-arrow-right ms-1"></i></span>
        </button>
      </div>

      <!-- AI Thinking indicator -->
      <div id="ai-thinking" class="ai-thinking d-none">
        <div class="thinking-dots"><span></span><span></span><span></span></div>
        <span>AI is evaluating your answer...</span>
      </div>

    </div>
  </div>

  <!-- ── Screen 3: Result ──────────────────────────────────── -->
  <div id="screen-result" class="quiz-screen d-none">
    <div class="quiz-card result-card">
      <div class="result-icon" id="result-icon"></div>
      <div class="result-badge" id="result-badge"></div>
      <h2 class="result-title" id="result-title"></h2>
      <p class="result-msg" id="result-msg"></p>

      <div class="result-stats">
        <div class="stat-box">
          <div class="stat-val" id="stat-correct">—</div>
          <div class="stat-label">Correct</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="stat-wrong">—</div>
          <div class="stat-label">Wrong</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="stat-marks">—</div>
          <div class="stat-label">Marks</div>
        </div>
        <div class="stat-box">
          <div class="stat-val" id="stat-pct">—</div>
          <div class="stat-label">Score %</div>
        </div>
      </div>

      <!-- Score arc -->
      <div class="score-arc-wrap">
        <svg class="score-arc" viewBox="0 0 120 120">
          <circle class="arc-bg" cx="60" cy="60" r="50" />
          <circle class="arc-fill" id="arc-fill" cx="60" cy="60" r="50"
            stroke-dasharray="314" stroke-dashoffset="314" />
        </svg>
        <div class="arc-text">
          <div class="arc-pct" id="arc-pct">0%</div>
          <div class="arc-label">Score</div>
        </div>
      </div>

      <div class="result-actions">
        <button class="btn-quiz-outline" onclick="location.href='/chat.php'">
          <i class="bi bi-arrow-left me-1"></i>Back to Chat
        </button>
        <button class="btn-quiz-start" onclick="resetQuiz()">
          <i class="bi bi-arrow-repeat me-1"></i>Try Again
        </button>
      </div>
    </div>
  </div>

</div><!-- .quiz-wrapper -->

<script>
const API      = '<?= API_PUBLIC_URL ?>/api';
const USER_ID  = <?= $userId ?>;
const IS_ADMIN = <?= $isAdmin ? 'true' : 'false' ?>;
let   LANG     = localStorage.getItem('quiz_lang') || '<?= $language ?>';

// Sync selector to stored lang
document.getElementById('lang-select').value = LANG;
document.getElementById('lang-select').addEventListener('change', function() {
  LANG = this.value;
  localStorage.setItem('quiz_lang', LANG);
});

let quizConfig     = {};
let sessionId      = null;
let questions      = [];
let currentIdx     = 0;
let correctCount   = 0;
let selectedOption = null;
let answered       = false;

// ── Load config & topics ──────────────────────────────────────
async function init() {
  const [cfgRes, topicsRes] = await Promise.all([
    fetch(`${API}/quiz/config`),
    fetch(`${API}/quiz/topics`)
  ]);
  quizConfig = await cfgRes.json();
  const topics = await topicsRes.json();

  document.getElementById('intro-text').textContent     = quizConfig.intro_text || '';
  document.getElementById('rule-questions').textContent = quizConfig.num_questions;
  document.getElementById('rule-marks').textContent     = quizConfig.marks_per_q;
  document.getElementById('rule-total').textContent     = quizConfig.total_marks;
  document.getElementById('rule-pass').textContent      =
    `${quizConfig.pass_marks} marks (${quizConfig.pass_mark_pct}%)`;

  const sel = document.getElementById('topic-select');

  // Build options — All Topics first, then each topic
  let html = '';
  if (topics.length > 1) {
    const totalQ = topics.reduce((sum, t) => sum + (t.question_count || 0), 0);
    html += `<option value="all">🌐 All Topics (${totalQ} questions)</option>`;
  }
  topics.forEach(t => {
    const qCount = t.question_count ? ` — ${t.question_count} questions` : '';
    html += `<option value="${t.slug}">${t.name}${qCount}</option>`;
  });

  sel.innerHTML = html || '<option value="">No topics available</option>';
}

// ── Start Quiz ────────────────────────────────────────────────
async function startQuiz() {
  const slug = document.getElementById('topic-select').value;
  if (!slug) { alert('Please select a topic.'); return; }

  const btn = document.getElementById('start-btn');
  btn.disabled = true;
  btn.innerHTML = '<span style="display:inline-flex;gap:4px"><span class="thinking-dots"><span></span><span></span><span></span></span> Loading...</span>';

  try {
    const r    = await fetch(`${API}/quiz/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: USER_ID, topic_slug: slug, language: LANG })
    });
    const data = await r.json();

    if (!r.ok) {
      // Session expired or user deleted → redirect to login
      if (r.status === 422 || r.status === 500) {
        alert('Session expired. Please log in again.');
        window.location.href = '/logout.php';
        return;
      }
      alert(data.detail || 'Could not start quiz. Please try again.');
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-play-fill me-2"></i>Start Quiz';
      return;
    }

    sessionId    = data.quiz_session_id;
    questions    = data.questions;
    currentIdx   = 0;
    correctCount = 0;

    showScreen('question');
    renderQuestion();

  } catch (err) {
    alert('Network error: ' + err.message);
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-play-fill me-2"></i>Start Quiz';
  }
}

// ── Render Question ───────────────────────────────────────────
function renderQuestion() {
  const q   = questions[currentIdx];
  const num = currentIdx + 1;
  const tot = questions.length;

  document.getElementById('q-number').textContent    = `Question ${num} of ${tot}`;
  document.getElementById('q-text').textContent      = q.question;
  document.getElementById('q-current').textContent   = `Q${num}`;
  document.getElementById('q-score-live').textContent = `Score: ${correctCount}/${currentIdx}`;
  document.getElementById('q-difficulty').textContent =
    q.difficulty ? `🔥 ${q.difficulty.charAt(0).toUpperCase() + q.difficulty.slice(1)}` : '';

  const pct = ((num - 1) / tot) * 100;
  document.getElementById('q-progress-fill').style.width = pct + '%';

  // Reset state
  answered = false;
  selectedOption = null;
  document.getElementById('answer-feedback').classList.add('d-none');
  document.getElementById('answer-actions').classList.remove('d-none');
  document.getElementById('ai-thinking').classList.add('d-none');
  document.getElementById('submit-btn').disabled = false;
  document.getElementById('submit-btn').innerHTML = '<i class="bi bi-send me-2"></i>Submit Answer';

  if (q.type === 'mcq' && q.options) {
    document.getElementById('mcq-options').classList.remove('d-none');
    document.getElementById('open-answer').classList.add('d-none');
    renderMCQ(q.options);
  } else {
    document.getElementById('mcq-options').classList.add('d-none');
    document.getElementById('open-answer').classList.remove('d-none');
    document.getElementById('open-input').value = '';
    document.getElementById('open-input').disabled = false;
  }
}

function renderMCQ(options) {
  const wrap = document.getElementById('mcq-options');
  wrap.innerHTML = options.map((opt, i) => `
    <button class="mcq-option" id="opt-${i}" onclick="selectMCQ(${i}, this)">
      <span class="opt-label">${String.fromCharCode(65 + i)}</span>
      <span class="opt-text">${opt}</span>
    </button>
  `).join('');
}

function selectMCQ(idx, el) {
  if (answered) return;
  document.querySelectorAll('.mcq-option').forEach(b => b.classList.remove('selected'));
  el.classList.add('selected');
  selectedOption = questions[currentIdx].options[idx];
}

// ── Submit Answer ─────────────────────────────────────────────
async function submitAnswer() {
  if (answered) return;
  const q = questions[currentIdx];

  let userAnswer = '';
  if (q.type === 'mcq') {
    if (!selectedOption) { alert('Please select an answer.'); return; }
    userAnswer = selectedOption;
  } else {
    userAnswer = document.getElementById('open-input').value.trim();
    if (!userAnswer) { alert('Please type your answer.'); return; }
  }

  answered = true;
  document.getElementById('answer-actions').classList.add('d-none');
  document.getElementById('open-input').disabled = true;

  if (q.type === 'open') {
    document.getElementById('ai-thinking').classList.remove('d-none');
  }

  const r = await fetch(`${API}/quiz/answer`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      quiz_session_id: sessionId,
      question_id: q.id,
      user_answer: userAnswer,
      language: LANG
    })
  });
  const data = await r.json();

  document.getElementById('ai-thinking').classList.add('d-none');

  // Admin-only: show LLM prompt inspector if debug is on
  if (IS_ADMIN && data.debug_prompt && typeof showPromptPopup === 'function') {
    showPromptPopup(data.debug_prompt);
  }

  if (data.is_correct) correctCount++;

  // Show feedback
  const fb      = document.getElementById('feedback-box');
  const verdict = document.getElementById('feedback-verdict');
  const text    = document.getElementById('feedback-text');
  const correct = document.getElementById('feedback-correct');

  fb.className = `feedback-box ${data.is_correct ? 'feedback-correct-box' : 'feedback-wrong-box'}`;
  verdict.innerHTML = data.is_correct
    ? `<i class="bi bi-check-circle-fill me-2"></i>Correct! +${data.marks_awarded} mark${data.marks_awarded !== 1 ? 's' : ''}`
    : `<i class="bi bi-x-circle-fill me-2"></i>Incorrect`;
  text.textContent = data.feedback || '';
  correct.textContent = data.is_correct ? '' : `✅ Correct Answer: ${data.correct_answer}`;

  // MCQ: highlight correct/wrong options
  if (q.type === 'mcq') {
    document.querySelectorAll('.mcq-option').forEach((btn, i) => {
      const optVal = q.options[i];
      if (optVal === data.correct_answer) btn.classList.add('correct');
      else if (optVal === userAnswer && !data.is_correct) btn.classList.add('wrong');
    });
  }

  // Next button label
  const isLast = currentIdx === questions.length - 1;
  document.getElementById('next-btn-text').innerHTML = isLast
    ? 'See Results <i class="bi bi-bar-chart-line ms-1"></i>'
    : 'Next Question <i class="bi bi-arrow-right ms-1"></i>';

  document.getElementById('answer-feedback').classList.remove('d-none');
  document.getElementById('q-score-live').textContent = `Score: ${correctCount}/${currentIdx + 1}`;
}

// ── Next Question / Finish ────────────────────────────────────
async function nextQuestion() {
  if (currentIdx < questions.length - 1) {
    currentIdx++;
    renderQuestion();
  } else {
    await finishQuiz();
  }
}

async function finishQuiz() {
  const r    = await fetch(`${API}/quiz/finish/${sessionId}`, { method: 'POST' });
  const data = await r.json();

  const passed = data.passed;
  const pct    = data.percentage;

  document.getElementById('result-icon').innerHTML = passed
    ? '<i class="bi bi-trophy-fill"></i>'
    : '<i class="bi bi-emoji-frown"></i>';
  document.getElementById('result-badge').innerHTML = passed
    ? '<span class="badge-passed">PASSED</span>'
    : '<span class="badge-failed">FAILED</span>';
  document.getElementById('result-title').textContent = passed ? 'Congratulations! 🎉' : 'Better Luck Next Time';
  document.getElementById('result-msg').textContent   = data.message;

  document.getElementById('stat-correct').textContent = data.score;
  document.getElementById('stat-wrong').textContent   = data.total - data.score;
  document.getElementById('stat-marks').textContent   = `${data.earned_marks}/${data.total_marks}`;
  document.getElementById('stat-pct').textContent     = `${pct}%`;

  // Animate arc
  const circumference = 314;
  const offset = circumference - (pct / 100) * circumference;
  const arc = document.getElementById('arc-fill');
  arc.style.stroke = passed ? '#22c55e' : '#ef4444';
  document.getElementById('arc-pct').textContent = `${pct}%`;
  document.getElementById('arc-pct').style.color = passed ? '#22c55e' : '#ef4444';

  showScreen('result');
  setTimeout(() => { arc.style.strokeDashoffset = offset; }, 100);
}

// ── Helpers ───────────────────────────────────────────────────
function showScreen(name) {
  ['intro', 'question', 'result'].forEach(s => {
    document.getElementById(`screen-${s}`).classList.toggle('d-none', s !== name);
  });
}

function resetQuiz() {
  sessionId = null; questions = []; currentIdx = 0; correctCount = 0;
  showScreen('intro');
}

init();
</script>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<?php if ($isAdmin): ?>
<!-- ── Prompt Inspector Popup (Admin Only) ─────────────────── -->
<div id="prompt-popup" style="
  display:none; position:fixed; inset:0; z-index:9999;
  background:rgba(0,0,0,0.65); backdrop-filter:blur(4px);
  align-items:flex-start; justify-content:center; padding:5vh 1rem;
">
  <div style="
    background:#111827; border:1px solid rgba(108,99,255,0.4);
    border-radius:16px; width:100%; max-width:720px; max-height:85vh;
    display:flex; flex-direction:column; box-shadow:0 24px 60px rgba(0,0,0,0.6);
  ">
    <!-- Header -->
    <div style="display:flex;align-items:center;justify-content:space-between;padding:1rem 1.25rem;border-bottom:1px solid rgba(255,255,255,0.07)">
      <div style="display:flex;align-items:center;gap:0.6rem">
        <i class="bi bi-terminal" style="color:#6c63ff;font-size:1.1rem"></i>
        <span style="font-weight:700;font-size:0.95rem">LLM Prompt Inspector</span>
        <span style="background:rgba(108,99,255,0.15);color:#8b85ff;border-radius:99px;padding:0.1rem 0.6rem;font-size:0.7rem;font-weight:700">ADMIN</span>
      </div>
      <button onclick="closePromptPopup()" style="
        background:rgba(255,255,255,0.07);border:none;color:#e8eaf0;
        width:30px;height:30px;border-radius:8px;cursor:pointer;font-size:1rem;
        display:flex;align-items:center;justify-content:center;
        transition:background 0.2s;
      " onmouseover="this.style.background='rgba(239,68,68,0.2)'" onmouseout="this.style.background='rgba(255,255,255,0.07)'">
        <i class="bi bi-x-lg"></i>
      </button>
    </div>
    <!-- Body -->
    <pre id="prompt-popup-text" style="
      flex:1; overflow-y:auto; margin:0; padding:1.25rem;
      font-family:'JetBrains Mono',monospace,sans-serif;
      font-size:0.78rem; line-height:1.7; color:#a8b4d0;
      white-space:pre-wrap; word-break:break-word;
    "></pre>
    <!-- Footer -->
    <div style="padding:0.75rem 1.25rem;border-top:1px solid rgba(255,255,255,0.07);display:flex;justify-content:flex-end;gap:0.5rem">
      <button onclick="navigator.clipboard.writeText(document.getElementById('prompt-popup-text').textContent)" style="
        background:rgba(108,99,255,0.15);border:1px solid rgba(108,99,255,0.3);
        color:#8b85ff;border-radius:8px;padding:0.35rem 0.9rem;cursor:pointer;
        font-size:0.8rem;font-weight:600;transition:background 0.2s;
      "><i class="bi bi-clipboard me-1"></i>Copy</button>
      <button onclick="closePromptPopup()" style="
        background:rgba(255,255,255,0.07);border:1px solid rgba(255,255,255,0.1);
        color:#e8eaf0;border-radius:8px;padding:0.35rem 0.9rem;cursor:pointer;
        font-size:0.8rem;font-weight:600;transition:background 0.2s;
      ">Close</button>
    </div>
  </div>
</div>
<script>
function showPromptPopup(text) {
  document.getElementById('prompt-popup-text').textContent = text;
  const p = document.getElementById('prompt-popup');
  p.style.display = 'flex';
  setTimeout(() => p.style.opacity = 1, 10);
}
function closePromptPopup() {
  document.getElementById('prompt-popup').style.display = 'none';
}
document.getElementById('prompt-popup').addEventListener('click', function(e) {
  if (e.target === this) closePromptPopup();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') closePromptPopup(); });
</script>
<?php endif; ?>
</body>
</html>
