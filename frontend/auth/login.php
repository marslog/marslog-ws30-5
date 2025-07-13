<?php
session_start();
if (isset($_SESSION['logged_in']) && $_SESSION['logged_in'] === true) {
    header("Location: /dashboard.php");
    exit();
}
?>
<!DOCTYPE html>
<html>
<head>
    <title>Login - MARSLOG</title>
    <script src="/static/sweetalert2.min.js"></script>
    <link href="/static/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-gray-900 text-white flex items-center justify-center h-screen">
    <form method="POST" action="/backend/authenticate.php" class="bg-gray-800 p-8 rounded-lg shadow-md w-full max-w-sm">
        <h2 class="text-2xl font-bold mb-4 text-center">Login to MARSLOG</h2>
        <input type="text" name="username" placeholder="Username" class="w-full p-2 mb-4 rounded bg-gray-700 text-white" required>
        <input type="password" name="password" placeholder="Password" class="w-full p-2 mb-4 rounded bg-gray-700 text-white" required>
        <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
            Login
        </button>
    </form>
</body>
</html>