"""
Custom Diet PDF Parser
Extracts nutrition info from user-uploaded diet plans
"""
import re
import json
from typing import Dict, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DietPDFParser:
    """
    Parses user-uploaded diet PDFs to extract:
    - Daily calories
    - Macros (protein, carbs, fat)
    - Meal times
    - Food items per meal
    """
    
    def __init__(self, pdf_text: str):
        self.text = pdf_text
        self.lower_text = pdf_text.lower()
    
    def parse(self) -> Dict:
        """
        Parse PDF and return structured diet data
        """
        return {
            "daily_calories": self._extract_calories(),
            "macros": self._extract_macros(),
            "meals": self._extract_meals(),
            "supplements": self._extract_supplements(),
            "notes": self._extract_notes(),
            "parsed_at": datetime.utcnow().isoformat()
        }
    
    def _extract_calories(self) -> Optional[int]:
        """Extract daily calorie target"""
        patterns = [
            r'(\d{3,5})\s*(?:kcal|calories|cal)',
            r'calories[:\s]*(\d{3,5})',
            r'(\d{3,5})\s*cal\s*/\s*day',
            r'daily[:\s]*(\d{3,5})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.lower_text)
            if match:
                return int(match.group(1))
        
        return None
    
    def _extract_macros(self) -> Dict[str, Optional[int]]:
        """Extract macro targets (protein, carbs, fat)"""
        macros = {"protein_g": None, "carbs_g": None, "fat_g": None}
        
        # Protein patterns
        protein_patterns = [
            r'protein[:\s]*(\d{2,3})\s*g',
            r'(\d{2,3})\s*g\s*(?:of\s*)?protein',
            r'protein[:\s]*(\d{1,2})(?:\s*-\s*(\d{2,3}))?\s*g/kg',
        ]
        for pattern in protein_patterns:
            match = re.search(pattern, self.lower_text)
            if match:
                macros["protein_g"] = int(match.group(1))
                break
        
        # Carbs patterns
        carbs_patterns = [
            r'carbs[:\s]*(\d{2,3})\s*g',
            r'carbohydrates[:\s]*(\d{2,3})\s*g',
            r'(\d{2,3})\s*g\s*(?:of\s*)?carbs',
        ]
        for pattern in carbs_patterns:
            match = re.search(pattern, self.lower_text)
            if match:
                macros["carbs_g"] = int(match.group(1))
                break
        
        # Fat patterns
        fat_patterns = [
            r'fat[:\s]*(\d{2,3})\s*g',
            r'(\d{2,3})\s*g\s*(?:of\s*)?fat',
        ]
        for pattern in fat_patterns:
            match = re.search(pattern, self.lower_text)
            if match:
                macros["fat_g"] = int(match.group(1))
                break
        
        return macros
    
    def _extract_meals(self) -> List[Dict]:
        """Extract meal times and food items"""
        meals = []
        
        # Common meal time patterns
        meal_patterns = [
            (r'breakfast[:\s]*(\d{1,2}:\d{2}\s*(?:am|pm)?)', 'breakfast'),
            (r'morning[:\s]*(\d{1,2}:\d{2}\s*(?:am|pm)?)', 'breakfast'),
            (r'lunch[:\s]*(\d{1,2}:\d{2}\s*(?:am|pm)?)', 'lunch'),
            (r'midday[:\s]*(\d{1,2}:\d{2}\s*(?:am|pm)?)', 'lunch'),
            (r'dinner[:\s]*(\d{1,2}:\d{2}\s*(?:pm)?)', 'dinner'),
            (r'supper[:\s]*(\d{1,2}:\d{2}\s*(?:pm)?)', 'dinner'),
            (r'pre[\s-]*workout[:\s]*(\d{1,2}:\d{2}\s*(?:am|pm)?)', 'pre_workout'),
            (r'post[\s-]*workout[:\s]*(\d{1,2}:\d{2}\s*(?:am|pm)?)', 'post_workout'),
            (r'snack[:\s]*(\d{1,2}:\d{2}\s*(?:am|pm)?)', 'snack'),
            (r'mid[\s-]*afternoon[:\s]*(\d{1,2}:\d{2}\s*(?:pm)?)', 'snack'),
        ]
        
        for pattern, meal_name in meal_patterns:
            match = re.search(pattern, self.lower_text)
            if match:
                time = match.group(1)
                # Extract foods near this meal
                foods = self._extract_foods_near(match.start())
                
                meals.append({
                    "name": meal_name,
                    "time": time,
                    "foods": foods,
                    "calories": self._estimate_meal_calories(foods)
                })
        
        return meals
    
    def _extract_foods_near(self, position: int, window: int = 200) -> List[str]:
        """Extract food items mentioned near a position"""
        text_chunk = self.lower_text[max(0, position-50):position+window]
        
        # Common food patterns
        foods = []
        food_patterns = [
            r'(\d+\s*(?:oz|g|ml|cups?|tbsp|tsp|pieces?|servings?)\s+(?:of\s+)?[\w\s]+)',
            r'([\w\s]+)\s+\(\d+\s*(?:oz|g|ml)\)',
            r'([a-zA-Z\s]+)\s*[:\-]?\s*\d+\s*(?:oz|g|ml|cups?)',
        ]
        
        for pattern in food_patterns:
            matches = re.findall(pattern, text_chunk)
            for match in matches:
                food = match.strip() if isinstance(match, str) else match[0].strip()
                if len(food) > 3 and len(food) < 50:
                    foods.append(food)
        
        return list(set(foods))[:5]  # Return max 5 unique items
    
    def _estimate_meal_calories(self, foods: List[str]) -> Optional[int]:
        """Rough estimate of meal calories based on food items"""
        if not foods:
            return None
        
        # Very rough estimates per food keyword
        calorie_keywords = {
            'chicken': 300, 'beef': 350, 'salmon': 300, 'fish': 200,
            'rice': 200, 'pasta': 200, 'bread': 150, 'potato': 150,
            'oatmeal': 150, 'eggs': 200, 'yogurt': 150, 'milk': 100,
            'protein': 150, 'shake': 250, 'salad': 150, 'vegetables': 50,
            'banana': 100, 'apple': 80, 'nuts': 200, 'avocado': 200,
            'cheese': 200, 'butter': 100, 'oil': 100, 'rice cakes': 50,
        }
        
        total = 0
        for food in foods:
            for keyword, cal in calorie_keywords.items():
                if keyword in food.lower():
                    total += cal
                    break
        
        return total if total > 0 else None
    
    def _extract_supplements(self) -> List[str]:
        """Extract supplement recommendations"""
        supplements = []
        
        supplement_patterns = [
            r'(creatine)[:\s-]?\s*(\d+\s*(?:g|mg))?',
            r'(whey|protein)[:\s-]?\s*(\d+\s*(?:g|mg))?',
            r'(bcaas?|eaa)[:\s-]?\s*(\d+\s*(?:g|mg))?',
            r'(vitamin\s*d|b12|iron|zinc|omega[\s-]?3|fish oil)[:\s-]?\s*(\d+\s*(?:g|mg|iu))?',
            r'(caffeine|pre[\s-]*workout)[:\s-]?\s*(\d+\s*(?:mg))?',
            r'(creatine monohydrate)',
        ]
        
        for pattern in supplement_patterns:
            matches = re.findall(pattern, self.lower_text)
            for match in matches:
                supp_name = match[0] if isinstance(match, tuple) else match
                supp_dose = match[1] if isinstance(match, tuple) and len(match) > 1 else ""
                supplements.append(f"{supp_name} {supp_dose}".strip())
        
        return list(set(supplements))
    
    def _extract_notes(self) -> str:
        """Extract any general notes or warnings"""
        notes = []
        
        note_patterns = [
            r'note[:\s]([^\.]+\.)',
            r'warning[:\s]([^\.]+\.)',
            r'important[:\s]([^\.]+\.)',
            r'remember[:\s]([^\.]+\.)',
        ]
        
        for pattern in note_patterns:
            matches = re.findall(pattern, self.lower_text)
            notes.extend([m.strip() for m in matches if len(m) > 10])
        
        return " | ".join(notes[:3]) if notes else ""


def parse_diet_pdf(pdf_text: str) -> Dict:
    """
    Main entry point for parsing a diet PDF
    
    Args:
        pdf_text: Extracted text from PDF
        
    Returns:
        Dict with calories, macros, meals, supplements, notes
    """
    parser = DietPDFParser(pdf_text)
    return parser.parse()
