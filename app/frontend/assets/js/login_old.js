// ===== MARSLOG Login JavaScript with Perfect SweetAlert =====

// 🎯 Global SweetAlert configuration for perfect centering and sizing
if (typeof Swal !== 'undefined') {
    const originalFire = Swal.fire;
    Swal.fire = function(options) {
        const defaultConfig = {
            width: '420px',
            padding: '25px',
            heightAuto: false,
            position: 'center',
            backdrop: true,
            showClass: {
                popup: 'animate__animated animate__zoomIn animate__faster'
            },
            hideClass: {
                popup: 'animate__animated animate__zoomOut animate__faster'
            },
            customClass: {
                popup: 'marslog-popup-perfect',
                title: 'marslog-popup-title',
                htmlContainer: 'marslog-popup-content',
                confirmButton: 'marslog-confirm-btn',
                cancelButton: 'marslog-cancel-btn'
            },
            buttonsStyling: false
        };
        
        // Merge with user options
        const mergedOptions = Object.assign({}, defaultConfig, options);
        return originalFire(mergedOptions);
    };
}

// 🎨 Add perfect CSS styling for SweetAlert
const style = document.createElement('style');
style.textContent = `
    .marslog-popup-perfect {
    }
    
    .marslog-popup-title {
    }
    
    .marslog-popup-content {
    }
    
    .marslog-confirm-btn {
    }
    
    .marslog-confirm-btn:hover {
    }
    
    .marslog-cancel-btn {
    }
    
    .marslog-cancel-btn:hover {
    }
    
    /* Mobile responsive */
    @media (max-width: 500px) {
        .marslog-popup-perfect {
        }
        
        .marslog-popup-title {
        }
        
        .marslog-popup-content {
        }
        
        .marslog-confirm-btn, .marslog-cancel-btn {
        }
    }
    
    /* Dark backdrop */
    .swal2-backdrop-show {
    }
`;
document.head.appendChild(style);

// 🔐 Login form functionality
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    // Add Enter key support
    document.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleLogin(e);
        }
    });
});

// 🎯 Main login handler
function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username')?.value?.trim();
    const password = document.getElementById('password')?.value;
    
    // Validation
        showValidationError();
        return;
    }
    
    // Show loading
    showLoadingAlert();
    
    // Create login request
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    fetch('/auth/authenticate.php', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessAlert().then(() => {
                window.location.href = data.redirect || '/dashboard.php';
            });
        } else {
            showErrorAlert(data.message || 'Login failed');
        }
    })
    .catch(error => {
        console.error('Login error:', error);
        showErrorAlert('Connection error occurred');
    });
}

// 🚨 Error alert for login failures
function showErrorAlert(message = 'Please check your login credentials and try again') {
    return Swal.fire({
        icon: 'error',
        title: '⚠️ Login Error',
        html: `<div style="text-align: center; padding: 10px;">${message}</div>`,
        confirmButtonText: '🔄 Try Again',
        timer: 8000,
        timerProgressBar: true
    });
}

// ✅ Success alert
function showSuccessAlert() {
    return Swal.fire({
        icon: 'success',
        title: '🚀 Login Successful!',
        html: '<div style="text-align: center; padding: 10px;">Welcome to MARSLOG System</div>',
        confirmButtonText: '📊 Go to Dashboard',
        timer: 3000,
        timerProgressBar: true,
        allowOutsideClick: false
    });
}

// ⚠️ Validation error alert
function showValidationError() {
    return Swal.fire({
        icon: 'warning',
        title: '⚠️ Please Check Input',
        html: '<div style="text-align: center; padding: 10px;">Please enter both username and password</div>',
        confirmButtonText: '🔧 Fix',
        timer: 5000,
        timerProgressBar: true
    });
}

// ⏳ Loading alert
function showLoadingAlert() {
    return Swal.fire({
        title: '🔄 Authenticating...',
        html: '<div style="text-align: center; padding: 20px;">Please wait while we verify your credentials</div>',
        allowOutsideClick: false,
        showConfirmButton: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
}

// 🧪 Test alert function
function testSweetAlert() {
    return Swal.fire({
        icon: 'info',
        title: '🧪 Test Alert System',
        html: '<div style="text-align: center; padding: 10px;">Alert system is working normally<br><small style="color: #666;">SweetAlert2 is ready!</small></div>',
        confirmButtonText: '🚀 Great!',
        timer: 4000,
        timerProgressBar: true
    });
}

// 📱 Mobile touch optimization
if ('ontouchstart' in window) {
    document.body.style.webkitTouchCallout = 'none';
    document.body.style.webkitUserSelect = 'none';
}

console.log('🚀 MARSLOG Login System v2.0 - Ready!');
