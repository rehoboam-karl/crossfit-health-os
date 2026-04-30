// CrossFit Health OS - Main JavaScript

// API base URL
const API_BASE = window.location.origin;

// Auth middleware - Check authentication on protected pages
function checkAuth() {
    const token = localStorage.getItem('access_token');
    const protectedPaths = ['/dashboard'];
    const currentPath = window.location.pathname;
    
    // Check if current page requires auth
    const isProtectedPage = protectedPaths.some(path => currentPath.startsWith(path));
    
    if (isProtectedPage && !token) {
        // No token on protected page - redirect to login
        window.location.href = '/login?redirect=' + encodeURIComponent(currentPath);
        return false;
    }
    
    return true;
}

// Setup jQuery AJAX defaults
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        // Add auth token to requests if available
        const token = localStorage.getItem('access_token');
        if (token && !settings.url.includes('/auth/')) {
            xhr.setRequestHeader('Authorization', 'Bearer ' + token);
        }
    },
    error: function(xhr) {
        // Handle 401 Unauthorized globally
        if (xhr.status === 401) {
            console.log('Unauthorized - clearing auth and redirecting to login');
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            if (!window.location.pathname.includes('/login')) {
                window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname);
            }
        }
    }
});

// Run auth check on page load
$(document).ready(function() {
    checkAuth();
});

// Utility functions
const Utils = {
    // Show Bootstrap alert
    showAlert: function(container, message, type = 'info') {
        const alert = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        $(container).html(alert);
        
        // Auto-dismiss after 5 seconds
        setTimeout(function() {
            $(container).find('.alert').alert('close');
        }, 5000);
    },
    
    // Format date
    formatDate: function(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    },
    
    // JWT validation helper
    isTokenExpired: function(token) {
        if (!token || token.split('.').length !== 3) return true;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            if (!payload.exp) return true;
            return Date.now() > payload.exp * 1000;
        } catch {
            return true;
        }
    },

    // Check if user is authenticated
    isAuthenticated: function() {
        const token = localStorage.getItem('access_token');
        if (!token) return false;
        if (this.isTokenExpired(token)) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            return false;
        }
        return true;
    },
    
    // Get current user
    getCurrentUser: function() {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    }
};

// Global error handler
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
});

// Smooth scroll for anchor links. Skip bare "#" / "#!" used as click stubs
// (Bootstrap dropdowns, button-as-link, etc.) — those aren't real fragments
// and jQuery throws "unrecognized expression: #" if we try to select them.
$(document).ready(function() {
    $('a[href^="#"]').on('click', function(e) {
        const href = this.getAttribute('href') || '';
        if (href.length < 2 || href === '#!' || href.includes(' ')) return;
        let target;
        try {
            target = $(href);
        } catch (_) {
            return;  // Invalid CSS selector — ignore.
        }
        if (target.length) {
            e.preventDefault();
            $('html, body').animate({
                scrollTop: target.offset().top - 80
            }, 500);
        }
    });
});

// Logout handler for all pages
$(document).ready(function() {
    $('#logout-btn').on('click', function(e) {
        e.preventDefault();
        const token = localStorage.getItem('access_token');
        
        $.ajax({
            url: '/api/v1/auth/logout',
            type: 'POST',
            headers: token ? { 'Authorization': 'Bearer ' + token } : {},
            complete: function() {
                localStorage.removeItem('access_token');
                localStorage.removeItem('user');
                window.location.href = '/';
            }
        });
    });
    
    // Load user name from localStorage
    const userJson = localStorage.getItem('user');
    const user = userJson && userJson !== 'undefined' ? JSON.parse(userJson) : {};
    if (user.name) {
        $('#user-name').text(user.name);
    }
});
