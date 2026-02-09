"use client";

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

interface DashboardStats {
  thisWeekWorkouts: number;
  completedWorkouts: number;
  todayReadiness: number | null;
  lastReviewDate: string | null;
}

export default function DashboardPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<DashboardStats>({
    thisWeekWorkouts: 0,
    completedWorkouts: 0,
    todayReadiness: null,
    lastReviewDate: null
  });

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      router.push('/login');
      return;
    }

    fetchDashboardStats();
  }, [router]);

  const fetchDashboardStats = async () => {
    try {
      // Get this week's workouts
      const today = new Date();
      const currentDayOfWeek = today.getDay();
      const daysToMonday = currentDayOfWeek === 0 ? -6 : 1 - currentDayOfWeek;
      
      const weekStart = new Date(today);
      weekStart.setDate(today.getDate() + daysToMonday);
      
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);

      const startDate = weekStart.toISOString().split('T')[0];
      const endDate = weekEnd.toISOString().split('T')[0];

      const workoutsResponse = await api.get('/api/v1/training/sessions', {
        params: { start_date: startDate, end_date: endDate }
      });

      const workouts = workoutsResponse.data || [];

      // Get today's recovery metric
      let todayReadiness = null;
      try {
        const todayDate = today.toISOString().split('T')[0];
        const recoveryResponse = await api.get('/api/v1/health/recovery', {
          params: { start_date: todayDate, end_date: todayDate }
        });
        
        if (recoveryResponse.data && recoveryResponse.data.length > 0) {
          todayReadiness = recoveryResponse.data[0].readiness_score;
        }
      } catch (err) {
        // No recovery data
      }

      // Get last review
      let lastReviewDate = null;
      try {
        const reviewsResponse = await api.get('/api/v1/review/weekly');
        if (reviewsResponse.data && reviewsResponse.data.length > 0) {
          lastReviewDate = reviewsResponse.data[0].created_at;
        }
      } catch (err) {
        // No reviews
      }

      setStats({
        thisWeekWorkouts: workouts.length,
        completedWorkouts: workouts.filter((w: any) => w.completed).length,
        todayReadiness,
        lastReviewDate
      });

      setLoading(false);
    } catch (err) {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    router.push('/login');
  };

  const getReadinessColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    if (score >= 40) return 'text-orange-600';
    return 'text-red-600';
  };

  const getReadinessLabel = (score: number) => {
    if (score >= 80) return 'Excellent';
    if (score >= 60) return 'Good';
    if (score >= 40) return 'Fair';
    return 'Poor';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold text-gray-900">
              🏋️ CrossFit Health OS
            </h1>
            <button
              onClick={logout}
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Logout
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          {/* This Week's Workouts */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">This Week</div>
            <div className="text-3xl font-bold text-gray-900">
              {stats.completedWorkouts}/{stats.thisWeekWorkouts}
            </div>
            <div className="text-sm text-gray-500 mt-1">Workouts Completed</div>
          </div>

          {/* Today's Readiness */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">Today's Readiness</div>
            {stats.todayReadiness !== null ? (
              <>
                <div className={`text-3xl font-bold ${getReadinessColor(stats.todayReadiness)}`}>
                  {stats.todayReadiness}
                </div>
                <div className="text-sm text-gray-500 mt-1">
                  {getReadinessLabel(stats.todayReadiness)}
                </div>
              </>
            ) : (
              <div className="text-gray-400 text-sm mt-2">Not logged yet</div>
            )}
          </div>

          {/* Completion Rate */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">Completion Rate</div>
            <div className="text-3xl font-bold text-gray-900">
              {stats.thisWeekWorkouts > 0
                ? Math.round((stats.completedWorkouts / stats.thisWeekWorkouts) * 100)
                : 0}%
            </div>
            <div className="text-sm text-gray-500 mt-1">This Week</div>
          </div>

          {/* Last Review */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="text-sm text-gray-600 mb-1">Last AI Review</div>
            {stats.lastReviewDate ? (
              <div className="text-sm text-gray-900 mt-2">
                {new Date(stats.lastReviewDate).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric'
                })}
              </div>
            ) : (
              <div className="text-gray-400 text-sm mt-2">No reviews yet</div>
            )}
          </div>
        </div>

        {/* Main Navigation */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Schedule */}
          <button
            onClick={() => router.push('/dashboard/schedule')}
            className="bg-white rounded-lg shadow p-8 hover:shadow-lg transition text-left group"
          >
            <div className="text-4xl mb-4">📅</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-blue-600">
              Schedule
            </h2>
            <p className="text-gray-600 text-sm">
              Set your training days and times
            </p>
          </button>

          {/* Workouts */}
          <button
            onClick={() => router.push('/dashboard/workouts')}
            className="bg-white rounded-lg shadow p-8 hover:shadow-lg transition text-left group"
          >
            <div className="text-4xl mb-4">💪</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-blue-600">
              Workouts
            </h2>
            <p className="text-gray-600 text-sm">
              View and track your training sessions
            </p>
          </button>

          {/* Recovery */}
          <button
            onClick={() => router.push('/dashboard/recovery')}
            className="bg-white rounded-lg shadow p-8 hover:shadow-lg transition text-left group"
          >
            <div className="text-4xl mb-4">🧘</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-blue-600">
              Recovery
            </h2>
            <p className="text-gray-600 text-sm">
              Log HRV, sleep, and readiness metrics
            </p>
          </button>

          {/* Reviews */}
          <button
            onClick={() => router.push('/dashboard/reviews')}
            className="bg-white rounded-lg shadow p-8 hover:shadow-lg transition text-left group"
          >
            <div className="text-4xl mb-4">🤖</div>
            <h2 className="text-xl font-bold text-gray-900 mb-2 group-hover:text-blue-600">
              AI Reviews
            </h2>
            <p className="text-gray-600 text-sm">
              Weekly performance analysis and adjustments
            </p>
          </button>
        </div>

        {/* Quick Start Guide */}
        <div className="mt-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg shadow p-8 text-white">
          <h2 className="text-2xl font-bold mb-4">Quick Start Guide</h2>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <span className="text-2xl">1️⃣</span>
              <div>
                <div className="font-semibold">Set Your Schedule</div>
                <div className="text-blue-100 text-sm">
                  Define your training days and times
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">2️⃣</span>
              <div>
                <div className="font-semibold">Generate AI Program</div>
                <div className="text-blue-100 text-sm">
                  Let AI create your weekly workouts
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">3️⃣</span>
              <div>
                <div className="font-semibold">Log Recovery Metrics</div>
                <div className="text-blue-100 text-sm">
                  Track HRV, sleep, stress daily
                </div>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">4️⃣</span>
              <div>
                <div className="font-semibold">Get Weekly Review</div>
                <div className="text-blue-100 text-sm">
                  AI analyzes your week and adjusts your program
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
