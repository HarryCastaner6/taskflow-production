document.addEventListener('DOMContentLoaded', function() {
    // Get CSRF token
    function getCSRFToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        if (meta) return meta.content;

        const match = document.cookie.match(/csrf_token=([^;]+)/);
        return match ? match[1] : '';
    }

    // Initialize Bootstrap toasts
    const toastElements = document.querySelectorAll('.toast');
    toastElements.forEach(toastEl => {
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    });

    // Function to show dynamic notifications
    window.showNotification = function(message, type = 'info', duration = 5000) {
        const toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) return;

        const iconMap = {
            'success': 'bi-check-circle-fill',
            'danger': 'bi-exclamation-triangle-fill',
            'warning': 'bi-exclamation-circle-fill',
            'info': 'bi-info-circle-fill'
        };

        const toastHtml = `
            <div class="toast" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="${duration}">
                <div class="toast-header text-bg-${type}">
                    <i class="${iconMap[type]} me-2"></i>
                    <strong class="me-auto">${type.charAt(0).toUpperCase() + type.slice(1)}</strong>
                    <button type="button" class="btn-close ${type === 'warning' ? '' : 'btn-close-white'}" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">${message}</div>
            </div>
        `;

        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        const newToast = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(newToast);
        toast.show();

        // Remove toast from DOM after it's hidden
        newToast.addEventListener('hidden.bs.toast', () => {
            newToast.remove();
        });
    };

    // Confirm delete buttons
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // Form submission loading state
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Only add loading state if form validation passes
            const submitBtn = this.querySelector('[type="submit"]');

            // Check if form has any validation errors
            const invalidFields = this.querySelectorAll('.is-invalid, :invalid');
            if (invalidFields.length > 0) {
                e.preventDefault();
                showNotification('Please correct the form errors before submitting.', 'danger');
                return false;
            }

            if (submitBtn && !submitBtn.disabled) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';

                // Re-enable after 10 seconds as fallback
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 10000);
            }
        });
    });

    // Add CSRF token to all AJAX requests
    const originalFetch = window.fetch;
    window.fetch = function(...args) {
        let [url, options = {}] = args;

        // Add CSRF token to headers for POST/PUT/DELETE requests
        if (options.method && ['POST', 'PUT', 'DELETE', 'PATCH'].includes(options.method.toUpperCase())) {
            options.headers = options.headers || {};
            if (!options.headers['X-CSRFToken']) {
                options.headers['X-CSRFToken'] = getCSRFToken();
            }
        }

        return originalFetch(url, options);
    };

    // Enhanced form validation
    forms.forEach(form => {
        const inputs = form.querySelectorAll('input, textarea, select');

        inputs.forEach(input => {
            // Real-time validation on input
            input.addEventListener('input', function() {
                validateField(this);
            });

            // Validation on blur
            input.addEventListener('blur', function() {
                validateField(this);
            });
        });
    });

    function validateField(field) {
        const value = field.value.trim();
        const fieldType = field.type;
        const isRequired = field.hasAttribute('required') || field.classList.contains('required');

        // Clear previous validation classes
        field.classList.remove('is-invalid', 'is-valid');

        // Remove existing feedback
        const existingFeedback = field.parentNode.querySelector('.invalid-feedback');
        if (existingFeedback) {
            existingFeedback.remove();
        }

        let isValid = true;
        let errorMessage = '';

        // Required field validation
        if (isRequired && !value) {
            isValid = false;
            errorMessage = 'This field is required.';
        }
        // Email validation
        else if (fieldType === 'email' && value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(value)) {
                isValid = false;
                errorMessage = 'Please enter a valid email address.';
            }
        }
        // Password validation
        else if (fieldType === 'password' && value) {
            if (value.length < 6) {
                isValid = false;
                errorMessage = 'Password must be at least 6 characters long.';
            }
        }
        // Username validation
        else if (field.name === 'username' && value) {
            if (value.length < 3) {
                isValid = false;
                errorMessage = 'Username must be at least 3 characters long.';
            }
        }
        // Confirm password validation
        else if (field.name === 'password2' || field.name === 'confirm_password') {
            const passwordField = field.form.querySelector('input[name="new_password"], input[name="password"]');
            if (passwordField && value !== passwordField.value) {
                isValid = false;
                errorMessage = 'Passwords do not match.';
            }
        }

        // Apply validation classes and feedback
        if (value) { // Only show validation if user has entered something
            if (isValid) {
                field.classList.add('is-valid');
            } else {
                field.classList.add('is-invalid');
                showFieldError(field, errorMessage);
            }
        }

        return isValid;
    }

    function showFieldError(field, message) {
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;
        field.parentNode.appendChild(feedback);
    }

    // Task form enhancements
    const taskForm = document.querySelector('#task-form, form[action*="tasks"]');
    if (taskForm) {
        const titleField = taskForm.querySelector('input[name="title"]');
        if (titleField) {
            titleField.addEventListener('input', function() {
                if (this.value.length > 200) {
                    this.classList.add('is-invalid');
                    showFieldError(this, 'Title cannot exceed 200 characters.');
                }
            });
        }
    }
});