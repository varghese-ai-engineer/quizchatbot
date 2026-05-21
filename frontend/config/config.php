<?php

declare(strict_types=1);

// ─── Database ──────────────────────────────────────────────────
define('DB_HOST', $_ENV['DB_HOST'] ?? 'mysql');
define('DB_PORT', (int) ($_ENV['DB_PORT'] ?? 3306));
define('DB_NAME', $_ENV['DB_NAME'] ?? 'quizchatbot');
define('DB_USER', $_ENV['DB_USER'] ?? 'quizuser');
define('DB_PASS', $_ENV['DB_PASS'] ?? 'quizpass');

// ─── API ───────────────────────────────────────────────────────
define('API_BASE_URL',    $_ENV['API_BASE_URL']    ?? 'http://localhost:8000');  // server-side (Docker internal)
define('API_PUBLIC_URL',  $_ENV['API_PUBLIC_URL']  ?? 'http://localhost:8100');  // browser-side (host port)
define('API_SECRET_KEY',  $_ENV['API_SECRET_KEY']  ?? 'change_me');

// ─── App ───────────────────────────────────────────────────────
define('APP_NAME', 'QuizChatbot');
define('SESSION_LIFETIME', 3600 * 24); // 24 hours
