// CrossFit Health OS - Main JavaScript

// API base URL
const API_BASE = window.location.origin;

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
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            if (!window.location.pathname.includes('/login')) {
                window.location.href = '/login';
            }
        }
    }
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
    
    // Check if user is authenticated
    isAuthenticated: function() {
        return !!localStorage.getItem('access_token');
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

// Smooth scroll for anchor links
$(document).ready(function() {
    $('a[href^="#"]').on('click', function(e) {
        const target = $(this.getAttribute('href'));
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
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    if (user.name) {
        $('#user-name').text(user.name);
    }
});
