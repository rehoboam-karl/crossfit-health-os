"""
Web Routes - HTML Pages (FastAPI + Jinja2)
Serves frontend templates for dashboard, training, health, nutrition
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import date, datetime, timedelta
import random

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Redirect to dashboard"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        **get_dashboard_data()
    })


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        **get_dashboard_data()
    })


@router.get("/training", response_class=HTMLResponse)
async def training(request: Request):
    """Training page - workout feed and generation"""
    return templates.TemplateResponse("training.html", {
        "request": request,
        **get_training_data()
    })


@router.get("/health", response_class=HTMLResponse)
async def health(request: Request):
    """Health page - biomarkers and recovery"""
    return templates.TemplateResponse("health.html", {
        "request": request,
        **get_health_data()
    })


@router.get("/nutrition", response_class=HTMLResponse)
async def nutrition(request: Request):
    """Nutrition page - meals and macros"""
    return templates.TemplateResponse("nutrition.html", {
        "request": request,
        **get_nutrition_data()
    })


# ==============================================
# Mock Data Functions (Replace with real DB calls)
# ==============================================

def get_dashboard_data():
    """Generate mock data for dashboard"""
    return {
        # Stats
        "readiness_score": 85,
        "total_workouts": 18,
        "avg_duration": 45.2,
        "hrv_value": 68,
        "hrv_ratio": 1.12,
        "calories_today": 2340,
        "calories_target": 2800,
        
        # Recovery
        "sleep_hours": 7.5,
        "sleep_quality": 88,
        "stress_level": 3,
        "soreness": 4,
        
        # Today's Workout
        "workout_name": "HWPO Strength Monday",
        "volume_multiplier": 1.1,
        "workout_recommendation": "💪 Excellent readiness - push for PRs",
        "workout_movements": [
            {"movement": "Back Squat", "sets": 5, "reps": 5, "intensity": "85%"},
            {"movement": "Bench Press", "sets": 4, "reps": 8, "intensity": "75%"},
            {"movement": "Barbell Row", "sets": 3, "reps": 10, "intensity": "70%"}
        ],
        
        # Charts Data
        "volume_data": [45, 52, 48, 61, 55, 57, 62, 58, 65, 70, 68, 72, 75, 71, 69, 73, 78, 76, 74, 80, 82, 79, 83, 85, 81, 84, 88, 86, 90, 92],
        "volume_dates": generate_last_30_days(),
        "hrv_data": [62, 65, 63, 68, 66, 64, 70, 72, 69, 71, 68, 73, 75, 71, 69, 74, 76, 73, 71, 77, 79, 75, 78, 80, 76, 79, 82, 80, 78, 81],
        "readiness_data": [72, 75, 73, 78, 76, 74, 80, 82, 79, 81, 78, 83, 85, 81, 79, 84, 86, 83, 81, 87, 89, 85, 88, 90, 86, 89, 92, 90, 88, 91],
        "hrv_dates": generate_last_30_days()
    }


def get_training_data():
    """Generate mock data for training page"""
    return {
        "recent_workouts": [
            {
                "date": "2026-02-07",
                "name": "Fran",
                "type": "metcon",
                "score": "3:45",
                "rpe": 9,
                "notes": "PR! Felt strong on thrusters"
            },
            {
                "date": "2026-02-06",
                "name": "Heavy Deadlifts",
                "type": "strength",
                "score": "5x3 @ 160kg",
                "rpe": 8,
                "notes": "Good bar speed"
            },
            {
                "date": "2026-02-05",
                "name": "Murph (Half)",
                "type": "hero",
                "score": "28:32",
                "rpe": 10,
                "notes": "Brutal but finished strong"
            }
        ],
        "personal_records": [
            {"movement": "Back Squat", "weight": 180, "unit": "kg", "date": "2026-01-15"},
            {"movement": "Clean & Jerk", "weight": 130, "unit": "kg", "date": "2026-01-20"},
            {"movement": "Fran", "time": "3:45", "unit": "min", "date": "2026-02-07"}
        ]
    }


def get_health_data():
    """Generate mock data for health page"""
    return {
        "biomarkers": [
            {"name": "Testosterone Total", "value": 720, "unit": "ng/dL", "status": "optimal", "date": "2026-01-15"},
            {"name": "Vitamin D", "value": 65, "unit": "ng/mL", "status": "optimal", "date": "2026-01-15"},
            {"name": "Cortisol AM", "value": 15.2, "unit": "μg/dL", "status": "normal", "date": "2026-01-15"},
            {"name": "CRP", "value": 0.8, "unit": "mg/L", "status": "optimal", "date": "2026-01-15"}
        ],
        "recovery_trend": generate_recovery_trend()
    }


def get_nutrition_data():
    """Generate mock data for nutrition page"""
    return {
        "today_macros": {
            "calories": 2340,
            "protein": 180,
            "carbs": 245,
            "fat": 78
        },
        "targets": {
            "calories": 2800,
            "protein": 200,
            "carbs": 300,
            "fat": 80
        },
        "recent_meals": [
            {"time": "07:30", "name": "Café da Manhã", "calories": 620, "protein": 45, "carbs": 65, "fat": 18},
            {"time": "12:00", "name": "Almoço", "calories": 850, "protein": 68, "carbs": 95, "fat": 28},
            {"time": "16:00", "name": "Pré-Treino", "calories": 320, "protein": 25, "carbs": 42, "fat": 8},
            {"time": "19:30", "name": "Pós-Treino", "calories": 550, "protein": 42, "carbs": 43, "fat": 24}
        ]
    }


def generate_last_30_days():
    """Generate last 30 days labels"""
    today = date.today()
    return [(today - timedelta(days=i)).strftime("%d/%m") for i in range(29, -1, -1)]


def generate_recovery_trend():
    """Generate 7-day recovery trend"""
    return [
        {"day": "Seg", "readiness": 78, "hrv": 65, "sleep": 7.2},
        {"day": "Ter", "readiness": 82, "hrv": 68, "sleep": 7.8},
        {"day": "Qua", "readiness": 75, "hrv": 62, "sleep": 6.5},
        {"day": "Qui", "readiness": 88, "hrv": 72, "sleep": 8.1},
        {"day": "Sex", "readiness": 85, "hrv": 70, "sleep": 7.6},
        {"day": "Sáb", "readiness": 91, "hrv": 74, "sleep": 8.5},
        {"day": "Dom", "readiness": 86, "hrv": 71, "sleep": 7.9}
    ]
