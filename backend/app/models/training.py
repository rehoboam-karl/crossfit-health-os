"""
Pydantic models for Training domain
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
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


class WorkoutSessionUpdate(BaseModel):
    """Update workout session (after completion)"""
    completed_at: datetime
    duration_minutes: float
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
    user_id: UUID
    date: date
    force_rest: bool = False  # Override and force rest day


class AdaptiveWorkoutResponse(BaseModel):
    """Generated workout with volume adjustment"""
    template: WorkoutTemplate
    volume_multiplier: float = Field(..., description="1.0 = normal, 0.8 = reduced, 1.1 = increased")
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
