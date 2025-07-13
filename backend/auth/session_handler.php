<?php
session_start();

// Check if user is logged in
if (!isset($_SESSION['logged_in']) || !$_SESSION['logged_in']) {
    // Redirect to login page
    header('Location: /auth/login.php');
    exit();
}

// Check session timeout
$session_timeout = 3600; // 1 hour
if (isset($_SESSION['login_time']) && (time() - $_SESSION['login_time']) > $session_timeout) {
    session_destroy();
    header('Location: /auth/login.php?msg=' . urlencode('Session expired. Please login again.'));
    exit();
}

// Update last activity time
$_SESSION['last_activity'] = time();
?>