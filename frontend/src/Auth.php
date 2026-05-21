<?php

declare(strict_types=1);

require_once __DIR__ . '/Database.php';

class Auth
{
    // ── Register ────────────────────────────────────────────────
    public static function register(
        string $username,
        string $email,
        string $password,
        string $fullName
    ): array {
        $db = Database::getConnection();

        // Check duplicate
        $stmt = $db->prepare('SELECT id FROM users WHERE email = ? OR username = ? LIMIT 1');
        $stmt->execute([$email, $username]);
        if ($stmt->fetch()) {
            return ['success' => false, 'message' => 'Email or username already exists.'];
        }

        $hash = password_hash($password, PASSWORD_BCRYPT);
        $stmt = $db->prepare(
            'INSERT INTO users (username, email, password, full_name) VALUES (?, ?, ?, ?)'
        );
        $stmt->execute([$username, $email, $hash, $fullName]);

        return ['success' => true, 'message' => 'Account created successfully!'];
    }

    // ── Login ────────────────────────────────────────────────────
    public static function login(string $email, string $password): array
    {
        $db   = Database::getConnection();
        $stmt = $db->prepare('SELECT * FROM users WHERE email = ? AND is_active = 1 LIMIT 1');
        $stmt->execute([$email]);
        $user = $stmt->fetch();

        if (!$user || !password_verify($password, $user['password'])) {
            return ['success' => false, 'message' => 'Invalid email or password.'];
        }

        // Start PHP session
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        $_SESSION['user_id']   = $user['id'];
        $_SESSION['username']  = $user['username'];
        $_SESSION['full_name'] = $user['full_name'];
        $_SESSION['credits']   = $user['credits'];
        $_SESSION['language']  = $user['language'];
        $_SESSION['role']      = $user['role'] ?? 'user';
        $_SESSION['logged_in'] = true;

        return ['success' => true, 'message' => 'Login successful!'];
    }

    // ── Logout ───────────────────────────────────────────────────
    public static function logout(): void
    {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        session_unset();
        session_destroy();
    }

    // ── Guard ────────────────────────────────────────────────────
    public static function requireLogin(): void
    {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        if (empty($_SESSION['logged_in'])) {
            header('Location: /login.php');
            exit;
        }
    }
}
