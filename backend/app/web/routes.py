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


@router.get("/dashboard")
async def dashboard_page(request: Request):
    """Dashboard page (protected client-side)"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


# Dashboard subpages (to be implemented)
@router.get("/dashboard/workouts")
async def workouts_page(request: Request):
    """Workouts page - placeholder"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/dashboard/schedule")
async def schedule_page(request: Request):
    """Schedule page - placeholder"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/dashboard/reviews")
async def reviews_page(request: Request):
    """Reviews page - placeholder"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@router.get("/dashboard/profile")
async def profile_page(request: Request):
    """Profile page - placeholder"""
    return templates.TemplateResponse("dashboard.html", {"request": request})
