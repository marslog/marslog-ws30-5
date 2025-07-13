<?php session_start(); ?>
<!DOCTYPE html>
<html>
<head>
    <title>Login Success</title>
    <link href="/static/tailwind.min.css" rel="stylesheet">
</head>
<body class="bg-green-100 flex items-center justify-center h-screen text-center">
    <div>
        <h1 class="text-3xl text-green-600 font-bold">Login Successful</h1>
        <p class="mt-2">Welcome, <?php echo htmlspecialchars($_SESSION['username']); ?>!</p>
        <a href="/dashboard.php" class="text-blue-500 underline mt-4 block">Go to Dashboard</a>
    </div>
</body>
</html>