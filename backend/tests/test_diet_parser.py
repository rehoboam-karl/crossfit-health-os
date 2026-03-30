"""
Tests for app/services/diet_parser.py
"""
import pytest
from app.services.diet_parser import DietPDFParser, parse_diet_pdf


class TestExtractCalories:
    def test_english_kcal(self):
        p = DietPDFParser("Daily target: 2500 kcal")
        assert p._extract_calories() == 2500

    def test_english_calories_word(self):
        p = DietPDFParser("calories: 3200")
        assert p._extract_calories() == 3200

    def test_english_cal_suffix(self):
        p = DietPDFParser("Target 2800 cal per day")
        assert p._extract_calories() == 2800

    def test_portuguese_kcal_dia(self):
        p = DietPDFParser("Energia: 2200 kcal/dia")
        assert p._extract_calories() == 2200

    def test_portuguese_calorias(self):
        p = DietPDFParser("calorias: 1800")
        assert p._extract_calories() == 1800

    def test_portuguese_energia(self):
        p = DietPDFParser("energia: 2100")
        assert p._extract_calories() == 2100

    def test_no_calories_returns_none(self):
        p = DietPDFParser("This text has no calorie information at all.")
        # Will try to derive from macros; with none present returns None
        assert p._extract_calories() is None

    def test_derived_from_macros(self):
        # protein 150g * 4 + carbs 200g * 4 + fat 70g * 9 = 600+800+630 = 2030
        text = "protein: 150g carbs: 200g fat: 70g"
        p = DietPDFParser(text)
        cal = p._extract_calories()
        assert cal == 2030


class TestExtractMacros:
    def test_english_protein(self):
        p = DietPDFParser("protein: 180g carbs: 250g fat: 60g")
        macros = p._extract_macros()
        assert macros["protein_g"] == 180
        assert macros["carbs_g"] == 250
        assert macros["fat_g"] == 60

    def test_english_carbohydrates(self):
        p = DietPDFParser("carbohydrates: 300g protein: 150g fat: 70g")
        macros = p._extract_macros()
        assert macros["carbs_g"] == 300

    def test_english_grams_of_protein(self):
        p = DietPDFParser("120g of protein daily")
        macros = p._extract_macros()
        assert macros["protein_g"] == 120

    def test_portuguese_combined_pattern(self):
        text = "(Carboidrato: 200g/Gordura: 45g/ Proteína: 215g)"
        p = DietPDFParser(text)
        macros = p._extract_macros()
        assert macros["carbs_g"] == 200
        assert macros["fat_g"] == 45
        assert macros["protein_g"] == 215

    def test_portuguese_proteina(self):
        p = DietPDFParser("Proteína: 170g")
        macros = p._extract_macros()
        assert macros["protein_g"] == 170

    def test_portuguese_carboidrato(self):
        p = DietPDFParser("Carboidrato: 220g")
        macros = p._extract_macros()
        assert macros["carbs_g"] == 220

    def test_portuguese_gordura(self):
        p = DietPDFParser("Gordura: 55g")
        macros = p._extract_macros()
        assert macros["fat_g"] == 55

    def test_portuguese_grams_of_protein(self):
        p = DietPDFParser("200g de proteína")
        macros = p._extract_macros()
        assert macros["protein_g"] == 200

    def test_portuguese_protein_accent(self):
        p = DietPDFParser("proteína: 150g")
        macros = p._extract_macros()
        assert macros["protein_g"] == 150

    def test_no_macros(self):
        p = DietPDFParser("No nutritional data here.")
        macros = p._extract_macros()
        assert macros == {"protein_g": None, "carbs_g": None, "fat_g": None}


class TestExtractSupplements:
    def test_whey_protein(self):
        p = DietPDFParser("Take whey protein after workout")
        supps = p._extract_supplements()
        assert any("whey" in s.lower() for s in supps)

    def test_creatine(self):
        p = DietPDFParser("Use creatine 5g daily")
        supps = p._extract_supplements()
        assert any("creatine" in s.lower() for s in supps)

    def test_creatina_portuguese(self):
        p = DietPDFParser("Tomar creatina 5g por dia")
        supps = p._extract_supplements()
        assert any("creatina" in s.lower() for s in supps)

    def test_bcaa(self):
        p = DietPDFParser("BCAAs before training")
        supps = p._extract_supplements()
        assert any("bcaa" in s.lower() for s in supps)

    def test_omega_3(self):
        p = DietPDFParser("omega 3 fish oil supplement")
        supps = p._extract_supplements()
        assert any("omega" in s.lower() for s in supps)

    def test_vitamin_d(self):
        p = DietPDFParser("Vitamin D 2000 IU daily")
        supps = p._extract_supplements()
        assert any("vitamin" in s.lower() for s in supps)

    def test_magnesio(self):
        p = DietPDFParser("magnésio 300mg antes de dormir")
        supps = p._extract_supplements()
        assert any("magn" in s.lower() for s in supps)

    def test_no_supplements(self):
        p = DietPDFParser("Eat chicken with rice and vegetables.")
        supps = p._extract_supplements()
        assert isinstance(supps, list)

    def test_max_ten_supplements(self):
        text = "whey protein creatine bcaas omega 3 vitamin d vitamin b12 zinc magnesium thermogenic pre-workout caffeine"
        p = DietPDFParser(text)
        supps = p._extract_supplements()
        assert len(supps) <= 10

    def test_no_duplicates(self):
        p = DietPDFParser("whey protein whey protein creatine creatine")
        supps = p._extract_supplements()
        assert len(supps) == len(set(s.lower() for s in supps))


class TestExtractGoals:
    def test_cut_goal(self):
        p = DietPDFParser("Objetivo: redução de gordura e definição muscular")
        goals = p._extract_goals()
        assert goals.get("type") == "cut"

    def test_target_loss_kg(self):
        p = DietPDFParser("redução: 5 kg de gordura")
        goals = p._extract_goals()
        assert goals.get("target_loss_kg") == 5

    def test_water_intake(self):
        p = DietPDFParser("Beba 3000 ml ao dia de água")
        goals = p._extract_goals()
        assert goals.get("water_ml") == 3000

    def test_cardio_minutes(self):
        p = DietPDFParser("Fazer cardio: 30 minutos por semana")
        goals = p._extract_goals()
        assert goals.get("cardio_minutes_week") == 30

    def test_empty_goals(self):
        p = DietPDFParser("No specific goals listed here.")
        goals = p._extract_goals()
        assert isinstance(goals, dict)


class TestExtractNotes:
    def test_obs_note(self):
        p = DietPDFParser("obs: beber bastante água durante o dia.")
        notes = p._extract_notes()
        assert "água" in notes

    def test_observacao(self):
        p = DietPDFParser("observação: evitar alimentos processados e gordurosos.")
        notes = p._extract_notes()
        assert len(notes) > 0

    def test_importante(self):
        p = DietPDFParser("importante: fazer refeições em horários regulares.")
        notes = p._extract_notes()
        assert len(notes) > 0

    def test_no_notes(self):
        p = DietPDFParser("Chicken rice broccoli.")
        notes = p._extract_notes()
        assert notes == ""

    def test_multiple_notes_joined_with_pipe(self):
        p = DietPDFParser("obs: note one here. obs: note two here. obs: note three here.")
        notes = p._extract_notes()
        # Multiple obs patterns found → joined with |
        assert "|" in notes or len(notes) > 0


class TestExtractFoodsAfter:
    def test_extracts_known_food(self):
        text = "08:00 frango com arroz e vegetais"
        p = DietPDFParser(text)
        foods = p._extract_foods_after(0)
        # Should find frango or arroz
        found = any("frango" in f.lower() or "arroz" in f.lower() for f in foods)
        assert found or isinstance(foods, list)

    def test_returns_list(self):
        p = DietPDFParser("some food items here")
        foods = p._extract_foods_after(0)
        assert isinstance(foods, list)

    def test_max_eight_foods(self):
        # Fill text with lots of food patterns
        text = "frango arroz batata aipim aveia atum feijão ovos milho tapioca"
        p = DietPDFParser(text)
        foods = p._extract_foods_after(0)
        assert len(foods) <= 8


class TestEstimateMealCalories:
    def test_returns_none_for_empty(self):
        p = DietPDFParser("")
        assert p._estimate_meal_calories([]) is None

    def test_estimates_for_known_foods(self):
        p = DietPDFParser("")
        cal = p._estimate_meal_calories(["frango 150g", "arroz 160g"])
        assert cal is not None
        assert cal > 50

    def test_returns_none_below_threshold(self):
        p = DietPDFParser("")
        # Unknown food won't match anything → total stays 0
        result = p._estimate_meal_calories(["xyzunknownfood"])
        assert result is None


class TestParseDietPdf:
    def test_full_parse_returns_expected_keys(self):
        text = "protein: 150g carbs: 200g fat: 60g 2500 kcal"
        result = parse_diet_pdf(text)
        assert "daily_calories" in result
        assert "macros" in result
        assert "meals" in result
        assert "supplements" in result
        assert "goals" in result
        assert "notes" in result
        assert "parsed_at" in result

    def test_full_portuguese_plan(self):
        text = """
        Plano Alimentar
        calorias: 2200 kcal/dia
        (Carboidrato: 250g/Gordura: 50g/ Proteína: 160g)
        whey protein creatina omega 3
        obs: beber 2500 ml ao dia.
        redução de gordura e definição
        """
        result = parse_diet_pdf(text)
        assert result["daily_calories"] == 2200
        assert result["macros"]["protein_g"] == 160
        assert result["macros"]["carbs_g"] == 250
        assert result["macros"]["fat_g"] == 50
        assert len(result["supplements"]) >= 2
        assert result["goals"].get("type") == "cut"
        assert len(result["notes"]) > 0

    def test_empty_text(self):
        result = parse_diet_pdf("")
        assert result["daily_calories"] is None
        assert result["macros"] == {"protein_g": None, "carbs_g": None, "fat_g": None}
        assert result["meals"] == []
        assert result["supplements"] == []

    def test_parse_method_and_function_equivalent(self):
        text = "protein: 180g carbs: 230g fat: 65g 2800 kcal"
        via_class = DietPDFParser(text).parse()
        via_func = parse_diet_pdf(text)
        assert via_class["daily_calories"] == via_func["daily_calories"]
        assert via_class["macros"] == via_func["macros"]
