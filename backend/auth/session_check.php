<?php
<?php
function checkAuthentication($redirectToLogin = true) {
    if (session_status() === PHP_SESSION_NONE) {
        session_start();
    }

    // Check if user is logged in
    if (!isset($_SESSION['logged_in']) || $_SESSION['logged_in'] !== true) {
        if ($redirectToLogin) {
            header('Location: /auth/login.php');
            exit;
        }
        return false;
    }

    // Check session timeout (1 hour)
    $sessionTimeout = 3600; // 1 hour
    if (isset($_SESSION['login_time']) && (time() - $_SESSION['login_time'] > $sessionTimeout)) {
        // Destroy session and remove cookie
        $_SESSION = [];
        if (ini_get("session.use_cookies")) {
            $params = session_get_cookie_params();
            setcookie(session_name(), '', time() - 42000,
                $params["path"], $params["domain"],
                $params["secure"], $params["httponly"]
            );
        }
        session_destroy();
        if ($redirectToLogin) {
            header('Location: /auth/login.php?timeout=1');
            exit;
        }
        return false;
    }

    return true;
}

function getUserInfo() {
    if (!checkAuthentication(false)) {
        return null;
    }
    // Return null if username or role is missing
    if (empty($_SESSION['username']) || empty($_SESSION['role'])) {
        return null;
    }
    return [
        'username' => $_SESSION['username'],
        'role' => $_SESSION['role'],
        'login_time' => $_SESSION['login_time'] ?? time()
    ];
}

function isAdmin() {
    $user = getUserInfo();
    return $user && in_array($user['role'], ['admin', 'superadmin']);
}

function requireRole($requiredRole) {
    $user = getUserInfo();
    if (!$user) {
        header('Location: /auth/login.php');
        exit;
    }

    $roleHierarchy = ['user' => 1, 'admin' => 2, 'superadmin' => 3];
    $userLevel = $roleHierarchy[$user['role']] ?? 0;
    $requiredLevel = $roleHierarchy[$requiredRole] ?? 0;

    if ($userLevel < $requiredLevel) {
        http_response_code(403);
        header('Location: /error/403.php');
        exit;
    }
}
?>