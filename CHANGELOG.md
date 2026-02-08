# Changelog - CrossFit Health OS

## [Unreleased] - 2026-02-08

### ✨ Added - Frontend Python Completo

#### **Frontend Unificado (FastAPI + Jinja2)**

Substituímos o Next.js planejado por um **frontend totalmente Python** integrado ao backend:

**Stack:**
- FastAPI (web routes)
- Jinja2 (templates server-side)
- Tailwind CSS (utility-first styling)
- Bootstrap 5 (components)
- ApexCharts (interactive charts)
- Alpine.js (lightweight JS)

**Páginas Criadas:**

1. **Dashboard** (`/dashboard`)
   - 4 stats cards (Readiness, Workouts, HRV, Calories)
   - Today's adaptive workout card
   - Recovery gauge (radial chart)
   - Volume trend chart (30 days)
   - HRV & Readiness dual-axis chart

2. **Training** (`/training`)
   - Recent workouts feed (cards)
   - Personal Records showcase
   - Workout type distribution (donut chart)
   - RPE average chart (7 days)

3. **Health** (`/health`)
   - Lab report upload banner (OCR ready)
   - Biomarker cards grid (4 metrics)
   - Recovery metrics table (7 days)
   - Biomarker trend chart (6 months)

4. **Nutrition** (`/nutrition`)
   - Macro rings (Protein/Carbs/Fat)
   - Daily calorie counter
   - Meal logging form
   - Recent meals feed
   - Weekly macro trend chart

**Features:**
- ✅ Responsive design (mobile-first)
- ✅ Dark sidebar with gradient
- ✅ Modern card hover effects
- ✅ Real-time date display
- ✅ Notification badge
- ✅ User profile sidebar

**Architecture Changes:**
- Added `app/web/routes.py` - Web HTML routes
- Added `app/templates/` - Jinja2 templates
- Added `app/static/` - Static files directory
- Updated `app/main.py` - Mount templates + static files
- Updated `requirements.txt` - Added jinja2, aiofiles

**Data Handling:**
- Mock data functions in `web/routes.py`
- Ready to connect to Supabase queries
- All charts using sample data

**Documentation:**
- Created `FRONTEND_GUIDE.md` - Complete frontend documentation
- Includes testing guide, customization, deployment

### 🔧 Changed

- **Stack Decision:** Next.js → FastAPI + Jinja2
  - **Reason:** Single Python stack, simpler deployment, one container
  - **Trade-off:** Less JavaScript interactivity, but faster SSR
  - **Benefit:** No build step, no hydration, instant loads

- **Deployment:** 2 containers → 1 container
  - Frontend + Backend unified in single FastAPI app
  - Simpler Coolify deployment
  - Shared auth context

### 📝 Notes

**Frontend Status:**
- ✅ UI/UX 100% complete
- ⏳ API integration pending
- ⏳ Authentication pending
- ✅ Charts functional
- ✅ Responsive layouts

**Next Steps:**
1. Connect mock data to Supabase
2. Implement JWT authentication
3. Add form handlers (workout log, meal entry)
4. Implement file upload (lab reports, meal photos)
5. Add real-time updates (WebSocket)

---

## [0.1.0] - 2026-02-08

### Initial Backend Release

- ✅ Complete FastAPI backend structure
- ✅ Adaptive training engine (HWPO/Mayhem)
- ✅ Supabase schema (13 tables)
- ✅ Docker Compose setup
- ✅ API endpoints (training, health, nutrition, integrations)
- ✅ Pydantic models
- ✅ Authentication layer
- ✅ Integration stubs (HealthKit, Calendar, OCR)

See `IMPLEMENTATION_GUIDE.md` for backend details.

---

## Legend

- ✨ Added
- 🔧 Changed
- 🐛 Fixed
- 🗑️ Removed
- ⚠️ Deprecated
- 🔒 Security
