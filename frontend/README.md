# CrossFit Health OS - Frontend

Next.js 14 frontend with App Router, TypeScript, and Tailwind CSS.

## 🚀 Quick Start

### Development

```bash
# Install dependencies
npm install

# Create .env.local
cp .env.example .env.local
# Edit .env.local with your backend URL

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### Production Build

```bash
npm run build
npm start
```

### Docker

```bash
# Build image
docker build -t crossfit-frontend .

# Run container
docker run -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://backend:8000 \
  crossfit-frontend
```

## 📁 Structure

```
frontend/
├── app/                        # Next.js App Router
│   ├── page.tsx               # Landing page
│   ├── login/                 # Login page
│   ├── register/              # Registration
│   ├── forgot-password/       # Password reset request
│   ├── dashboard/             # Dashboard (authenticated)
│   ├── layout.tsx             # Root layout
│   └── globals.css            # Global styles
│
├── components/                 # React components
│   └── (empty - to be added)
│
├── lib/                        # Utilities
│   └── api.ts                 # API client for backend
│
├── public/                     # Static assets
│
├── Dockerfile                  # Production Docker image
├── next.config.js              # Next.js configuration
├── tailwind.config.js          # Tailwind CSS config
├── tsconfig.json               # TypeScript config
└── package.json                # Dependencies
```

## 📄 Pages

### Public Pages
- **/** - Landing page with features, pricing, CTA
- **/login** - User login
- **/register** - New user registration with profile setup
- **/forgot-password** - Request password reset email

### Authenticated Pages
- **/dashboard** - Main dashboard (requires login)
- **/dashboard/workouts** - Training history (TODO)
- **/dashboard/schedule** - Weekly schedule management (TODO)
- **/dashboard/reviews** - Performance reviews (TODO)
- **/dashboard/profile** - User settings (TODO)

## 🔌 API Integration

### API Client (`lib/api.ts`)

```typescript
import { api } from '@/lib/api'

// Authentication
await api.register({ email, password, name, ... })
await api.login(email, password)
await api.logout()
await api.forgotPassword(email)

// User
const user = await api.getMe()
await api.updateProfile({ weight_kg: 82 })

// Schedule
const schedule = await api.getActiveSchedule()
await api.createSchedule({ ... })
await api.generateAIProgram({ methodology: 'hwpo', week_number: 1 })

// Reviews
await api.submitFeedback({ session_id, rpe_score, ... })
const review = await api.generateWeeklyReview({ week_number, ... })
```

### Authentication Flow

1. User registers or logs in
2. Backend returns `access_token`
3. Token stored in `localStorage`
4. Axios interceptor adds token to all requests
5. On 401 error, redirect to login

### State Management

- No global state library (yet)
- Local component state with `useState`
- API client handles token storage
- Consider adding Context API or Zustand later

## 🎨 Styling

### Tailwind CSS

Utility-first CSS framework. Custom theme in `tailwind.config.js`:

```js
theme: {
  extend: {
    colors: {
      primary: { ... }  // Custom blue palette
    }
  }
}
```

### Custom Classes (`globals.css`)

```css
.btn-primary      /* Primary button */
.btn-secondary    /* Secondary button */
.input-field      /* Form input */
.card             /* Card component */
```

## 🔧 Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

Variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.

## 📦 Dependencies

- **next**: 14.1.0 - React framework with App Router
- **react**: 18.2.0
- **@supabase/supabase-js**: 2.39.0 - Supabase client (optional)
- **axios**: 1.6.5 - HTTP client
- **typescript**: 5.x
- **tailwindcss**: 3.4.1 - CSS framework

## 🚧 TODO

### Pages to Build
- [ ] Dashboard → Workouts (list sessions)
- [ ] Dashboard → Schedule (create/edit schedule)
- [ ] Dashboard → Reviews (view weekly reviews)
- [ ] Dashboard → Profile (edit user profile)
- [ ] Reset Password page (with token from email)

### Components to Create
- [ ] Navbar component (extract from pages)
- [ ] Workout Card component
- [ ] Schedule Calendar component
- [ ] Review Card component
- [ ] Loading spinner
- [ ] Alert/Toast notifications

### Features
- [ ] HealthKit integration (iOS)
- [ ] Real-time workout tracking
- [ ] Progress charts (Chart.js or Recharts)
- [ ] Mobile PWA manifest
- [ ] Dark mode toggle

### Testing
- [ ] Unit tests (Jest + React Testing Library)
- [ ] E2E tests (Playwright or Cypress)

## 🐛 Known Issues

- No protected route middleware (manual `useEffect` check in each page)
- No loading states between route changes
- No error boundary for runtime errors
- localStorage used directly (should abstract to hook)

## 🔒 Security

- Tokens stored in localStorage (consider httpOnly cookies)
- CORS configured in backend
- XSS protection via React's default escaping
- CSRF protection via Supabase Auth

## 📱 Mobile

- Responsive design with Tailwind breakpoints
- PWA ready (TODO: add manifest.json + service worker)
- Touch-friendly UI elements

## 🚀 Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Coolify / Docker

```bash
# Build and run
docker compose up frontend
```

## 📖 Learn More

- [Next.js Docs](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Backend API Docs](http://localhost:8000/docs)
