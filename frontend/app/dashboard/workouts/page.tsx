"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

interface Exercise {
  name: string;
  sets?: number;
  reps?: number;
  weight_kg?: number;
  duration_seconds?: number;
  distance_meters?: number;
  notes?: string;
}

interface WorkoutSession {
  id: string;
  user_id: string;
  template_id?: string;
  scheduled_date: string;
  scheduled_time: string;
  duration_minutes: number;
  workout_type: string;
  title: string;
  description: string;
  exercises: Exercise[];
  completed: boolean;
  completed_at?: string;
  rpe?: number;
  notes?: string;
  created_at: string;
}

export default function WorkoutsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [workouts, setWorkouts] = useState<WorkoutSession[]>([]);
  const [selectedWeek, setSelectedWeek] = useState(0); // 0 = this week, 1 = next week, etc.
  const [error, setError] = useState('');

  useEffect(() => {
    fetchWorkouts();
  }, [selectedWeek]);

  const fetchWorkouts = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      // Calculate start and end dates for selected week
      const today = new Date();
      const currentDayOfWeek = today.getDay();
      const daysToMonday = currentDayOfWeek === 0 ? -6 : 1 - currentDayOfWeek;
      
      const weekStart = new Date(today);
      weekStart.setDate(today.getDate() + daysToMonday + (selectedWeek * 7));
      
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);

      const startDate = weekStart.toISOString().split('T')[0];
      const endDate = weekEnd.toISOString().split('T')[0];

      const response = await api.get('/api/v1/training/sessions', {
        params: {
          start_date: startDate,
          end_date: endDate
        }
      });

      setWorkouts(response.data || []);
      setLoading(false);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push('/login');
      } else {
        setError('Failed to load workouts');
        setLoading(false);
      }
    }
  };

  const markComplete = async (workoutId: string, rpe?: number) => {
    try {
      await api.patch(`/api/v1/training/sessions/${workoutId}`, {
        completed: true,
        completed_at: new Date().toISOString(),
        rpe: rpe || undefined
      });
      
      await fetchWorkouts();
    } catch (err: any) {
      setError('Failed to mark workout as complete');
    }
  };

  const markIncomplete = async (workoutId: string) => {
    try {
      await api.patch(`/api/v1/training/sessions/${workoutId}`, {
        completed: false,
        completed_at: null,
        rpe: null
      });
      
      await fetchWorkouts();
    } catch (err: any) {
      setError('Failed to mark workout as incomplete');
    }
  };

  const getWeekLabel = () => {
    if (selectedWeek === 0) return 'This Week';
    if (selectedWeek === 1) return 'Next Week';
    if (selectedWeek === -1) return 'Last Week';
    return `Week ${selectedWeek > 0 ? '+' : ''}${selectedWeek}`;
  };

  const getWeekDates = () => {
    const today = new Date();
    const currentDayOfWeek = today.getDay();
    const daysToMonday = currentDayOfWeek === 0 ? -6 : 1 - currentDayOfWeek;
    
    const weekStart = new Date(today);
    weekStart.setDate(today.getDate() + daysToMonday + (selectedWeek * 7));
    
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);

    const formatDate = (date: Date) => {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    return `${formatDate(weekStart)} - ${formatDate(weekEnd)}`;
  };

  const groupByDay = (workouts: WorkoutSession[]) => {
    const grouped: { [key: string]: WorkoutSession[] } = {};
    
    workouts.forEach(workout => {
      const date = workout.scheduled_date;
      if (!grouped[date]) {
        grouped[date] = [];
      }
      grouped[date].push(workout);
    });

    // Sort by date
    return Object.keys(grouped)
      .sort()
      .map(date => ({
        date,
        workouts: grouped[date].sort((a, b) => 
          a.scheduled_time.localeCompare(b.scheduled_time)
        )
      }));
  };

  const formatDayHeader = (dateString: string) => {
    const date = new Date(dateString + 'T00:00:00');
    const dayName = date.toLocaleDateString('en-US', { weekday: 'long' });
    const dateFormatted = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    return `${dayName}, ${dateFormatted}`;
  };

  const getWorkoutTypeColor = (type: string) => {
    const colors: { [key: string]: string } = {
      strength: 'bg-purple-100 text-purple-800',
      metcon: 'bg-red-100 text-red-800',
      skill: 'bg-blue-100 text-blue-800',
      mixed: 'bg-green-100 text-green-800',
      active_recovery: 'bg-yellow-100 text-yellow-800',
      rest: 'bg-gray-100 text-gray-800'
    };
    return colors[type] || 'bg-gray-100 text-gray-800';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading workouts...</p>
        </div>
      </div>
    );
  }

  const dayGroups = groupByDay(workouts);

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.push('/dashboard')}
            className="text-blue-600 hover:text-blue-800 mb-4"
          >
            ← Back to Dashboard
          </button>
          
          <h1 className="text-3xl font-bold text-gray-900">Workouts</h1>
          <p className="mt-2 text-gray-600">Your training sessions</p>
        </div>

        {/* Week Selector */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <div className="flex items-center justify-between">
            <button
              onClick={() => setSelectedWeek(selectedWeek - 1)}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              ← Previous Week
            </button>
            
            <div className="text-center">
              <h2 className="text-xl font-semibold text-gray-900">{getWeekLabel()}</h2>
              <p className="text-sm text-gray-600">{getWeekDates()}</p>
            </div>
            
            <button
              onClick={() => setSelectedWeek(selectedWeek + 1)}
              className="text-blue-600 hover:text-blue-800 font-medium"
            >
              Next Week →
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
            {error}
          </div>
        )}

        {/* Workouts */}
        {dayGroups.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-600 text-lg mb-4">No workouts scheduled for this week</p>
            <button
              onClick={() => router.push('/dashboard/schedule')}
              className="btn-primary"
            >
              Set Up Your Schedule
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {dayGroups.map(({ date, workouts }) => (
              <div key={date} className="bg-white rounded-lg shadow overflow-hidden">
                {/* Day Header */}
                <div className="bg-gray-50 px-6 py-3 border-b border-gray-200">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {formatDayHeader(date)}
                  </h3>
                </div>

                {/* Day's Workouts */}
                <div className="divide-y divide-gray-200">
                  {workouts.map((workout) => (
                    <div key={workout.id} className="p-6">
                      {/* Workout Header */}
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h4 className="text-lg font-semibold text-gray-900">
                              {workout.title}
                            </h4>
                            <span className={`px-2 py-1 rounded text-xs font-medium ${getWorkoutTypeColor(workout.workout_type)}`}>
                              {workout.workout_type.replace('_', ' ').toUpperCase()}
                            </span>
                            {workout.completed && (
                              <span className="px-2 py-1 rounded text-xs font-medium bg-green-100 text-green-800">
                                ✓ COMPLETED
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-sm text-gray-600">
                            <span>🕐 {workout.scheduled_time}</span>
                            <span>⏱️ {workout.duration_minutes} min</span>
                            {workout.rpe && (
                              <span>💪 RPE: {workout.rpe}/10</span>
                            )}
                          </div>
                        </div>

                        {/* Complete/Uncomplete Button */}
                        <div>
                          {workout.completed ? (
                            <button
                              onClick={() => markIncomplete(workout.id)}
                              className="text-sm text-gray-600 hover:text-gray-800"
                            >
                              Mark Incomplete
                            </button>
                          ) : (
                            <button
                              onClick={() => {
                                const rpe = prompt('How hard was it? (1-10)');
                                markComplete(workout.id, rpe ? parseInt(rpe) : undefined);
                              }}
                              className="btn-primary text-sm"
                            >
                              Mark Complete
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Description */}
                      {workout.description && (
                        <p className="text-gray-700 mb-4">{workout.description}</p>
                      )}

                      {/* Exercises */}
                      {workout.exercises && workout.exercises.length > 0 && (
                        <div className="bg-gray-50 rounded-lg p-4">
                          <h5 className="font-semibold text-gray-900 mb-3">Exercises</h5>
                          <div className="space-y-2">
                            {workout.exercises.map((exercise, idx) => (
                              <div key={idx} className="flex items-start gap-3">
                                <span className="text-gray-500 font-mono text-sm">{idx + 1}.</span>
                                <div className="flex-1">
                                  <div className="font-medium text-gray-900">{exercise.name}</div>
                                  <div className="text-sm text-gray-600">
                                    {exercise.sets && exercise.reps && (
                                      <span>{exercise.sets} × {exercise.reps} reps</span>
                                    )}
                                    {exercise.weight_kg && (
                                      <span className="ml-2">@ {exercise.weight_kg}kg</span>
                                    )}
                                    {exercise.duration_seconds && (
                                      <span>{Math.floor(exercise.duration_seconds / 60)}:{(exercise.duration_seconds % 60).toString().padStart(2, '0')}</span>
                                    )}
                                    {exercise.distance_meters && (
                                      <span>{exercise.distance_meters}m</span>
                                    )}
                                  </div>
                                  {exercise.notes && (
                                    <div className="text-sm text-gray-500 italic mt-1">
                                      {exercise.notes}
                                    </div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Notes */}
                      {workout.notes && (
                        <div className="mt-4 text-sm text-gray-600 italic">
                          📝 {workout.notes}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Week Stats */}
        {workouts.length > 0 && (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">Total Sessions</div>
              <div className="text-2xl font-bold text-gray-900">{workouts.length}</div>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">Completed</div>
              <div className="text-2xl font-bold text-green-600">
                {workouts.filter(w => w.completed).length}
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">Total Time</div>
              <div className="text-2xl font-bold text-gray-900">
                {workouts.reduce((sum, w) => sum + w.duration_minutes, 0)} min
              </div>
            </div>
            
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">Avg RPE</div>
              <div className="text-2xl font-bold text-gray-900">
                {(() => {
                  const completedWithRPE = workouts.filter(w => w.completed && w.rpe);
                  if (completedWithRPE.length === 0) return '—';
                  const avgRPE = completedWithRPE.reduce((sum, w) => sum + (w.rpe || 0), 0) / completedWithRPE.length;
                  return avgRPE.toFixed(1);
                })()}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
