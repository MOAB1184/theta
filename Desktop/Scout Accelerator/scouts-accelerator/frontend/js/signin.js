// Scout Accelerator Sign In Page JavaScript

// Load API utility
const script = document.createElement('script');
script.src = 'js/api.js';
script.onload = function() {
    console.log('API utility loaded');
};
document.head.appendChild(script);

document.addEventListener('DOMContentLoaded', function() {
    // Form elements
    const signinForm = document.getElementById('signinForm');
    const passwordInput = document.getElementById('password');
    const passwordToggle = document.getElementById('passwordToggle');
    const emailInput = document.getElementById('email');

    // Password toggle functionality
    passwordToggle.addEventListener('click', function() {
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);

        // Update toggle icon
        const icon = this.querySelector('svg');
        if (type === 'text') {
            icon.innerHTML = `
                <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <line x1="1" y1="1" x2="23" y2="23" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            `;
        } else {
            icon.innerHTML = `
                <path d="M1 12C1 12 5 4 12 4C19 4 23 12 23 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/>
            `;
        }
    });



    // Form submission
    signinForm.addEventListener('submit', function(e) {
        e.preventDefault();

        if (validateForm()) {
            submitForm();
        }
    });

    // Enter key support
    signinForm.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (validateForm()) {
                submitForm();
            }
        }
    });
});

// Form validation
function validateForm() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    if (!email || !password) {
        showNotification('Please fill in all fields.', 'error');
        return false;
    }

    if (!isValidEmail(email)) {
        showNotification('Please enter a valid email address.', 'error');
        return false;
    }

    if (password.length < 8) {
        showNotification('Password must be at least 8 characters long.', 'error');
        return false;
    }

    return true;
}

// Email validation
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Form submission
async function submitForm() {
    const formData = {
        email: document.getElementById('email').value,
        password: document.getElementById('password').value,
        rememberMe: document.querySelector('input[name="rememberMe"]').checked
    };

    try {
        // Show loading state
        const submitBtn = document.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Signing In...';
        submitBtn.disabled = true;

        // Make real API call
        const response = await API.login(formData);

        // Show success message
        showNotification(`Welcome back, ${response.user.role === 'scoutmaster' ? 'Scoutmaster' : 'Scout'}!`, 'success');

        // Redirect to appropriate dashboard based on user role
        setTimeout(() => {
            if (response.user.role === 'scoutmaster') {
                window.location.href = 'scoutmaster-dashboard.html';
            } else {
                window.location.href = 'scout-dashboard.html';
            }
        }, 1000);

    } catch (error) {
        console.error('Error signing in:', error);
        showNotification(error.message || 'Invalid email or password. Please try again.', 'error');
    } finally {
        // Reset button state
        const submitBtn = document.querySelector('button[type="submit"]');
        submitBtn.textContent = 'Sign In';
        submitBtn.disabled = false;
    }
}

// Notification system
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;

    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 10000;
        min-width: 300px;
        max-width: 500px;
    `;

    const content = notification.querySelector('.notification-content');
    content.style.cssText = `
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-radius: 8px;
        font-weight: 500;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    `;

    // Set colors based on type
    if (type === 'success') {
        content.style.background = 'linear-gradient(135deg, #00D4FF, #0078FF)';
        content.style.color = 'white';
    } else if (type === 'error') {
        content.style.background = 'linear-gradient(135deg, #ff4444, #cc3333)';
        content.style.color = 'white';
    } else {
        content.style.background = 'var(--bg-tertiary)';
        content.style.color = 'var(--text-primary)';
        content.style.border = '1px solid var(--border-color)';
    }

    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: inherit;
        font-size: 20px;
        cursor: pointer;
        padding: 0;
        margin-left: 12px;
    `;

    // Add to page
    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }
    }, 5000);
}

// Add notification styles to head
const notificationStyles = document.createElement('style');
notificationStyles.textContent = `
    .notification {
        animation: slideIn 0.3s ease-out;
    }

    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
`;
document.head.appendChild(notificationStyles);
