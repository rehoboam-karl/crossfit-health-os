'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { api } from '@/lib/api'

export default function DashboardPage() {
  const router = useRouter()
  const [user, setUser] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadUser = async () => {
      if (!api.isAuthenticated()) {
        router.push('/login')
        return
      }

      try {
        const userData = await api.getMe()
        setUser(userData)
      } catch (error) {
        console.error('Failed to load user:', error)
        router.push('/login')
      } finally {
        setLoading(false)
      }
    }

    loadUser()
  }, [router])

  const handleLogout = async () => {
    await api.logout()
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white shadow">
        <div className="container mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <Link href="/dashboard" className="text-2xl font-bold text-primary-600">
                🏋️ CrossFit Health OS
              </Link>
              <div className="hidden md:flex space-x-4">
                <Link href="/dashboard/workouts" className="text-gray-600 hover:text-primary-600">
                  Workouts
                </Link>
                <Link href="/dashboard/schedule" className="text-gray-600 hover:text-primary-600">
                  Schedule
                </Link>
                <Link href="/dashboard/reviews" className="text-gray-600 hover:text-primary-600">
                  Reviews
                </Link>
                <Link href="/dashboard/profile" className="text-gray-600 hover:text-primary-600">
                  Profile
                </Link>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-gray-700">Hi, {user?.name}</span>
              <button onClick={handleLogout} className="text-gray-600 hover:text-primary-600">
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-8">
        {/* Welcome Banner */}
        <div className="card bg-gradient-to-r from-primary-600 to-primary-800 text-white mb-8">
          <h1 className="text-3xl font-bold mb-2">
            Welcome back, {user?.name}! 💪
          </h1>
          <p className="text-primary-100">
            Ready to crush today's workout? Your AI coach has your program ready.
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="card">
            <div className="text-sm text-gray-600 mb-1">Readiness Score</div>
            <div className="text-3xl font-bold text-primary-600">--</div>
            <div className="text-xs text-gray-500 mt-1">Sync HealthKit</div>
          </div>

          <div className="card">
            <div className="text-sm text-gray-600 mb-1">This Week</div>
            <div className="text-3xl font-bold text-gray-900">0/5</div>
            <div className="text-xs text-gray-500 mt-1">Sessions Complete</div>
          </div>

          <div className="card">
            <div className="text-sm text-gray-600 mb-1">Current Week</div>
            <div className="text-3xl font-bold text-gray-900">1</div>
            <div className="text-xs text-gray-500 mt-1">Accumulation Phase</div>
          </div>

          <div className="card">
            <div className="text-sm text-gray-600 mb-1">Next Review</div>
            <div className="text-3xl font-bold text-gray-900">--</div>
            <div className="text-xs text-gray-500 mt-1">Days until</div>
          </div>
        </div>

        {/* Today's Workout */}
        <div className="card mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-bold">Today's Workout</h2>
            <span className="text-sm text-gray-600">Monday, Feb 8, 2026</span>
          </div>

          <div className="bg-gray-50 p-6 rounded-lg">
            <div className="text-center text-gray-600 py-8">
              <div className="text-4xl mb-4">🎯</div>
              <p className="text-lg font-semibold mb-2">No workout generated yet</p>
              <p className="text-sm mb-4">
                Create your training schedule to get AI-powered workouts
              </p>
              <Link href="/dashboard/schedule" className="btn-primary inline-block">
                Create Schedule
              </Link>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid md:grid-cols-3 gap-6">
          <Link href="/dashboard/schedule" className="card hover:shadow-lg transition-shadow">
            <div className="text-3xl mb-3">📅</div>
            <h3 className="font-bold text-lg mb-2">Create Schedule</h3>
            <p className="text-sm text-gray-600">
              Set up your weekly training schedule with AI-powered programming
            </p>
          </Link>

          <Link href="/dashboard/workouts" className="card hover:shadow-lg transition-shadow">
            <div className="text-3xl mb-3">💪</div>
            <h3 className="font-bold text-lg mb-2">View Workouts</h3>
            <p className="text-sm text-gray-600">
              Browse your training history and track progress
            </p>
          </Link>

          <Link href="/dashboard/profile" className="card hover:shadow-lg transition-shadow">
            <div className="text-3xl mb-3">⚙️</div>
            <h3 className="font-bold text-lg mb-2">Profile Settings</h3>
            <p className="text-sm text-gray-600">
              Update your goals, weaknesses, and preferences
            </p>
          </Link>
        </div>

        {/* Getting Started Guide */}
        <div className="card mt-8 bg-blue-50 border border-blue-200">
          <h3 className="font-bold text-lg mb-4">🚀 Getting Started</h3>
          <ol className="space-y-3 text-sm">
            <li className="flex items-start">
              <span className="bg-primary-600 text-white rounded-full w-6 h-6 flex items-center justify-center mr-3 shrink-0 text-xs font-bold">
                1
              </span>
              <div>
                <strong>Create your training schedule:</strong> Choose training days and times that fit your lifestyle
              </div>
            </li>
            <li className="flex items-start">
              <span className="bg-primary-600 text-white rounded-full w-6 h-6 flex items-center justify-center mr-3 shrink-0 text-xs font-bold">
                2
              </span>
              <div>
                <strong>Generate AI workouts:</strong> Select methodology (HWPO, Mayhem, CompTrain) and week number
              </div>
            </li>
            <li className="flex items-start">
              <span className="bg-primary-600 text-white rounded-full w-6 h-6 flex items-center justify-center mr-3 shrink-0 text-xs font-bold">
                3
              </span>
              <div>
                <strong>Track your sessions:</strong> Log weights, reps, RPE, and recovery metrics
              </div>
            </li>
            <li className="flex items-start">
              <span className="bg-primary-600 text-white rounded-full w-6 h-6 flex items-center justify-center mr-3 shrink-0 text-xs font-bold">
                4
              </span>
              <div>
                <strong>Weekly reviews:</strong> AI analyzes your performance and adjusts next week's program
              </div>
            </li>
          </ol>
        </div>
      </main>
    </div>
  )
}
