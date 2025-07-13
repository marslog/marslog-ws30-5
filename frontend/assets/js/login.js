// ===== MARSLOG Login JavaScript (Enhanced SweetAlert Configuration) =====

// ฟังก์ชันสำหรับแสดง SweetAlert เมื่อ Login สำเร็จ
async function showLoginSuccessAlert() {
    await Swal.fire({
        icon: 'success',
        title: 'Login Successful!',
        html: '<div style="text-align: center; padding: 10px;">Welcome to MARSLOG System</div>',
        showConfirmButton: true,
        confirmButtonText: '📊 Go to Dashboard',
        allowOutsideClick: false
    });
    // หมายเหตุ: Redirect จะถูกจัดการใน client-side หลังจากนี้
}

// ฟังก์ชันสำหรับแสดง SweetAlert เมื่อมีข้อผิดพลาดจากการตรวจสอบ
async function showValidationError() {
    await Swal.fire({
        icon: 'warning',
        title: '⚠️ Please Check Input',
        html: '<div style="text-align: center; padding: 10px;">Please enter both username and password</div>',
        showConfirmButton: true,
        confirmButtonText: '🔧 Fix'
    });
}

// ฟังก์ชันสำหรับแสดง SweetAlert เมื่อมีข้อผิดพลาดในการ Login
async function showErrorAlert(message = 'Please check your login credentials and try again') {
    const sanitizedMessage = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(message) : message.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    if (typeof Swal === 'undefined') {
        alert(sanitizedMessage);
        return;
    }
    await Swal.fire({
        icon: 'error',
        title: '⚠️ Login Error',
        html: `<div style="text-align:center;padding:18px;">${sanitizedMessage}</div>`,
        showConfirmButton: true,
        confirmButtonText: '🔄 Try Again'
    });
}

// ฟังก์ชันสำหรับแสดง SweetAlert สถานะกำลังโหลด
async function showLoadingAlert() {
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

// ฟังก์ชันสำหรับรับ CSRF token
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// --- Event Listeners and Form Submission Logic ---

// แก้ไขสำหรับ iOS zoom ในช่อง input
if ('ontouchstart' in window) {
    document.documentElement.style.fontSize = '16px';
}

// Consolidated DOMContentLoaded Event Listener
document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const togglePassword = document.getElementById('togglePassword');
    const signInButton = document.getElementById('signInButton');
    const spinner = document.getElementById('spinner');

    // ตรวจสอบว่า DOM elements มีอยู่
    if (!loginForm || !usernameInput || !passwordInput || !signInButton || !spinner) {
        console.warn('Required DOM elements not found');
        Swal.fire({
            icon: 'error',
            title: 'Initialization Error',
            text: 'Required form elements are missing. Please contact support.'
        });
        return;
    }

    // เพิ่ม accessibility สำหรับ toggle password
    if (togglePassword) {
        togglePassword.setAttribute('tabindex', '0');
        togglePassword.setAttribute('aria-label', 'Toggle password visibility');
        togglePassword.addEventListener('click', function() {
            const isHidden = passwordInput.type === 'password';
            passwordInput.type = isHidden ? 'text' : 'password';
            togglePassword.innerHTML = isHidden
                ? '<i class="fas fa-eye-slash"></i>'
                : '<i class="fas fa-eye"></i>';
        });
        togglePassword.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                togglePassword.click();
            }
        });
    }

    // การจัดการ submit ฟอร์ม
    loginForm.addEventListener('submit', async function(event) {
        event.preventDefault();

        // ตรวจสอบ input
        if (!usernameInput.value.trim() || !passwordInput.value.trim()) {
            await showValidationError();
            signInButton.disabled = false;
            spinner.classList.add('hidden');
            return;
        }

        // แสดง spinner และ disable ปุ่ม
        signInButton.disabled = true;
        spinner.classList.remove('hidden');

        // แสดง loading alert
        let loadingAlert;
        try {
            loadingAlert = await showLoadingAlert();
        } catch (e) {
            console.error('Failed to show loading alert:', e);
            signInButton.disabled = false;
            spinner.classList.add('hidden');
            return;
        }

        // สร้าง FormData และเพิ่ม CSRF token
        const formData = new FormData(loginForm);
        formData.append('csrf_token', getCsrfToken());

        // สร้าง AbortController สำหรับ timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            controller.abort();
            if (loadingAlert) loadingAlert.close();
            showErrorAlert('The server took too long to respond. Please try again.');
            signInButton.disabled = false;
            spinner.classList.add('hidden');
        }, 10000); // 10 วินาที timeout

        try {
            const response = await fetch('/backend/auth/authenticate.php', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            // ปิด loading alert
            if (loadingAlert) loadingAlert.close();

            // ตรวจสอบ HTTP status
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ message: 'Server error during authentication.' }));
                await showErrorAlert(errorData.message);
                return;
            }

            // ตรวจสอบ JSON response
            const data = await response.json();
            if (data.success) {
                await showLoginSuccessAlert();
                window.location.href = data.redirect || '/dashboard.php';
            } else {
                await showErrorAlert(data.message || 'Authentication failed.');
            }
        } catch (error) {
            clearTimeout(timeoutId);
            if (loadingAlert) loadingAlert.close(); // ตรวจสอบและปิด loading alert ในกรณี error
            await showErrorAlert(error.name === 'AbortError' 
                ? 'The server took too long to respond. Please try again.'
                : 'Could not connect to the server. Please check your internet connection.');
            console.error('Fetch error:', error);
        } finally {
            signInButton.disabled = false;
            spinner.classList.add('hidden');
        }
    });

    // การจัดการ Enter key
    document.addEventListener('keypress', async function(e) {
        if (e.key === 'Enter') {
            const swalConfirmButton = Swal.getConfirmButton();
            if (Swal.isVisible() && swalConfirmButton && !Swal.isLoading()) {
                swalConfirmButton.click();
                e.preventDefault();
            } else if (!Swal.isVisible()) {
                if (!usernameInput.value.trim() || !passwordInput.value.trim()) {
                    await showValidationError();
                    e.preventDefault();
                    return;
                }
                loginForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                e.preventDefault();
            }
        }
    });

    // ตรวจสอบ URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('error') === '1') {
        Swal.fire({
            icon: 'error',
            title: 'Login Failed!',
            text: 'Please check your username and password.',
            showConfirmButton: true,
            confirmButtonText: 'OK'
        }).then(() => {
            urlParams.delete('error');
            const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
            window.history.replaceState({}, document.title, newUrl);
        });
    }
});

console.log('🚀 MARSLOG Login System v2.2 - Ready!');