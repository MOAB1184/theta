// Signup form handling
document.addEventListener('DOMContentLoaded', function() {
    const signupForm = document.getElementById('signupForm');
    const nextBtn = document.getElementById('nextBtn');
    const backBtn = document.getElementById('backBtn');
    const scoutBackBtn = document.getElementById('scoutBackBtn');

    // Check if all required elements exist
    if (!signupForm || !nextBtn) {
        console.error('Required form elements not found');
        return;
    }

    const step1 = document.getElementById('step1');
    const step2 = document.getElementById('step2');
    const step3 = document.getElementById('step3');

    // Check if all step elements exist
    if (!step1 || !step2 || !step3) {
        console.error('Required step elements not found');
        return;
    }

    const userTypeInputs = document.querySelectorAll('input[name="userType"]');
    const troopActionInputs = document.querySelectorAll('input[name="troopAction"]');
    const troopCodeGroup = document.getElementById('troopCodeGroup');
    const troopNameGroup = document.getElementById('troopNameGroup');

    // Check if additional elements exist
    if (!troopCodeGroup || !troopNameGroup) {
        console.error('Required troop elements not found');
        return;
    }

    const formContainer = document.querySelector('.signup-form-container');
    const progressBar = document.querySelector('.progress-bar');

    // Check if container elements exist
    if (!formContainer || !progressBar) {
        console.error('Required container elements not found');
        return;
    }

    // Function to update progress
    function updateProgress(step) {
        formContainer.className = `signup-form-container step-${step}`;

        const dots = document.querySelectorAll('.step-dot');
        dots.forEach((dot, index) => {
            dot.classList.remove('active', 'completed');
            if (index + 1 < step) {
                dot.classList.add('completed');
            } else if (index + 1 === step) {
                dot.classList.add('active');
            }
        });
    }

    // Handle next button click
    nextBtn.addEventListener('click', function() {
        if (validateStep1()) {
            const userType = document.querySelector('input[name="userType"]:checked').value;

            // Add slide animation
            step1.style.animation = 'slideOutLeft 0.3s ease-out forwards';

            setTimeout(() => {
                step1.style.display = 'none';
                if (userType === 'scoutmaster') {
                    step2.style.display = 'block';
                    step2.style.animation = 'slideInRight 0.3s ease-out forwards';
                    updateProgress(2);
                } else {
                    step3.style.display = 'block';
                    step3.style.animation = 'slideInRight 0.3s ease-out forwards';
                    updateProgress(3);
                }
            }, 300);
        }
    });

    // Handle back button clicks
    backBtn.addEventListener('click', function() {
        // Add slide animation
        step2.style.animation = 'slideOutRight 0.3s ease-out forwards';

        setTimeout(() => {
            step2.style.display = 'none';
            step1.style.display = 'block';
            step1.style.animation = 'slideInLeft 0.3s ease-out forwards';
            updateProgress(1);

            // Reset step 2 form
            const troopActionInputs = document.querySelectorAll('input[name="troopAction"]');
            troopActionInputs.forEach(input => {
                input.checked = false;
                if (input.parentElement) {
                    input.parentElement.classList.remove('selected');
                }
            });
            const troopCode = document.getElementById('troopCode');
            const troopName = document.getElementById('troopName');
            if (troopCode) troopCode.value = '';
            if (troopName) troopName.value = '';
            troopCodeGroup.style.display = 'none';
            troopNameGroup.style.display = 'none';
        }, 300);
    });

    scoutBackBtn.addEventListener('click', function() {
        // Add slide animation
        step3.style.animation = 'slideOutRight 0.3s ease-out forwards';

        setTimeout(() => {
            step3.style.display = 'none';
            step1.style.display = 'block';
            step1.style.animation = 'slideInLeft 0.3s ease-out forwards';
            updateProgress(1);

            // Reset step 3 form
            const scoutTroopCode = document.getElementById('scoutTroopCode');
            if (scoutTroopCode) scoutTroopCode.value = '';
        }, 300);
    });

    // Handle user type selection
    userTypeInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Remove selected class from all radio options
            userTypeInputs.forEach(otherInput => {
                if (otherInput.parentElement) {
                    otherInput.parentElement.classList.remove('selected');
                }
            });

            // Add selected class to the current option
            if (this.parentElement) {
                this.parentElement.classList.add('selected');
            }
        });
    });

    // Handle troop action selection
    troopActionInputs.forEach(input => {
        input.addEventListener('change', function() {
            // Remove selected class from all radio options
            troopActionInputs.forEach(otherInput => {
                if (otherInput.parentElement) {
                    otherInput.parentElement.classList.remove('selected');
                }
            });

            // Add selected class to the current option
            if (this.parentElement) {
                this.parentElement.classList.add('selected');
            }

            const action = this.value;

            if (action === 'join') {
                troopCodeGroup.style.display = 'flex';
                troopNameGroup.style.display = 'none';
                const troopCode = document.getElementById('troopCode');
                const troopName = document.getElementById('troopName');
                if (troopCode) troopCode.required = true;
                if (troopName) troopName.required = false;
            } else if (action === 'create') {
                troopCodeGroup.style.display = 'none';
                troopNameGroup.style.display = 'flex';
                const troopCode = document.getElementById('troopCode');
                const troopName = document.getElementById('troopName');
                if (troopCode) troopCode.required = false;
                if (troopName) troopName.required = true;
            }
        });
    });

    // Form validation
    function validateStep1() {
        const fullName = document.getElementById('fullName');
        const email = document.getElementById('email');
        const userType = document.querySelector('input[name="userType"]:checked');

        if (!fullName || !email) {
            console.error('Required form fields not found');
            return false;
        }

        const fullNameValue = fullName.value.trim();
        const emailValue = email.value.trim();

        if (!fullNameValue) {
            alert('Please enter your full name.');
            return false;
        }

        if (!emailValue) {
            alert('Please enter your email address.');
            return false;
        }

        if (!isValidEmail(emailValue)) {
            alert('Please enter a valid email address.');
            return false;
        }

        if (!userType) {
            alert('Please select whether you are a scoutmaster or scout.');
            return false;
        }

        return true;
    }

    function validateStep2() {
        const troopAction = document.querySelector('input[name="troopAction"]:checked');

        if (!troopAction) {
            alert('Please select whether you want to join or create a troop.');
            return false;
        }

        if (troopAction.value === 'join') {
            const troopCode = document.getElementById('troopCode');
            if (!troopCode) {
                console.error('Troop code field not found');
                return false;
            }
            const troopCodeValue = troopCode.value.trim();
            if (!troopCodeValue) {
                alert('Please enter the troop code.');
                return false;
            }
        } else if (troopAction.value === 'create') {
            const troopName = document.getElementById('troopName');
            if (!troopName) {
                console.error('Troop name field not found');
                return false;
            }
            const troopNameValue = troopName.value.trim();
            if (!troopNameValue) {
                alert('Please enter the troop name.');
                return false;
            }
        }

        return true;
    }

    function validateStep3() {
        const scoutTroopCode = document.getElementById('scoutTroopCode');
        if (!scoutTroopCode) {
            console.error('Scout troop code field not found');
            return false;
        }

        const scoutTroopCodeValue = scoutTroopCode.value.trim();

        if (!scoutTroopCodeValue) {
            alert('Please enter your troop code.');
            return false;
        }

        return true;
    }

    function isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }

    // Handle form submission
    signupForm.addEventListener('submit', function(e) {
        e.preventDefault();

        const userType = document.querySelector('input[name="userType"]:checked');
        if (!userType) {
            alert('Please select your user type.');
            return;
        }

        if (userType.value === 'scoutmaster') {
            if (!validateStep2()) return;
        } else {
            if (!validateStep3()) return;
        }

        // Collect form data
        const formData = new FormData(signupForm);
        const userData = {};

        for (let [key, value] of formData.entries()) {
            userData[key] = value;
        }

        // Here you would typically send the data to your backend
        console.log('Form submitted:', userData);

        // Show success message
        showSuccessMessage(userType.value);

        // Reset form
        signupForm.reset();
        step1.style.display = 'block';
        step2.style.display = 'none';
        step3.style.display = 'none';
        troopCodeGroup.style.display = 'none';
        troopNameGroup.style.display = 'none';

        // Clear selected classes
        const radioOptions = document.querySelectorAll('.radio-option');
        radioOptions.forEach(option => {
            option.classList.remove('selected');
        });
    });

    function showSuccessMessage(userType) {
        if (!userType) {
            console.error('User type not provided for success message');
            return;
        }

        const message = userType === 'scoutmaster'
            ? 'Account created successfully! You can now manage your troop.'
            : 'Account created successfully! Welcome to your troop.';

        // Create success message element
        const successDiv = document.createElement('div');
        successDiv.className = 'success-message';
        successDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--primary-color);
            color: white;
            padding: 1rem 2rem;
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        `;
        successDiv.textContent = message;

        document.body.appendChild(successDiv);

        // Remove message after 5 seconds
        setTimeout(() => {
            if (successDiv.parentNode) {
                successDiv.style.animation = 'slideOut 0.3s ease-out';
                setTimeout(() => {
                    if (successDiv.parentNode) {
                        document.body.removeChild(successDiv);
                    }
                }, 300);
            }
        }, 5000);
    }

    // Add CSS animations for success message
    const style = document.createElement('style');
    if (style) {
        style.textContent = `
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
        if (document.head) {
            document.head.appendChild(style);
        }
    }

    // Initialize radio button states on page load
    userTypeInputs.forEach(input => {
        if (input.checked && input.parentElement) {
            input.parentElement.classList.add('selected');
        }
    });

    troopActionInputs.forEach(input => {
        if (input.checked && input.parentElement) {
            input.parentElement.classList.add('selected');
        }
    });

    // Handle input floating labels
    const inputWrappers = document.querySelectorAll('.input-wrapper');
    inputWrappers.forEach(wrapper => {
        const input = wrapper.querySelector('.form-input');
        
        if (!input) {
            console.error('Form input not found in wrapper');
            return;
        }

        // Handle input events
        input.addEventListener('input', function() {
            if (this.value.trim() !== '') {
                wrapper.classList.add('has-value');
            } else {
                wrapper.classList.remove('has-value');
            }
        });

        // Handle focus events
        input.addEventListener('focus', function() {
            wrapper.classList.add('focused');
        });

        input.addEventListener('blur', function() {
            wrapper.classList.remove('focused');
            if (this.value.trim() !== '') {
                wrapper.classList.add('has-value');
            } else {
                wrapper.classList.remove('has-value');
            }
        });

        // Check initial state
        if (input.value.trim() !== '') {
            wrapper.classList.add('has-value');
        }
    });
});
