"""
Pydantic models for Training domain
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Dict, Any
import datetime as dt_module
from datetime import datetime, date, time as dt_time
from enum import Enum
from uuid import UUID


class WorkoutType(str, Enum):
    """Workout type enumeration"""
    STRENGTH = "strength"
    METCON = "metcon"
    SKILL = "skill"
    CONDITIONING = "conditioning"
    MIXED = "mixed"


class ScoreType(str, Enum):
    """Workout score type"""
    TIME = "time"
    ROUNDS = "rounds"
    REPS = "reps"
    WEIGHT = "weight"
    DISTANCE = "distance"


class Methodology(str, Enum):
    """Training methodology"""
    HWPO = "hwpo"
    MAYHEM = "mayhem"
    COMPTRAIN = "comptrain"
    CUSTOM = "custom"


# ============================================
# Movement & Exercise Models
# ============================================

class Movement(BaseModel):
    """Individual movement in a workout"""
    movement: str = Field(..., description="Movement name (e.g., 'back_squat', 'thruster')")
    sets: Optional[int] = None
    reps: Optional[int | str] = None  # Can be '21-15-9' or int
    weight_kg: Optional[float] = None
    distance_meters: Optional[float] = None
    duration_seconds: Optional[float] = None
    rest: Optional[str] = None  # '3min', '90s'
    intensity: Optional[str] = None  # '85%', 'RPE 8'
    notes: Optional[str] = None


class ExerciseSet(BaseModel):
    """Individual set within a workout session"""
    set_number: int
    movement_name: str
    reps: Optional[int] = None
    weight_kg: Optional[float] = None
    distance_meters: Optional[float] = None
    duration_seconds: Optional[float] = None
    form_rating: Optional[int] = Field(None, ge=1, le=5)
    tempo: Optional[str] = None
    rest_after_seconds: Optional[int] = None
    notes: Optional[str] = None


# ============================================
# Workout Template Models
# ============================================

class WorkoutTemplateBase(BaseModel):
    """Base workout template"""
    name: str
    description: Optional[str] = None
    methodology: Methodology
    difficulty_level: str = "rx"
    workout_type: WorkoutType
    duration_minutes: Optional[int] = None
    movements: List[Movement]
    target_stimulus: Optional[str] = None
    rep_scheme: Optional[str] = None
    tags: List[str] = []
    equipment_required: List[str] = []
    video_url: Optional[str] = None


class WorkoutTemplateCreate(WorkoutTemplateBase):
    """Create workout template"""
    pass


class WorkoutTemplate(WorkoutTemplateBase):
    """Workout template response"""
    id: UUID
    created_at: datetime
    is_public: bool
    created_by_coach_id: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================
# Workout Session Models
# ============================================

class WorkoutSessionBase(BaseModel):
    """Base workout session"""
    workout_type: WorkoutType
    movements: List[Movement]
    prescribed_weight_kg: Optional[Dict[str, float]] = None
    prescribed_reps: Optional[Dict[str, int]] = None
    notes: Optional[str] = None
    location: Optional[str] = "gym"


class WorkoutSessionCreate(WorkoutSessionBase):
    """Create workout session"""
    template_id: Optional[UUID] = None
    scheduled_at: Optional[datetime] = None
    allow_retroactive: bool = False  # Allow logging past workouts

    @field_validator('scheduled_at')
    @classmethod
    def validate_future_date(cls, v, info):
        """
        Validate scheduled_at date

        - For scheduled workouts (future planning): must be in future
        - For retroactive logging: can be in past if allow_retroactive=True
        """
        if not v:
            return v

        # Allow retroactive logging if flag is set
        allow_retroactive = info.data.get('allow_retroactive', False)
        if allow_retroactive:
            # For retroactive logging, allow past dates up to 30 days back
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            if v < thirty_days_ago:
                raise ValueError('Retroactive workouts must be within the last 30 days')
            return v

        # For scheduled workouts, ensure future date
        if v < datetime.utcnow():
            raise ValueError('Scheduled workouts must be in the future. Use allow_retroactive=True to log past workouts.')

        return v


class WorkoutSessionUpdate(BaseModel):
    """Update workout session (after completion or to mark incomplete)"""
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[float] = None
    actual_weight_kg: Optional[Dict[str, float]] = None
    actual_reps: Optional[Dict[str, int]] = None
    score: Optional[float] = None
    score_type: Optional[ScoreType] = None
    rpe_score: Optional[int] = Field(None, ge=1, le=10)
    
    # Heart rate data
    avg_heart_rate_bpm: Optional[int] = None
    max_heart_rate_bpm: Optional[int] = None
    calories_burned: Optional[int] = None
    
    # Pre-workout metrics
    hrv_pre_workout: Optional[int] = None
    sleep_quality_pre: Optional[int] = Field(None, ge=1, le=10)
    
    # Post-workout
    muscle_groups_worked: List[str] = []
    video_url: Optional[str] = None


class WorkoutSession(WorkoutSessionBase):
    """Workout session response"""
    id: UUID
    user_id: UUID
    template_id: Optional[UUID] = None
    
    scheduled_at: Optional[datetime] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_minutes: Optional[float] = None
    
    actual_weight_kg: Optional[Dict[str, float]] = None
    actual_reps: Optional[Dict[str, int]] = None
    score: Optional[float] = None
    score_type: Optional[ScoreType] = None
    rpe_score: Optional[int] = None
    
    avg_heart_rate_bpm: Optional[int] = None
    max_heart_rate_bpm: Optional[int] = None
    calories_burned: Optional[int] = None
    
    hrv_pre_workout: Optional[int] = None
    sleep_quality_pre: Optional[int] = None
    
    muscle_groups_worked: List[str] = []
    video_url: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================
# Workout Generation Models
# ============================================

class WorkoutGenerationRequest(BaseModel):
    """Request to generate adaptive workout"""
    user_id: Optional[UUID] = None  # Filled from authenticated user if not provided
    date: Optional[dt_module.date] = None  # Defaults to today if not provided
    force_rest: bool = False  # Override and force rest day


class AdaptiveWorkoutResponse(BaseModel):
    """Generated workout with volume adjustment"""
    template: WorkoutTemplate
    volume_multiplier: float = Field(..., ge=0.0, le=2.0, description="1.0 = normal, 0.8 = reduced, 1.1 = increased")
    readiness_score: int = Field(..., ge=0, le=100)
    recommendation: str
    adjusted_movements: List[Movement]
    reasoning: str = Field(..., description="Why this workout and volume")


# ============================================
# Personal Records
# ============================================

class PersonalRecordType(str, Enum):
    """PR type"""
    ONE_RM = "1rm"
    THREE_RM = "3rm"
    FIVE_RM = "5rm"
    TEN_RM = "10rm"
    MAX_REPS = "max_reps"
    BEST_TIME = "best_time"


class PersonalRecordCreate(BaseModel):
    """Create personal record"""
    movement_name: str
    record_type: PersonalRecordType
    value: float
    unit: str
    notes: Optional[str] = None
    video_url: Optional[str] = None


class PersonalRecord(PersonalRecordCreate):
    """Personal record response"""
    id: UUID
    user_id: UUID
    achieved_at: datetime
    session_id: Optional[UUID] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================
# Weekly Training Schedule
# ============================================

class DayOfWeek(str, Enum):
    """Days of the week"""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class TrainingSessionSlot(BaseModel):
    """Individual training session slot in a day"""
    time: dt_time = Field(..., description="Time of day (e.g., 06:00, 18:30)")
    duration_minutes: int = Field(60, ge=30, le=180, description="Session duration")
    workout_type: Optional[WorkoutType] = None
    notes: Optional[str] = None


class DailyTrainingSchedule(BaseModel):
    """Training schedule for a single day"""
    day: DayOfWeek
    sessions: List[TrainingSessionSlot] = Field(..., min_length=0, max_length=3, description="Max 3 sessions per day")
    rest_day: bool = Field(False, description="Mark as rest day")

    @model_validator(mode='after')
    def validate_no_sessions_on_rest_day(self):
        """Ensure no sessions if rest_day=True"""
        if self.rest_day and len(self.sessions) > 0:
            raise ValueError('Rest days cannot have training sessions')
        return self


class WeeklyScheduleCreate(BaseModel):
    """Create weekly training schedule"""
    name: str = Field(..., max_length=100, description="Schedule name (e.g., 'HWPO 5x/week')")
    methodology: Methodology = Field(Methodology.HWPO, description="Training methodology")
    schedule: Dict[DayOfWeek, DailyTrainingSchedule] = Field(..., description="Schedule for each day")
    start_date: date = Field(..., description="When this schedule starts")
    end_date: Optional[date] = None
    active: bool = True
    
    @field_validator('end_date')
    @classmethod
    def validate_end_after_start(cls, v, info):
        """Ensure end_date is after start_date"""
        if v and 'start_date' in info.data and v <= info.data['start_date']:
            raise ValueError('end_date must be after start_date')
        return v


class WeeklySchedule(WeeklyScheduleCreate):
    """Weekly schedule response"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================
# Meal Timing (Synced with Training)
# ============================================

class MealType(str, Enum):
    """Meal types"""
    PRE_WORKOUT = "pre_workout"
    POST_WORKOUT = "post_workout"
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


class MealWindow(BaseModel):
    """Meal timing window"""
    meal_type: MealType
    time: dt_time
    duration_minutes: int = Field(30, ge=15, le=90)
    macros: Optional[Dict[str, float]] = Field(None, description="Target macros: {protein, carbs, fats}")
    notes: Optional[str] = None


class DailyMealPlan(BaseModel):
    """Meal plan for a single day"""
    day: DayOfWeek
    meals: List[MealWindow] = Field(..., min_length=1, max_length=8)
    total_calories: Optional[int] = None
    training_day: bool = True


class WeeklyMealPlanCreate(BaseModel):
    """Create weekly meal plan (auto-generated from training schedule)"""
    training_schedule_id: UUID = Field(..., description="Linked training schedule")
    meal_plans: Dict[DayOfWeek, DailyMealPlan]
    pre_workout_offset_minutes: int = Field(-60, description="Minutes before workout (negative)")
    post_workout_offset_minutes: int = Field(30, description="Minutes after workout")


class WeeklyMealPlan(WeeklyMealPlanCreate):
    """Weekly meal plan response"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
