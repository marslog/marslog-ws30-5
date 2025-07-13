<?php
// File: /opt/marslog/app/frontend/auth/logout.php
session_start();
session_unset();
session_destroy();
header("Location: /auth/login.php");
exit;
