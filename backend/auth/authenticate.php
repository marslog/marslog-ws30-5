<?php
session_start();
$inputUser = $_POST['username'];
$inputPass = $_POST['password'];
$userFile = '/opt/marslog/app/frontend/data/users/users.json';
if (!file_exists($userFile)) {
    die("User database not found.");
}

$users = json_decode(file_get_contents($userFile), true);
foreach ($users as $user) {
    if ($user['username'] === $inputUser && password_verify($inputPass, $user['password'])) {
        $_SESSION['logged_in'] = true;
        $_SESSION['username'] = $user['username'];
        $_SESSION['role'] = $user['role'];
        header("Location: /dashboard.php");
        exit();
    }
}
header("Location: /auth/login_failed.php");
exit();
?>