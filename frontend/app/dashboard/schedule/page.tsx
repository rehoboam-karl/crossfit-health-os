"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

interface Session {
  day_index: number;
  session_number: number;
  start_time: string;
  duration_minutes: number;
  workout_type: string;
}

interface WeeklySchedule {
  id: string;
  user_id: string;
  week_start: string;
  is_active: boolean;
  sessions: Session[];
  created_at: string;
  updated_at: string;
}

const DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const WORKOUT_TYPES = ['strength', 'metcon', 'skill', 'mixed', 'active_recovery', 'rest'];

export default function SchedulePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [schedule, setSchedule] = useState<WeeklySchedule | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchSchedule();
  }, []);

  const fetchSchedule = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      const response = await api.get('/api/v1/schedule/weekly/active');
      
      if (response.data) {
        setSchedule(response.data);
        setSessions(response.data.sessions || []);
      }
      
      setLoading(false);
    } catch (err: any) {
      if (err.response?.status === 404) {
        // No active schedule
        setLoading(false);
      } else if (err.response?.status === 401) {
        router.push('/login');
      } else {
        setError('Failed to load schedule');
        setLoading(false);
      }
    }
  };

  const addSession = (dayIndex: number) => {
    const daySessions = sessions.filter(s => s.day_index === dayIndex);
    if (daySessions.length >= 3) {
      setError('Maximum 3 sessions per day');
      return;
    }

    const newSession: Session = {
      day_index: dayIndex,
      session_number: daySessions.length + 1,
      start_time: '09:00',
      duration_minutes: 60,
      workout_type: 'mixed'
    };

    setSessions([...sessions, newSession]);
    setError('');
  };

  const removeSession = (dayIndex: number, sessionNumber: number) => {
    setSessions(sessions.filter(
      s => !(s.day_index === dayIndex && s.session_number === sessionNumber)
    ));
  };

  const updateSession = (dayIndex: number, sessionNumber: number, field: string, value: any) => {
    setSessions(sessions.map(s => 
      (s.day_index === dayIndex && s.session_number === sessionNumber)
        ? { ...s, [field]: value }
        : s
    ));
  };

  const saveSchedule = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');

      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      // Get next Monday
      const today = new Date();
      const dayOfWeek = today.getDay();
      const daysUntilMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek;
      const nextMonday = new Date(today);
      nextMonday.setDate(today.getDate() + daysUntilMonday);
      const weekStart = nextMonday.toISOString().split('T')[0];

      const payload = {
        week_start: weekStart,
        is_active: true,
        sessions: sessions
      };

      if (schedule) {
        // Update existing
        await api.patch(`/api/v1/schedule/weekly/${schedule.id}`, payload);
      } else {
        // Create new
        await api.post('/api/v1/schedule/weekly', payload);
      }

      setSuccess('Schedule saved successfully!');
      await fetchSchedule();
      
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save schedule');
    } finally {
      setSaving(false);
    }
  };

  const generateAIProgram = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');

      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      if (!schedule) {
        setError('Please create a schedule first');
        return;
      }

      // Get user profile for methodology
      const userResponse = await api.get('/api/v1/users/me');
      const methodology = userResponse.data.training_methodology || 'custom';

      const response = await api.post('/api/v1/schedule/weekly/generate-ai', {
        schedule_id: schedule.id,
        methodology: methodology,
        focus_movements: []
      });

      setSuccess('AI program generated! Check your workouts.');
      router.push('/dashboard/workouts');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate AI program');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading schedule...</p>
        </div>
      </div>
    );
  }

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
          
          <h1 className="text-3xl font-bold text-gray-900">Weekly Training Schedule</h1>
          <p className="mt-2 text-gray-600">
            Set your training days and times. The AI will generate workouts based on your schedule.
          </p>
        </div>

        {/* Alerts */}
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
            {error}
          </div>
        )}
        
        {success && (
          <div className="mb-4 bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded">
            {success}
          </div>
        )}

        {/* Schedule Grid */}
        <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
          <div className="p-6">
            <div className="space-y-6">
              {DAYS.map((day, dayIndex) => {
                const daySessions = sessions.filter(s => s.day_index === dayIndex);
                
                return (
                  <div key={dayIndex} className="border-b border-gray-200 pb-6 last:border-0">
                    {/* Day Header */}
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-lg font-semibold text-gray-900">{day}</h3>
                      <button
                        onClick={() => addSession(dayIndex)}
                        disabled={daySessions.length >= 3}
                        className="btn-secondary text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        + Add Session
                      </button>
                    </div>

                    {/* Sessions */}
                    {daySessions.length === 0 ? (
                      <p className="text-gray-500 italic">Rest day</p>
                    ) : (
                      <div className="space-y-3">
                        {daySessions.map((session) => (
                          <div
                            key={`${session.day_index}-${session.session_number}`}
                            className="border border-gray-200 rounded-lg p-4 bg-gray-50"
                          >
                            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                              {/* Start Time */}
                              <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                  Start Time
                                </label>
                                <input
                                  type="time"
                                  value={session.start_time}
                                  onChange={(e) => updateSession(
                                    session.day_index,
                                    session.session_number,
                                    'start_time',
                                    e.target.value
                                  )}
                                  className="input-field"
                                />
                              </div>

                              {/* Duration */}
                              <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                  Duration (min)
                                </label>
                                <input
                                  type="number"
                                  min="30"
                                  max="180"
                                  step="15"
                                  value={session.duration_minutes}
                                  onChange={(e) => updateSession(
                                    session.day_index,
                                    session.session_number,
                                    'duration_minutes',
                                    parseInt(e.target.value)
                                  )}
                                  className="input-field"
                                />
                              </div>

                              {/* Workout Type */}
                              <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                  Type
                                </label>
                                <select
                                  value={session.workout_type}
                                  onChange={(e) => updateSession(
                                    session.day_index,
                                    session.session_number,
                                    'workout_type',
                                    e.target.value
                                  )}
                                  className="input-field"
                                >
                                  {WORKOUT_TYPES.map(type => (
                                    <option key={type} value={type}>
                                      {type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                    </option>
                                  ))}
                                </select>
                              </div>

                              {/* Remove Button */}
                              <div className="flex items-end">
                                <button
                                  onClick={() => removeSession(session.day_index, session.session_number)}
                                  className="w-full bg-red-50 text-red-600 px-4 py-2 rounded hover:bg-red-100 transition"
                                >
                                  Remove
                                </button>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4">
          <button
            onClick={saveSchedule}
            disabled={saving || sessions.length === 0}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save Schedule'}
          </button>

          {schedule && (
            <button
              onClick={generateAIProgram}
              disabled={saving}
              className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              🤖 Generate AI Program
            </button>
          )}
        </div>

        {/* Stats */}
        {sessions.length > 0 && (
          <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
            <h3 className="font-semibold text-blue-900 mb-2">Week Summary</h3>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-blue-700">Training Days:</span>
                <span className="ml-2 font-semibold text-blue-900">
                  {new Set(sessions.map(s => s.day_index)).size}
                </span>
              </div>
              <div>
                <span className="text-blue-700">Total Sessions:</span>
                <span className="ml-2 font-semibold text-blue-900">{sessions.length}</span>
              </div>
              <div>
                <span className="text-blue-700">Total Time:</span>
                <span className="ml-2 font-semibold text-blue-900">
                  {sessions.reduce((sum, s) => sum + s.duration_minutes, 0)} min
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
