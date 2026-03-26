"""
Gamification service - handles streaks, badges, XP, and achievements
"""
import json
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from app.db.supabase import supabase_client
from app.models.gamification import (
    Badge, BadgeType, BADGE_DEFINITIONS, 
    StreakData, UserStats, calculate_level, xp_for_action
)


class GamificationService:
    """Service for managing user gamification elements."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def get_user_stats(self) -> UserStats:
        """Get comprehensive user stats including XP, level, badges."""
        stats = UserStats()
        
        # Get workout sessions
        sessions = self._get_user_sessions()
        stats.total_workouts = len([s for s in sessions if s.get("completed_at")])
        
        # Calculate streak
        streak_data = self._calculate_streak(sessions)
        stats.current_streak = streak_data.current_streak
        stats.longest_streak = streak_data.longest_streak
        
        # Calculate XP
        stats.xp = self._get_user_xp()
        stats.level, stats.xp_to_next_level = calculate_level(stats.xp)
        
        # Get badges
        stats.badges = self._get_user_badges()
        
        # Calculate average RPE
        completed = [s for s in sessions if s.get("rpe_score")]
        if completed:
            stats.average_rpe = sum(s["rpe_score"] for s in completed) / len(completed)
        
        return stats
    
    def _get_user_sessions(self) -> List[Dict]:
        """Get all user workout sessions."""
        try:
            response = supabase_client.table("workout_sessions").select("*").eq(
                "user_id", self.user_id
            ).order("started_at", desc=True).execute()
            return response.data or []
        except:
            return []
    
    def _get_user_xp(self) -> int:
        """Get user's total XP."""
        try:
            response = supabase_client.table("user_stats").select("xp").eq(
                "user_id", self.user_id
            ).single().execute()
            if response.data:
                return response.data.get("xp", 0)
        except:
            pass
        return 0
    
    def _get_user_badges(self) -> List[Badge]:
        """Get all badges earned by user."""
        try:
            response = supabase_client.table("user_badges").select("*").eq(
                "user_id", self.user_id
            ).execute()
            return [Badge.from_db(row) for row in (response.data or [])]
        except:
            return []
    
    def _calculate_streak(self, sessions: List[Dict]) -> StreakData:
        """Calculate current and longest streak from sessions."""
        streak_data = StreakData()
        
        # Get completed sessions by date
        completed_dates = set()
        for session in sessions:
            if session.get("completed_at"):
                try:
                    dt = datetime.fromisoformat(session["completed_at"].replace("Z", "+00:00"))
                    completed_dates.add(dt.date())
                except:
                    pass
        
        if not completed_dates:
            return streak_data
        
        sorted_dates = sorted(completed_dates, reverse=True)
        streak_data.last_workout_date = sorted_dates[0]
        
        # Count this week's workouts
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        streak_data.this_week_workouts = len([d for d in completed_dates if d >= week_start])
        
        # Count this month's workouts
        month_start = today.replace(day=1)
        streak_data.this_month_workouts = len([d for d in completed_dates if d >= month_start])
        
        # Calculate current streak
        current_streak = 0
        check_date = today
        
        # Allow for today or yesterday as start
        if check_date not in completed_dates:
            check_date -= timedelta(days=1)
        
        while check_date in completed_dates:
            current_streak += 1
            check_date -= timedelta(days=1)
        
        streak_data.current_streak = current_streak
        streak_data.longest_streak = max(
            current_streak,
            self._get_longest_streak(completed_dates)
        )
        
        return streak_data
    
    def _get_longest_streak(self, dates: set) -> int:
        """Calculate longest streak from set of dates."""
        if not dates:
            return 0
        
        sorted_dates = sorted(dates)
        longest = 1
        current = 1
        
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                current += 1
                longest = max(longest, current)
            else:
                current = 1
        
        return longest
    
    def check_and_award_badges(self, session_data: Optional[Dict] = None) -> List[Badge]:
        """Check conditions and award applicable badges."""
        new_badges = []
        existing_badges = {b.id for b in self._get_user_badges()}
        sessions = self._get_user_sessions()
        
        # Check each badge type
        badge_checks = [
            (BadgeType.FIRST_WORKOUT, lambda: len(sessions) >= 1),
            (BadgeType.WEEK_STREAK_3, lambda: self._check_streak(3)),
            (BadgeType.WEEK_STREAK_7, lambda: self._check_streak(7)),
            (BadgeType.WEEK_STREAK_30, lambda: self._check_streak(30)),
            (BadgeType.MONTH_WORKER, lambda: self._get_month_workouts() >= 20),
            (BadgeType.PERFECT_WEEK, lambda: self._check_perfect_week()),
        ]
        
        # Time-based checks
        if session_data:
            hour = datetime.now().hour
            if hour < 7 and BadgeType.EARLY_BIRD not in existing_badges:
                badge_checks.append((BadgeType.EARLY_BIRD, lambda: True))
            if hour >= 21 and BadgeType.NIGHT_OWL not in existing_badges:
                badge_checks.append((BadgeType.NIGHT_OWL, lambda: True))
            
            # Volume check
            volume = session_data.get("total_volume_kg", 0)
            if volume >= 10000 and BadgeType.VOLUME_KING not in existing_badges:
                badge_checks.append((BadgeType.VOLUME_KING, lambda: True))
        
        # Award badges
        for badge_type, check_func in badge_checks:
            if badge_type.value not in existing_badges:
                try:
                    if check_func():
                        badge = self._award_badge(badge_type.value)
                        if badge:
                            new_badges.append(badge)
                except:
                    pass
        
        return new_badges
    
    def _check_streak(self, days: int) -> bool:
        """Check if user has current streak of given days."""
        sessions = self._get_user_sessions()
        streak_data = self._calculate_streak(sessions)
        return streak_data.current_streak >= days
    
    def _get_month_workouts(self) -> int:
        """Get number of workouts this month."""
        sessions = self._get_user_sessions()
        streak_data = self._calculate_streak(sessions)
        return streak_data.this_month_workouts
    
    def _check_perfect_week(self) -> bool:
        """Check if user completed all scheduled workouts this week."""
        # Get user's weekly schedule
        try:
            schedule_resp = supabase_client.table("weekly_schedules").select("*").eq(
                "user_id", self.user_id
            ).eq("active", True).single().execute()
            
            if not schedule_resp.data:
                return False
            
            schedule = schedule_resp.data
            # Count scheduled days
            days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            scheduled_count = sum(1 for d in days if not schedule.get(d, {}).get("rest_day", True))
            
            # Get this week's workouts
            streak_data = self._calculate_streak(sessions)
            return streak_data.this_week_workouts >= scheduled_count
        except:
            return False
    
    def _award_badge(self, badge_id: str) -> Optional[Badge]:
        """Award a badge to the user."""
        try:
            response = supabase_client.table("user_badges").insert({
                "user_id": self.user_id,
                "badge_id": badge_id,
                "earned_at": datetime.utcnow().isoformat()
            }).execute()
            
            if response.data:
                return Badge.from_db(response.data[0])
        except Exception as e:
            print(f"Error awarding badge: {e}")
        return None
    
    def add_xp(self, amount: int) -> tuple[int, int]:
        """Add XP to user and return new level/XP."""
        current_xp = self._get_user_xp()
        new_xp = current_xp + amount
        
        try:
            supabase_client.table("user_stats").upsert({
                "user_id": self.user_id,
                "xp": new_xp
            }, on_conflict="user_id").execute()
        except:
            # Try insert if upsert fails
            try:
                supabase_client.table("user_stats").insert({
                    "user_id": self.user_id,
                    "xp": new_xp
                }).execute()
            except:
                pass
        
        new_level, xp_needed = calculate_level(new_xp)
        return new_level, new_xp
    
    def record_workout_complete(self, session_data: Dict) -> Dict[str, Any]:
        """Handle workout completion - check badges, add XP."""
        result = {
            "new_badges": [],
            "xp_earned": 0,
            "level_up": False,
            "old_level": 0,
            "new_level": 0
        }
        
        # Get current level
        current_xp = self._get_user_xp()
        old_level, _ = calculate_level(current_xp)
        result["old_level"] = old_level
        
        # Add XP for workout
        xp_earned = xp_for_action("workout_complete")
        
        # Check for streak bonuses
        streak_data = self._calculate_streak(self._get_user_sessions())
        if streak_data.current_streak >= 3:
            xp_earned += xp_for_action("streak_3")
        if streak_data.current_streak >= 7:
            xp_earned += xp_for_action("streak_7")
        
        result["xp_earned"] = xp_earned
        
        # Add XP
        new_level, _ = self.add_xp(xp_earned)
        result["new_level"] = new_level
        result["level_up"] = new_level > old_level
        
        # Check badges
        new_badges = self.check_and_award_badges(session_data)
        result["new_badges"] = [
            {"id": b.id, "name": b.name, "icon": b.icon} 
            for b in new_badges
        ]
        
        # Add badge XP
        for badge in new_badges:
            badge_info = BADGE_DEFINITIONS.get(badge.id)
            if badge_info:
                self.add_xp(badge_info.get("xp", 100))
        
        return result
