// Scout Accelerator Sign Up Page JavaScript

// Load API utility
const script = document.createElement('script');
script.src = 'js/api.js';
script.onload = function() {
    console.log('API utility loaded');
};
document.head.appendChild(script);

document.addEventListener('DOMContentLoaded', function() {
    // Form elements
    const signupForm = document.getElementById('signupForm');
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const strengthBar = document.getElementById('strengthBar');
    const roleSelect = document.getElementById('role');
    const scoutmasterOptions = document.getElementById('scoutmasterOptions');
    const scoutOptions = document.getElementById('scoutOptions');
    const joinTroopRadio = document.getElementById('joinTroop');
    const createTroopRadio = document.getElementById('createTroop');
    const joinTroopSection = document.getElementById('joinTroopSection');
    const createTroopSection = document.getElementById('createTroopSection');

    // Password strength checker
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        const strength = checkPasswordStrength(password);
        updatePasswordStrengthBar(strength);
    });

    // Role selection handler
    roleSelect.addEventListener('change', function() {
        const role = this.value;

        if (role === 'scoutmaster') {
            scoutmasterOptions.style.display = 'block';
            scoutOptions.style.display = 'none';
        } else if (role === 'scout') {
            scoutmasterOptions.style.display = 'none';
            scoutOptions.style.display = 'block';
        } else {
            scoutmasterOptions.style.display = 'none';
            scoutOptions.style.display = 'none';
        }
    });

    // Scoutmaster choice handler
    joinTroopRadio.addEventListener('change', function() {
        if (this.checked) {
            joinTroopSection.style.display = 'block';
            createTroopSection.style.display = 'none';
        }
    });

    createTroopRadio.addEventListener('change', function() {
        if (this.checked) {
            createTroopSection.style.display = 'block';
            joinTroopSection.style.display = 'none';
        }
    });

    // Form submission
    signupForm.addEventListener('submit', function(e) {
        e.preventDefault();

        if (validateForm()) {
            submitForm();
        }
    });
});

// Step navigation functions
function nextStep(stepNumber) {
    if (validateStep(stepNumber - 1)) {
        document.getElementById('step' + (stepNumber - 1)).style.display = 'none';
        document.getElementById('step' + stepNumber).style.display = 'block';
    }
}

function prevStep(stepNumber) {
    document.getElementById('step' + (stepNumber + 1)).style.display = 'none';
    document.getElementById('step' + stepNumber).style.display = 'block';
}

// Form validation
function validateStep(stepNumber) {
    if (stepNumber === 1) {
        const fullName = document.getElementById('fullName').value;
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        const role = document.getElementById('role').value;

        if (!fullName || !email || !password || !confirmPassword || !role) {
            alert('Please fill in all required fields.');
            return false;
        }

        if (password !== confirmPassword) {
            alert('Passwords do not match.');
            return false;
        }

        if (password.length < 8) {
            alert('Password must be at least 8 characters long.');
            return false;
        }

        if (!isValidEmail(email)) {
            alert('Please enter a valid email address.');
            return false;
        }
    }

    return true;
}

function validateForm() {
    const role = document.getElementById('role').value;

    if (role === 'scoutmaster') {
        const scoutmasterChoice = document.querySelector('input[name="scoutmasterChoice"]:checked');
        if (!scoutmasterChoice) {
            alert('Please select whether you want to join or create a troop.');
            return false;
        }

        if (scoutmasterChoice.value === 'join') {
            const troopCode = document.getElementById('troopCode').value;
            if (!troopCode) {
                alert('Please enter a troop code.');
                return false;
            }
        } else if (scoutmasterChoice.value === 'create') {
            const troopName = document.getElementById('troopName').value;
            if (!troopName) {
                alert('Please enter a troop name.');
                return false;
            }
        }
    } else if (role === 'scout') {
        const scoutTroopCode = document.getElementById('scoutTroopCode').value;
        if (!scoutTroopCode) {
            alert('Please enter your troop code.');
            return false;
        }
    }

    return true;
}

// Password strength checker
function checkPasswordStrength(password) {
    let strength = 0;

    if (password.length >= 8) strength += 25;
    if (password.match(/[a-z]/)) strength += 25;
    if (password.match(/[A-Z]/)) strength += 25;
    if (password.match(/[0-9]/)) strength += 15;
    if (password.match(/[^a-zA-Z0-9]/)) strength += 10;

    return Math.min(strength, 100);
}

function updatePasswordStrengthBar(strength) {
    const strengthBar = document.getElementById('strengthBar');
    strengthBar.style.width = strength + '%';

    // Change color based on strength
    if (strength < 25) {
        strengthBar.style.background = '#ff4444';
    } else if (strength < 50) {
        strengthBar.style.background = '#ffaa00';
    } else if (strength < 75) {
        strengthBar.style.background = '#00aa00';
    } else {
        strengthBar.style.background = '#00dd00';
    }
}

// Email validation
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Form submission
async function submitForm() {
    const formData = {
        full_name: document.getElementById('fullName').value,
        email: document.getElementById('email').value,
        password: document.getElementById('password').value,
        role: document.getElementById('role').value
    };

    // Add role-specific data
    if (formData.role === 'scoutmaster') {
        const scoutmasterChoice = document.querySelector('input[name="scoutmasterChoice"]:checked').value;

        if (scoutmasterChoice === 'join') {
            formData.troop_code = document.getElementById('troopCode').value;
        } else if (scoutmasterChoice === 'create') {
            formData.troop_name = document.getElementById('troopName').value;
        }
    } else if (formData.role === 'scout') {
        formData.troop_code = document.getElementById('scoutTroopCode').value;
    }

    try {
        // Show loading state
        const submitBtn = document.querySelector('button[type="submit"]');
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Creating Account...';
        submitBtn.disabled = true;

        // Make real API call
        const response = await API.signup(formData);

        // Show success message
        showNotification('Account created successfully! You can now sign in.', 'success');

        // Redirect to sign in page
        setTimeout(() => {
            window.location.href = 'signin.html';
        }, 1500);

    } catch (error) {
        console.error('Error creating account:', error);
        showNotification(error.message || 'There was an error creating your account. Please try again.', 'error');
    } finally {
        // Reset button state
        const submitBtn = document.querySelector('button[type="submit"]');
        submitBtn.textContent = 'Create Account';
        submitBtn.disabled = false;
    }
}
