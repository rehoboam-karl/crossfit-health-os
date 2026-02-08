"""
Adaptive Training Engine
Adjusts workout volume based on recovery metrics (HRV, sleep, readiness)
"""
from datetime import date, datetime, timedelta
from typing import Optional, Tuple
from uuid import UUID
import logging

from app.models.training import (
    AdaptiveWorkoutResponse,
    WorkoutTemplate,
    Movement,
    Methodology
)
from app.db.supabase import supabase_client
from app.db.helpers import handle_supabase_response

logger = logging.getLogger(__name__)


class AdaptiveTrainingEngine:
    """
    Core engine that implements the feedback loop:
    Biometric Data → Recovery Assessment → Volume Adjustment → Training Prescription
    """
    
    # Volume multiplier thresholds
    OPTIMAL_THRESHOLD = 80  # readiness >= 80 → push harder
    NORMAL_THRESHOLD = 60   # readiness >= 60 → maintain
    REDUCED_THRESHOLD = 40  # readiness >= 40 → reduce volume
    # Below 40 → active recovery only
    
    def __init__(self):
        self.supabase = supabase_client
    
    async def generate_workout(
        self,
        user_id: UUID,
        target_date: date,
        force_rest: bool = False
    ) -> AdaptiveWorkoutResponse:
        """
        Generate adaptive workout for user on target date
        
        Algorithm:
        1. Get user's recovery metrics for today
        2. Calculate readiness score (0-100)
        3. Determine volume multiplier
        4. Select appropriate workout template
        5. Adjust workout based on multiplier
        6. Return adapted workout with reasoning
        """
        # Step 1: Get recovery metrics
        recovery = await self._get_recovery_metrics(user_id, target_date)
        
        # Step 2: Calculate readiness score
        readiness_score = self._calculate_readiness_score(recovery)
        
        # Step 3: Determine volume multiplier and recommendation
        volume_multiplier, recommendation = self._determine_volume_adjustment(
            readiness_score,
            force_rest
        )
        
        # Step 4: Get user profile and select workout
        user_profile = await self._get_user_profile(user_id)
        base_workout = await self._select_workout_template(
            user_id,
            target_date,
            user_profile,
            readiness_score
        )
        
        # Step 5: Adjust workout movements
        adjusted_movements = self._adjust_movements(
            base_workout.movements,
            volume_multiplier,
            readiness_score
        )
        
        # Step 6: Generate reasoning
        reasoning = self._generate_reasoning(
            recovery,
            readiness_score,
            volume_multiplier,
            base_workout.methodology
        )
        
        return AdaptiveWorkoutResponse(
            template=base_workout,
            volume_multiplier=volume_multiplier,
            readiness_score=readiness_score,
            recommendation=recommendation,
            adjusted_movements=adjusted_movements,
            reasoning=reasoning
        )
    
    async def _get_recovery_metrics(
        self,
        user_id: UUID,
        target_date: date
    ) -> dict:
        """Get recovery metrics for user on date"""
        response = self.supabase.table("recovery_metrics").select("*").eq(
            "user_id", str(user_id)
        ).eq("date", target_date.isoformat()).execute()
        
        # ✅ Check for errors
        data = handle_supabase_response(response, "Failed to fetch recovery metrics")
        
        if data:
            return data[0]
        
        # If no data, return default "unknown" state
        logger.warning(f"No recovery data for user {user_id} on {target_date}, using defaults")
        return {
            "hrv_ratio": 1.0,
            "sleep_quality_score": 70,
            "stress_level": 5,
            "muscle_soreness": 5,
            "energy_level": 7,
            "readiness_score": 70
        }
    
    async def _get_user_profile(self, user_id: UUID) -> dict:
        """Get user profile"""
        response = self.supabase.table("users").select("*").eq(
            "id", str(user_id)
        ).single().execute()
        
        # ✅ Check for errors
        data = handle_supabase_response(response, "Failed to fetch user profile")
        return data
    
    def _calculate_readiness_score(self, recovery: dict) -> int:
        """
        Calculate readiness score (0-100) from recovery metrics
        
        Weighted formula:
        - HRV ratio: 40%
        - Sleep quality: 30%
        - Stress (inverted): 20%
        - Soreness (inverted): 10%
        """
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
        
        # Clamp to 0-100
        return max(0, min(100, int(readiness)))
    
    def _determine_volume_adjustment(
        self,
        readiness_score: int,
        force_rest: bool
    ) -> Tuple[float, str]:
        """
        Determine volume multiplier and recommendation based on readiness
        
        Returns:
            (volume_multiplier, recommendation_text)
        """
        if force_rest:
            return 0.0, "🛌 Forced rest day - complete recovery"
        
        if readiness_score >= self.OPTIMAL_THRESHOLD:
            return 1.1, "💪 Excellent readiness - push for PRs and high volume"
        
        elif readiness_score >= self.NORMAL_THRESHOLD:
            return 1.0, "✅ Normal readiness - train as programmed"
        
        elif readiness_score >= self.REDUCED_THRESHOLD:
            return 0.8, "⚠️  Moderate fatigue - reduce volume by 20%"
        
        else:
            return 0.5, "🔴 High fatigue - active recovery only (mobility, light cardio)"
    
    async def _select_workout_template(
        self,
        user_id: UUID,
        target_date: date,
        user_profile: dict,
        readiness_score: int
    ) -> WorkoutTemplate:
        """
        Select appropriate workout template based on:
        - Day of week
        - User's methodology preference
        - Readiness score
        - Training periodization
        """
        day_of_week = target_date.weekday()  # 0=Monday, 6=Sunday
        methodology = user_profile.get("preferences", {}).get("methodology", "hwpo")
        fitness_level = user_profile.get("fitness_level", "intermediate")
        
        # HWPO Weekly Structure (Mat Fraser methodology)
        if methodology == "hwpo":
            if day_of_week == 0:  # Monday: Heavy Strength
                workout_type = "strength"
                target_stimulus = "max_strength"
            elif day_of_week == 1:  # Tuesday: Gymnastics Skill
                workout_type = "skill"
                target_stimulus = "body_control"
            elif day_of_week == 2:  # Wednesday: Active Recovery or Moderate
                workout_type = "conditioning" if readiness_score >= 60 else "skill"
                target_stimulus = "recovery"
            elif day_of_week == 3:  # Thursday: Threshold Training
                workout_type = "metcon"
                target_stimulus = "power_endurance"
            elif day_of_week == 4:  # Friday: Competition Sim
                workout_type = "mixed"
                target_stimulus = "competition"
            elif day_of_week == 5:  # Saturday: Long Chipper
                workout_type = "metcon"
                target_stimulus = "endurance"
            else:  # Sunday: Rest or Zone 2
                workout_type = "conditioning"
                target_stimulus = "recovery"
        
        # Query workout templates
        response = self.supabase.table("workout_templates").select("*").eq(
            "methodology", methodology
        ).eq("workout_type", workout_type).eq(
            "difficulty_level", fitness_level
        ).limit(1).execute()
        
        if response.data:
            template_data = response.data[0]
            return WorkoutTemplate(**template_data)
        
        # Fallback: create a simple default workout
        return self._create_default_workout(workout_type, target_stimulus)
    
    def _adjust_movements(
        self,
        movements: list[Movement],
        volume_multiplier: float,
        readiness_score: int
    ) -> list[Movement]:
        """
        Adjust movement volume based on multiplier
        
        Adjustments:
        - Sets/reps reduced/increased proportionally
        - Weight % adjusted for strength work
        - Rest periods adjusted
        """
        adjusted = []
        
        for movement in movements:
            adjusted_movement = movement.model_copy(deep=True)
            
            # Adjust sets
            if adjusted_movement.sets:
                adjusted_movement.sets = max(1, int(adjusted_movement.sets * volume_multiplier))
            
            # Adjust reps (if numeric)
            if isinstance(adjusted_movement.reps, int):
                adjusted_movement.reps = max(1, int(adjusted_movement.reps * volume_multiplier))
            
            # Adjust weight for low readiness
            if readiness_score < 50 and adjusted_movement.weight_kg:
                adjusted_movement.weight_kg = adjusted_movement.weight_kg * 0.85
                adjusted_movement.notes = (adjusted_movement.notes or "") + " (Weight reduced due to fatigue)"
            
            adjusted.append(adjusted_movement)
        
        return adjusted
    
    def _generate_reasoning(
        self,
        recovery: dict,
        readiness_score: int,
        volume_multiplier: float,
        methodology: Methodology
    ) -> str:
        """Generate human-readable reasoning for the prescription"""
        
        hrv_ratio = recovery.get("hrv_ratio", 1.0)
        sleep_quality = recovery.get("sleep_quality_score", 70)
        
        reasoning_parts = []
        
        # HRV interpretation
        if hrv_ratio > 1.1:
            reasoning_parts.append(f"HRV is elevated ({hrv_ratio:.2f}x baseline) - excellent recovery")
        elif hrv_ratio < 0.9:
            reasoning_parts.append(f"HRV is suppressed ({hrv_ratio:.2f}x baseline) - incomplete recovery")
        else:
            reasoning_parts.append(f"HRV is normal ({hrv_ratio:.2f}x baseline)")
        
        # Sleep interpretation
        if sleep_quality >= 80:
            reasoning_parts.append(f"Sleep quality is excellent ({sleep_quality}/100)")
        elif sleep_quality < 60:
            reasoning_parts.append(f"Sleep quality is poor ({sleep_quality}/100)")
        
        # Overall readiness
        reasoning_parts.append(f"Overall readiness: {readiness_score}/100")
        
        # Volume decision
        if volume_multiplier > 1.0:
            reasoning_parts.append(f"Increasing volume by {int((volume_multiplier - 1) * 100)}% to capitalize on recovery")
        elif volume_multiplier < 1.0:
            reasoning_parts.append(f"Reducing volume by {int((1 - volume_multiplier) * 100)}% to prioritize recovery")
        else:
            reasoning_parts.append("Training at programmed volume")
        
        # Methodology context
        reasoning_parts.append(f"Following {methodology.value.upper()} methodology")
        
        return " • ".join(reasoning_parts)
    
    def _create_default_workout(
        self,
        workout_type: str,
        target_stimulus: str
    ) -> WorkoutTemplate:
        """Create a simple default workout when no template found"""
        
        # Simple fallback workouts
        if workout_type == "strength":
            movements = [
                Movement(
                    movement="back_squat",
                    sets=5,
                    reps=5,
                    intensity="80%",
                    rest="3min"
                )
            ]
        elif workout_type == "metcon":
            movements = [
                Movement(
                    movement="burpees",
                    reps=21
                ),
                Movement(
                    movement="air_squats",
                    reps=21
                ),
                Movement(
                    movement="burpees",
                    reps=15
                ),
                Movement(
                    movement="air_squats",
                    reps=15
                )
            ]
        else:
            movements = [
                Movement(
                    movement="run",
                    distance_meters=400,
                    sets=5,
                    rest="90s"
                )
            ]
        
        return WorkoutTemplate(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            name=f"Default {workout_type.title()}",
            description="Auto-generated fallback workout",
            methodology=Methodology.CUSTOM,
            difficulty_level="rx",
            workout_type=workout_type,
            movements=movements,
            target_stimulus=target_stimulus,
            tags=["auto_generated"],
            equipment_required=[],
            created_at=datetime.utcnow(),
            is_public=False
        )


# Global engine instance
adaptive_engine = AdaptiveTrainingEngine()
