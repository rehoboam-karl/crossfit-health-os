// CrossFit Health OS - Dashboard JavaScript

// Check authentication on dashboard pages
$(document).ready(function() {
    if (window.location.pathname.startsWith('/dashboard')) {
        if (!Utils.isAuthenticated()) {
            window.location.href = '/login';
            return;
        }
    }
});

// Dashboard API calls
const DashboardAPI = {
    // Get user profile
    getProfile: function() {
        return $.ajax({
            url: '/api/v1/users/me',
            type: 'GET'
        });
    },
    
    // Get active schedule
    getActiveSchedule: function() {
        return $.ajax({
            url: '/api/v1/schedule/weekly/active',
            type: 'GET'
        });
    },
    
    // Get today's workout
    getTodayWorkout: function() {
        return $.ajax({
            url: '/api/v1/training/workouts/today',
            type: 'GET'
        });
    },
    
    // Get latest review
    getLatestReview: function() {
        return $.ajax({
            url: '/api/v1/review/weekly/latest',
            type: 'GET'
        });
    }
};

// Load dashboard data
function loadDashboardData() {
    // Load user profile
    DashboardAPI.getProfile().done(function(user) {
        // Update UI with user data
        console.log('User profile loaded:', user);
    }).fail(function(xhr) {
        if (xhr.status !== 401) {
            console.error('Failed to load profile:', xhr);
        }
    });
    
    // Load today's workout
    DashboardAPI.getTodayWorkout().done(function(workout) {
        // Display workout
        console.log('Today workout:', workout);
    }).fail(function(xhr) {
        // No workout yet
        console.log('No workout scheduled');
    });
}

// Initialize dashboard
$(document).ready(function() {
    if (window.location.pathname === '/dashboard') {
        loadDashboardData();
    }
});
