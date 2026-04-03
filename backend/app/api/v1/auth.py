"""
Authentication API Endpoints (PostgreSQL version)
Registration, Login, Password Reset
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import logging
import re
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.db.database import init_db, fetchone, execute
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Initialize database on module load
try:
    init_db()
except Exception as e:
    logger.warning(f"Could not initialize database: {e}")

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
        
        if not re.search(r'[0-9]', self.password):
            raise ValueError("Password must contain at least one number")
        
        return True


class LoginRequest(BaseModel):
    """User login"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response model"""
    id: int
    email: str
    name: str
    birth_date: Optional[str] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    fitness_level: str
    goals: list[str]


# ============================================
# Helper Functions
# ============================================

def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt_token(user_id: int, email: str) -> str:
    """Create a JWT token for a user"""
    from app.core.config import settings
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload"""
    from app.core.config import settings
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None

def get_user_by_id(user_id: int):
    """Get user by ID"""
    return fetchone(
        "SELECT id, email, name, birth_date, weight_kg, height_cm, fitness_level, goals FROM users WHERE id = %s",
        user_id
    )

def get_user_by_email(email: str):
    """Get user by email"""
    return fetchone(
        "SELECT id, email, password_hash, name, birth_date, weight_kg, height_cm, fitness_level, goals FROM users WHERE email = %s",
        email
    )

def create_user(user_data: RegisterRequest) -> int:
    """Create a new user"""
    password_hash = hash_password(user_data.password)
    
    # Convert goals list to PostgreSQL array format
    goals_array = "{" + ",".join(f'"{g}"' for g in user_data.goals) + "}"
    
    result = execute(
        """INSERT INTO users (email, password_hash, name, birth_date, weight_kg, height_cm, fitness_level, goals)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        user_data.email,
        password_hash,
        user_data.name,
        user_data.birth_date,
        user_data.weight_kg,
        user_data.height_cm,
        user_data.fitness_level,
        goals_array
    )
    
    # Get the inserted ID
    user = fetchone("SELECT lastval()")
    return user[0] if user else None


# ============================================
# API Endpoints
# ============================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, background_tasks: BackgroundTasks):
    """Register a new user"""
    try:
        # Validate password
        request.validate_password()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Check if user already exists
    existing_user = get_user_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    try:
        # Create user
        user_id = create_user(request)
        
        return UserResponse(
            id=user_id,
            email=request.email,
            name=request.name,
            birth_date=request.birth_date,
            weight_kg=request.weight_kg,
            height_cm=request.height_cm,
            fitness_level=request.fitness_level,
            goals=request.goals
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.post("/login")
async def login(request: LoginRequest):
    """Login user"""
    # Get user by email
    user = get_user_by_email(request.email)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    user_id, email, password_hash, name, birth_date, weight_kg, height_cm, fitness_level, goals = user
    
    # Verify password
    if not verify_password(request.password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create JWT token
    token = create_jwt_token(user_id, email)
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "email": email,
            "name": name,
            "birth_date": str(birth_date) if birth_date else None,
            "weight_kg": weight_kg,
            "height_cm": height_cm,
            "fitness_level": fitness_level,
            "goals": goals if goals else []
        }
    }


def extract_user_from_token(req):
    """Extract and validate user from request Authorization header"""
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header"
        )
    token = auth_header[7:]
    payload = verify_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    user_id = int(payload.get("sub", 0))
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

@router.get("/me", response_model=UserResponse)
async def get_current_user(req: Request):
    """Get current authenticated user"""
    user = extract_user_from_token(req)
    user_id, email, name, birth_date, weight_kg, height_cm, fitness_level, goals = user
    return UserResponse(
        id=user_id,
        email=email,
        name=name,
        birth_date=str(birth_date) if birth_date else None,
        weight_kg=weight_kg,
        height_cm=height_cm,
        fitness_level=fitness_level,
        goals=goals if goals else []
    )


@router.post("/logout")
async def logout():
    """Logout user"""
    return {"message": "Logged out successfully"}
