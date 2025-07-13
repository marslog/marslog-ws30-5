<?php
// File: /opt/marslog/app/backend/auth/session_guard.php

session_start();

if (!isset($_SESSION['username'])) {
    header('Location: /auth/login.php');
    exit;
}
