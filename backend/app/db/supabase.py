"""
Supabase Client
Database and authentication
"""
from supabase import create_client, Client
from app.core.config import settings

# Initialize Supabase client
supabase_client: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)
