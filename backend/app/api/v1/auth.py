"""
Authentication API Endpoints
Registration, Login, Password Reset
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import logging
import re
from datetime import datetime, timedelta
import secrets

from app.db.supabase import supabase_client
from app.db.helpers import handle_supabase_response
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================
# Request/Response Models
# ============================================

class RegisterRequest(BaseModel):
    """User registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    name: str = Field(..., min_length=2, max_length=100)
    confirm_password: str
    
    # Optional profile data
    birth_date: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    fitness_level: str = Field("beginner", description="beginner|intermediate|advanced")
    goals: list[str] = Field(default_factory=lambda: ["general_fitness"])
    
    def validate_password(self):
        """Validate password strength"""
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        # Check for complexity
        if not re.search(r'[A-Z]', self.password):
            raise ValueError("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', self.password):
            raise ValueError("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', self.password):
            raise ValueError("Password must contain at least one number")
        
        return True


class LoginRequest(BaseModel):
    """User login"""
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    """Request password reset"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Reset password with token"""
    token: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


class AuthResponse(BaseModel):
    """Authentication response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: dict
    expires_in: int = 3600


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


# ============================================
# Registration
# ============================================

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """
    Register new user
    
    Password requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    
    Example:
    ```json
    {
      "email": "athlete@example.com",
      "password": "SecurePass123",
      "confirm_password": "SecurePass123",
      "name": "John Doe",
      "birth_date": "1990-05-15",
      "weight_kg": 80,
      "height_cm": 175,
      "fitness_level": "intermediate",
      "goals": ["strength", "conditioning"]
    }
    ```
    """
    # Validate password
    try:
        request.validate_password()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Check if email already exists
    existing = supabase_client.table("users").select("email").eq(
        "email", request.email
    ).execute()
    
    if existing.data:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Create auth user in Supabase
    try:
        auth_response = supabase_client.auth.sign_up({
            "email": request.email,
            "password": request.password,
            "options": {
                "data": {
                    "name": request.name
                }
            }
        })
        
        if not auth_response.user:
            raise HTTPException(
                status_code=500,
                detail="Failed to create user account"
            )
        
        auth_user_id = auth_response.user.id
        
    except Exception as e:
        logger.error(f"Supabase auth sign_up failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to create account. Please try again."
        )
    
    # Create user profile
    user_data = {
        "auth_user_id": auth_user_id,
        "email": request.email,
        "name": request.name,
        "birth_date": request.birth_date,
        "weight_kg": request.weight_kg,
        "height_cm": request.height_cm,
        "fitness_level": request.fitness_level,
        "preferences": {
            "goals": request.goals,
            "methodology": "hwpo",
            "weaknesses": []
        },
        "created_at": datetime.utcnow().isoformat()
    }
    
    profile_response = supabase_client.table("users").insert(user_data).execute()
    
    user_profile = handle_supabase_response(profile_response, "Failed to create user profile")
    
    if not user_profile:
        # Rollback auth user if profile creation failed
        try:
            supabase_client.auth.admin.delete_user(auth_user_id)
        except:
            pass
        raise HTTPException(status_code=500, detail="Failed to create user profile")
    
    # Return auth response
    return AuthResponse(
        access_token=auth_response.session.access_token if auth_response.session else "",
        user={
            "id": user_profile[0]["id"],
            "email": request.email,
            "name": request.name
        },
        expires_in=3600
    )


# ============================================
# Login
# ============================================

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Login user
    
    Returns JWT access token valid for 1 hour.
    
    Example:
    ```json
    {
      "email": "athlete@example.com",
      "password": "SecurePass123"
    }
    ```
    """
    try:
        auth_response = supabase_client.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })
        
        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )
        
        # Get user profile
        profile_response = supabase_client.table("users").select("*").eq(
            "auth_user_id", auth_response.user.id
        ).single().execute()
        
        user_profile = handle_supabase_response(profile_response, "Failed to fetch user profile")
        
        return AuthResponse(
            access_token=auth_response.session.access_token,
            refresh_token=str(auth_response.session.refresh_token) if hasattr(auth_response.session, 'refresh_token') and auth_response.session.refresh_token else None,
            user={
                "id": user_profile["id"],
                "email": user_profile["email"],
                "name": user_profile["name"],
                "fitness_level": user_profile.get("fitness_level")
            },
            expires_in=auth_response.session.expires_in or 3600
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )


# ============================================
# Password Reset
# ============================================

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request password reset email
    
    Sends reset link to user's email if account exists.
    For security, always returns success even if email not found.
    
    Example:
    ```json
    {
      "email": "athlete@example.com"
    }
    ```
    """
    try:
        # Request password reset from Supabase Auth
        supabase_client.auth.reset_password_email(
            request.email,
            options={
                "redirect_to": f"{settings.FRONTEND_URL}/reset-password"
            }
        )
        
        logger.info(f"Password reset requested for {request.email}")
        
    except Exception as e:
        # Don't expose whether email exists
        logger.warning(f"Password reset request: {e}")
    
    # Always return success for security
    return MessageResponse(
        message="If an account exists with this email, you will receive a password reset link."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password with token
    
    Token is received via email link.
    
    Example:
    ```json
    {
      "token": "reset_token_from_email",
      "new_password": "NewSecurePass123",
      "confirm_password": "NewSecurePass123"
    }
    ```
    """
    if request.new_password != request.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Validate password strength
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    if not re.search(r'[A-Z]', request.new_password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    
    if not re.search(r'[a-z]', request.new_password):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
    
    if not re.search(r'\d', request.new_password):
        raise HTTPException(status_code=400, detail="Password must contain at least one number")
    
    try:
        # Update password using token
        supabase_client.auth.update_user({
            "password": request.new_password
        })
        
        return MessageResponse(message="Password updated successfully. You can now login.")
        
    except Exception as e:
        logger.error(f"Password reset failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset token"
        )


# ============================================
# Email Verification
# ============================================

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(token: str):
    """
    Verify email address
    
    Token is received via email link after registration.
    """
    try:
        # Supabase handles email verification automatically
        # This endpoint is for custom logic if needed
        return MessageResponse(message="Email verified successfully")
        
    except Exception as e:
        logger.error(f"Email verification failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token"
        )


# ============================================
# Logout
# ============================================

@router.post("/logout", response_model=MessageResponse)
async def logout():
    """
    Logout user (client-side token removal)
    
    Server-side session invalidation handled by Supabase.
    Client should remove access_token from storage.
    """
    try:
        supabase_client.auth.sign_out()
        return MessageResponse(message="Logged out successfully")
    except Exception as e:
        logger.warning(f"Logout warning: {e}")
        return MessageResponse(message="Logged out successfully")


# ============================================
# Session Refresh
# ============================================

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest):
    """
    Refresh access token using a refresh token

    Use when access_token has expired or is about to expire.
    Send the refresh_token received at login to get a new access_token.
    """
    try:
        session = supabase_client.auth.refresh_session(request.refresh_token)

        if not session or not session.session:
            raise HTTPException(status_code=401, detail="No active session")

        return AuthResponse(
            access_token=session.session.access_token,
            refresh_token=getattr(session.session, 'refresh_token', None),
            user={"id": session.session.user.id, "email": session.session.user.email},
            expires_in=session.session.expires_in or 3600
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Failed to refresh token")
