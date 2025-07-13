<?php
/**
 * MARSLOG License Access Guard
 * Protects pages based on license status
 */

require_once(__DIR__ . '/license_handler_api.php');

// Check for development bypass
$devBypassFile = __DIR__ . '/dev_bypass.php';
if (file_exists($devBypassFile)) {
    require_once($devBypassFile);
}

class LicenseAccessGuard {
    private $licenseHandler;
    private $currentPage;
    public function __construct() {
        $this->licenseHandler = new LicenseHandler();
        $this->currentPage = $this->getCurrentPageName();
    }
    private function getCurrentPageName() {
        $path = $_SERVER['REQUEST_URI'];
        $filename = basename(parse_url($path, PHP_URL_PATH), '.php');
        return $filename;
    }
    public function checkAccess() {
        $validation = $this->licenseHandler->validateLicense();
        $limits = $this->licenseHandler->getLicenseLimits();
        if (isset($validation['trial_expired']) && $validation['trial_expired']) {
            $allowedPages = ['dashboard_monitor', 'dashboard_admin', 'license_info', 'login', 'logout'];
            if (!in_array($this->currentPage, $allowedPages)) {
                $this->redirectToLicense('Trial period has expired. Please activate your license to continue.');
                return false;
            }
        }
        if (!$limits['active'] && !isset($validation['trial_mode'])) {
            $allowedPages = ['dashboard_monitor', 'dashboard_admin', 'license_info', 'login', 'logout'];
            if (!in_array($this->currentPage, $allowedPages)) {
                $this->redirectToLicense('License expired or invalid. Please activate your license.');
                return false;
            }
        }
        if (isset($validation['trial_mode']) && $validation['warning']) {
            $hoursRemaining = $validation['hours_remaining'] ?? 0;
            $this->showTrialWarning($hoursRemaining);
        }
        if ($limits['expires_soon'] && $limits['days_remaining'] <= 7) {
            $this->showExpiryWarning($limits['days_remaining']);
        }
        return true;
    }
    private function redirectToLicense($message) {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        $_SESSION['license_error'] = $message;
        header('Location: /ui/license_info.php');
        exit;
    }
    private function showExpiryWarning($daysRemaining) {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        $_SESSION['license_warning'] = [
            'days_remaining' => $daysRemaining,
            'show_warning' => true
        ];
    }
    private function showTrialWarning($hoursRemaining) {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        $_SESSION['trial_warning'] = [
            'hours_remaining' => $hoursRemaining,
            'show_warning' => true
        ];
    }
    public function getDeviceLimit() {
        return $this->licenseHandler->getLicenseLimits()['devices'];
    }
    public function getEPSLimit() {
        return $this->licenseHandler->getLicenseLimits()['eps'];
    }
    public function canAddDevice($currentCount) {
        return $this->licenseHandler->canAddDevice($currentCount);
    }
    public function getLicenseHandler() {
        return $this->licenseHandler;
    }
    public function renderWarningScript() {
        if (session_status() === PHP_SESSION_NONE) {
            session_start();
        }
        $script = '';
        if (isset($_SESSION['trial_warning']) && $_SESSION['trial_warning']['show_warning']) {
            $hoursRemaining = $_SESSION['trial_warning']['hours_remaining'];
            unset($_SESSION['trial_warning']);
            $script .= "<script>document.addEventListener('DOMContentLoaded', function() {if (typeof Swal !== 'undefined') {Swal.fire({icon: 'warning',title: 'Trial Expiring Soon',html: '<div class=\"text-center\"><i class=\"fas fa-clock text-4xl text-yellow-400 mb-3\"></i><p>Your MARSLOG trial expires in <strong>{$hoursRemaining} hours</strong>.</p><p class=\"text-sm text-gray-400 mt-2\">Activate your license to continue using all features.</p></div>',showConfirmButton: true,confirmButtonText: 'Activate License',showCancelButton: true,cancelButtonText: 'Continue Trial',background: 'var(--color-card)',color: 'var(--color-text)'}).then((result) => {if (result.isConfirmed) {window.location.href = '/ui/license_info.php';}});}});</script>";
        }
        if (isset($_SESSION['license_warning']) && $_SESSION['license_warning']['show_warning']) {
            $daysRemaining = $_SESSION['license_warning']['days_remaining'];
            unset($_SESSION['license_warning']);
            $script .= "<script>document.addEventListener('DOMContentLoaded', function() {if (typeof Swal !== 'undefined') {Swal.fire({icon: 'warning',title: 'License Expiring Soon',html: '<div class=\"text-center\"><i class=\"fas fa-exclamation-triangle text-4xl text-yellow-400 mb-3\"></i><p>Your MARSLOG license will expire in <strong>{$daysRemaining} days</strong>.</p><p class=\"text-sm text-gray-400 mt-2\">Please contact sales to renew your license.</p></div>',showConfirmButton: true,confirmButtonText: 'Manage License',showCancelButton: true,cancelButtonText: 'Remind Later',background: 'var(--color-card)',color: 'var(--color-text)'}).then((result) => {if (result.isConfirmed) {window.location.href = '/ui/license_info.php';}});}});</script>";
        }
        return $script;
    }
}
function getLicenseGuard() {
    static $instance = null;
    if ($instance === null) {
        $instance = new LicenseAccessGuard();
    }
    return $instance;
}
function requireLicenseAccess() {
    $guard = getLicenseGuard();
    return $guard->checkAccess();
}
function renderLicenseWarningScript() {
    $guard = getLicenseGuard();
    return $guard->renderWarningScript();
}
