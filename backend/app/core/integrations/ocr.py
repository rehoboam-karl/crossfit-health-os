"""
OCR Lab Report Parser
Extract biomarkers from PDF lab reports using OpenAI GPT-4 Vision
"""
from fastapi import UploadFile


async def parse_lab_report(file: UploadFile) -> list:
    """
    Parse lab report PDF and extract biomarkers
    
    TODO: Implement with OpenAI GPT-4 Vision
    1. Convert PDF to images
    2. Send to GPT-4 Vision
    3. Extract structured biomarker data
    4. Return parsed values
    """
    return []
