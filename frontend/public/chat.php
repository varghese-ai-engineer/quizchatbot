<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/Auth.php';
require_once __DIR__ . '/../src/Database.php';

Auth::requireLogin();

$user     = $_SESSION['username'];
$fullName = $_SESSION['full_name'];
$language = $_SESSION['language'] ?? 'en';
$isAdmin  = ($_SESSION['role'] ?? 'user') === 'admin';

// Always fetch live credits from MySQL — session value is stale after API deductions
try {
    $db   = Database::getConnection();
    $stmt = $db->prepare('SELECT credits FROM users WHERE id = ? AND is_active = 1 LIMIT 1');
    $stmt->execute([$_SESSION['user_id']]);
    $row  = $stmt->fetch();
    $credits = $row ? (int) $row['credits'] : (int) ($_SESSION['credits'] ?? 0);
    $_SESSION['credits'] = $credits; // keep session in sync
} catch (Throwable $e) {
    $credits = (int) ($_SESSION['credits'] ?? 0);
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="QuizChatbot AI chat — multilingual training assistant.">
    <title>Chat — <?= APP_NAME ?></title>

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">
    <link rel="stylesheet" href="/assets/css/chat.css">
</head>
<body>

<!-- ── Navbar ─────────────────────────────────────────────── -->
<nav class="chat-nav" id="main-nav">
    <div class="nav-brand">
        <div class="nav-brand-icon"><i class="bi bi-robot"></i></div>
        <span class="nav-brand-name"><?= APP_NAME ?></span>
    </div>

    <div class="nav-controls">
        <!-- Admin Link (admins only) -->
        <?php if (($_SESSION['role'] ?? 'user') === 'admin'): ?>
        <a href="/admin/knowledge.php" class="admin-nav-link" title="Admin Panel">
            <i class="bi bi-shield-check"></i>
        </a>
        <?php endif; ?>

        <!-- Language Selector -->
        <select class="lang-select" id="language-select" aria-label="Choose language">
            <option value="en" <?= $language === 'en' ? 'selected' : '' ?>>🇬🇧 English</option>
            <option value="ta" <?= $language === 'ta' ? 'selected' : '' ?>>🇮🇳 Tamil</option>
            <option value="hi" <?= $language === 'hi' ? 'selected' : '' ?>>🇮🇳 Hindi</option>
        </select>

        <!-- Credits Badge -->
        <div class="credits-badge" id="credits-badge" title="Your remaining credits">
            <i class="bi bi-lightning-charge-fill"></i>
            <span id="credits-count"><?= (int) $credits ?></span>
        </div>

        <!-- User Menu -->
        <div class="user-menu" id="user-menu-btn">
            <div class="user-avatar"><?= strtoupper(substr($fullName, 0, 1)) ?></div>
            <span class="user-name"><?= htmlspecialchars($fullName) ?></span>
            <i class="bi bi-chevron-down"></i>

            <div class="user-dropdown" id="user-dropdown">
                <a href="/logout.php" class="dropdown-item" id="logout-link">
                    <i class="bi bi-box-arrow-right"></i> Sign Out
                </a>
            </div>
        </div>
    </div>
</nav>

<!-- ── Chat Layout ─────────────────────────────────────────── -->
<div class="chat-layout" id="chat-layout">

    <!-- Sidebar -->
    <aside class="chat-sidebar" id="chat-sidebar">
        <button class="new-chat-btn" id="new-chat-btn">
            <i class="bi bi-plus-lg me-2"></i>New Chat
        </button>

        <div class="sidebar-section-label">Capabilities</div>
        <div class="capability-list">
            <div class="capability-item active" data-mode="rag" id="mode-rag">
                <i class="bi bi-book-half"></i>
                <span>Knowledge Q&amp;A</span>
            </div>
            <div class="capability-item" data-mode="quiz" id="mode-quiz">
                <i class="bi bi-patch-question"></i>
                <span>Take a Quiz</span>
            </div>
            <div class="capability-item" data-mode="scores" id="mode-scores">
                <i class="bi bi-bar-chart-line"></i>
                <span>My Scores</span>
            </div>
        </div>

        <div class="sidebar-section-label mt-auto">Recent</div>
        <div class="history-list" id="history-list">
            <p class="history-empty">No chats yet.</p>
        </div>
    </aside>

    <!-- Main Chat Area -->
    <main class="chat-main" id="chat-main">

        <!-- Welcome Screen (shown when no messages) -->
        <div class="welcome-screen" id="welcome-screen">
            <div class="welcome-icon"><i class="bi bi-stars"></i></div>
            <h2 class="welcome-title">Hello, <?= htmlspecialchars($fullName) ?>!</h2>
            <p class="welcome-sub">Ask me anything, take a quiz, or check your scores.</p>

            <div class="starter-chips" id="starter-chips">
                <button class="chip" id="chip-ipl-winners" data-msg="Who has won the most IPL trophies?">
                    <i class="bi bi-trophy-fill"></i> IPL Winners
                </button>
                <button class="chip" id="chip-quiz" data-msg="Quiz me on IPL">
                    <i class="bi bi-patch-question"></i> Start a quiz
                </button>
                <button class="chip" id="chip-scores" data-msg="How did I do in my last quiz?">
                    <i class="bi bi-bar-chart-line"></i> My last score
                </button>
                <button class="chip" id="chip-records" data-msg="What are the famous IPL records?">
                    <i class="bi bi-stars"></i> IPL Records
                </button>
            </div>
        </div>

        <!-- Messages -->
        <div class="messages-container" id="messages-container"></div>

        <!-- Input Area -->
        <div class="input-area" id="input-area">
            <div class="input-box">
                <textarea
                    id="chat-input"
                    class="chat-textarea"
                    placeholder="Ask about IPL teams, players, records…"
                    rows="1"
                    maxlength="2000"
                    aria-label="Chat input"
                ></textarea>
                <button class="send-btn" id="send-btn" aria-label="Send message" disabled>
                    <i class="bi bi-arrow-up-short"></i>
                </button>
            </div>
            <p class="input-hint">
                <i class="bi bi-info-circle me-1"></i>
                Each message costs <strong>1 credit</strong>. You have
                <strong id="credits-hint"><?= (int) $credits ?></strong> remaining.
            </p>
        </div>

    </main>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script>
    // Expose PHP session data to JS
    const APP_CONFIG = {
        userId: <?= (int) $_SESSION['user_id'] ?>,
        username: <?= json_encode($user) ?>,
        fullName: <?= json_encode($fullName) ?>,
        credits: <?= (int) $credits ?>,
        language: <?= json_encode($language) ?>,
        apiBase: <?= json_encode(API_PUBLIC_URL) ?>,
        role: <?= json_encode($_SESSION['role'] ?? 'user') ?>,
    };
</script>
<script src="https://cdn.jsdelivr.net/npm/marked@9/marked.min.js"></script>
<script src="/assets/js/chat.js"></script>
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
// Listen for Escape key
document.addEventListener('keydown', e => { if (e.key === 'Escape') closePromptPopup(); });
</script>
<?php endif; ?>
</body>
</html>
