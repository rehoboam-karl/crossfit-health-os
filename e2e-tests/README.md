# CrossFit Health OS - Playwright E2E Test Suite

## Overview
Automated end-to-end tests for all user workflows using Playwright.

## Setup

```bash
# Install dependencies
cd e2e-tests
npm install
npx playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your BASE_URL
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

## Test Coverage

| Test File | Status | Description |
|-----------|--------|-------------|
| `auth.spec.js` | ✅ 38 passing | Login, registration, password reset, validation |
| `edge-cases.spec.js` | ✅ Passing | Error handling, input validation |
| `dashboard.spec.js` | ⏸️ Needs backend fix | Requires bcrypt fix in backend |
| `onboarding.spec.js` | ⏸️ Needs backend fix | Requires bcrypt fix in backend |
| `profile.spec.js` | ⏸️ Needs backend fix | Requires bcrypt fix in backend |

## Backend Issue

**Note:** The backend has a bcrypt/passlib compatibility issue that prevents user registration:
```
ERROR: app.api.v1.auth: Registration error: password cannot be longer than 72 bytes
```

This affects tests that require authenticated users. Once fixed:
1. Run `createAndLoginTestUser()` helper to authenticate
2. Move skipped tests back to their proper files

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
│   └── edge-cases.spec.js    # Error handling, edge cases
└── utils/
    ├── fixtures.js           # Test data fixtures
    └── helpers.js            # API helpers, utilities
```
