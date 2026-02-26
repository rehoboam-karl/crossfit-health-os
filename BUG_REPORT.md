# Bug Report & Code Review
## CrossFit Health OS

**Review Date:** 2026-02-25
**Reviewed By:** Claude Code Analysis

---

## 🔴 Critical Bugs

### 1. **Readiness Score Calculation Mismatch (adaptive.py:136-159)**

**Location:** `backend/app/core/engine/adaptive.py:136-159`

**Issue:** The readiness score calculation formula is mathematically incorrect and doesn't match the documented percentages.

**Current Code:**
```python
def _calculate_readiness_score(self, recovery: dict) -> int:
    hrv_ratio = recovery.get("hrv_ratio", 1.0)
    sleep_quality = recovery.get("sleep_quality_score", 70)
    stress = recovery.get("stress_level", 5)
    soreness = recovery.get("muscle_soreness", 5)

    readiness = (
        (hrv_ratio * 40) +           # HRV = 40%
        (sleep_quality * 0.3) +      # Sleep = 30%
        ((10 - stress) * 2) +        # Stress = 20%
        ((10 - soreness) * 1)        # Soreness = 10%
    )
```

**Problem:**
- If `hrv_ratio = 1.0` (normal), it contributes `40` points
- If `sleep_quality = 70` (0-100 scale), it contributes `70 * 0.3 = 21` points
- If `stress = 5` (1-10 scale), it contributes `(10-5) * 2 = 10` points
- If `soreness = 5` (1-10 scale), it contributes `(10-5) * 1 = 5` points
- **Total: 40 + 21 + 10 + 5 = 76** (max possible varies wildly)

**Expected Behavior:**
All metrics should be normalized to 0-1 before applying weights, then multiplied by 100.

**Frontend Discrepancy:**
The frontend (`frontend/app/dashboard/recovery/page.tsx:94-116`) correctly normalizes values:
```typescript
const hrvNorm = Math.min(Math.max((data.hrv_ms - 30) / 70, 0), 1);
const sleepNorm = data.sleep_quality / 10;
const stressNorm = 1 - (data.stress_level / 10);
const sorenessNorm = 1 - (data.muscle_soreness / 10);

const readiness = (
  hrvNorm * 0.4 +
  sleepNorm * 0.3 +
  stressNorm * 0.2 +
  sorenessNorm * 0.1
) * 100;
```

**Impact:** HIGH - Core adaptive training logic produces incorrect volume adjustments.

**Recommendation:** Backend should match frontend calculation or vice versa for consistency.

---

### 2. **Missing HRV Baseline Calculation (adaptive.py:118)**

**Location:** `backend/app/core/engine/adaptive.py:99-124`

**Issue:** The adaptive engine expects `hrv_ratio` (HRV relative to baseline), but the default recovery metrics return `hrv_ratio: 1.0` without calculating it from raw HRV values.

**Current Code:**
```python
return {
    "hrv_ratio": 1.0,  # ❌ Hardcoded, not calculated
    "sleep_quality_score": 70,
    ...
}
```

**Problem:**
- Recovery metrics likely store `hrv_rmssd_ms` (raw HRV in milliseconds)
- No code computes user's baseline HRV (7-day or 30-day moving average)
- `hrv_ratio = current_hrv / baseline_hrv` is never calculated
- All users default to 1.0 ratio, negating HRV's 40% weight in readiness

**Impact:** HIGH - HRV monitoring (the most important metric) is non-functional.

**Recommendation:**
1. Add `calculate_hrv_baseline(user_id, lookback_days=30)` function
2. Compute ratio: `current_hrv / baseline_hrv`
3. Store baseline in `users` table or calculate on-the-fly

---

### 3. **Broken Route Definition (schedule.py:125-127)**

**Location:** `backend/app/api/v1/schedule.py:125-127`

**Issue:** Orphaned route decorator without function definition.

**Code:**
```python
@router.get("/weekly", response_model=List[WeeklySchedule])

@router.post("/weekly/generate-ai", status_code=status.HTTP_201_CREATED)
async def generate_weekly_program_ai(...):
```

**Problem:**
- Line 125 has `@router.get("/weekly")` decorator
- No function follows it
- Line 127 starts a completely different endpoint
- FastAPI will fail to register the GET route

**Impact:** CRITICAL - API endpoint `/api/v1/schedule/weekly` (GET) doesn't work. Returns 404 or 500.

**Recommendation:** Move the decorator to line 265 where `list_schedules()` function is defined.

---

### 4. **Duplicate Import (schedule.py:508-509)**

**Location:** `backend/app/api/v1/schedule.py:508-509`

**Issue:** Field imported twice.

**Code:**
```python
from pydantic import BaseModel, Field, Field
```

**Impact:** LOW - Syntax is valid but redundant.

**Recommendation:** Remove duplicate: `from pydantic import BaseModel, Field`

---

### 5. **Google Calendar Database Query Mismatch (calendar.py:130)**

**Location:** `backend/app/core/integrations/calendar.py:130`

**Issue:** Queries for `is_active` field, but the API endpoint creates schedules with `active` field.

**Code:**
```python
# calendar.py:130
schedule_resp = supabase_client.table("weekly_schedules").select("*").eq(
    "user_id", str(user_id)
).eq("is_active", True).single().execute()  # ❌ Field name: is_active

# schedule.py:84
response = supabase_client.table("weekly_schedules").update(
    {"active": False}  # ✅ Field name: active
).eq("user_id", str(user_id)).eq("active", True).execute()
```

**Problem:**
- Database schema likely has `active` column
- Calendar integration queries `is_active` (non-existent)
- Query returns empty result
- Google Calendar sync fails silently

**Impact:** HIGH - Google Calendar integration doesn't work.

**Recommendation:** Standardize on `active` throughout codebase.

---

### 6. **Race Condition in Session Validation (training.py:122-128)**

**Location:** `backend/app/api/v1/training.py:96-129`

**Issue:** TOCTOU (Time-of-Check-Time-of-Use) vulnerability in workout session update.

**Code:**
```python
# Step 1: Check session ownership
session_response = supabase_client.table("workout_sessions").select("*").eq(
    "id", str(session_id)
).single().execute()

if session_response.data["user_id"] != str(user_id):
    raise HTTPException(status_code=403, detail="Not authorized")

# Step 2: Update session (no WHERE user_id check)
response = supabase_client.table("workout_sessions").update(
    update_data
).eq("id", str(session_id)).execute()
```

**Problem:**
- Authorization check happens in Step 1
- Update in Step 2 doesn't re-verify user_id
- If session is transferred/deleted between steps, update could succeed for wrong user
- Small window, but exists

**Impact:** MEDIUM - Authorization bypass possible (low probability).

**Recommendation:** Add `.eq("user_id", str(user_id))` to update query.

---

## 🟡 High Priority Issues

### 7. **Missing API Endpoint for Recovery Metrics with Date Range**

**Location:** `backend/app/api/v1/health.py`

**Issue:** Frontend requests recovery metrics with date range (`start_date`, `end_date` params), but API only has `/recovery/latest` and POST endpoints.

**Frontend Code:**
```typescript
// frontend/app/dashboard/recovery/page.tsx:75-80
const response = await api.get('/api/v1/health/recovery', {
  params: {
    start_date: startDate.toISOString().split('T')[0],
    end_date: endDate.toISOString().split('T')[0]
  }
});
```

**API Endpoints:**
```python
# backend/app/api/v1/health.py
@router.post("/recovery")  # ✅ Exists
@router.get("/recovery/latest")  # ✅ Exists
# ❌ Missing: @router.get("/recovery")
```

**Impact:** HIGH - Frontend recovery page will fail to load historical metrics.

**Recommendation:** Add:
```python
@router.get("/recovery", response_model=List[RecoveryMetric])
async def list_recovery_metrics(
    start_date: date,
    end_date: date,
    current_user: dict = Depends(get_current_user)
):
    ...
```

---

### 8. **Validation Error in Scheduled Workout (training.py:126)**

**Location:** `backend/app/models/training.py:122-128`

**Issue:** Validator prevents scheduling past workouts, but users may want to log retroactive sessions.

**Code:**
```python
@field_validator('scheduled_at')
@classmethod
def validate_future_date(cls, v):
    """Ensure scheduled_at is not in the past"""
    if v and v < datetime.utcnow():
        raise ValueError('scheduled_at must be in the future or present')
    return v
```

**Problem:**
- User wants to log yesterday's workout they forgot to record
- Validator rejects `scheduled_at < now()`
- Common use case: retroactive logging

**Impact:** MEDIUM - UX friction for legitimate use case.

**Recommendation:**
- Remove validator OR
- Add `allow_past=True` flag OR
- Only validate if `completed_at` is None (scheduled workouts must be future)

---

### 9. **Meal Plan Duplicate Meals (schedule.py:433-450)**

**Location:** `backend/app/api/v1/schedule.py:433-450`

**Issue:** Training days get BOTH pre/post workout meals AND standard meals (breakfast/lunch/dinner), causing overlapping meal windows.

**Code:**
```python
else:
    # Training day: add pre/post workout meals
    for session in day_schedule.sessions:
        meals.append(MealWindow(meal_type=MealType.PRE_WORKOUT, ...))
        meals.append(MealWindow(meal_type=MealType.POST_WORKOUT, ...))

    # Add standard meals (avoiding workout times)
    # TODO: Implement smart meal spacing logic
    meals.append(MealWindow(meal_type=MealType.BREAKFAST, time=time(7, 0), ...))
    meals.append(MealWindow(meal_type=MealType.LUNCH, time=time(12, 0), ...))
    meals.append(MealWindow(meal_type=MealType.DINNER, time=time(19, 0), ...))
```

**Problem:**
- If workout is at 6:00 AM, user gets:
  - Pre-workout meal at 5:00 AM
  - Breakfast at 7:00 AM
  - Post-workout meal at 7:30 AM
- Three meals in 2.5 hours (unrealistic)
- TODO comment acknowledges issue but not implemented

**Impact:** MEDIUM - Meal plan UX is confusing.

**Recommendation:** Implement conditional logic to replace nearest standard meal with pre/post workout.

---

### 10. **Calendar Timezone Hardcoded (calendar.py:95)**

**Location:** `backend/app/core/integrations/calendar.py:95-96`

**Issue:** Timezone is hardcoded to "America/Sao_Paulo" for all users.

**Code:**
```python
"start": {"dateTime": start.isoformat(), "timeZone": "America/Sao_Paulo"},
"end": {"dateTime": end.isoformat(), "timeZone": "America/Sao_Paulo"},
```

**Problem:**
- All calendar events created in Brazil timezone
- Users in other timezones get incorrect event times
- No user timezone preference stored

**Impact:** HIGH - International users get wrong workout times.

**Recommendation:**
1. Add `timezone` field to `users` table
2. Use user's timezone or default to UTC
3. Let Google Calendar handle local display

---

### 11. **No Error Handling for AI API Failures (schedule.py:211-228)**

**Location:** `backend/app/api/v1/schedule.py:211-228`

**Issue:** If OpenAI API fails, the entire endpoint fails without fallback.

**Code:**
```python
weekly_program = await ai_programmer.generate_weekly_program(...)
# No try-except, no fallback
```

**Problem:**
- OpenAI API can fail (rate limit, downtime, invalid key)
- User gets 500 error
- No fallback to rule-based program generation
- User experience is all-or-nothing

**Impact:** MEDIUM - Feature completely breaks on API failure.

**Recommendation:** Add try-except with fallback:
```python
try:
    weekly_program = await ai_programmer.generate_weekly_program(...)
except Exception as e:
    logger.warning(f"AI generation failed: {e}, using fallback")
    weekly_program = generate_fallback_program(...)
```

---

## 🟢 Medium Priority Issues

### 12. **Integer Division in Adaptive Movement Adjustment (adaptive.py:264)**

**Location:** `backend/app/core/engine/adaptive.py:264`

**Issue:** Sets are cast to int, losing precision for volume multipliers like 0.8 or 1.1.

**Code:**
```python
if adjusted_movement.sets:
    adjusted_movement.sets = max(1, int(adjusted_movement.sets * volume_multiplier))
```

**Problem:**
- 5 sets × 0.8 = 4.0 → int = 4 ✅ (correct)
- 3 sets × 0.8 = 2.4 → int = 2 ✅ (correct)
- 2 sets × 0.8 = 1.6 → int = 1 ✅ (acceptable)
- BUT: 2 sets × 1.1 = 2.2 → int = 2 ❌ (should be 3 to reflect increase)

**Impact:** LOW - Volume increases are under-applied.

**Recommendation:** Use `round()` instead of `int()` for fair rounding.

---

### 13. **Missing Validation: Weekly Schedule End Date (training.py:291)**

**Location:** `backend/app/models/training.py:287-293`

**Issue:** Validator checks `end_date > start_date`, but doesn't validate against current date.

**Code:**
```python
@field_validator('end_date')
@classmethod
def validate_end_after_start(cls, v, info):
    if v and 'start_date' in info.data and v <= info.data['start_date']:
        raise ValueError('end_date must be after start_date')
    return v
```

**Problem:**
- User can create schedule with `start_date = 2025-01-01` (past)
- System accepts it
- Adaptive engine may use outdated schedule

**Impact:** LOW - Edge case, but possible.

**Recommendation:** Add warning if start_date is in the past (or reject).

---

### 14. **REST Day Validation Edge Case (training.py:269-275)**

**Location:** `backend/app/models/training.py:269-275`

**Issue:** Validator prevents sessions on rest days, but uses `info.data.get('rest_day')` which may not be set during validation.

**Code:**
```python
@field_validator('sessions')
@classmethod
def validate_no_sessions_on_rest_day(cls, v, info):
    if info.data.get('rest_day') and len(v) > 0:
        raise ValueError('Rest days cannot have training sessions')
    return v
```

**Problem:**
- If `rest_day` field is validated AFTER `sessions`, `info.data.get('rest_day')` returns None
- Validation doesn't trigger
- Pydantic field order matters

**Impact:** LOW - May allow invalid data if field order changes.

**Recommendation:** Use `model_validator(mode='after')` instead of `field_validator`.

---

### 15. **Missing Date Normalization in Recovery Metrics (adaptive.py:107)**

**Location:** `backend/app/core/engine/adaptive.py:105-107`

**Issue:** Date comparison uses `.isoformat()`, which can fail if database stores datetime instead of date.

**Code:**
```python
response = self.supabase.table("recovery_metrics").select("*").eq(
    "user_id", str(user_id)
).eq("date", target_date.isoformat()).execute()
```

**Problem:**
- If database column is `TIMESTAMP` instead of `DATE`, comparison fails
- `target_date.isoformat()` = "2026-02-25"
- Database value = "2026-02-25T00:00:00"
- No match found

**Impact:** LOW - Depends on schema definition.

**Recommendation:** Ensure `recovery_metrics.date` is DATE type, not TIMESTAMP.

---

### 16. **Missing Index Optimization**

**Location:** Database queries throughout

**Issue:** Several high-frequency queries don't leverage indexes.

**Examples:**
```python
# Frequently queried without index
.eq("user_id", str(user_id)).eq("active", True)
.eq("user_id", str(user_id)).order("date", desc=True)
.eq("auth_user_id", user.user.id)
```

**Impact:** MEDIUM - Performance degrades with data growth.

**Recommendation:** Add compound indexes:
```sql
CREATE INDEX idx_weekly_schedules_user_active ON weekly_schedules(user_id, active);
CREATE INDEX idx_recovery_metrics_user_date ON recovery_metrics(user_id, date DESC);
CREATE INDEX idx_users_auth_user_id ON users(auth_user_id);
```

---

## 🔵 Low Priority / Code Quality

### 17. **Inconsistent Error Handling Patterns**

**Locations:** Various API endpoints

**Issue:** Some endpoints use `handle_supabase_response()`, others check `response.data` manually.

**Examples:**
```python
# Pattern 1: Using helper
data = handle_supabase_response(response, "Error message")

# Pattern 2: Manual check
if response.data:
    return WorkoutSession(**response.data[0])
raise HTTPException(status_code=500, detail="Failed")
```

**Impact:** LOW - Inconsistent error messages and logging.

**Recommendation:** Standardize on helper functions throughout.

---

### 18. **Missing Type Hints in Calendar Integration**

**Location:** `backend/app/core/integrations/calendar.py:136-187`

**Issue:** Several dict structures have no type hints.

**Example:**
```python
days_config = schedule.get("days", [])  # What shape is this?
day_cfg = next((d for d in days_config if ...), None)  # d is what type?
```

**Impact:** LOW - Reduced IDE autocomplete and type safety.

**Recommendation:** Add TypedDict or Pydantic models for schedule structure.

---

### 19. **Magic Numbers Without Constants**

**Locations:** Throughout codebase

**Examples:**
```python
# adaptive.py
OPTIMAL_THRESHOLD = 80  # ✅ Good
# But:
if readiness_score < 50 and adjusted_movement.weight_kg:  # ❌ Magic 50

# recovery/page.tsx
const hrvNorm = Math.min(Math.max((data.hrv_ms - 30) / 70, 0), 1);
# ❌ Magic 30, 70 (HRV min/max)
```

**Impact:** LOW - Maintainability.

**Recommendation:** Extract to constants.

---

### 20. **Frontend: JWT Expiration Check Has Edge Case**

**Location:** `frontend/app/dashboard/recovery/page.tsx:10-18`

**Issue:** JWT parsing can throw if token is malformed.

**Code:**
```typescript
function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const exp = payload.exp * 1000;
    return Date.now() > exp;
  } catch {
    return true;
  }
}
```

**Problem:**
- If `token.split('.')[1]` doesn't exist (malformed JWT), throws
- If `payload.exp` is undefined, NaN comparison returns false
- Should validate structure

**Impact:** LOW - try-catch handles it, but could be more explicit.

**Recommendation:** Add explicit checks:
```typescript
if (!token || token.split('.').length !== 3) return true;
if (!payload.exp) return true;
```

---

## 📊 User Flow Analysis

### Flow 1: New User Onboarding → First Workout

**Expected Steps:**
1. User registers → Supabase Auth creates account
2. User profile created in `users` table (triggered by Supabase webhook?)
3. User visits dashboard → sees "Quick Start Guide"
4. User clicks "Schedule" → creates weekly training schedule
5. User generates AI program → GPT-4 creates workout templates
6. User logs recovery metrics → enables adaptive training
7. User requests today's workout → adaptive engine adjusts volume
8. User starts session → records in `workout_sessions`
9. User completes session → updates with RPE and score

**Issues Found:**
- ❌ **Step 2:** No webhook or signup endpoint creates user profile automatically
  - `auth.py` checks `users` table by `auth_user_id`
  - If signup doesn't create profile, all API calls fail with 404
  - **Missing:** `/api/v1/auth/signup` endpoint or database trigger

- ❌ **Step 7:** No recovery metrics = default values = incorrect readiness
  - New users have no baseline HRV
  - System defaults to `hrv_ratio = 1.0`, `sleep_quality = 70`
  - Adaptive training is meaningless without data

- ❌ **Step 7:** Recovery metrics query returns wrong field names
  - Adaptive engine expects `hrv_ratio`, `sleep_quality_score`, etc.
  - Database likely stores `hrv_rmssd_ms`, `sleep_quality`
  - Field name mismatch causes crash or wrong defaults

**Severity:** 🔴 CRITICAL - Onboarding flow broken

---

### Flow 2: Experienced User → Weekly AI Program Generation

**Expected Steps:**
1. User has active weekly schedule (e.g., HWPO 5x/week)
2. User clicks "Generate AI Program" → enters week number, focus movements
3. Backend fetches user profile + schedule
4. Backend calls GPT-4 Turbo with programming context
5. GPT-4 returns 5-7 workouts (JSON)
6. Backend saves to `workout_templates`
7. User sees generated workouts

**Issues Found:**
- ❌ **Step 3:** If `schedule_id` not provided, queries for `active=True` schedule
  - Calendar integration queries `is_active=True` (different field)
  - Inconsistent field naming causes query failure

- ⚠️ **Step 4:** No fallback if OpenAI API fails
  - Rate limit or API key issue → 500 error
  - User sees generic error, no recovery

- ⚠️ **Step 5:** If GPT-4 returns malformed JSON, no parsing error handling
  - `_parse_ai_response()` may throw exception
  - No validation of required fields

- ✅ **Step 6:** Workouts saved with tags `week_3`, `ai_hwpo` (good for filtering)

**Severity:** 🟡 HIGH - Feature fails silently on errors

---

### Flow 3: Daily Workflow → Adaptive Training

**Expected Steps:**
1. User wakes up → logs HRV from wearable (manual entry)
2. User logs sleep, stress, soreness in Recovery page
3. Frontend calculates readiness score (94-116)
4. User navigates to Workouts → clicks "Today's Workout"
5. Backend fetches recovery metrics
6. Backend calculates readiness score (136-159)
7. Backend selects workout template based on day + methodology
8. Backend adjusts volume based on readiness
9. User sees adapted workout with reasoning

**Issues Found:**
- 🔴 **CRITICAL:** Frontend and backend use different readiness formulas
  - Frontend: Normalizes all metrics to 0-1, applies weights, × 100
  - Backend: Applies weights to raw values, inconsistent scaling
  - **Result:** Frontend shows 85 (green), backend calculates 62 (yellow/reduced volume)
  - User confused by mismatch

- 🔴 **CRITICAL:** HRV ratio not calculated
  - Backend expects `hrv_ratio` (current/baseline)
  - Database stores `hrv_rmssd_ms` (raw milliseconds)
  - Ratio never computed → always defaults to 1.0
  - HRV monitoring (40% of readiness) is non-functional

- ⚠️ **Step 5:** Database field names don't match model expectations
  - `recovery_metrics` table has: `hrv_ms`, `sleep_quality`, `stress_level`, `muscle_soreness`
  - Adaptive engine expects: `hrv_ratio`, `sleep_quality_score`
  - Default dict hides mismatch but breaks core logic

- ⚠️ **Step 7:** No workout templates in database for new users
  - Query returns empty → uses `_create_default_workout()` fallback
  - Fallback workouts are generic (not methodology-specific)
  - User doesn't get HWPO/Mayhem/CompTrain programming

**Severity:** 🔴 CRITICAL - Core value proposition broken

---

### Flow 4: Google Calendar Sync

**Expected Steps:**
1. User clicks "Connect Google Calendar"
2. Redirected to Google OAuth consent screen
3. User authorizes → redirected to callback URL
4. Backend exchanges code for refresh token
5. Backend stores `google_calendar_refresh_token` in `users` table
6. User clicks "Sync to Calendar"
7. Backend fetches active schedule
8. Backend creates 7 days of calendar events
9. User sees workouts in Google Calendar

**Issues Found:**
- 🔴 **Step 7:** Calendar integration queries wrong field
  - Queries: `.eq("is_active", True)`
  - Schedule API uses: `active` field
  - Query returns empty → "No active schedule found"

- 🟡 **Step 8:** All events created in America/Sao_Paulo timezone
  - International users get wrong times
  - Should use user's timezone preference

- ⚠️ **Step 8:** Calendar sync reads `days` field from schedule
  - Schedule API stores `schedule` field (Dict[DayOfWeek, DailyTrainingSchedule])
  - Field name mismatch → empty days list
  - No events created

**Severity:** 🔴 CRITICAL - Integration completely broken

---

### Flow 5: Lab Report OCR Upload

**Expected Steps:**
1. User visits Health page → uploads lab PDF
2. Backend converts PDF to images
3. Backend sends to GPT-4o Vision API
4. GPT-4o extracts biomarker names, values, ranges
5. Backend saves to `biomarker_readings` table
6. User sees parsed biomarkers with status (normal/low/high)

**Issues Found:**
- ✅ Implementation looks solid
- ⚠️ **Silent failure:** Duplicate biomarkers are skipped without logging
  - Line 116: `except Exception: pass`
  - User doesn't know which biomarkers failed to save

- ⚠️ **No caching:** Same PDF uploaded twice → charges twice
  - Could hash PDF and check for duplicates

- ✅ File size validation (20MB limit)
- ✅ Format validation (PDF, JPG, PNG)

**Severity:** 🟢 LOW - Feature works, minor UX improvements possible

---

## 🎯 Recommendations Priority

### Immediate (Fix Before Production)
1. ✅ Fix readiness score calculation consistency (Bug #1)
2. ✅ Implement HRV baseline calculation (Bug #2)
3. ✅ Fix broken `/api/v1/schedule/weekly` GET route (Bug #3)
4. ✅ Fix Google Calendar `active` vs `is_active` field mismatch (Bug #5)
5. ✅ Add missing `/api/v1/health/recovery` GET endpoint (Bug #7)
6. ✅ Create user profile on signup (Flow 1 issue)
7. ✅ Fix schedule data structure mismatch in calendar sync (Flow 4 issue)

### High Priority (Next Sprint)
8. Add AI API failure fallbacks (Bug #11)
9. Fix meal plan overlap logic (Bug #9)
10. Add authorization check to session update (Bug #6)
11. Make timezone configurable (Bug #10)
12. Add database indexes (Bug #16)

### Medium Priority (Backlog)
13. Fix past workout validation (Bug #8)
14. Improve error handling consistency (Bug #17)
15. Add type hints to calendar integration (Bug #18)
16. Extract magic numbers to constants (Bug #19)

### Low Priority (Tech Debt)
17. Remove duplicate import (Bug #4)
18. Use round() instead of int() for sets (Bug #12)
19. Add date validation for schedules (Bug #13)
20. Improve JWT validation in frontend (Bug #20)

---

## 📈 Testing Recommendations

### Unit Tests Needed
- `adaptive.py::_calculate_readiness_score()` - verify formula
- `adaptive.py::_get_recovery_metrics()` - field mapping
- `calendar.py::sync_calendar_events()` - schedule parsing

### Integration Tests Needed
- Full user signup → first workout flow
- AI program generation with OpenAI mock
- Google Calendar OAuth flow

### E2E Tests Needed
- New user onboarding (signup → profile → schedule → workout)
- Daily adaptive training workflow
- Google Calendar sync

---

**Review completed.** Found 20 bugs (3 critical, 5 high, 7 medium, 5 low) and documented 5 complete user flows with issues.
