"""
Authentication utilities
JWT validation with Supabase
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.core.config import settings
from app.db.supabase import supabase_client

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Validate JWT token and return user
    Supabase auth integration
    """
    token = credentials.credentials
    
    try:
        # Verify token with Supabase
        user = supabase_client.auth.get_user(token)
        
        # ✅ FIX: Validate user and user.user before accessing
        if not user or not user.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Get full user profile
        response = supabase_client.table("users").select("*").eq(
            "auth_user_id", user.user.id
        ).single().execute()
        
        # ✅ FIX: Check for Supabase errors
        if response.error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch user profile"
            )
        
        if response.data:
            return response.data
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
        
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
