import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-primary-600 to-primary-800 text-white">
        <nav className="container mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div className="text-2xl font-bold">
              🏋️ CrossFit Health OS
            </div>
            <div className="space-x-4">
              <Link href="/login" className="hover:text-primary-200">
                Login
              </Link>
              <Link
                href="/register"
                className="bg-white text-primary-600 px-4 py-2 rounded-lg font-semibold hover:bg-gray-100"
              >
                Get Started
              </Link>
            </div>
          </div>
        </nav>

        <div className="container mx-auto px-6 py-20 text-center">
          <h1 className="text-5xl md:text-6xl font-bold mb-6">
            Elite Human Performance
            <br />
            <span className="text-primary-200">Powered by AI</span>
          </h1>
          <p className="text-xl md:text-2xl mb-8 text-primary-100 max-w-3xl mx-auto">
            Integrating biometrics, adaptive training, and nutritional intelligence
            to create a closed-loop system for performance optimization.
          </p>
          <div className="space-x-4">
            <Link
              href="/register"
              className="inline-block bg-white text-primary-600 px-8 py-4 rounded-lg font-bold text-lg hover:bg-gray-100 transition-colors"
            >
              Start Free Trial →
            </Link>
            <Link
              href="#features"
              className="inline-block border-2 border-white px-8 py-4 rounded-lg font-bold text-lg hover:bg-white hover:text-primary-600 transition-colors"
            >
              Learn More
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 bg-gray-50">
        <div className="container mx-auto px-6">
          <h2 className="text-4xl font-bold text-center mb-12">
            Everything You Need to Perform
          </h2>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="card">
              <div className="text-4xl mb-4">🧠</div>
              <h3 className="text-xl font-bold mb-2">AI-Powered Programming</h3>
              <p className="text-gray-600">
                GPT-4 generates personalized training programs adapting to your
                recovery, goals, and weaknesses. HWPO, Mayhem, CompTrain methodologies.
              </p>
            </div>

            <div className="card">
              <div className="text-4xl mb-4">📊</div>
              <h3 className="text-xl font-bold mb-2">Adaptive Training</h3>
              <p className="text-gray-600">
                Your workouts adjust automatically based on HRV, sleep quality,
                and readiness scores. Volume and intensity optimized daily.
              </p>
            </div>

            <div className="card">
              <div className="text-4xl mb-4">🔄</div>
              <h3 className="text-xl font-bold mb-2">Weekly Reviews</h3>
              <p className="text-gray-600">
                AI analyzes your performance, identifies strengths and weaknesses,
                and recommends specific adjustments for progressive overload.
              </p>
            </div>

            <div className="card">
              <div className="text-4xl mb-4">🍽️</div>
              <h3 className="text-xl font-bold mb-2">Auto Meal Planning</h3>
              <p className="text-gray-600">
                Pre/post-workout nutrition automatically synced with training
                schedule. Macro calculations based on your goals.
              </p>
            </div>

            <div className="card">
              <div className="text-4xl mb-4">💓</div>
              <h3 className="text-xl font-bold mb-2">Recovery Tracking</h3>
              <p className="text-gray-600">
                HRV, sleep, readiness, biomarker tracking. Apple HealthKit
                integration for seamless data sync.
              </p>
            </div>

            <div className="card">
              <div className="text-4xl mb-4">📈</div>
              <h3 className="text-xl font-bold mb-2">Performance Analytics</h3>
              <p className="text-gray-600">
                Track PRs, benchmark times, volume trends. Monthly analysis
                with Gemini AI for long-term insights.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-20">
        <div className="container mx-auto px-6">
          <h2 className="text-4xl font-bold text-center mb-12">
            The Feedback Loop
          </h2>

          <div className="max-w-4xl mx-auto">
            <div className="space-y-8">
              <div className="flex items-start space-x-4">
                <div className="bg-primary-600 text-white rounded-full w-12 h-12 flex items-center justify-center font-bold shrink-0">
                  1
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2">Track Recovery</h3>
                  <p className="text-gray-600">
                    Log HRV, sleep quality, stress, and soreness. Sync with Apple
                    HealthKit for automatic tracking.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="bg-primary-600 text-white rounded-full w-12 h-12 flex items-center justify-center font-bold shrink-0">
                  2
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2">AI Generates Workout</h3>
                  <p className="text-gray-600">
                    Based on your readiness score, AI adjusts workout volume and
                    intensity. High HRV → push harder. Low HRV → reduce volume.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="bg-primary-600 text-white rounded-full w-12 h-12 flex items-center justify-center font-bold shrink-0">
                  3
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2">Train & Track</h3>
                  <p className="text-gray-600">
                    Complete your workout. Log actual weights, reps, RPE, and
                    technique quality. The more data, the smarter the system.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="bg-primary-600 text-white rounded-full w-12 h-12 flex items-center justify-center font-bold shrink-0">
                  4
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2">Weekly Review</h3>
                  <p className="text-gray-600">
                    Every Sunday, Claude AI analyzes your week. Identifies what's
                    working, what needs work, and adjusts next week's program.
                  </p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="bg-primary-600 text-white rounded-full w-12 h-12 flex items-center justify-center font-bold shrink-0">
                  5
                </div>
                <div>
                  <h3 className="text-xl font-bold mb-2">Progressive Overload</h3>
                  <p className="text-gray-600">
                    Week 1-3: Volume accumulation. Week 4: Deload. Week 5-7:
                    Intensification. Week 8: Test PRs. Rinse and repeat.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20 bg-gray-50">
        <div className="container mx-auto px-6">
          <h2 className="text-4xl font-bold text-center mb-12">
            Simple, Transparent Pricing
          </h2>

          <div className="max-w-md mx-auto card">
            <div className="text-center">
              <div className="text-5xl font-bold text-primary-600 mb-2">
                $29<span className="text-2xl text-gray-600">/mo</span>
              </div>
              <p className="text-gray-600 mb-6">Everything included. No hidden fees.</p>
              
              <ul className="text-left space-y-3 mb-8">
                <li className="flex items-center">
                  <span className="text-primary-600 mr-2">✓</span>
                  AI-powered weekly programming
                </li>
                <li className="flex items-center">
                  <span className="text-primary-600 mr-2">✓</span>
                  Adaptive training adjustments
                </li>
                <li className="flex items-center">
                  <span className="text-primary-600 mr-2">✓</span>
                  Weekly performance reviews
                </li>
                <li className="flex items-center">
                  <span className="text-primary-600 mr-2">✓</span>
                  Auto meal planning
                </li>
                <li className="flex items-center">
                  <span className="text-primary-600 mr-2">✓</span>
                  Recovery & biomarker tracking
                </li>
                <li className="flex items-center">
                  <span className="text-primary-600 mr-2">✓</span>
                  HealthKit integration
                </li>
                <li className="flex items-center">
                  <span className="text-primary-600 mr-2">✓</span>
                  Unlimited workouts
                </li>
              </ul>

              <Link
                href="/register"
                className="btn-primary w-full inline-block text-center"
              >
                Start Free 14-Day Trial
              </Link>
              <p className="text-sm text-gray-500 mt-2">
                No credit card required
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-primary-600 text-white py-16">
        <div className="container mx-auto px-6 text-center">
          <h2 className="text-4xl font-bold mb-4">
            Ready to Optimize Your Performance?
          </h2>
          <p className="text-xl text-primary-100 mb-8">
            Join elite athletes using AI to train smarter, not just harder.
          </p>
          <Link
            href="/register"
            className="inline-block bg-white text-primary-600 px-8 py-4 rounded-lg font-bold text-lg hover:bg-gray-100 transition-colors"
          >
            Get Started Free →
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900 text-gray-400 py-8">
        <div className="container mx-auto px-6 text-center">
          <p>© 2026 CrossFit Health OS. Built for athletes, by athletes.</p>
          <p className="text-sm mt-2">
            Powered by GPT-4, Claude 3.5 Sonnet, and Gemini 1.5 Pro
          </p>
        </div>
      </footer>
    </main>
  )
}
