"""
Notification service - handles reminders and motivational notifications
"""
from datetime import datetime, time
from typing import Optional, List, Dict, Any
from enum import Enum

from app.db.supabase import supabase_client


class NotificationType(str, Enum):
    WORKOUT_REMINDER = "workout_reminder"
    STREAK_WARNING = "streak_warning"
    STREAK_BROKEN = "streak_broken"
    WEEKLY_PROGRAM_READY = "weekly_program_ready"
    NEW_BADGE = "new_badge"
    LEVEL_UP = "level_up"
    PR_ACHIEVED = "pr_achieved"
    WEEKLY_SUMMARY = "weekly_summary"
    MOTIVATIONAL = "motivational"
    CHECK_IN = "check_in"  # Ask about recovery


MOTIVATIONAL_QUOTES = [
    "The only bad workout is the one that didn't happen.",
    "Consistency beats intensity. Show up every day.",
    "Your body can stand almost anything. It's your mind you have to convince.",
    "The pain you feel today will be the strength you feel tomorrow.",
    "Don't stop when you're tired. Stop when you're done.",
    "Champions are made when no one is watching and everyone doubts.",
    "The difference between try and triumph is a little umph.",
    "You don't have to be great to start, but you have to start to be great.",
    "Every workout counts. Make today one that matters.",
    "Your only limit is you. Push harder than yesterday.",
]


class NotificationPreferences(BaseModel):
    workout_reminders: bool = True
    reminder_time: str = "07:00"  # HH:MM format
    streak_alerts: bool = True
    weekly_summary: bool = True
    motivational: bool = True
    motivational_interval: int = 3  # Days between motivational
    check_in_enabled: bool = True
    check_in_time: str = "20:00"


class NotificationService:
    """Service for managing user notifications."""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def get_user_preferences(self) -> NotificationPreferences:
        """Get user's notification preferences."""
        try:
            response = supabase_client.table("notification_preferences").select("*").eq(
                "user_id", self.user_id
            ).single().execute()
            
            if response.data:
                return NotificationPreferences(**response.data)
        except:
            pass
        
        return NotificationPreferences()
    
    def update_preferences(self, prefs: NotificationPreferences) -> bool:
        """Update notification preferences."""
        try:
            prefs_dict = prefs.model_dump()
            prefs_dict["user_id"] = self.user_id
            supabase_client.table("notification_preferences").upsert(
                prefs_dict, on_conflict="user_id"
            ).execute()
            return True
        except:
            return False
    
    def schedule_workout_reminder(self, day: str, time_str: str) -> Dict:
        """Schedule a workout reminder for a specific day and time."""
        try:
            reminder = {
                "user_id": self.user_id,
                "type": NotificationType.WORKOUT_REMINDER.value,
                "schedule_day": day,
                "schedule_time": time_str,
                "enabled": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = supabase_client.table("scheduled_notifications").insert(reminder).execute()
            return {"success": True, "id": response.data[0]["id"] if response.data else None}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_notification(
        self,
        notification_type: NotificationType,
        title: str,
        body: str,
        data: Optional[Dict] = None
    ) -> Optional[str]:
        """Create a notification for the user."""
        try:
            notification = {
                "user_id": self.user_id,
                "type": notification_type.value,
                "title": title,
                "body": body,
                "data": data or {},
                "read": False,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = supabase_client.table("notifications").insert(notification).execute()
            return response.data[0]["id"] if response.data else None
        except Exception as e:
            print(f"Error creating notification: {e}")
            return None
    
    def get_unread_count(self) -> int:
        """Get count of unread notifications."""
        try:
            response = supabase_client.table("notifications").select("id", count="exact").eq(
                "user_id", self.user_id
            ).eq("read", False).execute()
            return response.count or 0
        except:
            return 0
    
    def get_notifications(self, limit: int = 20, unread_only: bool = False) -> List[Dict]:
        """Get user's notifications."""
        try:
            query = supabase_client.table("notifications").select("*").eq(
                "user_id", self.user_id
            ).order("created_at", desc=True).limit(limit)
            
            if unread_only:
                query = query.eq("read", False)
            
            response = query.execute()
            return response.data or []
        except:
            return []
    
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        try:
            supabase_client.table("notifications").update({"read": True}).eq(
                "id", notification_id
            ).eq("user_id", self.user_id).execute()
            return True
        except:
            return False
    
    def mark_all_read(self) -> bool:
        """Mark all notifications as read."""
        try:
            supabase_client.table("notifications").update({"read": True}).eq(
                "user_id", self.user_id
            ).eq("read", False).execute()
            return True
        except:
            return False
    
    def send_streak_warning(self, current_streak: int) -> Optional[str]:
        """Send a warning that streak is at risk."""
        prefs = self.get_user_preferences()
        if not prefs.streak_alerts:
            return None
        
        title = "🔥 Don't Lose Your Streak!"
        body = f"You've been on a {current_streak}-day streak. Train today to keep it alive!"
        
        return self.create_notification(
            NotificationType.STREAK_WARNING,
            title,
            body,
            {"streak": current_streak}
        )
    
    def send_streak_broken(self, previous_streak: int) -> Optional[str]:
        """Send notification that streak was broken."""
        prefs = self.get_user_preferences()
        if not prefs.streak_alerts:
            return None
        
        title = "😔 Streak Lost"
        body = f"Your {previous_streak}-day streak ended. Start a new one today!"
        
        return self.create_notification(
            NotificationType.STREAK_BROKEN,
            title,
            body,
            {"previous_streak": previous_streak}
        )
    
    def send_new_badge(self, badge_name: str, badge_icon: str, xp_earned: int) -> Optional[str]:
        """Send notification for new badge."""
        title = f"{badge_icon} Badge Earned!"
        body = f"You unlocked '{badge_name}'! +{xp_earned} XP"
        
        return self.create_notification(
            NotificationType.NEW_BADGE,
            title,
            body,
            {"badge_name": badge_name, "xp": xp_earned}
        )
    
    def send_level_up(self, new_level: int) -> Optional[str]:
        """Send notification for level up."""
        title = "🎉 Level Up!"
        body = f"Congratulations! You've reached Level {new_level}!"
        
        return self.create_notification(
            NotificationType.LEVEL_UP,
            title,
            body,
            {"level": new_level}
        )
    
    def send_weekly_summary(self, stats: Dict) -> Optional[str]:
        """Send weekly training summary."""
        prefs = self.get_user_preferences()
        if not prefs.weekly_summary:
            return None
        
        workouts = stats.get("workouts", 0)
        volume = stats.get("volume_kg", 0)
        avg_rpe = stats.get("avg_rpe", 0)
        
        title = "📊 Weekly Summary"
        body = f"You completed {workouts} workouts, {volume/1000:.1f}t total volume, avg RPE {avg_rpe:.1f}/10"
        
        return self.create_notification(
            NotificationType.WEEKLY_SUMMARY,
            title,
            body,
            stats
        )
    
    def send_motivational(self) -> Optional[str]:
        """Send a random motivational notification."""
        import random
        prefs = self.get_user_preferences()
        if not prefs.motivational:
            return None
        
        quote = random.choice(MOTIVATIONAL_QUOTES)
        
        return self.create_notification(
            NotificationType.MOTIVATIONAL,
            "💪 Stay Strong",
            quote,
            {}
        )
    
    def send_check_in(self) -> Optional[str]:
        """Send a daily check-in about recovery."""
        prefs = self.get_user_preferences()
        if not prefs.check_in_enabled:
            return None
        
        title = "📝 How are you feeling?"
        body = "Log your recovery metrics to get personalized workout recommendations."
        
        return self.create_notification(
            NotificationType.CHECK_IN,
            title,
            body,
            {"action": "log_recovery"}
        )
    
    def cleanup_old_notifications(self, days: int = 30) -> int:
        """Delete notifications older than specified days."""
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        try:
            response = supabase_client.table("notifications").delete().eq(
                "user_id", self.user_id
            ).lt("created_at", cutoff).eq("read", True).execute()
            return len(response.data) if response.data else 0
        except:
            return 0
