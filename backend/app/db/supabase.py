"""
Supabase Client
Database and authentication
"""
from supabase import create_client, Client
from app.core.config import settings

# Initialize Supabase client (only if URL is set)
supabase_client: Client = None

if settings.SUPABASE_URL and settings.SUPABASE_URL.startswith("http"):
    try:
        supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_ANON_KEY
        )
    except Exception as e:
        print(f"Warning: Could not initialize Supabase client: {e}")
        supabase_client = None
else:
    print("Supabase not configured - using PostgreSQL instead")
