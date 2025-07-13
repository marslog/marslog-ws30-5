<?php
/**
 * MARSLOG-ClickHouse License Handler
 * Enhanced license validation and management for ClickHouse version
 */

class MarslogLicenseHandler {
    private $licenseFile;
    private $trialFile;
    private $pythonValidator;
    
    public function __construct($licenseFile = null) {
        // Try multiple possible paths for license file
        if ($licenseFile) {
            $this->licenseFile = $licenseFile;
        } else {
            $possiblePaths = [
                '/app/license/license_0.json.enc',
                '/var/www/html/license/license_0.json.enc',
                __DIR__ . '/../license/license_0.json.enc',
                __DIR__ . '/../../data/license_0.json.enc',
                '/tmp/license_0.json.enc'
            ];
            
            $this->licenseFile = null;
            foreach ($possiblePaths as $path) {
                if (file_exists($path) && is_readable($path) && filesize($path) > 0) {
                    $this->licenseFile = $path;
                    break;
                }
            }
            
            // Default to the primary path if none found
            if (!$this->licenseFile) {
                $this->licenseFile = $possiblePaths[0];
            }
        }
        
        // Trial file paths
        $trialPaths = [
            '/app/data/trial_started.json',
            '/var/www/html/data/trial_started.json',
            __DIR__ . '/../../data/trial_started.json',
            '/tmp/trial_started.json'
        ];
        
        $this->trialFile = null;
        foreach ($trialPaths as $trialDir) {
            $dir = dirname($trialDir);
            if (is_dir($dir) && is_writable($dir)) {
                $this->trialFile = $trialDir;
                break;
            }
        }
        
        // Final fallback to system temp directory
        if ($this->trialFile === null) {
            $this->trialFile = sys_get_temp_dir() . '/trial_started.json';
        }
        
        $this->pythonValidator = __DIR__ . '/license_validator.py';
    }
    
    /**
     * Validate license using Python validator
     */
    public function validateLicense() {
        if (!file_exists($this->licenseFile)) {
            return [
                'valid' => false,
                'status' => 'No License File',
                'error' => 'License file not found',
                'trial_mode' => $this->checkTrialStatus()
            ];
        }
        
        // Check if Python and required packages are available
        if (!$this->isPythonAvailable()) {
            // Fallback: check trial status
            $trialStatus = $this->checkTrialStatus();
            if ($trialStatus['active']) {
                return [
                    'valid' => true,
                    'status' => 'Trial Mode',
                    'trial_mode' => $trialStatus,
                    'days_remaining' => $trialStatus['days_remaining']
                ];
            } else {
                return [
                    'valid' => false,
                    'status' => 'Trial Expired',
                    'error' => 'Trial period has expired and no valid license found',
                    'trial_mode' => $trialStatus
                ];
            }
        }
        
        // Execute Python validator
        $command = "python3 " . escapeshellarg($this->pythonValidator) . " " . escapeshellarg($this->licenseFile);
        $output = [];
        $returnCode = 0;
        
        exec($command . " 2>&1", $output, $returnCode);
        
        if ($returnCode === 0 && !empty($output)) {
            $result = json_decode(implode("\n", $output), true);
            if ($result) {
                return $result;
            }
        }
        
        // If license validation fails, check trial status
        $trialStatus = $this->checkTrialStatus();
        return [
            'valid' => $trialStatus['active'],
            'status' => $trialStatus['active'] ? 'Trial Mode' : 'Invalid License',
            'trial_mode' => $trialStatus,
            'error' => $trialStatus['active'] ? null : 'License validation failed and trial expired'
        ];
    }
    
    /**
     * Check if Python is available and can run the validator
     */
    private function isPythonAvailable() {
        if (!file_exists($this->pythonValidator)) {
            return false;
        }
        
        // Check Python availability
        $pythonCommands = ['python3', 'python'];
        
        foreach ($pythonCommands as $cmd) {
            $output = [];
            $returnCode = 0;
            exec("which $cmd 2>&1", $output, $returnCode);
            
            if ($returnCode === 0) {
                // Check if required packages are available
                exec("$cmd -c 'import cryptography, json, base64, hashlib' 2>&1", $output, $returnCode);
                if ($returnCode === 0) {
                    return true;
                }
            }
        }
        
        return false;
    }
    
    /**
     * Check trial status
     */
    public function checkTrialStatus() {
        $trialData = $this->loadTrialData();
        
        if (!$trialData['trial_started']) {
            return [
                'active' => false,
                'started' => false,
                'start_date' => null,
                'expire_date' => null,
                'days_remaining' => 0,
                'can_start' => true
            ];
        }
        
        $startDate = new DateTime($trialData['start_date']);
        $currentDate = new DateTime();
        $expireDate = clone $startDate;
        $expireDate->add(new DateInterval('P30D')); // 30 days trial
        
        $daysRemaining = $currentDate < $expireDate 
            ? $expireDate->diff($currentDate)->days + 1 
            : 0;
        
        return [
            'active' => $daysRemaining > 0,
            'started' => true,
            'start_date' => $startDate->format('Y-m-d H:i:s'),
            'expire_date' => $expireDate->format('Y-m-d H:i:s'),
            'days_remaining' => max(0, $daysRemaining),
            'can_start' => false
        ];
    }
    
    /**
     * Start trial period
     */
    public function startTrial() {
        $trialData = $this->loadTrialData();
        
        if ($trialData['trial_started']) {
            return [
                'success' => false,
                'message' => 'Trial already started',
                'trial_status' => $this->checkTrialStatus()
            ];
        }
        
        $newTrialData = [
            'trial_started' => true,
            'start_date' => date('Y-m-d H:i:s')
        ];
        
        if ($this->saveTrialData($newTrialData)) {
            return [
                'success' => true,
                'message' => 'Trial started successfully',
                'trial_status' => $this->checkTrialStatus()
            ];
        } else {
            return [
                'success' => false,
                'message' => 'Failed to start trial - permission denied',
                'trial_status' => $this->checkTrialStatus()
            ];
        }
    }
    
    /**
     * Load trial data
     */
    private function loadTrialData() {
        if (!file_exists($this->trialFile)) {
            return [
                'trial_started' => false,
                'start_date' => null
            ];
        }
        
        try {
            $content = file_get_contents($this->trialFile);
            $data = json_decode($content, true);
            
            if (!is_array($data)) {
                return [
                    'trial_started' => false,
                    'start_date' => null
                ];
            }
            
            return [
                'trial_started' => $data['trial_started'] ?? false,
                'start_date' => $data['start_date'] ?? null
            ];
        } catch (Exception $e) {
            error_log("Trial data load error: " . $e->getMessage());
            return [
                'trial_started' => false,
                'start_date' => null
            ];
        }
    }
    
    /**
     * Save trial data with fallback paths
     */
    private function saveTrialData($data) {
        $jsonData = json_encode($data, JSON_PRETTY_PRINT);
        
        // Try to write to the configured trial file path
        $result = $this->writeFileWithFallback($this->trialFile, $jsonData);
        
        if ($result !== false) {
            // Also try to write to Flask API data directory for compatibility
            $flaskTrialFile = '/app/data/trial_started.json';
            @file_put_contents($flaskTrialFile, $jsonData);
            return true;
        }
        
        return false;
    }
    
    /**
     * Get license information for display
     */
    public function getLicenseInfo() {
        $validation = $this->validateLicense();
        $trialStatus = $this->checkTrialStatus();
        
        return [
            'license_valid' => $validation['valid'],
            'license_status' => $validation['status'],
            'trial_mode' => $trialStatus,
            'system_info' => [
                'license_file' => $this->licenseFile,
                'license_exists' => file_exists($this->licenseFile),
                'trial_file' => $this->trialFile,
                'trial_writable' => is_writable(dirname($this->trialFile)),
                'python_available' => $this->isPythonAvailable()
            ]
        ];
    }
    
    /**
     * Reset trial (admin only)
     */
    public function resetTrial() {
        if (file_exists($this->trialFile)) {
            if (unlink($this->trialFile)) {
                // Also try to remove Flask API trial file
                $flaskTrialFile = '/app/data/trial_started.json';
                @unlink($flaskTrialFile);
                
                return [
                    'success' => true,
                    'message' => 'Trial reset successfully'
                ];
            }
        }
        
        return [
            'success' => false,
            'message' => 'Failed to reset trial'
        ];
    }
    
    /**
     * Write data to file with multiple fallback attempts
     */
    private function writeFileWithFallback($filename, $data) {
        $fallbackPaths = [
            dirname($this->trialFile),  // Current trial directory
            '/app/data',                // App data directory
            '/tmp',                     // System temp
            sys_get_temp_dir(),        // PHP temp dir
            '/var/tmp'                 // Alternative temp
        ];
        
        $baseName = basename($filename);
        
        foreach ($fallbackPaths as $dir) {
            try {
                // Ensure directory exists and is writable
                if ($this->ensureDirectoryWritable($dir)) {
                    $fullPath = $dir . '/' . $baseName;
                    $result = file_put_contents($fullPath, $data);
                    if ($result !== false) {
                        // Update trial file path if it changed
                        if ($filename === $this->trialFile && $fullPath !== $this->trialFile) {
                            $this->trialFile = $fullPath;
                        }
                        return $fullPath;
                    }
                }
            } catch (Exception $e) {
                error_log("Failed to write to $dir: " . $e->getMessage());
                continue;
            }
        }
        
        error_log("Failed to write file $filename to any location");
        return false;
    }
    
    /**
     * Ensure directory is writable, create if needed
     */
    private function ensureDirectoryWritable($dir) {
        try {
            // Try to create directory if it doesn't exist
            if (!is_dir($dir)) {
                if (!mkdir($dir, 0777, true)) {
                    return false;
                }
            }
            
            // Check if directory is writable
            if (!is_writable($dir)) {
                // Try to fix permissions
                if (!chmod($dir, 0777)) {
                    return false;
                }
            }
            
            // Final test - try to write a test file
            $testFile = $dir . '/test_write.tmp';
            if (file_put_contents($testFile, 'test') === false) {
                return false;
            }
            
            // Clean up test file
            @unlink($testFile);
            
            return true;
        } catch (Exception $e) {
            error_log("License directory error: " . $e->getMessage());
            return false;
        }
    }
}

/**
 * Global function to get license handler instance
 */
function getLicenseHandler() {
    static $instance = null;
    if ($instance === null) {
        $instance = new MarslogLicenseHandler();
    }
    return $instance;
}

/**
 * Quick license check function
 */
function checkLicense() {
    $handler = getLicenseHandler();
    return $handler->validateLicense();
}

/**
 * Access guard for protected pages
 */
function requireValidLicense($allowTrial = true) {
    $license = checkLicense();
    
    if (!$license['valid']) {
        if ($allowTrial && isset($license['trial_mode']) && !$license['trial_mode']['started']) {
            // Redirect to trial start page
            header('Location: /license/trial-start.php');
            exit;
        } else {
            // Redirect to license error page
            header('Location: /license/error.php');
            exit;
        }
    }
}
?>
