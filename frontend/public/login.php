<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/Auth.php';

if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// Already logged in → go to chat
if (!empty($_SESSION['logged_in'])) {
    header('Location: /chat.php');
    exit;
}

$error   = '';
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email    = trim($_POST['email']    ?? '');
    $password = trim($_POST['password'] ?? '');

    if ($email === '' || $password === '') {
        $error = 'Please fill in all fields.';
    } else {
        $result = Auth::login($email, $password);
        if ($result['success']) {
            header('Location: /chat.php');
            exit;
        }
        $error = $result['message'];
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Sign in to QuizChatbot — your AI-powered multilingual training assistant.">
    <title>Login — <?= APP_NAME ?></title>

    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">

    <!-- Bootstrap 5 -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">

    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css">

    <link rel="stylesheet" href="/assets/css/auth.css">
</head>
<body>

<div class="auth-wrapper">

    <!-- Animated background orbs -->
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>

    <div class="auth-card">

        <!-- Brand -->
        <div class="auth-brand">
            <div class="brand-icon">
                <i class="bi bi-robot"></i>
            </div>
            <h1 class="brand-name"><?= APP_NAME ?></h1>
            <p class="brand-tagline">AI-Powered Multilingual Training</p>
        </div>

        <h2 class="auth-title">Welcome back</h2>
        <p class="auth-subtitle">Sign in to continue learning</p>

        <?php if ($error !== ''): ?>
        <div class="alert-custom alert-error" role="alert" id="alert-error">
            <i class="bi bi-exclamation-circle-fill me-2"></i>
            <?= htmlspecialchars($error) ?>
        </div>
        <?php endif; ?>

        <form method="POST" action="/login.php" id="login-form" novalidate>

            <div class="form-floating-custom">
                <label for="email">Email address</label>
                <div class="input-wrapper">
                    <i class="bi bi-envelope input-icon"></i>
                    <input
                        type="email"
                        id="email"
                        name="email"
                        class="form-input"
                        placeholder="you@example.com"
                        value="<?= htmlspecialchars($_POST['email'] ?? '') ?>"
                        autocomplete="email"
                        required
                    >
                </div>
            </div>

            <div class="form-floating-custom">
                <label for="password">Password</label>
                <div class="input-wrapper">
                    <i class="bi bi-lock input-icon"></i>
                    <input
                        type="password"
                        id="password"
                        name="password"
                        class="form-input"
                        placeholder="••••••••"
                        autocomplete="current-password"
                        required
                    >
                    <button
                        type="button"
                        class="toggle-password"
                        id="toggle-password-btn"
                        aria-label="Toggle password visibility"
                        onclick="togglePassword('password', this)"
                    >
                        <i class="bi bi-eye" id="toggle-password-icon"></i>
                    </button>
                </div>
            </div>

            <button type="submit" class="btn-auth" id="login-submit-btn">
                <span class="btn-text">
                    <i class="bi bi-box-arrow-in-right me-2"></i>Sign In
                </span>
                <span class="btn-loader d-none" id="login-loader">
                    <span class="spinner"></span> Signing in...
                </span>
            </button>
        </form>

        <div class="auth-divider"><span>or</span></div>

        <p class="auth-switch">
            Don't have an account?
            <a href="/signup.php" id="goto-signup-link">Create one free</a>
        </p>

    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="/assets/js/auth.js"></script>
</body>
</html>
