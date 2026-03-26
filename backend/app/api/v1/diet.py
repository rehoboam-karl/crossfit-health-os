"""
Custom Diet API - Handle user-uploaded diet plans
"""
import os
import uuid
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from typing import Optional

from app.core.auth import get_current_user
from app.db.supabase import supabase_client
from app.services.diet_parser import parse_diet_pdf

router = APIRouter(prefix="/api/v1/diet", tags=["diet"])


@router.post("/upload")
async def upload_diet_pdf(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Upload a diet plan PDF and parse it
    
    The system will:
    1. Store the PDF
    2. Extract calories, macros, meal times
    3. Create reminder schedule based on meal times
    """
    user_id = current_user["id"]
    
    # Validate file
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Read PDF content
    content = await file.read()
    
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    
    try:
        # Extract text from PDF (simplified - in production use pdfplumber)
        pdf_text = extract_pdf_text(content)
        
        if not pdf_text or len(pdf_text) < 50:
            raise HTTPException(
                status_code=400, 
                detail="Could not extract text from PDF. Please ensure the PDF contains selectable text."
            )
        
        # Parse the diet plan
        diet_data = parse_diet_pdf(pdf_text)
        
        # Save file to storage
        file_id = str(uuid.uuid4())
        filename = f"diet_{user_id}_{file_id}.pdf"
        
        # Store in Supabase Storage or local
        try:
            storage_path = f"diet_plans/{user_id}/{filename}"
            supabase_client.storage.from_("diet_plans").upload(
                path=storage_path,
                file=content
            )
            file_url = f"{supabase_client.storage_url}/diet_plans/{storage_path}"
        except Exception as e:
            logger.warning(f"Storage upload failed: {e}")
            file_url = None
        
        # Save to database
        diet_record = {
            "user_id": user_id,
            "file_name": file.filename,
            "file_url": file_url,
            "daily_calories": diet_data.get("daily_calories"),
            "protein_g": diet_data.get("macros", {}).get("protein_g"),
            "carbs_g": diet_data.get("macros", {}).get("carbs_g"),
            "fat_g": diet_data.get("macros", {}).get("fat_g"),
            "meals": diet_data.get("meals"),
            "supplements": diet_data.get("supplements"),
            "notes": diet_data.get("notes"),
            "parsed_data": diet_data,
            "uploaded_at": datetime.utcnow().isoformat(),
            "active": True
        }
        
        # Deactivate previous plans
        try:
            supabase_client.table("user_diet_plans").update(
                {"active": False}
            ).eq("user_id", user_id).execute()
        except:
            pass
        
        # Insert new plan
        response = supabase_client.table("user_diet_plans").insert(diet_record).execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to save diet plan")
        
        # Create meal reminders based on parsed meal times
        await create_meal_reminders(user_id, diet_data.get("meals", []))
        
        return {
            "success": True,
            "plan_id": response.data[0].get("id"),
            "file_name": file.filename,
            "parsed": {
                "daily_calories": diet_data.get("daily_calories"),
                "macros": diet_data.get("macros"),
                "meals_count": len(diet_data.get("meals", [])),
                "supplements": diet_data.get("supplements")[:5] if diet_data.get("supplements") else [],
            },
            "message": "Diet plan uploaded and parsed successfully!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.get("/current")
async def get_current_diet_plan(current_user: dict = Depends(get_current_user)):
    """Get the user's current active diet plan"""
    user_id = current_user["id"]
    
    try:
        response = supabase_client.table("user_diet_plans").select("*").eq(
            "user_id", user_id
        ).eq("active", True).single().execute()
        
        if not response.data:
            return {
                "has_plan": False,
                "message": "No diet plan uploaded yet"
            }
        
        plan = response.data
        
        # Format meals for display
        meals = plan.get("meals", [])
        formatted_meals = []
        for meal in meals:
            formatted_meals.append({
                "name": meal.get("name", "").replace("_", " ").title(),
                "time": meal.get("time", ""),
                "foods": meal.get("foods", [])[:3],
                "calories": meal.get("calories")
            })
        
        return {
            "has_plan": True,
            "plan": {
                "id": plan.get("id"),
                "file_name": plan.get("file_name"),
                "uploaded_at": plan.get("uploaded_at"),
                "daily_calories": plan.get("daily_calories"),
                "macros": {
                    "protein_g": plan.get("protein_g"),
                    "carbs_g": plan.get("carbs_g"),
                    "fat_g": plan.get("fat_g")
                },
                "meals": formatted_meals,
                "supplements": plan.get("supplements", [])[:5],
                "notes": plan.get("notes")
            }
        }
        
    except Exception as e:
        return {
            "has_plan": False,
            "error": str(e)
        }


@router.delete("/current")
async def delete_diet_plan(current_user: dict = Depends(get_current_user)):
    """Delete the user's current diet plan"""
    user_id = current_user["id"]
    
    try:
        supabase_client.table("user_diet_plans").update(
            {"active": False}
        ).eq("user_id", user_id).eq("active", True).execute()
        
        # Also delete reminders
        try:
            supabase_client.table("scheduled_notifications").delete().eq(
                "user_id", user_id
            ).eq("type", "meal_reminder").execute()
        except:
            pass
        
        return {
            "success": True,
            "message": "Diet plan deleted"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reminders")
async def get_diet_reminders(current_user: dict = Depends(get_current_user)):
    """Get configured meal reminders"""
    user_id = current_user["id"]
    
    try:
        response = supabase_client.table("scheduled_notifications").select("*").eq(
            "user_id", user_id
        ).eq("type", "meal_reminder").eq("enabled", True).execute()
        
        reminders = []
        for r in (response.data or []):
            reminders.append({
                "id": r.get("id"),
                "meal": r.get("meal_name"),
                "time": r.get("schedule_time"),
                "enabled": r.get("enabled")
            })
        
        return {"reminders": reminders}
        
    except Exception as e:
        return {"reminders": [], "error": str(e)}


@router.post("/reminders/{reminder_id}/toggle")
async def toggle_reminder(
    reminder_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Enable/disable a meal reminder"""
    user_id = current_user["id"]
    
    try:
        # Get current state
        response = supabase_client.table("scheduled_notifications").select("enabled").eq(
            "id", reminder_id
        ).eq("user_id", user_id).single().execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Reminder not found")
        
        new_state = not response.data.get("enabled", True)
        
        supabase_client.table("scheduled_notifications").update(
            {"enabled": new_state}
        ).eq("id", reminder_id).execute()
        
        return {
            "success": True,
            "enabled": new_state
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def create_meal_reminders(user_id: str, meals: list):
    """Create scheduled notifications for each meal"""
    try:
        for meal in meals:
            meal_time = meal.get("time", "08:00")
            meal_name = meal.get("name", "Meal")
            
            # Convert 12h to 24h if needed
            if "am" in meal_time.lower() or "pm" in meal_time.lower():
                meal_time = convert_to_24h(meal_time)
            
            reminder = {
                "user_id": user_id,
                "type": "meal_reminder",
                "meal_name": meal_name,
                "schedule_day": "monday,tuesday,wednesday,thursday,friday,saturday,sunday",  # Every day
                "schedule_time": meal_time,
                "enabled": True
            }
            
            supabase_client.table("scheduled_notifications").insert(reminder).execute()
            
    except Exception as e:
        logger.warning(f"Failed to create meal reminders: {e}")


def convert_to_24h(time_str: str) -> str:
    """Convert 12-hour time to 24-hour format"""
    try:
        # Extract time and AM/PM
        import re
        match = re.match(r'(\d{1,2}):?(\d{2})?\s*(am|pm)', time_str.lower())
        if not match:
            return time_str
        
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        period = match.group(3)
        
        if period == "pm" and hour != 12:
            hour += 12
        elif period == "am" and hour == 12:
            hour = 0
        
        return f"{hour:02d}:{minute:02d}"
    except:
        return time_str


def extract_pdf_text(content: bytes) -> str:
    """
    Extract text from PDF bytes
    In production, use pdfplumber or PyMuPDF
    """
    try:
        import pdfplumber
        
        import io
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
    except ImportError:
        # Fallback: try PyMuPDF
        try:
            import fitz  # PyMuPDF
            
            import io
            doc = fitz.open(io.BytesIO(content))
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            return text
        except ImportError:
            logger.error("No PDF library available. Install pdfplumber or PyMuPDF")
            return ""
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""


import logging
logger = logging.getLogger(__name__)
