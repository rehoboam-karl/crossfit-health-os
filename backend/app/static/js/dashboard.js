// CrossFit Health OS - Dashboard JavaScript

// JWT validation helper
function isTokenExpired(token) {
    if (!token || token.split('.').length !== 3) return true;
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        if (!payload.exp) return true;
        return Date.now() > payload.exp * 1000;
    } catch {
        return true;
    }
}

// Check authentication on dashboard pages
$(document).ready(function() {
    const token = localStorage.getItem('access_token');
    
    if (window.location.pathname.startsWith('/dashboard')) {
        if (!token || isTokenExpired(token)) {
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            window.location.href = '/login';
            return;
        }
    }
});

// Dashboard API calls
const DashboardAPI = {
    // Get user profile
    getProfile: function() {
        const token = localStorage.getItem('access_token');
        return $.ajax({
            url: '/api/v1/users/me',
            type: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        });
    },
    
    // Get user stats
    getStats: function() {
        const token = localStorage.getItem('access_token');
        return $.ajax({
            url: '/api/v1/users/stats',
            type: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        });
    },
    
    // Get active schedule
    getActiveSchedule: function() {
        const token = localStorage.getItem('access_token');
        return $.ajax({
            url: '/api/v1/schedule/weekly/active',
            type: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        });
    },
    
    // Get today's workout
    getTodayWorkout: function() {
        const token = localStorage.getItem('access_token');
        return $.ajax({
            url: '/api/v1/training/workouts/today',
            type: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        });
    }
};

// Update dashboard UI with user data
function updateUserUI(user) {
    if (user.name) {
        $('#user-name').text(user.name);
        $('#welcome-name').text(user.name.split(' ')[0]);
    }
    
    if (user.fitness_level) {
        $('#fitness-level').text(user.fitness_level.charAt(0).toUpperCase() + user.fitness_level.slice(1));
    }
}

// Update stats cards
function updateStatsUI(stats) {
    if (stats) {
        if (stats.weekly_sessions !== undefined) {
            $('#sessions-count').text(stats.weekly_sessions + '/5');
        }
        if (stats.current_phase) {
            $('#current-phase').text(stats.current_phase);
        }
    }
}

// Load dashboard data
function loadDashboardData() {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    
    // Load user profile
    DashboardAPI.getProfile()
        .done(function(user) {
            updateUserUI(user);
            localStorage.setItem('user', JSON.stringify(user));
        })
        .fail(function(xhr) {
            console.error('Failed to load profile:', xhr);
        });
    
    // Load stats
    DashboardAPI.getStats()
        .done(function(stats) {
            updateStatsUI(stats);
        })
        .fail(function(xhr) {
            console.log('No stats available yet');
        });
}

// Initialize dashboard
$(document).ready(function() {
    if (window.location.pathname === '/dashboard') {
        loadDashboardData();
    }
});
