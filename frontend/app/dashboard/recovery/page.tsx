"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

interface RecoveryMetric {
  id: string;
  user_id: string;
  date: string;
  hrv_ms: number;
  resting_hr_bpm: number;
  sleep_hours: number;
  sleep_quality: number;
  stress_level: number;
  muscle_soreness: number;
  energy_level: number;
  mood: number;
  readiness_score: number;
  notes?: string;
  created_at: string;
}

export default function RecoveryPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [metrics, setMetrics] = useState<RecoveryMetric[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [formData, setFormData] = useState({
    date: new Date().toISOString().split('T')[0],
    hrv_ms: 50,
    resting_hr_bpm: 60,
    sleep_hours: 7.5,
    sleep_quality: 7,
    stress_level: 5,
    muscle_soreness: 3,
    energy_level: 7,
    mood: 7,
    notes: ''
  });

  useEffect(() => {
    fetchMetrics();
  }, []);

  const fetchMetrics = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      // Get last 30 days
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(endDate.getDate() - 30);

      const response = await api.get('/api/v1/health/recovery', {
        params: {
          start_date: startDate.toISOString().split('T')[0],
          end_date: endDate.toISOString().split('T')[0]
        }
      });

      setMetrics(response.data || []);
      setLoading(false);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push('/login');
      } else {
        setError('Failed to load recovery metrics');
        setLoading(false);
      }
    }
  };

  const calculateReadinessScore = (data: any) => {
    // Normalize HRV (assume 30-100ms range)
    const hrvNorm = Math.min(Math.max((data.hrv_ms - 30) / 70, 0), 1);
    
    // Normalize sleep (0-10 scale)
    const sleepNorm = data.sleep_quality / 10;
    
    // Normalize stress (inverted, 0-10 scale)
    const stressNorm = 1 - (data.stress_level / 10);
    
    // Normalize soreness (inverted, 0-10 scale)
    const sorenessNorm = 1 - (data.muscle_soreness / 10);
    
    // Weighted average
    const readiness = (
      hrvNorm * 0.4 +
      sleepNorm * 0.3 +
      stressNorm * 0.2 +
      sorenessNorm * 0.1
    ) * 100;
    
    return Math.round(readiness);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    try {
      setSaving(true);
      setError('');
      setSuccess('');

      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      const readinessScore = calculateReadinessScore(formData);

      await api.post('/api/v1/health/recovery', {
        ...formData,
        readiness_score: readinessScore
      });

      setSuccess('Recovery metrics saved!');
      setShowForm(false);
      await fetchMetrics();
      
      // Reset form
      setFormData({
        date: new Date().toISOString().split('T')[0],
        hrv_ms: 50,
        resting_hr_bpm: 60,
        sleep_hours: 7.5,
        sleep_quality: 7,
        stress_level: 5,
        muscle_soreness: 3,
        energy_level: 7,
        mood: 7,
        notes: ''
      });

      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save metrics');
    } finally {
      setSaving(false);
    }
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
          <p className="mt-4 text-gray-600">Loading recovery data...</p>
        </div>
      </div>
    );
  }

  const todayMetric = metrics.find(m => m.date === new Date().toISOString().split('T')[0]);
  const last7Days = metrics.slice(0, 7);

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
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Recovery Metrics</h1>
              <p className="mt-2 text-gray-600">Track your readiness and optimize training</p>
            </div>
            
            {!showForm && (
              <button
                onClick={() => setShowForm(true)}
                className="btn-primary"
              >
                + Log Today's Metrics
              </button>
            )}
          </div>
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

        {/* Today's Readiness */}
        {todayMetric && (
          <div className="bg-white rounded-lg shadow p-8 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Today's Readiness</h2>
            <div className="text-center">
              <div className={`text-6xl font-bold ${getReadinessColor(todayMetric.readiness_score)}`}>
                {todayMetric.readiness_score}
              </div>
              <div className="text-xl text-gray-600 mt-2">
                {getReadinessLabel(todayMetric.readiness_score)}
              </div>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
              <div className="text-center">
                <div className="text-sm text-gray-600">HRV</div>
                <div className="text-xl font-semibold">{todayMetric.hrv_ms}ms</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600">Sleep</div>
                <div className="text-xl font-semibold">{todayMetric.sleep_quality}/10</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600">Stress</div>
                <div className="text-xl font-semibold">{todayMetric.stress_level}/10</div>
              </div>
              <div className="text-center">
                <div className="text-sm text-gray-600">Soreness</div>
                <div className="text-xl font-semibold">{todayMetric.muscle_soreness}/10</div>
              </div>
            </div>
          </div>
        )}

        {/* Log Form */}
        {showForm && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900">Log Recovery Metrics</h2>
              <button
                onClick={() => setShowForm(false)}
                className="text-gray-600 hover:text-gray-800"
              >
                ✕ Cancel
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Date */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Date
                </label>
                <input
                  type="date"
                  value={formData.date}
                  onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                  className="input-field"
                  required
                />
              </div>

              {/* HRV & Resting HR */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    HRV (ms)
                  </label>
                  <input
                    type="number"
                    value={formData.hrv_ms}
                    onChange={(e) => setFormData({ ...formData, hrv_ms: parseFloat(e.target.value) })}
                    className="input-field"
                    min="20"
                    max="150"
                    step="1"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Resting HR (bpm)
                  </label>
                  <input
                    type="number"
                    value={formData.resting_hr_bpm}
                    onChange={(e) => setFormData({ ...formData, resting_hr_bpm: parseFloat(e.target.value) })}
                    className="input-field"
                    min="40"
                    max="100"
                    step="1"
                    required
                  />
                </div>
              </div>

              {/* Sleep */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sleep Hours
                  </label>
                  <input
                    type="number"
                    value={formData.sleep_hours}
                    onChange={(e) => setFormData({ ...formData, sleep_hours: parseFloat(e.target.value) })}
                    className="input-field"
                    min="0"
                    max="12"
                    step="0.5"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Sleep Quality (1-10)
                  </label>
                  <input
                    type="number"
                    value={formData.sleep_quality}
                    onChange={(e) => setFormData({ ...formData, sleep_quality: parseInt(e.target.value) })}
                    className="input-field"
                    min="1"
                    max="10"
                    step="1"
                    required
                  />
                </div>
              </div>

              {/* Stress & Soreness */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Stress Level (1-10)
                  </label>
                  <input
                    type="number"
                    value={formData.stress_level}
                    onChange={(e) => setFormData({ ...formData, stress_level: parseInt(e.target.value) })}
                    className="input-field"
                    min="1"
                    max="10"
                    step="1"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Muscle Soreness (1-10)
                  </label>
                  <input
                    type="number"
                    value={formData.muscle_soreness}
                    onChange={(e) => setFormData({ ...formData, muscle_soreness: parseInt(e.target.value) })}
                    className="input-field"
                    min="1"
                    max="10"
                    step="1"
                    required
                  />
                </div>
              </div>

              {/* Energy & Mood */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Energy Level (1-10)
                  </label>
                  <input
                    type="number"
                    value={formData.energy_level}
                    onChange={(e) => setFormData({ ...formData, energy_level: parseInt(e.target.value) })}
                    className="input-field"
                    min="1"
                    max="10"
                    step="1"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Mood (1-10)
                  </label>
                  <input
                    type="number"
                    value={formData.mood}
                    onChange={(e) => setFormData({ ...formData, mood: parseInt(e.target.value) })}
                    className="input-field"
                    min="1"
                    max="10"
                    step="1"
                    required
                  />
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Notes (optional)
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="input-field"
                  rows={3}
                  placeholder="Any additional notes..."
                />
              </div>

              {/* Readiness Preview */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-sm text-blue-900 font-semibold mb-1">
                  Estimated Readiness Score
                </div>
                <div className={`text-3xl font-bold ${getReadinessColor(calculateReadinessScore(formData))}`}>
                  {calculateReadinessScore(formData)}
                </div>
              </div>

              {/* Submit */}
              <div className="flex gap-4">
                <button
                  type="submit"
                  disabled={saving}
                  className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Saving...' : 'Save Metrics'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {/* History */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-6">Last 7 Days</h2>
          
          {last7Days.length === 0 ? (
            <p className="text-gray-600 text-center py-8">
              No recovery metrics logged yet. Start tracking today!
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-gray-700">Date</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Readiness</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">HRV</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Sleep</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Stress</th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-gray-700">Soreness</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {last7Days.map((metric) => (
                    <tr key={metric.id} className="hover:bg-gray-50">
                      <td className="py-3 px-4 text-sm text-gray-900">
                        {new Date(metric.date).toLocaleDateString('en-US', { 
                          weekday: 'short',
                          month: 'short',
                          day: 'numeric'
                        })}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`text-lg font-bold ${getReadinessColor(metric.readiness_score)}`}>
                          {metric.readiness_score}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center text-sm text-gray-600">
                        {metric.hrv_ms}ms
                      </td>
                      <td className="py-3 px-4 text-center text-sm text-gray-600">
                        {metric.sleep_quality}/10
                      </td>
                      <td className="py-3 px-4 text-center text-sm text-gray-600">
                        {metric.stress_level}/10
                      </td>
                      <td className="py-3 px-4 text-center text-sm text-gray-600">
                        {metric.muscle_soreness}/10
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
