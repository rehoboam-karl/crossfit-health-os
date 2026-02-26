// CrossFit Health OS - Form Validation Utilities

/**
 * Form validation utilities
 * Provides real-time client-side validation for all forms
 */
const FormValidator = {
    /**
     * Validation rules
     */
    rules: {
        email: {
            pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
            message: 'Please enter a valid email address'
        },
        password: {
            minLength: 8,
            pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
            message: 'Password must be at least 8 characters with 1 uppercase, 1 lowercase, and 1 number'
        },
        name: {
            minLength: 2,
            maxLength: 100,
            pattern: /^[a-zA-ZÀ-ÿ\s'-]+$/,
            message: 'Name must be 2-100 characters and contain only letters'
        },
        weight: {
            min: 30,
            max: 300,
            message: 'Weight must be between 30 and 300 kg'
        },
        height: {
            min: 100,
            max: 250,
            message: 'Height must be between 100 and 250 cm'
        },
        birthDate: {
            minAge: 13,
            maxAge: 120,
            message: 'You must be at least 13 years old'
        }
    },

    /**
     * Validate email format
     */
    validateEmail: function(email) {
        if (!email || email.trim() === '') {
            return { valid: false, message: 'Email is required' };
        }

        if (!this.rules.email.pattern.test(email)) {
            return { valid: false, message: this.rules.email.message };
        }

        return { valid: true };
    },

    /**
     * Validate password strength (for registration/password creation only)
     */
    validatePassword: function(password) {
        if (!password || password.trim() === '') {
            return { valid: false, message: 'Password is required' };
        }

        if (password.length < this.rules.password.minLength) {
            return { valid: false, message: `Password must be at least ${this.rules.password.minLength} characters` };
        }

        if (!this.rules.password.pattern.test(password)) {
            return { valid: false, message: this.rules.password.message };
        }

        return { valid: true };
    },

    /**
     * Validate password for login (just check if not empty)
     */
    validatePasswordLogin: function(password) {
        if (!password || password.trim() === '') {
            return { valid: false, message: 'Password is required' };
        }

        return { valid: true };
    },

    /**
     * Validate password confirmation
     */
    validatePasswordConfirm: function(password, confirmPassword) {
        if (!confirmPassword || confirmPassword.trim() === '') {
            return { valid: false, message: 'Please confirm your password' };
        }

        if (password !== confirmPassword) {
            return { valid: false, message: 'Passwords do not match' };
        }

        return { valid: true };
    },

    /**
     * Validate name
     */
    validateName: function(name) {
        if (!name || name.trim() === '') {
            return { valid: false, message: 'Name is required' };
        }

        const trimmedName = name.trim();

        if (trimmedName.length < this.rules.name.minLength) {
            return { valid: false, message: `Name must be at least ${this.rules.name.minLength} characters` };
        }

        if (trimmedName.length > this.rules.name.maxLength) {
            return { valid: false, message: `Name must not exceed ${this.rules.name.maxLength} characters` };
        }

        if (!this.rules.name.pattern.test(trimmedName)) {
            return { valid: false, message: this.rules.name.message };
        }

        return { valid: true };
    },

    /**
     * Validate weight
     */
    validateWeight: function(weight) {
        if (!weight || weight === '') {
            return { valid: true }; // Optional field
        }

        const numWeight = parseFloat(weight);

        if (isNaN(numWeight)) {
            return { valid: false, message: 'Weight must be a valid number' };
        }

        if (numWeight < this.rules.weight.min || numWeight > this.rules.weight.max) {
            return { valid: false, message: this.rules.weight.message };
        }

        return { valid: true };
    },

    /**
     * Validate height
     */
    validateHeight: function(height) {
        if (!height || height === '') {
            return { valid: true }; // Optional field
        }

        const numHeight = parseInt(height);

        if (isNaN(numHeight)) {
            return { valid: false, message: 'Height must be a valid number' };
        }

        if (numHeight < this.rules.height.min || numHeight > this.rules.height.max) {
            return { valid: false, message: this.rules.height.message };
        }

        return { valid: true };
    },

    /**
     * Validate birth date
     */
    validateBirthDate: function(birthDate) {
        if (!birthDate || birthDate === '') {
            return { valid: true }; // Optional field
        }

        const date = new Date(birthDate);
        const today = new Date();

        // Check if date is valid
        if (isNaN(date.getTime())) {
            return { valid: false, message: 'Please enter a valid date' };
        }

        // Check if date is in the future
        if (date > today) {
            return { valid: false, message: 'Birth date cannot be in the future' };
        }

        // Calculate age
        let age = today.getFullYear() - date.getFullYear();
        const monthDiff = today.getMonth() - date.getMonth();

        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < date.getDate())) {
            age--;
        }

        // Check minimum age
        if (age < this.rules.birthDate.minAge) {
            return { valid: false, message: this.rules.birthDate.message };
        }

        // Check maximum age (sanity check)
        if (age > this.rules.birthDate.maxAge) {
            return { valid: false, message: 'Please enter a valid birth date' };
        }

        return { valid: true };
    },

    /**
     * Show validation feedback on input
     */
    showFeedback: function($input, result) {
        const $formGroup = $input.closest('.mb-3, .col-md-6, .col-md-4');

        // Remove existing feedback
        $formGroup.find('.invalid-feedback, .valid-feedback').remove();
        $input.removeClass('is-invalid is-valid');

        if (!result.valid) {
            $input.addClass('is-invalid');
            $input.after(`<div class="invalid-feedback d-block">${result.message}</div>`);
        } else {
            $input.addClass('is-valid');
        }
    },

    /**
     * Clear feedback from input
     */
    clearFeedback: function($input) {
        const $formGroup = $input.closest('.mb-3, .col-md-6, .col-md-4');
        $formGroup.find('.invalid-feedback, .valid-feedback').remove();
        $input.removeClass('is-invalid is-valid');
    },

    /**
     * Clear all feedback from form
     */
    clearAllFeedback: function($form) {
        $form.find('.is-invalid, .is-valid').removeClass('is-invalid is-valid');
        $form.find('.invalid-feedback, .valid-feedback').remove();
    },

    /**
     * Validate entire form
     * Returns { valid: boolean, errors: [] }
     */
    validateForm: function($form) {
        const errors = [];
        let firstInvalidInput = null;

        // Clear previous feedback
        this.clearAllFeedback($form);

        // Validate each input
        $form.find('input[required], input[data-validate]').each((index, input) => {
            const $input = $(input);
            const fieldName = $input.attr('name') || $input.attr('id');
            const value = $input.val();
            let result = { valid: true };

            // Determine validation type
            if ($input.attr('type') === 'email') {
                result = this.validateEmail(value);
            } else if ($input.attr('type') === 'password') {
                if ($input.attr('name') === 'confirm_password' || $input.attr('id') === 'confirm_password') {
                    const password = $form.find('#password').val();
                    result = this.validatePasswordConfirm(password, value);
                } else {
                    // Check if this is a login form (don't validate password strength)
                    const isLoginForm = $form.attr('id') === 'login-form';
                    if (isLoginForm) {
                        result = this.validatePasswordLogin(value);
                    } else {
                        result = this.validatePassword(value);
                    }
                }
            } else if ($input.attr('name') === 'name' || $input.attr('id') === 'name') {
                result = this.validateName(value);
            } else if ($input.attr('name') === 'weight_kg') {
                result = this.validateWeight(value);
            } else if ($input.attr('name') === 'height_cm') {
                result = this.validateHeight(value);
            } else if ($input.attr('name') === 'birth_date') {
                result = this.validateBirthDate(value);
            } else if ($input.attr('required') && (!value || value.trim() === '')) {
                result = { valid: false, message: 'This field is required' };
            }

            // Show feedback
            if (!result.valid) {
                this.showFeedback($input, result);
                errors.push({ field: fieldName, message: result.message });

                if (!firstInvalidInput) {
                    firstInvalidInput = $input;
                }
            }
        });

        // Focus first invalid input
        if (firstInvalidInput) {
            firstInvalidInput.focus();

            // Scroll to first error
            $('html, body').animate({
                scrollTop: firstInvalidInput.offset().top - 100
            }, 300);
        }

        return {
            valid: errors.length === 0,
            errors: errors
        };
    },

    /**
     * Setup real-time validation for a form
     */
    setupRealtimeValidation: function($form) {
        const self = this;

        // Email validation
        $form.find('input[type="email"]').on('blur', function() {
            const $input = $(this);
            const result = self.validateEmail($input.val());
            self.showFeedback($input, result);
        });

        // Password validation
        $form.find('input[type="password"]#password').on('blur', function() {
            const $input = $(this);
            const isLoginForm = $form.attr('id') === 'login-form';

            // Don't validate password strength on login form
            if (isLoginForm) {
                const result = self.validatePasswordLogin($input.val());
                self.showFeedback($input, result);
            } else {
                const result = self.validatePassword($input.val());
                self.showFeedback($input, result);
            }
        });

        // Confirm password validation
        $form.find('input#confirm_password').on('blur keyup', function() {
            const $input = $(this);
            const password = $form.find('#password').val();
            const result = self.validatePasswordConfirm(password, $input.val());
            self.showFeedback($input, result);
        });

        // Name validation
        $form.find('input#name').on('blur', function() {
            const $input = $(this);
            const result = self.validateName($input.val());
            self.showFeedback($input, result);
        });

        // Weight validation
        $form.find('input#weight_kg').on('blur', function() {
            const $input = $(this);
            const result = self.validateWeight($input.val());
            if ($input.val() !== '') {
                self.showFeedback($input, result);
            }
        });

        // Height validation
        $form.find('input#height_cm').on('blur', function() {
            const $input = $(this);
            const result = self.validateHeight($input.val());
            if ($input.val() !== '') {
                self.showFeedback($input, result);
            }
        });

        // Birth date validation
        $form.find('input#birth_date').on('blur change', function() {
            const $input = $(this);
            const result = self.validateBirthDate($input.val());
            if ($input.val() !== '') {
                self.showFeedback($input, result);
            }
        });

        // Clear validation on focus
        $form.find('input').on('focus', function() {
            if ($(this).hasClass('is-invalid')) {
                self.clearFeedback($(this));
            }
        });
    }
};
