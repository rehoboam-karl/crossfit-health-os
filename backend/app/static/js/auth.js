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
const AuthUtils = {
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
    
    if (authPages.includes(currentPath) && AuthUtils.isAuthenticated()) {
        window.location.href = '/dashboard';
    }
});

// Password validation is now handled by validation.js
// (removed duplicate password strength and match validation code)
