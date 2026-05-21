<?php

declare(strict_types=1);

require_once __DIR__ . '/../config/config.php';


if (session_status() === PHP_SESSION_NONE) {
    session_start();
}

// Route: / → login or chat
$uri = rtrim(parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH), '/');

$publicRoutes = ['', '/login', '/signup'];
$isPublic     = in_array($uri, $publicRoutes, true);

if (!$isPublic && empty($_SESSION['logged_in'])) {
    header('Location: /login.php');
    exit;
}

switch ($uri) {
    case '':
    case '/':
        if (!empty($_SESSION['logged_in'])) {
            header('Location: /chat.php');
        } else {
            header('Location: /login.php');
        }
        exit;
    default:
        http_response_code(404);
        echo '<h1>404 Not Found</h1>';
        exit;
}
