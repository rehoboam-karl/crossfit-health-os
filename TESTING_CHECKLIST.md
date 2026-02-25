# CrossFit Health OS - Phase 1 Testing Checklist

## Pre-Testing Setup

1. **Start the backend server:**
   ```bash
   cd /home/rehoboam/crossfit-health-os
   python -m backend.app.main
   # or
   uvicorn backend.app.main:app --reload
   ```

2. **Access the app:**
   - Open browser to `http://localhost:8000`
   - Or deployment URL if hosted

---

## ✅ Authentication Flow

- [ ] Visit `/login` - login page loads
- [ ] Login with valid credentials
- [ ] Token stored in localStorage
- [ ] Redirected to `/dashboard`
- [ ] Visit protected page while logged in - works
- [ ] Clear localStorage and visit `/dashboard` - redirects to login
- [ ] 401 response from API - auto-logout and redirect to login

---

## ✅ Navigation Bar

- [ ] **Dashboard page** - "Dashboard" nav item highlighted
- [ ] **Workouts page** - "Workouts" nav item highlighted
- [ ] **Schedule page** - "Schedule" nav item highlighted
- [ ] **Reviews page** - "Reviews" nav item highlighted
- [ ] **Health page** - "Health" nav item highlighted
- [ ] **Nutrition page** - "Nutrition" nav item highlighted
- [ ] **Profile page** - "Profile" nav item highlighted
- [ ] User dropdown shows user name from localStorage
- [ ] Logout button clears token and redirects to home

---

## ✅ Dashboard Page (`/dashboard`)

- [ ] Page loads without errors
- [ ] Welcome banner shows user name
- [ ] Quick stats cards display (even with placeholder data)
- [ ] Today's workout card shows
- [ ] Quick action cards clickable
- [ ] Getting started guide visible
- [ ] Responsive on mobile

---

## ✅ Workouts Page (`/dashboard/workouts`)

- [ ] Page loads without errors
- [ ] "Generate Adaptive Workout" button present
- [ ] Clicking generate button:
  - [ ] Shows loading spinner
  - [ ] Makes POST to `/api/v1/training/generate`
  - [ ] Shows success/error toast
- [ ] Recent workouts section (empty state if no data)
- [ ] Personal records section (empty state if no data)
- [ ] ApexCharts render:
  - [ ] Workout type donut chart
  - [ ] RPE bar chart
- [ ] Responsive on mobile

---

## ✅ Schedule Page (`/dashboard/schedule`)

- [ ] Page loads without errors
- [ ] Training days checkboxes work
- [ ] Session duration input (min 30, max 180)
- [ ] Methodology dropdown populates
- [ ] Week number input (1-8)
- [ ] Start date defaults to today
- [ ] Week preview updates when days selected
- [ ] Save Schedule button:
  - [ ] Shows loading spinner
  - [ ] Makes POST to `/api/v1/schedule/weekly`
  - [ ] Shows success/error toast
- [ ] Generate AI Workouts button:
  - [ ] Validates methodology selected
  - [ ] Shows loading spinner
  - [ ] Makes POST to `/api/v1/schedule/weekly/generate-ai`
  - [ ] Shows success/error toast
- [ ] Current schedule loads on page load (if exists)
- [ ] Responsive on mobile

---

## ✅ Reviews Page (`/dashboard/reviews`)

- [ ] Page loads without errors
- [ ] Current week summary cards display
- [ ] Generate New Review button:
  - [ ] Shows loading spinner
  - [ ] Makes POST to `/api/v1/review/weekly`
  - [ ] Shows success/error toast
  - [ ] Displays latest review on success
- [ ] Latest review section shows (if data exists):
  - [ ] Strengths list
  - [ ] Weaknesses list
  - [ ] Recovery status badge
  - [ ] AI recommendations
  - [ ] Apply Auto-Adjustments button
  - [ ] View Full Details button
- [ ] Review history list loads
- [ ] Empty state shows if no reviews
- [ ] Responsive on mobile

---

## ✅ Profile Page (`/dashboard/profile`)

- [ ] Page loads without errors
- [ ] Profile loads on mount (GET `/api/v1/profile`)
- [ ] Account form populates with user data
- [ ] Account form submission:
  - [ ] Shows loading spinner
  - [ ] Makes PUT to `/api/v1/profile`
  - [ ] Updates localStorage user name
  - [ ] Shows success/error toast
- [ ] CrossFit form populates
- [ ] CrossFit form submission:
  - [ ] Shows loading spinner
  - [ ] Makes PUT to `/api/v1/profile/crossfit`
  - [ ] Shows success/error toast
- [ ] Profile sidebar shows:
  - [ ] User name
  - [ ] Email
  - [ ] Experience level
  - [ ] Methodology
  - [ ] Member since date
- [ ] Change Password link goes to `/update-password`
- [ ] Delete Account button:
  - [ ] Shows double confirmation
  - [ ] Makes DELETE to `/api/v1/profile`
  - [ ] Clears localStorage
  - [ ] Redirects to home
- [ ] Responsive on mobile

---

## ✅ Health Page (`/dashboard/health`)

- [ ] Page loads without errors
- [ ] No navbar duplication (inherited from base.html)
- [ ] Upload lab report section visible
- [ ] Biomarkers grid (empty state if no data)
- [ ] Recovery metrics table (empty state if no data)
- [ ] Biomarker trend chart renders
- [ ] Responsive on mobile

---

## ✅ Nutrition Page (`/dashboard/nutrition`)

- [ ] Page loads without errors
- [ ] No navbar duplication (inherited from base.html)
- [ ] Macro rings render (ApexCharts):
  - [ ] Protein ring
  - [ ] Carbs ring
  - [ ] Fat ring
- [ ] Calories progress displays
- [ ] Add meal form functional
- [ ] Recent meals section (empty state if no data)
- [ ] Weekly macro trend chart renders
- [ ] Responsive on mobile

---

## ✅ CSS & Bootstrap Consistency

- [ ] No Tailwind CDN link in HTML
- [ ] All pages use Bootstrap 5 classes
- [ ] Cards have consistent `.card.shadow-sm` styling
- [ ] Loading spinners styled identically
- [ ] Toast notifications styled identically
- [ ] Buttons use Bootstrap variants (`btn-primary`, `btn-outline-secondary`)
- [ ] Forms use `.form-control`, `.form-select`, `.form-label`
- [ ] Responsive grid uses `.row.g-3` and `.col-md-*`

---

## ✅ Loading States & Notifications

All AJAX calls should:
- [ ] Show loading spinner during request
- [ ] Hide loading spinner on complete
- [ ] Show success toast on success
- [ ] Show error toast on failure
- [ ] Extract error message from `xhr.responseJSON?.detail`

---

## ✅ Mobile Responsiveness

Test on mobile viewport (375px width):
- [ ] Navbar collapses to hamburger
- [ ] Cards stack vertically
- [ ] Forms are single column
- [ ] Tables scroll horizontally
- [ ] Buttons are full-width or properly sized
- [ ] No horizontal overflow

---

## ✅ Browser Console

Check for:
- [ ] No JavaScript errors on page load
- [ ] No 404s for CSS/JS files
- [ ] AJAX calls show in Network tab
- [ ] localStorage `access_token` present after login
- [ ] ApexCharts load without errors

---

## ✅ API Endpoints (Backend Requirements)

These will return 404 until backend implements them:

### Schedule:
- `POST /api/v1/schedule/weekly`
- `GET /api/v1/schedule/weekly/current`
- `POST /api/v1/schedule/weekly/generate-ai`

### Reviews:
- `POST /api/v1/review/weekly`
- `GET /api/v1/review/weekly/list`
- `GET /api/v1/review/weekly/latest`
- `POST /api/v1/review/{id}/apply-adjustments`

### Profile:
- `GET /api/v1/profile`
- `PUT /api/v1/profile`
- `PUT /api/v1/profile/crossfit`
- `DELETE /api/v1/profile`

### Training:
- `POST /api/v1/training/generate`

---

## Known Limitations (Phase 1)

These are expected and will be fixed in Phase 2:

- [ ] API calls will fail (404/500) until backend implemented
- [ ] No real data displayed (empty states everywhere)
- [ ] Generated workouts don't display (placeholder function)
- [ ] Review details modal not implemented
- [ ] PR entry form not implemented
- [ ] Photo upload for meals not functional

---

## Success Criteria

**Phase 1 is successful if:**
1. ✅ All pages load without JavaScript errors
2. ✅ Navigation works and highlights correctly
3. ✅ Forms are functional and make AJAX calls
4. ✅ Loading spinners and toasts work
5. ✅ Mobile responsive
6. ✅ Bootstrap 5 styling consistent
7. ✅ Auth middleware redirects properly
8. ✅ No Tailwind utility classes in new code

**Backend implementation is Phase 2.**
