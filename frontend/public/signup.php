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
    $fullName = trim($_POST['full_name'] ?? '');
    $username = trim($_POST['username']  ?? '');
    $email    = trim($_POST['email']     ?? '');
    $password = trim($_POST['password']  ?? '');
    $confirm  = trim($_POST['confirm']   ?? '');

    if ($fullName === '' || $username === '' || $email === '' || $password === '') {
        $error = 'Please fill in all fields.';
    } elseif (strlen($password) < 6) {
        $error = 'Password must be at least 6 characters.';
    } elseif ($password !== $confirm) {
        $error = 'Passwords do not match.';
    } else {
        $result = Auth::register($username, $email, $password, $fullName);
        if ($result['success']) {
            $success = 'Account created! You can now sign in.';
        } else {
            $error = $result['message'];
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Create your free QuizChatbot account — AI-powered multilingual training assistant.">
    <title>Sign Up — <?= APP_NAME ?></title>

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

    <div class="auth-card auth-card--signup">

        <!-- Brand -->
        <div class="auth-brand">
            <div class="brand-icon">
                <i class="bi bi-robot"></i>
            </div>
            <h1 class="brand-name"><?= APP_NAME ?></h1>
            <p class="brand-tagline">AI-Powered Multilingual Training</p>
        </div>

        <h2 class="auth-title">Create account</h2>
        <p class="auth-subtitle">Start your learning journey today</p>

        <?php if ($error !== ''): ?>
        <div class="alert-custom alert-error" role="alert" id="alert-error">
            <i class="bi bi-exclamation-circle-fill me-2"></i>
            <?= htmlspecialchars($error) ?>
        </div>
        <?php endif; ?>

        <?php if ($success !== ''): ?>
        <div class="alert-custom alert-success" role="alert" id="alert-success">
            <i class="bi bi-check-circle-fill me-2"></i>
            <?= htmlspecialchars($success) ?>
            <a href="/login.php" class="ms-2 fw-semibold">Sign in →</a>
        </div>
        <?php endif; ?>

        <form method="POST" action="/signup.php" id="signup-form" novalidate>

            <div class="form-row-two">
                <div class="form-floating-custom">
                    <label for="full_name">Full Name</label>
                    <div class="input-wrapper">
                        <i class="bi bi-person input-icon"></i>
                        <input
                            type="text"
                            id="full_name"
                            name="full_name"
                            class="form-input"
                            placeholder="John Doe"
                            value="<?= htmlspecialchars($_POST['full_name'] ?? '') ?>"
                            autocomplete="name"
                            required
                        >
                    </div>
                </div>

                <div class="form-floating-custom">
                    <label for="username">Username</label>
                    <div class="input-wrapper">
                        <i class="bi bi-at input-icon"></i>
                        <input
                            type="text"
                            id="username"
                            name="username"
                            class="form-input"
                            placeholder="johndoe"
                            value="<?= htmlspecialchars($_POST['username'] ?? '') ?>"
                            autocomplete="username"
                            required
                        >
                    </div>
                </div>
            </div>

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
                        placeholder="Min. 6 characters"
                        autocomplete="new-password"
                        required
                    >
                    <button
                        type="button"
                        class="toggle-password"
                        id="toggle-password-btn"
                        aria-label="Toggle password visibility"
                        onclick="togglePassword('password', this)"
                    >
                        <i class="bi bi-eye"></i>
                    </button>
                </div>
                <!-- Strength bar -->
                <div class="password-strength" id="password-strength">
                    <div class="strength-bar" id="strength-bar"></div>
                </div>
                <span class="strength-label" id="strength-label"></span>
            </div>

            <div class="form-floating-custom">
                <label for="confirm">Confirm Password</label>
                <div class="input-wrapper">
                    <i class="bi bi-lock-fill input-icon"></i>
                    <input
                        type="password"
                        id="confirm"
                        name="confirm"
                        class="form-input"
                        placeholder="Repeat password"
                        autocomplete="new-password"
                        required
                    >
                </div>
            </div>

            <!-- Perks row -->
            <div class="perks-row">
                <div class="perk"><i class="bi bi-stars"></i> 100 free credits</div>
                <div class="perk"><i class="bi bi-translate"></i> 3 languages</div>
                <div class="perk"><i class="bi bi-mortarboard"></i> AI quizzes</div>
            </div>

            <button type="submit" class="btn-auth" id="signup-submit-btn">
                <span class="btn-text">
                    <i class="bi bi-person-plus me-2"></i>Create Account
                </span>
                <span class="btn-loader d-none" id="signup-loader">
                    <span class="spinner"></span> Creating...
                </span>
            </button>
        </form>

        <div class="auth-divider"><span>or</span></div>

        <p class="auth-switch">
            Already have an account?
            <a href="/login.php" id="goto-login-link">Sign in</a>
        </p>

    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="/assets/js/auth.js"></script>
</body>
</html>
