<?php
session_start();
/*
 * MARSLOG Logout Handler
 * ตาม pattern ของ MARSLOG.V1
 * จัดการการ logout และเปลี่ยนเส้นทางไปหน้า login
 */

// Include session handler
require_once(__DIR__ . '/session_handler.php');

// ทำการ logout
SessionHandler::logout();

// เปลี่ยนเส้นทางไปหน้า login พร้อมข้อความ
header('Location: /auth/login.php?msg=' . urlencode('You have been successfully logged out.'));
exit;

?>