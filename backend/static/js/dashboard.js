/**
 * Dashboard page - Load real API data
 */

$(document).ready(async function() {
    // Check authentication
    if (!CHOS.auth.isAuthenticated()) {
        window.location.href = '/login';
        return;
    }
    
    // Load user info
    const user = CHOS.auth.getUser();
    if (user && user.name) {
        $('#user-name').text(user.name);
        $('#welcome-name').text(user.name.split(' ')[0]);
    }
    
    // Set today's date
    const today = new Date().toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
    $('#today-date').text(today);
    
    // Load dashboard data
    await loadQuickStats();
    await loadWeeklyVolumeChart();
    
    // Logout handler
    $('#logout-btn').on('click', function(e) {
        e.preventDefault();
        CHOS.auth.logout();
    });
});

/**
 * Load Quick Stats cards with real data
 */
async function loadQuickStats() {
    try {
        // 1. Readiness Score
        try {
            const recovery = await CHOS.api.get('/api/v1/health/recovery/latest');
            if (recovery && recovery.readiness_score) {
                $('.card-body h2.text-primary').first()
                    .text(recovery.readiness_score)
                    .next('small').text('Updated today');
            }
        } catch (err) {
            console.log('No recovery data available');
        }
        
        // 2. This Week sessions
        try {
            const sessions = await CHOS.api.get('/api/v1/training/sessions?limit=100');
            
            // Get start of week (Monday)
            const now = new Date();
            const dayOfWeek = now.getDay();
            const diff = now.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
            const monday = new Date(now.setDate(diff));
            monday.setHours(0, 0, 0, 0);
            
            // Count sessions this week
            const thisWeekSessions = sessions.filter(s => {
                const sessionDate = new Date(s.started_at);
                return sessionDate >= monday;
            });
            
            // Assume 5 workouts per week target
            const targetSessions = 5;
            const completedCount = thisWeekSessions.length;
            
            $('.card-body h2').eq(1)
                .text(`${completedCount}/${targetSessions}`)
                .next('small').text('Sessions Complete');
        } catch (err) {
            console.log('No session data available');
        }
        
        // 3. Current Week (from schedule)
        try {
            const schedule = await CHOS.api.get('/api/v1/schedule/weekly/active');
            if (schedule) {
                // Calculate week number from start_date
                const startDate = new Date(schedule.start_date);
                const now = new Date();
                const diffTime = Math.abs(now - startDate);
                const diffWeeks = Math.ceil(diffTime / (1000 * 60 * 60 * 24 * 7));
                
                $('.card-body h2').eq(2)
                    .text(diffWeeks)
                    .next('small').text('Accumulation Phase');
            }
        } catch (err) {
            console.log('No active schedule');
        }
        
        // 4. Next Review
        try {
            const reviews = await CHOS.api.get('/api/v1/review/weekly?limit=1');
            if (reviews && reviews.length > 0) {
                const lastReview = new Date(reviews[0].created_at);
                const nextReview = new Date(lastReview);
                nextReview.setDate(nextReview.getDate() + 7);
                
                const now = new Date();
                const diffTime = nextReview - now;
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                
                $('.card-body h2').eq(3)
                    .text(diffDays > 0 ? diffDays : 0)
                    .next('small').text('Days until');
            }
        } catch (err) {
            console.log('No review data available');
        }
        
    } catch (error) {
        console.error('Error loading quick stats:', error);
    }
}

/**
 * Load Weekly Volume Chart (sessions per week over last 8 weeks)
 */
async function loadWeeklyVolumeChart() {
    try {
        const sessions = await CHOS.api.get('/api/v1/training/sessions?limit=1000');
        
        // Calculate sessions per week for last 8 weeks
        const now = new Date();
        const weeks = [];
        const weekCounts = [];
        
        for (let i = 7; i >= 0; i--) {
            const weekStart = new Date(now);
            weekStart.setDate(weekStart.getDate() - (i * 7));
            weekStart.setHours(0, 0, 0, 0);
            
            const weekEnd = new Date(weekStart);
            weekEnd.setDate(weekEnd.getDate() + 7);
            
            const weekSessions = sessions.filter(s => {
                const sessionDate = new Date(s.started_at);
                return sessionDate >= weekStart && sessionDate < weekEnd;
            });
            
            weeks.push(`W${8 - i}`);
            weekCounts.push(weekSessions.length);
        }
        
        // Create chart
        const chartOptions = {
            series: [{
                name: 'Sessions',
                data: weekCounts
            }],
            chart: {
                type: 'area',
                height: 200,
                toolbar: { show: false },
                sparkline: { enabled: false }
            },
            dataLabels: {
                enabled: false
            },
            stroke: {
                curve: 'smooth',
                width: 2
            },
            fill: {
                type: 'gradient',
                gradient: {
                    shadeIntensity: 1,
                    opacityFrom: 0.5,
                    opacityTo: 0.1
                }
            },
            xaxis: {
                categories: weeks
            },
            yaxis: {
                min: 0,
                forceNiceScale: true
            },
            colors: ['#0d6efd'],
            tooltip: {
                y: {
                    formatter: function(val) {
                        return val + ' sessions';
                    }
                }
            }
        };
        
        // Add chart container if it doesn't exist
        if (!$('#weekly-volume-chart').length) {
            $('.row.g-3.mb-4').last().after(`
                <div class="card shadow-sm border-0 mb-4">
                    <div class="card-body">
                        <h5 class="fw-bold mb-3">Weekly Training Volume</h5>
                        <div id="weekly-volume-chart"></div>
                    </div>
                </div>
            `);
        }
        
        const chart = new ApexCharts(document.querySelector("#weekly-volume-chart"), chartOptions);
        chart.render();
        
    } catch (error) {
        console.error('Error loading weekly volume chart:', error);
        // Show empty state
        if ($('#weekly-volume-chart').length) {
            $('#weekly-volume-chart').html(`
                <div class="text-center text-muted py-4">
                    <i class="fas fa-chart-line fa-3x mb-2"></i>
                    <p>No training data yet</p>
                </div>
            `);
        }
    }
}
