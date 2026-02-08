'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'

export default function RegisterPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirm_password: '',
    name: '',
    birth_date: '',
    weight_kg: '',
    height_cm: '',
    fitness_level: 'intermediate',
    goals: [] as string[],
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const goalOptions = [
    { value: 'strength', label: 'Increase Strength' },
    { value: 'conditioning', label: 'Improve Conditioning' },
    { value: 'lose_fat', label: 'Lose Fat' },
    { value: 'gain_muscle', label: 'Gain Muscle' },
    { value: 'general_fitness', label: 'General Fitness' },
    { value: 'competition', label: 'Competition Prep' },
  ]

  const handleGoalToggle = (goal: string) => {
    setFormData((prev) => ({
      ...prev,
      goals: prev.goals.includes(goal)
        ? prev.goals.filter((g) => g !== goal)
        : [...prev.goals, goal],
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const payload = {
        ...formData,
        weight_kg: formData.weight_kg ? parseFloat(formData.weight_kg) : undefined,
        height_cm: formData.height_cm ? parseFloat(formData.height_cm) : undefined,
      }

      await api.register(payload)
      router.push('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-2xl w-full space-y-8">
        <div>
          <Link href="/" className="flex justify-center">
            <span className="text-4xl">🏋️</span>
          </Link>
          <h2 className="mt-6 text-center text-3xl font-bold text-gray-900">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Already have an account?{' '}
            <Link href="/login" className="font-medium text-primary-600 hover:text-primary-500">
              Sign in
            </Link>
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-700">{error}</div>
            </div>
          )}

          <div className="card space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
                  Full Name *
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  required
                  className="input-field"
                  placeholder="John Doe"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
                  Email *
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  className="input-field"
                  placeholder="athlete@example.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
                  Password *
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  className="input-field"
                  placeholder="Min 8 chars, 1 uppercase, 1 number"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                />
              </div>

              <div>
                <label htmlFor="confirm_password" className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm Password *
                </label>
                <input
                  id="confirm_password"
                  name="confirm_password"
                  type="password"
                  required
                  className="input-field"
                  placeholder="Re-enter password"
                  value={formData.confirm_password}
                  onChange={(e) => setFormData({ ...formData, confirm_password: e.target.value })}
                />
              </div>
            </div>

            <div className="border-t pt-4">
              <h3 className="font-semibold mb-3">Profile Information (Optional)</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label htmlFor="birth_date" className="block text-sm font-medium text-gray-700 mb-1">
                    Birth Date
                  </label>
                  <input
                    id="birth_date"
                    name="birth_date"
                    type="date"
                    className="input-field"
                    value={formData.birth_date}
                    onChange={(e) => setFormData({ ...formData, birth_date: e.target.value })}
                  />
                </div>

                <div>
                  <label htmlFor="weight_kg" className="block text-sm font-medium text-gray-700 mb-1">
                    Weight (kg)
                  </label>
                  <input
                    id="weight_kg"
                    name="weight_kg"
                    type="number"
                    step="0.1"
                    className="input-field"
                    placeholder="80"
                    value={formData.weight_kg}
                    onChange={(e) => setFormData({ ...formData, weight_kg: e.target.value })}
                  />
                </div>

                <div>
                  <label htmlFor="height_cm" className="block text-sm font-medium text-gray-700 mb-1">
                    Height (cm)
                  </label>
                  <input
                    id="height_cm"
                    name="height_cm"
                    type="number"
                    className="input-field"
                    placeholder="175"
                    value={formData.height_cm}
                    onChange={(e) => setFormData({ ...formData, height_cm: e.target.value })}
                  />
                </div>
              </div>

              <div className="mt-4">
                <label htmlFor="fitness_level" className="block text-sm font-medium text-gray-700 mb-1">
                  Fitness Level
                </label>
                <select
                  id="fitness_level"
                  name="fitness_level"
                  className="input-field"
                  value={formData.fitness_level}
                  onChange={(e) => setFormData({ ...formData, fitness_level: e.target.value })}
                >
                  <option value="beginner">Beginner (0-1 year training)</option>
                  <option value="intermediate">Intermediate (1-3 years)</option>
                  <option value="advanced">Advanced (3+ years)</option>
                </select>
              </div>

              <div className="mt-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Training Goals (Select all that apply)
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {goalOptions.map((goal) => (
                    <div key={goal.value} className="flex items-center">
                      <input
                        id={goal.value}
                        type="checkbox"
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        checked={formData.goals.includes(goal.value)}
                        onChange={() => handleGoalToggle(goal.value)}
                      />
                      <label htmlFor={goal.value} className="ml-2 block text-sm text-gray-900">
                        {goal.label}
                      </label>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </div>

          <p className="text-xs text-center text-gray-500">
            By creating an account, you agree to our Terms of Service and Privacy Policy.
          </p>
        </form>

        <div className="text-center text-sm text-gray-600">
          <Link href="/" className="hover:text-primary-600">
            ← Back to home
          </Link>
        </div>
      </div>
    </div>
  )
}
