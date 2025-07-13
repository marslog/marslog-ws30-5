document.addEventListener('DOMContentLoaded', () => {
  // Form Elements
  const loginForm = document.getElementById('loginForm');
  const usernameInput = document.getElementById('username');
  const passwordInput = document.getElementById('password');
  const signInButton = document.getElementById('signInButton');
  const togglePassword = document.getElementById('togglePassword');

  // Create particles for visual effect
  createParticles();

  // Password Toggle Functionality with animation
  togglePassword.addEventListener('click', () => {
    const isHidden = passwordInput.type === 'password';
    passwordInput.type = isHidden ? 'text' : 'password';
    
    // Animate icon change
    togglePassword.style.transform = 'scale(0.8)';
    setTimeout(() => {
      togglePassword.innerHTML = isHidden
        ? '<i class="fas fa-eye-slash"></i>'
        : '<i class="fas fa-eye"></i>';
      togglePassword.style.transform = 'scale(1)';
    }, 150);
  });

  // Enhanced form submission with MARSLOG.V1 pattern
  loginForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    // Validate inputs
    if (!username || !password) {
      showValidationError('Please fill in all fields');
      return;
    }

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    // Update button state with Mars-themed loading
    updateButtonState('loading');

    try {
      const response = await fetch('../../backend/auth/authenticate.php', {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (data.status === 'success') {
        updateButtonState('success');
        
        // Show success message with enhanced animation
        Swal.fire({
          title: 'Connection Established!',
          html: `
            <div class="text-center">
              <div class="mb-4">
                <i class="fas fa-rocket text-4xl text-purple-400 animate-bounce"></i>
              </div>
              <p class="text-gray-300">Launching to MARSLOG Command Center...</p>
              <div class="mt-4 w-full bg-gray-700 rounded-full h-2">
                <div class="bg-gradient-to-r from-purple-500 to-purple-600 h-2 rounded-full animate-pulse" style="width: 100%"></div>
              </div>
            </div>
          `,
          background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
          color: '#fff',
          allowOutsideClick: false,
          allowEscapeKey: false,
          showConfirmButton: false,
          timer: 2000,
          customClass: {
            popup: 'border border-purple-500/30 rounded-3xl',
          },
          didOpen: () => {
            // Add particle effect to success popup
            const popup = Swal.getPopup();
            popup.style.overflow = 'hidden';
          }
        });
        
        // Redirect after animation
        setTimeout(() => {
          window.location.href = data.redirect_url;
        }, 2000);
        
      } else {
        updateButtonState('error');
        showErrorAlert('Authentication Failed', data.message || 'Invalid credentials. Please try again.');
      }
    } catch (error) {
      console.error('Login error:', error);
      updateButtonState('error');
      showErrorAlert('Connection Error', 'Unable to connect to Mars base. Please try again later.');
    }
  });

  // Enhanced button state management
  function updateButtonState(state) {
    const button = signInButton;
    
    switch(state) {
      case 'loading':
        button.innerHTML = `
          <div class="relative flex items-center justify-center gap-2">
            <i class="fas fa-spinner fa-spin"></i>
            <span class="font-semibold">Connecting to Mars Base...</span>
          </div>
        `;
        button.disabled = true;
        button.classList.add('opacity-80');
        break;
        
      case 'success':
        button.innerHTML = `
          <div class="relative flex items-center justify-center gap-2">
            <i class="fas fa-check text-green-400"></i>
            <span class="font-semibold">Connected!</span>
          </div>
        `;
        button.classList.remove('opacity-80');
        button.classList.add('bg-green-600');
        break;
        
      case 'error':
        button.innerHTML = `
          <div class="relative flex items-center justify-center gap-2">
            <i class="fas fa-exclamation-triangle text-red-400"></i>
            <span class="font-semibold">Try Again</span>
          </div>
        `;
        button.classList.remove('opacity-80', 'bg-green-600');
        button.classList.add('bg-red-600');
        button.disabled = false;
        
        // Reset button after 3 seconds
        setTimeout(() => {
          resetButtonState();
        }, 3000);
        break;
        
      default:
        resetButtonState();
    }
  }

  function resetButtonState() {
    signInButton.innerHTML = `
      <div class="relative flex items-center justify-center gap-2">
        <i class="fas fa-rocket"></i>
        <span class="font-semibold">Access MARSLOG</span>
        <i class="fas fa-arrow-right"></i>
      </div>
    `;
    signInButton.disabled = false;
    signInButton.classList.remove('opacity-80', 'bg-green-600', 'bg-red-600');
  }

  // MARSLOG.V1 style error alert function
  function showErrorAlert(title, message) {
    Swal.fire({
      icon: 'error',
      title: title,
      html: message,
      background: '#1a1a2e',
      color: '#fff',
      confirmButtonColor: '#8b5cf6',
      confirmButtonText: 'Try Again'
    });
  }

  // Validation error function
  function showValidationError(message, title = '🚀 Authentication Required') {
    Swal.fire({
      icon: 'warning',
      title: title,
      html: message,
      background: '#1a1a2e',
      color: '#fff',
      confirmButtonColor: '#8b5cf6',
      confirmButtonText: 'Try Again'
    });
  }

  // Create animated particles background
  function createParticles() {
    const particlesContainer = document.querySelector('.particles');
    if (!particlesContainer) return;

    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
      const particle = document.createElement('div');
      particle.className = 'particle';
      
      // Random positioning and animation
      particle.style.left = Math.random() * 100 + '%';
      particle.style.top = Math.random() * 100 + '%';
      particle.style.animationDelay = Math.random() * 20 + 's';
      particle.style.animationDuration = (Math.random() * 10 + 10) + 's';
      
      particlesContainer.appendChild(particle);
    }
  }

  // Enhanced input focus effects
  [usernameInput, passwordInput].forEach(input => {
    input.addEventListener('focus', () => {
      input.parentElement.classList.add('input-focused');
    });
    
    input.addEventListener('blur', () => {
      input.parentElement.classList.remove('input-focused');
    });
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    // Enter key shortcut
    if (e.key === 'Enter' && (usernameInput.focus || passwordInput.focus)) {
      loginForm.dispatchEvent(new Event('submit'));
    }
    
    // Escape key to clear form
    if (e.key === 'Escape') {
      usernameInput.value = '';
      passwordInput.value = '';
      usernameInput.focus();
    }
  });

  // Auto-focus username field
  setTimeout(() => {
    usernameInput.focus();
  }, 500);

  console.log('🚀 MARSLOG Login System Initialized - Enhanced with MARSLOG.V1 patterns');
});
