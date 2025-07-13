<?php
// File: /opt/marslog/app/backend/auth/access_guard.php

function require_role($required_role) {
    if (!isset($_SESSION['role']) || $_SESSION['role'] !== $required_role) {
        echo "<h1 class='text-red-500 text-center mt-10'>403 Forbidden: Access Denied</h1>";
        exit;
    }
}
