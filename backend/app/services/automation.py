"""
Automation service - handles weekly program generation and scheduled tasks
"""
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
import asyncio

from app.db.supabase import supabase_client


class AutomationService:
    """Service for automated tasks like weekly program generation."""
    
    @staticmethod
    def generate_weekly_program_for_user(user_id: str) -> Dict[str, Any]:
        """
        Automatically generate weekly program for a user.
        Called on schedule or manually.
        """
        try:
            # Get user profile
            user_resp = supabase_client.table("users").select("*").eq(
                "id", user_id
            ).single().execute()
            
            if not user_resp.data:
                return {"success": False, "error": "User not found"}
            
            user = user_resp.data
            
            # Get active schedule
            schedule_resp = supabase_client.table("weekly_schedules").select("*").eq(
                "user_id", user_id
            ).eq("active", True).single().execute()
            
            if not schedule_resp.data:
                return {"success": False, "error": "No active schedule"}
            
            schedule = schedule_resp.data
            
            # Get previous week's performance for progression
            previous_week = AutomationService._get_previous_week_data(user_id)
            
            # Get AI-generated workouts (simplified - in production would call OpenAI)
            workouts = AutomationService._generate_workouts(
                user=user,
                schedule=schedule,
                previous_week=previous_week
            )
            
            # Save to workout_templates
            for workout in workouts:
                workout["user_id"] = user_id
                workout["week_start"] = schedule.get("start_date", date.today().isoformat())
                workout["created_by"] = "automation"
                
                try:
                    supabase_client.table("workout_templates").insert(workout).execute()
                except Exception as e:
                    print(f"Error saving workout: {e}")
            
            # Create notification
            try:
                supabase_client.table("notifications").insert({
                    "user_id": user_id,
                    "type": "weekly_program_ready",
                    "title": "📅 New Week, New Program!",
                    "body": f"Your {len(workouts)}-day program is ready. Let's crush Week {schedule.get('current_week', 1)}!",
                    "data": {"workout_count": len(workouts)},
                    "read": False,
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
            except:
                pass
            
            return {
                "success": True,
                "workouts_generated": len(workouts),
                "week": schedule.get("current_week", 1)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def _get_previous_week_data(user_id: str) -> Dict:
        """Get previous week's training data for progression."""
        try:
            # Get last 7 days of sessions
            week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
            
            sessions = supabase_client.table("workout_sessions").select("*").eq(
                "user_id", user_id
            ).gte("started_at", week_ago).execute()
            
            if not sessions.data:
                return {}
            
            # Calculate averages
            total_volume = 0
            total_rpe = 0
            count = len(sessions.data)
            
            for session in sessions.data:
                total_rpe += session.get("rpe_score", 0)
                # Volume calculation would come from movements
            
            return {
                "sessions_completed": count,
                "avg_rpe": total_rpe / count if count > 0 else 5,
                "volume_change": 0  # Would calculate from movements
            }
        except:
            return {}
    
    @staticmethod
    def _generate_workouts(user: Dict, schedule: Dict, previous_week: Dict) -> List[Dict]:
        """Generate workouts based on schedule and user profile."""
        workouts = []
        
        methodology = schedule.get("methodology", "hwpo")
        days_map = {
            "monday": "monday", "tuesday": "tuesday", "wednesday": "wednesday",
            "thursday": "thursday", "friday": "friday", "saturday": "saturday", "sunday": "sunday"
        }
        
        for day_name, day_key in days_map.items():
            day_data = schedule.get("schedule", {}).get(day_key, {})
            
            if day_data.get("rest_day", True):
                continue
            
            sessions = day_data.get("sessions", [])
            if not sessions:
                continue
            
            for session in sessions:
                workout_type = session.get("workout_type", "mixed")
                
                # Generate workout based on type and methodology
                workout = AutomationService._create_workout_template(
                    day=day_name,
                    workout_type=workout_type,
                    methodology=methodology,
                    user=user,
                    previous_week=previous_week
                )
                
                if workout:
                    workouts.append(workout)
        
        return workouts
    
    @staticmethod
    def _create_workout_template(
        day: str,
        workout_type: str,
        methodology: str,
        user: Dict,
        previous_week: Dict
    ) -> Optional[Dict]:
        """Create a single workout template."""
        
        # Simplified workout templates based on methodology
        templates = {
            "hwpo": {
                "strength": {
                    "name": f"HWPO {day.title()} Strength",
                    "description": "Main lift followed by accessory work",
                    "movements": [
                        {"movement": "back_squat", "sets": 5, "reps": 5, "intensity": "65-75%"},
                        {"movement": "bench_press", "sets": 5, "reps": 5, "intensity": "65-75%"},
                        {"movement": "pull_ups", "sets": 3, "reps": "AMRAP"}
                    ]
                },
                "metcon": {
                    "name": f"HWPO {day.title()} Metcon",
                    "description": "High-intensity conditioning",
                    "movements": [
                        {"movement": "wall_balls", "sets": 4, "reps": 21, "intensity": "moderate"},
                        {"movement": "box_jumps", "sets": 4, "reps": 15},
                        {"movement": "row_calories", "sets": 4, "reps": 250}
                    ]
                },
                "mixed": {
                    "name": f"HWPO {day.title()} Mixed",
                    "description": "Strength and conditioning combined",
                    "movements": [
                        {"movement": "clean_and_jerk", "sets": 5, "reps": 3, "intensity": "70-80%"},
                        {"movement": "front_squat", "sets": 3, "reps": 5, "intensity": "70%"},
                        {"movement": "burpees", "sets": 5, "reps": 12}
                    ]
                }
            }
        }
        
        template = templates.get(methodology, templates["hwpo"]).get(workout_type, templates["hwpo"]["mixed"])
        
        return {
            "name": template["name"],
            "description": template["description"],
            "workout_type": workout_type,
            "day_of_week": day,
            "duration_minutes": 60,
            "movements": template["movements"],
            "methodology": methodology,
            "notes": f"Generated for {user.get('name', 'user')}"
        }
    
    @staticmethod
    def run_weekly_generation() -> Dict[str, Any]:
        """Run weekly generation for all active users."""
        try:
            # Get all users with active schedules
            users_resp = supabase_client.table("users").select("id").eq(
                "onboarding_completed", True
            ).execute()
            
            if not users_resp.data:
                return {"success": True, "users_processed": 0}
            
            results = []
            for user in users_resp.data:
                result = AutomationService.generate_weekly_program_for_user(user["id"])
                results.append(result)
            
            successful = sum(1 for r in results if r.get("success"))
            
            return {
                "success": True,
                "users_processed": len(users_resp.data),
                "programs_generated": successful
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


def run_daily_tasks():
    """Run all daily automated tasks."""
    today = date.today()
    
    # Monday = day for weekly generation
    if today.weekday() == 0:  # Monday
        result = AutomationService.run_weekly_generation()
        print(f"Weekly generation: {result}")
    
    # Daily streak check
    try:
        users_resp = supabase_client.table("users").select("id").eq(
            "onboarding_completed", True
        ).execute()
        
        for user in users_resp.data or []:
            AutomationService.check_and_notify_streaks(user["id"])
    except Exception as e:
        print(f"Streak check error: {e}")


def run_automated_onboarding_email():
    """Send welcome email to new users who haven't completed onboarding."""
    try:
        users_resp = supabase_client.table("users").select("id, email, name").eq(
            "onboarding_completed", False
        ).execute()
        
        for user in users_resp.data or []:
            # Would integrate with email service
            print(f"Would send onboarding email to {user.get('email')}")
    except Exception as e:
        print(f"Onboarding email error: {e}")
