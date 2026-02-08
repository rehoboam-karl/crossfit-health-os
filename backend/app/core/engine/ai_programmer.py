"""
AI-Powered Training Programmer
Generates progressive training programs using LLM
"""
from datetime import date, timedelta
from typing import List, Dict, Optional
from uuid import UUID
import json
import logging
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.training import (
    WorkoutTemplate,
    Movement,
    WorkoutType,
    Methodology,
    DayOfWeek
)

logger = logging.getLogger(__name__)


class AITrainingProgrammer:
    """
    AI-powered training programmer that generates progressive workouts
    Similar to HWPO, Mayhem, CompTrain but personalized
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
    
    async def generate_weekly_program(
        self,
        user_profile: dict,
        methodology: Methodology,
        training_days: List[DayOfWeek],
        session_durations: Dict[DayOfWeek, int],
        week_number: int = 1,
        focus_movements: Optional[List[str]] = None,
        previous_week_data: Optional[dict] = None
    ) -> Dict[DayOfWeek, WorkoutTemplate]:
        """
        Generate complete weekly training program using AI
        
        Args:
            user_profile: User fitness level, goals, weaknesses, PRs
            methodology: HWPO, Mayhem, CompTrain, Custom
            training_days: List of days to train (e.g., [monday, wednesday, friday])
            session_durations: Duration for each day {monday: 90, wednesday: 60, ...}
            week_number: Current week in mesocycle (for progression)
            focus_movements: Optional list of movements to emphasize
            previous_week_data: Results from previous week for progressive overload
            
        Returns:
            Dict mapping DayOfWeek to WorkoutTemplate
        """
        if not self.client:
            logger.warning("OpenAI API key not configured, using fallback templates")
            return self._generate_fallback_program(training_days, session_durations)
        
        # Build context for AI
        context = self._build_programming_context(
            user_profile,
            methodology,
            training_days,
            session_durations,
            week_number,
            focus_movements,
            previous_week_data
        )
        
        # Generate program via LLM
        prompt = self._build_programming_prompt(context)
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            program_json = json.loads(response.choices[0].message.content)
            
            # Parse JSON into WorkoutTemplate objects
            weekly_program = self._parse_ai_response(program_json, training_days)
            
            logger.info(f"Generated weekly program for week {week_number} with {len(weekly_program)} workouts")
            return weekly_program
            
        except Exception as e:
            logger.error(f"Failed to generate AI program: {e}", exc_info=True)
            return self._generate_fallback_program(training_days, session_durations)
    
    def _get_system_prompt(self) -> str:
        """
        System prompt defining AI's role as elite CrossFit programmer
        """
        return """You are an elite CrossFit programming coach with expertise in HWPO (Mat Fraser), Mayhem (Rich Froning), and CompTrain (Ben Bergeron) methodologies.

Your role is to create intelligent, progressive training programs that:
1. Follow proven periodization principles (volume cycles, deload weeks, progressive overload)
2. Balance strength, metcon, gymnastics, and conditioning
3. Adapt to the athlete's fitness level, weaknesses, and goals
4. Consider session duration constraints (short: ≤60min, long: >60min)
5. Provide clear rep schemes, intensities, and coaching cues
6. Include appropriate warm-up and cooldown guidance

Programming Philosophy:
- Week 1-3: Volume accumulation
- Week 4: Deload/Active recovery
- Week 5-7: Intensity phase
- Week 8: Test week

Session Structure:
**Short Sessions (≤60min):**
- Warm-up: 10min
- Skill/Strength: 15-20min (1-2 movements)
- MetCon: 15-20min
- Cooldown: 5min

**Long Sessions (>60min):**
- Warm-up: 15min
- Strength: 30min (3-4 movements, multiple sets)
- Accessory: 15min
- MetCon: 20-25min
- Cooldown: 10min

Movement Selection:
- Prioritize compound lifts (squat, deadlift, press, olympic lifts)
- Include gymnastics progressions (pull-ups, handstands, muscle-ups)
- Balance pushing/pulling, squatting/hinging
- Address user's weakness areas

Intensity Guidelines:
- Strength: 70-90% 1RM
- MetCon: 75-85% max effort
- Conditioning: 60-75% (Zone 2-3)
- Skill: Focus on quality, not fatigue

You must return a valid JSON object with workout details for each training day."""
    
    def _build_programming_context(
        self,
        user_profile: dict,
        methodology: Methodology,
        training_days: List[DayOfWeek],
        session_durations: Dict[DayOfWeek, int],
        week_number: int,
        focus_movements: Optional[List[str]],
        previous_week_data: Optional[dict]
    ) -> dict:
        """Build context dictionary for AI prompt"""
        
        # Extract user info
        fitness_level = user_profile.get("fitness_level", "intermediate")
        weight_kg = user_profile.get("weight_kg", 80)
        goals = user_profile.get("preferences", {}).get("goals", ["strength", "conditioning"])
        weaknesses = user_profile.get("preferences", {}).get("weaknesses", [])
        
        # Determine mesocycle phase
        if week_number <= 3:
            phase = "accumulation"
        elif week_number == 4:
            phase = "deload"
        elif week_number <= 7:
            phase = "intensification"
        else:
            phase = "test_week"
        
        context = {
            "user": {
                "fitness_level": fitness_level,
                "bodyweight_kg": weight_kg,
                "goals": goals,
                "weaknesses": weaknesses
            },
            "program": {
                "methodology": methodology.value,
                "week_number": week_number,
                "phase": phase,
                "training_days": [day.value for day in training_days],
                "session_durations": {day.value: duration for day, duration in session_durations.items()},
                "focus_movements": focus_movements or []
            },
            "previous_week": previous_week_data
        }
        
        return context
    
    def _build_programming_prompt(self, context: dict) -> str:
        """
        Build the actual prompt for workout generation
        """
        user = context["user"]
        program = context["program"]
        previous = context.get("previous_week")
        
        prompt = f"""Generate a weekly training program with the following parameters:

**Athlete Profile:**
- Fitness Level: {user['fitness_level']}
- Bodyweight: {user['bodyweight_kg']}kg
- Goals: {', '.join(user['goals'])}
- Weaknesses: {', '.join(user['weaknesses']) if user['weaknesses'] else 'None specified'}

**Program Parameters:**
- Methodology: {program['methodology'].upper()}
- Week Number: {program['week_number']} ({program['phase']} phase)
- Training Days: {', '.join(program['training_days'])}
- Session Durations: {json.dumps(program['session_durations'])}
- Focus Movements: {', '.join(program['focus_movements']) if program['focus_movements'] else 'None'}

**Previous Week Results:**
{json.dumps(previous, indent=2) if previous else 'First week - no previous data'}

**Requirements:**
1. Create a workout for EACH training day listed above
2. Respect session duration constraints (short ≤60min, long >60min)
3. Apply progressive overload if previous week data exists
4. Follow {program['methodology'].upper()} principles:
   - HWPO: Heavy strength + short intense metcons
   - Mayhem: High volume, competition prep focus
   - CompTrain: Balanced, sustainable programming
   - Custom: Adapt to athlete's specific needs
5. Address athlete's weaknesses
6. Include clear instructions (sets, reps, weights, rest)

**Output Format:**
Return a JSON object with this structure:
```json
{{
  "program_summary": "Brief overview of the week's focus",
  "workouts": {{
    "monday": {{
      "name": "Heavy Squat + Short AMRAP",
      "duration_minutes": 90,
      "workout_type": "strength",
      "description": "Focus on building squat strength with accessory work",
      "warm_up": "10min: Row 500m, 2 rounds (10 air squats, 10 PVC pass-throughs, 5 inchworms)",
      "parts": [
        {{
          "part_name": "Strength",
          "duration_minutes": 30,
          "movements": [
            {{
              "movement": "back_squat",
              "sets": 5,
              "reps": 5,
              "intensity": "80% 1RM",
              "rest": "3min",
              "notes": "Focus on depth and speed out of the hole"
            }},
            {{
              "movement": "bulgarian_split_squat",
              "sets": 3,
              "reps": 10,
              "intensity": "Bodyweight + 20kg DB",
              "rest": "90s",
              "notes": "Per leg, control the descent"
            }}
          ]
        }},
        {{
          "part_name": "MetCon",
          "duration_minutes": 15,
          "format": "AMRAP 12min",
          "movements": [
            {{
              "movement": "thruster",
              "reps": 5,
              "weight_kg": 42.5,
              "notes": "Barbell, aim for unbroken sets"
            }},
            {{
              "movement": "burpee_box_jump",
              "reps": 10,
              "notes": "24inch box, step down"
            }},
            {{
              "movement": "cal_row",
              "reps": 15,
              "notes": "Damper 10, hold pace"
            }}
          ]
        }}
      ],
      "cooldown": "5min: Easy bike, foam roll quads and hamstrings",
      "target_stimulus": "Leg strength + lactate tolerance",
      "scaling_options": {{
        "rx": "As written",
        "scaled": "Thruster 35kg, Box jumps 20inch",
        "beginner": "Goblet squats, step-ups, bike instead of row"
      }}
    }},
    "wednesday": {{
      // ... similar structure for wednesday
    }},
    // ... other training days
  }}
}}
```

Generate the complete weekly program now."""
        
        return prompt
    
    def _parse_ai_response(
        self,
        program_json: dict,
        training_days: List[DayOfWeek]
    ) -> Dict[DayOfWeek, WorkoutTemplate]:
        """
        Parse AI-generated JSON into WorkoutTemplate objects
        """
        weekly_program = {}
        
        workouts = program_json.get("workouts", {})
        
        for day in training_days:
            day_key = day.value
            if day_key not in workouts:
                logger.warning(f"AI response missing workout for {day_key}")
                continue
            
            workout_data = workouts[day_key]
            
            # Parse movements from all parts
            all_movements = []
            for part in workout_data.get("parts", []):
                for mov in part.get("movements", []):
                    movement = Movement(
                        movement=mov.get("movement"),
                        sets=mov.get("sets"),
                        reps=mov.get("reps"),
                        weight_kg=mov.get("weight_kg"),
                        intensity=mov.get("intensity"),
                        rest=mov.get("rest"),
                        notes=mov.get("notes")
                    )
                    all_movements.append(movement)
            
            # Create WorkoutTemplate
            template = WorkoutTemplate(
                id=UUID("00000000-0000-0000-0000-000000000000"),  # Will be replaced on save
                name=workout_data.get("name", f"{day_key.title()} Workout"),
                description=workout_data.get("description", ""),
                methodology=Methodology.CUSTOM,  # AI-generated is custom
                difficulty_level="rx",
                workout_type=WorkoutType(workout_data.get("workout_type", "mixed")),
                duration_minutes=workout_data.get("duration_minutes"),
                movements=all_movements,
                target_stimulus=workout_data.get("target_stimulus"),
                tags=["ai_generated", day_key],
                equipment_required=[],
                created_at=date.today(),
                is_public=False
            )
            
            weekly_program[day] = template
        
        return weekly_program
    
    def _generate_fallback_program(
        self,
        training_days: List[DayOfWeek],
        session_durations: Dict[DayOfWeek, int]
    ) -> Dict[DayOfWeek, WorkoutTemplate]:
        """
        Fallback program generator if AI is unavailable
        Simple default workouts
        """
        fallback_workouts = {
            DayOfWeek.MONDAY: self._create_strength_workout(session_durations.get(DayOfWeek.MONDAY, 60)),
            DayOfWeek.TUESDAY: self._create_metcon_workout(session_durations.get(DayOfWeek.TUESDAY, 60)),
            DayOfWeek.WEDNESDAY: self._create_skill_workout(session_durations.get(DayOfWeek.WEDNESDAY, 60)),
            DayOfWeek.THURSDAY: self._create_mixed_workout(session_durations.get(DayOfWeek.THURSDAY, 60)),
            DayOfWeek.FRIDAY: self._create_conditioning_workout(session_durations.get(DayOfWeek.FRIDAY, 60)),
            DayOfWeek.SATURDAY: self._create_metcon_workout(session_durations.get(DayOfWeek.SATURDAY, 60)),
        }
        
        return {day: fallback_workouts[day] for day in training_days if day in fallback_workouts}
    
    def _create_strength_workout(self, duration: int) -> WorkoutTemplate:
        """Create basic strength workout"""
        if duration > 60:
            movements = [
                Movement(movement="back_squat", sets=5, reps=5, intensity="80%", rest="3min"),
                Movement(movement="deadlift", sets=3, reps=5, intensity="75%", rest="3min"),
                Movement(movement="strict_press", sets=4, reps=8, intensity="70%", rest="2min"),
            ]
        else:
            movements = [
                Movement(movement="front_squat", sets=4, reps=6, intensity="75%", rest="2min"),
                Movement(movement="push_press", sets=4, reps=8, intensity="70%", rest="90s"),
            ]
        
        return WorkoutTemplate(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            name="Strength Day",
            description="Compound strength work",
            methodology=Methodology.CUSTOM,
            difficulty_level="rx",
            workout_type=WorkoutType.STRENGTH,
            duration_minutes=duration,
            movements=movements,
            target_stimulus="Build maximal strength",
            tags=["fallback", "strength"],
            equipment_required=["barbell", "rack"],
            created_at=date.today(),
            is_public=False
        )
    
    def _create_metcon_workout(self, duration: int) -> WorkoutTemplate:
        """Create basic metcon workout"""
        movements = [
            Movement(movement="thruster", reps=21, weight_kg=42.5),
            Movement(movement="pull_up", reps=21),
            Movement(movement="thruster", reps=15, weight_kg=42.5),
            Movement(movement="pull_up", reps=15),
            Movement(movement="thruster", reps=9, weight_kg=42.5),
            Movement(movement="pull_up", reps=9),
        ]
        
        return WorkoutTemplate(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            name="Fran (Classic)",
            description="21-15-9 Thrusters and Pull-ups",
            methodology=Methodology.CUSTOM,
            difficulty_level="rx",
            workout_type=WorkoutType.METCON,
            duration_minutes=duration,
            movements=movements,
            target_stimulus="High intensity, short duration",
            rep_scheme="21-15-9",
            tags=["fallback", "metcon", "classic"],
            equipment_required=["barbell", "pull_up_bar"],
            created_at=date.today(),
            is_public=False
        )
    
    def _create_skill_workout(self, duration: int) -> WorkoutTemplate:
        """Create basic skill workout"""
        movements = [
            Movement(movement="handstand_walk", sets=10, duration_seconds=30, rest="60s"),
            Movement(movement="muscle_up", sets=5, reps=3, rest="2min"),
            Movement(movement="double_under", sets=5, reps=50, rest="60s"),
        ]
        
        return WorkoutTemplate(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            name="Gymnastics Skills",
            description="Skill practice and development",
            methodology=Methodology.CUSTOM,
            difficulty_level="rx",
            workout_type=WorkoutType.SKILL,
            duration_minutes=duration,
            movements=movements,
            target_stimulus="Skill acquisition",
            tags=["fallback", "gymnastics"],
            equipment_required=["rings", "jump_rope"],
            created_at=date.today(),
            is_public=False
        )
    
    def _create_mixed_workout(self, duration: int) -> WorkoutTemplate:
        """Create mixed workout"""
        movements = [
            Movement(movement="deadlift", sets=3, reps=8, intensity="75%", rest="2min"),
            Movement(movement="rowing", distance_meters=500, sets=5, rest="90s"),
        ]
        
        return WorkoutTemplate(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            name="Mixed Modal",
            description="Strength + Conditioning",
            methodology=Methodology.CUSTOM,
            difficulty_level="rx",
            workout_type=WorkoutType.MIXED,
            duration_minutes=duration,
            movements=movements,
            target_stimulus="Balanced work capacity",
            tags=["fallback", "mixed"],
            equipment_required=["barbell", "rower"],
            created_at=date.today(),
            is_public=False
        )
    
    def _create_conditioning_workout(self, duration: int) -> WorkoutTemplate:
        """Create conditioning workout"""
        movements = [
            Movement(movement="air_bike", duration_seconds=60, sets=10, rest="60s"),
            Movement(movement="run", distance_meters=400, sets=6, rest="2min"),
        ]
        
        return WorkoutTemplate(
            id=UUID("00000000-0000-0000-0000-000000000000"),
            name="Conditioning",
            description="Aerobic capacity work",
            methodology=Methodology.CUSTOM,
            difficulty_level="rx",
            workout_type=WorkoutType.CONDITIONING,
            duration_minutes=duration,
            movements=movements,
            target_stimulus="Aerobic endurance",
            tags=["fallback", "conditioning"],
            equipment_required=["bike", "track"],
            created_at=date.today(),
            is_public=False
        )


# Global instance
ai_programmer = AITrainingProgrammer()
