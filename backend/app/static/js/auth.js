// CrossFit Health OS - Authentication JavaScript

// JWT validation helper
function isTokenExpired(token) {
    // Check token structure first
    if (!token || token.split('.').length !== 3) {
        return true;  // Invalid structure = expired
    }

    try {
        const payload = JSON.parse(atob(token.split('.')[1]));

        // Check if exp field exists
        if (!payload.exp) {
            return true;  // No expiration = expired (be safe)
        }

        const exp = payload.exp * 1000;
        return Date.now() > exp;
    } catch {
        return true;  // Parse error = expired
    }
}

// Utils object with authentication helpers
const Utils = {
    /**
     * Check if user is authenticated
     * @returns {boolean} True if user has valid access token
     */
    isAuthenticated: function() {
        const accessToken = localStorage.getItem('access_token');

        if (!accessToken) {
            return false;
        }

        // Check if token is expired
        if (isTokenExpired(accessToken)) {
            // Clean up expired token
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            return false;
        }

        return true;
    },

    /**
     * Get current user from localStorage
     * @returns {object|null} User object or null
     */
    getUser: function() {
        try {
            const userStr = localStorage.getItem('user');
            return userStr ? JSON.parse(userStr) : null;
        } catch {
            return null;
        }
    },

    /**
     * Get access token
     * @returns {string|null} Access token or null
     */
    getAccessToken: function() {
        return localStorage.getItem('access_token');
    },

    /**
     * Logout user - clear all auth data
     */
    logout: function() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
    }
};

// Check if already authenticated and redirect to dashboard
$(document).ready(function() {
    const currentPath = window.location.pathname;
    const authPages = ['/login', '/register', '/forgot-password'];
    
    if (authPages.includes(currentPath) && Utils.isAuthenticated()) {
        window.location.href = '/dashboard';
    }
});

// Password strength indicator
function checkPasswordStrength(password) {
    let strength = 0;
    const checks = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /\d/.test(password),
        special: /[!@#$%^&*]/.test(password)
    };
    
    for (let key in checks) {
        if (checks[key]) strength++;
    }
    
    if (strength < 3) return { level: 'weak', color: 'danger' };
    if (strength < 4) return { level: 'medium', color: 'warning' };
    return { level: 'strong', color: 'success' };
}

// Add password strength indicator on register page
if (window.location.pathname === '/register') {
    $(document).ready(function() {
        $('#password').on('input', function() {
            const password = $(this).val();
            if (password.length > 0) {
                const strength = checkPasswordStrength(password);
                
                // Remove existing indicator
                $('#password-strength').remove();
                
                // Add new indicator
                const indicator = `
                    <div id="password-strength" class="mt-1">
                        <small class="text-${strength.color}">
                            Password strength: <strong>${strength.level}</strong>
                        </small>
                    </div>
                `;
                $(this).after(indicator);
            } else {
                $('#password-strength').remove();
            }
        });
        
        // Check password match
        $('#confirm_password').on('input', function() {
            const password = $('#password').val();
            const confirm = $(this).val();
            
            $('#password-match').remove();
            
            if (confirm.length > 0) {
                if (password === confirm) {
                    $(this).after('<div id="password-match" class="mt-1"><small class="text-success"><i class="fas fa-check-circle me-1"></i> Passwords match</small></div>');
                } else {
                    $(this).after('<div id="password-match" class="mt-1"><small class="text-danger"><i class="fas fa-times-circle me-1"></i> Passwords do not match</small></div>');
                }
            }
        });
    });
}
