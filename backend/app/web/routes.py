"""
Web routes for serving HTML pages with Jinja2
"""
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()

# Setup Jinja2 templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# ============================================
# Public pages
# ============================================

@router.get("/")
async def home(request: Request):
    """Landing page"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/login")
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register")
async def register_page(request: Request):
    """Registration page"""
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/forgot-password")
async def forgot_password_page(request: Request):
    """Forgot password page"""
    return templates.TemplateResponse("forgot_password.html", {"request": request})


# ============================================
# Dashboard pages
# ============================================

@router.get("/dashboard")
async def dashboard_page(request: Request):
    """Main dashboard"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "active_page": "dashboard"
    })


@router.get("/dashboard/workouts")
async def workouts_page(request: Request):
    """Workouts page"""
    return templates.TemplateResponse("training.html", {
        "request": request,
        "active_page": "workouts",
        "recent_workouts": [],
        "personal_records": []
    })


@router.get("/dashboard/schedule")
async def schedule_page(request: Request):
    """Schedule page"""
    return templates.TemplateResponse("schedule.html", {
        "request": request,
        "active_page": "schedule"
    })


@router.get("/dashboard/health")
async def health_page(request: Request):
    """Health/biometrics page"""
    return templates.TemplateResponse("health.html", {
        "request": request,
        "active_page": "health",
        "biomarkers": [],
        "recovery_trend": []
    })


@router.get("/dashboard/nutrition")
async def nutrition_page(request: Request):
    """Nutrition page"""
    return templates.TemplateResponse("nutrition.html", {
        "request": request,
        "active_page": "nutrition",
        "today_macros": {"protein": 0, "carbs": 0, "fat": 0, "calories": 0},
        "targets": {"protein": 150, "carbs": 200, "fat": 70, "calories": 2000},
        "meals": [],
        "protein_pct": 0,
        "carbs_pct": 0,
        "fat_pct": 0
    })


@router.get("/dashboard/reviews")
async def reviews_page(request: Request):
    """Reviews page"""
    return templates.TemplateResponse("reviews.html", {
        "request": request,
        "active_page": "reviews"
    })


@router.get("/dashboard/profile")
async def profile_page(request: Request):
    """Profile page"""
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "active_page": "profile"
    })


# ============================================
# Auth Verification Routes (Supabase callbacks)
# ============================================

@router.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle Supabase auth callback"""
    from app.core.config import settings
    
    token = request.query_params.get("token")
    type_param = request.query_params.get("type")
    redirect_to = request.query_params.get("redirect_to", "/dashboard")
    
    return templates.TemplateResponse("auth_callback.html", {
        "request": request,
        "token": token,
        "type": type_param,
        "redirect_to": redirect_to,
        "supabase_url": settings.SUPABASE_URL,
        "supabase_anon_key": settings.SUPABASE_ANON_KEY
    })


@router.get("/auth/verify")
async def auth_verify(request: Request):
    """Alternative verify route"""
    token = request.query_params.get("token")
    type_param = request.query_params.get("type")
    
    return templates.TemplateResponse("auth_callback.html", {
        "request": request,
        "token": token,
        "type": type_param,
        "redirect_to": "/dashboard"
    })


@router.get("/auth/handler")
async def auth_handler(request: Request):
    """Handle auth responses with tokens in URL hash"""
    return templates.TemplateResponse("auth_handler.html", {"request": request})


@router.get("/reset-password")
async def reset_password_redirect(request: Request):
    """Redirect from forgot-password email to update-password page"""
    from fastapi.responses import RedirectResponse
    # Preserve hash fragment by redirecting to update-password
    return RedirectResponse(url="/update-password", status_code=302)


@router.get("/update-password")
async def update_password_page(request: Request):
    """Page to set new password after recovery link"""
    from app.core.config import settings
    
    return templates.TemplateResponse("update_password.html", {
        "request": request,
        "supabase_url": settings.SUPABASE_URL,
        "supabase_anon_key": settings.SUPABASE_ANON_KEY
    })
