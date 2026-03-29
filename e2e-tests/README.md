# CrossFit Health OS - Playwright E2E Test Suite

## Overview
Automated end-to-end tests for all user workflows using Playwright.

## Setup

```bash
# Install dependencies
cd e2e-tests
npm init -y
npm install @playwright/test
npx playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your test configuration
```

## Running Tests

```bash
# Run all tests
npx playwright test

# Run with UI (headed mode)
npx playwright test --headed

# Run specific test file
npx playwright test tests/auth.spec.js

# Run specific test
npx playwright test tests/auth.spec.js --grep "login success"

# Run with trace viewer (on failure)
npx playwright test --trace on
```

## Test Structure

```
e2e-tests/
├── playwright.config.js
├── .env.example
├── package.json
├── tests/
│   ├── auth.spec.js          # Login, registration, password reset
│   ├── onboarding.spec.js    # New user onboarding flow
│   ├── dashboard.spec.js     # Dashboard and navigation
│   ├── profile.spec.js       # Profile management
│   ├── training.spec.js      # Training features
│   ├── nutrition.spec.js     # Nutrition features
│   ├── health.spec.js        # Health/biometrics features
│   └── edge-cases.spec.js     # Error handling, edge cases
└── utils/
    ├── api.js                # API helper functions
    ├── fixtures.js           # Test data fixtures
    └── helpers.js            # Common helper functions
```

## Environment Variables

```env
BASE_URL=http://localhost:8000
API_BASE_URL=http://localhost:8000/api/v1
TEST_EMAIL=test@example.com
TEST_PASSWORD=TestPass123
ADMIN_EMAIL=admin@example.com
```

## Test Coverage

### Authentication (auth.spec.js)
- ✅ Login success with valid credentials
- ✅ Login failure with invalid password
- ✅ Login failure with non-existent email
- ✅ Login with empty email field
- ✅ Login with empty password field
- ✅ Register success with valid data
- ✅ Register failure with password mismatch
- ✅ Register failure with weak password (no uppercase)
- ✅ Register failure with weak password (no number)
- ✅ Register failure with short password (<8 chars)
- ✅ Register failure with duplicate email
- ✅ Register success with optional fields
- ✅ Forgot password flow (existing user)
- ✅ Forgot password flow (non-existent user)
- ✅ Password reset with valid token
- ✅ Password reset with invalid token
- ✅ Password reset with password mismatch
- ✅ Remember me checkbox persistence
- ✅ Logout clears session

### Onboarding (onboarding.spec.js)
- ✅ Full onboarding flow (6 steps)
- ✅ Onboarding step navigation (next/prev)
- ✅ Onboarding with focus = training
- ✅ Onboarding with focus = full
- ✅ Onboarding with focus = custom
- ✅ Onboarding with different fitness levels
- ✅ Onboarding with selected training days
- ✅ Onboarding with preferred time selection
- ✅ Onboarding review step shows correct data
- ✅ Onboarding completion awards XP
- ✅ Skip onboarding if already completed
- ✅ Onboarding validates required fields

### Dashboard (dashboard.spec.js)
- ✅ Dashboard loads for authenticated user
- ✅ Dashboard redirects unauthenticated to login
- ✅ Navigation to workouts page
- ✅ Navigation to schedule page
- ✅ Navigation to health page
- ✅ Navigation to nutrition page
- ✅ Navigation to reviews page
- ✅ Navigation to profile page
- ✅ Navigation to badges page
- ✅ Dashboard shows user name

### Profile (profile.spec.js)
- ✅ Profile page loads
- ✅ Update name
- ✅ Update birth date
- ✅ Update weight
- ✅ Update height
- ✅ Update fitness level
- ✅ Goals selection updates

### Edge Cases (edge-cases.spec.js)
- ✅ Repeated registration attempts
- ✅ Session reset clears localStorage
- ✅ Invalid email format rejected
- ✅ Future birth date rejected
- ✅ Network error shows error message
- ✅ 404 page handling
- ✅ Concurrent login sessions handling
