"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';

interface WeeklyReview {
  id: string;
  user_id: string;
  week_start: string;
  week_end: string;
  summary: string;
  strengths: string[];
  weaknesses: string[];
  recovery_status: string;
  volume_assessment: string;
  progressions: string[];
  recommendations: {
    volume_change_percent: number;
    intensity_change: string;
    focus_movements: string[];
    skill_work_minutes: number;
    mobility_work: boolean;
  };
  ai_model: string;
  created_at: string;
}

export default function ReviewsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [reviews, setReviews] = useState<WeeklyReview[]>([]);
  const [selectedReview, setSelectedReview] = useState<WeeklyReview | null>(null);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    fetchReviews();
  }, []);

  const fetchReviews = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      const response = await api.get('/api/v1/review/weekly');
      setReviews(response.data || []);
      setLoading(false);
    } catch (err: any) {
      if (err.response?.status === 401) {
        router.push('/login');
      } else {
        setError('Failed to load reviews');
        setLoading(false);
      }
    }
  };

  const generateReview = async () => {
    try {
      setGenerating(true);
      setError('');
      setSuccess('');

      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      // Calculate last week's dates
      const today = new Date();
      const lastMonday = new Date(today);
      lastMonday.setDate(today.getDate() - today.getDay() - 6);
      
      const lastSunday = new Date(lastMonday);
      lastSunday.setDate(lastMonday.getDate() + 6);

      const weekStart = lastMonday.toISOString().split('T')[0];
      const weekEnd = lastSunday.toISOString().split('T')[0];

      const response = await api.post('/api/v1/review/weekly', {
        week_start: weekStart,
        week_end: weekEnd
      });

      setSuccess('AI review generated successfully!');
      await fetchReviews();
      setSelectedReview(response.data);

      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate review');
    } finally {
      setGenerating(false);
    }
  };

  const applyRecommendations = async (reviewId: string) => {
    try {
      setError('');
      setSuccess('');

      const token = localStorage.getItem('token');
      if (!token) {
        router.push('/login');
        return;
      }

      await api.post(`/api/v1/review/weekly/${reviewId}/apply`);

      setSuccess('Recommendations applied to next week!');
      setTimeout(() => setSuccess(''), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to apply recommendations');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getRecoveryStatusColor = (status: string) => {
    const colors: { [key: string]: string } = {
      'optimal': 'bg-green-100 text-green-800',
      'adequate': 'bg-yellow-100 text-yellow-800',
      'compromised': 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getVolumeAssessmentColor = (assessment: string) => {
    const colors: { [key: string]: string } = {
      'too_low': 'bg-blue-100 text-blue-800',
      'appropriate': 'bg-green-100 text-green-800',
      'too_high': 'bg-red-100 text-red-800'
    };
    return colors[assessment] || 'bg-gray-100 text-gray-800';
  };

  const getIntensityChangeIcon = (change: string) => {
    const icons: { [key: string]: string } = {
      'decrease': '📉',
      'maintain': '➡️',
      'increase': '📈'
    };
    return icons[change] || '➡️';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading reviews...</p>
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
          
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Weekly Reviews</h1>
              <p className="mt-2 text-gray-600">AI-powered performance analysis</p>
            </div>
            
            <button
              onClick={generateReview}
              disabled={generating}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {generating ? (
                <>
                  <span className="animate-spin mr-2">⚙️</span>
                  Generating...
                </>
              ) : (
                '🤖 Generate New Review'
              )}
            </button>
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

        {/* Reviews List */}
        {reviews.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-600 text-lg mb-4">No reviews yet</p>
            <p className="text-gray-500 mb-6">
              Complete at least one week of training to generate your first AI review
            </p>
            <button
              onClick={generateReview}
              disabled={generating}
              className="btn-primary disabled:opacity-50"
            >
              🤖 Generate First Review
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {reviews.map((review) => (
              <div key={review.id} className="bg-white rounded-lg shadow overflow-hidden">
                {/* Review Header */}
                <div
                  className="bg-gradient-to-r from-blue-500 to-purple-600 text-white p-6 cursor-pointer hover:from-blue-600 hover:to-purple-700 transition"
                  onClick={() => setSelectedReview(selectedReview?.id === review.id ? null : review)}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xl font-semibold mb-2">
                        Week of {formatDate(review.week_start)} - {formatDate(review.week_end)}
                      </h3>
                      <div className="flex items-center gap-4 text-sm opacity-90">
                        <span>🤖 {review.ai_model}</span>
                        <span>•</span>
                        <span>Generated {formatDate(review.created_at)}</span>
                      </div>
                    </div>
                    <div className="text-3xl">
                      {selectedReview?.id === review.id ? '▼' : '▶'}
                    </div>
                  </div>
                </div>

                {/* Review Content (Expandable) */}
                {selectedReview?.id === review.id && (
                  <div className="p-6 space-y-6">
                    {/* Summary */}
                    <div>
                      <h4 className="font-semibold text-gray-900 mb-2">📊 Summary</h4>
                      <p className="text-gray-700">{review.summary}</p>
                    </div>

                    {/* Status Badges */}
                    <div className="flex gap-4">
                      <div>
                        <span className="text-sm text-gray-600 block mb-1">Recovery Status</span>
                        <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getRecoveryStatusColor(review.recovery_status)}`}>
                          {review.recovery_status.replace('_', ' ').toUpperCase()}
                        </span>
                      </div>
                      
                      <div>
                        <span className="text-sm text-gray-600 block mb-1">Volume Assessment</span>
                        <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${getVolumeAssessmentColor(review.volume_assessment)}`}>
                          {review.volume_assessment.replace('_', ' ').toUpperCase()}
                        </span>
                      </div>
                    </div>

                    {/* Strengths & Weaknesses */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <h4 className="font-semibold text-green-900 mb-3">💪 Strengths</h4>
                        <ul className="space-y-2">
                          {review.strengths.map((strength, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-green-600 mt-1">✓</span>
                              <span className="text-gray-700">{strength}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div>
                        <h4 className="font-semibold text-orange-900 mb-3">⚠️ Areas to Improve</h4>
                        <ul className="space-y-2">
                          {review.weaknesses.map((weakness, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-orange-600 mt-1">→</span>
                              <span className="text-gray-700">{weakness}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Progressions */}
                    {review.progressions && review.progressions.length > 0 && (
                      <div>
                        <h4 className="font-semibold text-blue-900 mb-3">📈 Progressions Detected</h4>
                        <ul className="space-y-2">
                          {review.progressions.map((progression, idx) => (
                            <li key={idx} className="flex items-start gap-2">
                              <span className="text-blue-600 mt-1">🎯</span>
                              <span className="text-gray-700">{progression}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Recommendations */}
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
                      <h4 className="font-semibold text-purple-900 mb-4">🎯 Recommendations for Next Week</h4>
                      
                      <div className="space-y-4">
                        {/* Volume & Intensity */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <span className="text-sm text-purple-700 block mb-1">Volume Change</span>
                            <div className="text-2xl font-bold text-purple-900">
                              {review.recommendations.volume_change_percent > 0 ? '+' : ''}
                              {review.recommendations.volume_change_percent}%
                            </div>
                          </div>
                          
                          <div>
                            <span className="text-sm text-purple-700 block mb-1">Intensity</span>
                            <div className="text-2xl font-bold text-purple-900">
                              {getIntensityChangeIcon(review.recommendations.intensity_change)}{' '}
                              {review.recommendations.intensity_change.toUpperCase()}
                            </div>
                          </div>
                        </div>

                        {/* Focus Movements */}
                        {review.recommendations.focus_movements.length > 0 && (
                          <div>
                            <span className="text-sm text-purple-700 block mb-2">Focus On</span>
                            <div className="flex flex-wrap gap-2">
                              {review.recommendations.focus_movements.map((movement, idx) => (
                                <span key={idx} className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm">
                                  {movement}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Additional Work */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {review.recommendations.skill_work_minutes > 0 && (
                            <div className="flex items-center gap-2">
                              <span className="text-purple-600">🎯</span>
                              <span className="text-sm text-purple-900">
                                Add {review.recommendations.skill_work_minutes} min skill work
                              </span>
                            </div>
                          )}
                          
                          {review.recommendations.mobility_work && (
                            <div className="flex items-center gap-2">
                              <span className="text-purple-600">🧘</span>
                              <span className="text-sm text-purple-900">
                                Increase mobility work
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Apply Button */}
                        <div className="pt-4 border-t border-purple-200">
                          <button
                            onClick={() => applyRecommendations(review.id)}
                            className="btn-primary w-full"
                          >
                            ✨ Apply Recommendations to Next Week
                          </button>
                          <p className="text-xs text-purple-600 text-center mt-2">
                            This will automatically adjust your training program
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
