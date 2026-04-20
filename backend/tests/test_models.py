"""
Tests for Pydantic Models
Tests model validation, field constraints, and serialization
"""
import pytest
from pydantic import ValidationError
from datetime import datetime, date
from uuid import uuid4

from app.models.training import (
    Movement,
    WorkoutTemplate,
    WorkoutSessionCreate,
    PersonalRecordCreate,
    DayOfWeek,
    WorkoutType,
    Methodology,
    PersonalRecordType,
)
from app.models.health import (
    RecoveryMetricCreate,
    BiomarkerReadingCreate
)


class TestTrainingModels:
    """Test training domain models"""
    
    def test_movement_valid(self):
        """Test valid movement creation"""
        movement = Movement(
            movement="back_squat",
            sets=5,
            reps=5,
            weight_kg=100.0,
            intensity="85%",
            rest="3min"
        )
        
        assert movement.movement == "back_squat"
        assert movement.sets == 5
        assert movement.reps == 5
        assert movement.weight_kg == 100.0
    
    def test_movement_minimal(self):
        """Test movement with minimal required fields"""
        movement = Movement(movement="burpees")
        
        assert movement.movement == "burpees"
        assert movement.sets is None
        assert movement.reps is None
    
    def test_workout_template_valid(self):
        """Test valid workout template"""
        template = WorkoutTemplate(
            id=uuid4(),
            name="Heavy Squats",
            methodology=Methodology.HWPO,
            difficulty_level="rx",
            workout_type=WorkoutType.STRENGTH,
            duration_minutes=90,
            movements=[
                Movement(movement="back_squat", sets=5, reps=5)
            ],
            target_stimulus="max_strength",
            tags=["strength", "legs"],
            equipment_required=["barbell"],
            created_at=datetime.utcnow(),
            is_public=True
        )
        
        assert template.name == "Heavy Squats"
        assert template.methodology == Methodology.HWPO
        assert len(template.movements) == 1
    
    def test_workout_session_create_valid(self):
        """Test valid workout session creation"""
        from datetime import timedelta
        session = WorkoutSessionCreate(
            workout_type=WorkoutType.STRENGTH,
            movements=[Movement(movement="squat", sets=5, reps=5)],
            notes="Good session",
            scheduled_at=datetime.utcnow() + timedelta(hours=1)
        )
        
        assert session.workout_type == WorkoutType.STRENGTH
        assert len(session.movements) == 1
    
    def test_workout_session_past_date_validation(self):
        """Test workout session validates future/present scheduled_at"""
        # This validation might not be active in the current implementation
        # but the test demonstrates the intent
        past_time = datetime(2020, 1, 1, 12, 0, 0)
        
        with pytest.raises(ValidationError):
            WorkoutSessionCreate(
                workout_type=WorkoutType.STRENGTH,
                movements=[],
                scheduled_at=past_time
            )
    
    def test_personal_record_create(self):
        """Test personal record creation"""
        pr = PersonalRecordCreate(
            movement_name="back_squat",
            record_type=PersonalRecordType.ONE_RM,
            value=150.0,
            unit="kg",
            notes="New PR!",
            video_url="https://youtube.com/watch?v=123"
        )
        
        assert pr.movement_name == "back_squat"
        assert pr.record_type == PersonalRecordType.ONE_RM
        assert pr.value == 150.0


class TestHealthModels:
    """Test health domain models"""
    
    def test_recovery_metric_valid(self):
        """Test valid recovery metric"""
        recovery = RecoveryMetricCreate(
            date=date.today(),
            sleep_duration_hours=8.5,
            sleep_quality_score=85,
            hrv_rmssd_ms=65,
            resting_heart_rate_bpm=52,
            stress_level=3,
            muscle_soreness=4,
            energy_level=8,
            mood_score=8,
            notes="Felt great"
        )
        
        assert recovery.sleep_duration_hours == 8.5
        assert recovery.hrv_rmssd_ms == 65
        assert recovery.stress_level == 3
    
    def test_recovery_metric_score_constraints(self):
        """Test recovery metric score validation (1-10 or 1-100)"""
        with pytest.raises(ValidationError):
            RecoveryMetricCreate(
                date=date.today(),
                stress_level=15  # Above max of 10
            )
        
        with pytest.raises(ValidationError):
            RecoveryMetricCreate(
                date=date.today(),
                sleep_quality_score=150  # Above max of 100
            )
    
    def test_biomarker_reading_create(self):
        """Test biomarker reading creation (free-form name, not FK)"""
        biomarker = BiomarkerReadingCreate(
            biomarker_name="glucose_fasting",
            test_date=date(2026, 2, 1),
            value=95.0,
            unit="mg/dL",
            lab_name="LabCorp",
            notes="Fasting glucose",
        )
        assert biomarker.value == 95.0
        assert biomarker.unit == "mg/dL"
        assert biomarker.lab_name == "LabCorp"
        assert biomarker.biomarker_name == "glucose_fasting"


class TestEnumModels:
    """Test enum validations"""
    
    def test_workout_type_enum(self):
        """Test WorkoutType enum values"""
        assert WorkoutType.STRENGTH.value == "strength"
        assert WorkoutType.METCON.value == "metcon"
        assert WorkoutType.SKILL.value == "skill"
    
    def test_methodology_enum(self):
        """Test Methodology enum values"""
        assert Methodology.HWPO.value == "hwpo"
        assert Methodology.MAYHEM.value == "mayhem"
        assert Methodology.COMPTRAIN.value == "comptrain"
    
    def test_day_of_week_enum(self):
        """Test DayOfWeek enum values"""
        assert DayOfWeek.MONDAY.value == "monday"
        assert DayOfWeek.SUNDAY.value == "sunday"
    
    def test_invalid_enum_value(self):
        """Test invalid enum value raises error"""
        with pytest.raises(ValidationError):
            WorkoutSessionCreate(
                workout_type="invalid_type",  # Invalid enum value
                movements=[]
            )


class TestModelSerialization:
    """Test model serialization and deserialization"""
    
    def test_movement_json_serialization(self):
        """Test movement serializes to JSON"""
        movement = Movement(
            movement="back_squat",
            sets=5,
            reps=5,
            weight_kg=100.0
        )
        
        json_data = movement.model_dump()
        
        assert json_data["movement"] == "back_squat"
        assert json_data["sets"] == 5
        assert json_data["reps"] == 5
        assert json_data["weight_kg"] == 100.0
    
    def test_model_from_dict(self):
        """Test creating model from dictionary"""
        data = {
            "movement": "deadlift",
            "sets": 3,
            "reps": 5,
            "weight_kg": 150.0
        }
        
        movement = Movement(**data)
        
        assert movement.movement == "deadlift"
        assert movement.sets == 3
