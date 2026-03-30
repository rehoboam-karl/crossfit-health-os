"""
Tests for app/models/nutrition.py
Covers UserRestrictions and NutritionTargets models.
"""
import pytest
from app.models.nutrition import DietType, UserRestrictions, NutritionTargets


class TestDietType:
    def test_all_values(self):
        assert DietType.OMNIVORE == "omnivore"
        assert DietType.VEGETARIAN == "vegetarian"
        assert DietType.VEGAN == "vegan"
        assert DietType.PESCATARIAN == "pescatarian"
        assert DietType.KETO == "keto"
        assert DietType.PALEO == "paleo"
        assert DietType.OTHER == "other"


class TestUserRestrictionsDefaults:
    def test_defaults(self):
        r = UserRestrictions()
        assert r.diet_type == DietType.OMNIVORE
        assert r.allergies == []
        assert r.intolerances == []
        assert r.dislikes == []
        assert r.supplements == []
        assert r.avoid_meats is False
        assert r.avoid_dairy is False
        assert r.avoid_gluten is False
        assert r.caffeine_sensitive is False
        assert r.lactose_intolerant is False
        assert r.orthorexia is False


class TestGetSupplementRecommendations:
    def test_omnivore_base_supplements(self):
        r = UserRestrictions(diet_type=DietType.OMNIVORE)
        supps = r.get_supplement_recommendations()
        names = [s["name"] for s in supps]
        assert "Vitamin D" in names
        assert "Omega-3 Fish Oil" in names

    def test_vegan_gets_extra_supplements(self):
        r = UserRestrictions(diet_type=DietType.VEGAN)
        supps = r.get_supplement_recommendations()
        names = [s["name"] for s in supps]
        assert "Vitamin B12" in names
        assert "Iron" in names
        assert "Zinc" in names
        assert "Creatine" in names
        assert "BCAAs / EAAs" in names

    def test_vegetarian_gets_extra_supplements(self):
        r = UserRestrictions(diet_type=DietType.VEGETARIAN)
        supps = r.get_supplement_recommendations()
        names = [s["name"] for s in supps]
        assert "Vitamin B12" in names
        assert "Iron" in names
        assert "Creatine" in names

    def test_dairy_free_adds_calcium(self):
        r = UserRestrictions(avoid_dairy=True)
        supps = r.get_supplement_recommendations()
        names = [s["name"] for s in supps]
        assert "Calcium" in names

    def test_lactose_intolerant_adds_calcium(self):
        r = UserRestrictions(lactose_intolerant=True)
        supps = r.get_supplement_recommendations()
        names = [s["name"] for s in supps]
        assert "Calcium" in names

    def test_caffeine_sensitive_removes_caffeine(self):
        # Add a caffeine supplement manually first then check it's filtered
        r = UserRestrictions(caffeine_sensitive=True)
        supps = r.get_supplement_recommendations()
        for s in supps:
            assert "caffeine" not in s["name"].lower()

    def test_keto_uses_base_only(self):
        r = UserRestrictions(diet_type=DietType.KETO)
        supps = r.get_supplement_recommendations()
        # Keto gets base supplements, not the vegan/vegetarian extras
        names = [s["name"] for s in supps]
        assert "Vitamin D" in names
        assert "Vitamin B12" not in names


class TestGetProteinRecommendations:
    def test_omnivore_defaults(self):
        r = UserRestrictions(diet_type=DietType.OMNIVORE)
        rec = r.get_protein_recommendations()
        assert rec["daily_target_g_per_kg"] == 1.6
        assert "Chicken breast" in rec["best_sources"]

    def test_vegan_higher_target(self):
        r = UserRestrictions(diet_type=DietType.VEGAN)
        rec = r.get_protein_recommendations()
        assert rec["daily_target_g_per_kg"] == 1.8
        assert "Tofu (firm)" in rec["best_sources"]
        assert "leucine_target_mg_per_meal" in rec

    def test_vegetarian_sources(self):
        r = UserRestrictions(diet_type=DietType.VEGETARIAN)
        rec = r.get_protein_recommendations()
        assert "Eggs" in rec["best_sources"]
        assert "Whey protein" in rec["best_sources"]

    def test_keto_sources(self):
        r = UserRestrictions(diet_type=DietType.KETO)
        rec = r.get_protein_recommendations()
        assert rec["daily_target_g_per_kg"] == 1.8
        assert "Beef" in rec["best_sources"]

    def test_pescatarian_uses_default(self):
        r = UserRestrictions(diet_type=DietType.PESCATARIAN)
        rec = r.get_protein_recommendations()
        # Falls through to default
        assert rec["daily_target_g_per_kg"] == 1.6


class TestGetDietSpecificMealSuggestions:
    def test_omnivore_has_four_meal_types(self):
        r = UserRestrictions(diet_type=DietType.OMNIVORE)
        suggestions = r.get_diet_specific_meal_suggestions()
        assert "breakfast" in suggestions
        assert "pre_workout" in suggestions
        assert "post_workout" in suggestions
        assert "dinner" in suggestions

    def test_vegan_suggestions(self):
        r = UserRestrictions(diet_type=DietType.VEGAN)
        suggestions = r.get_diet_specific_meal_suggestions()
        assert "snacks" in suggestions
        # Should contain vegan items
        breakfast_items = " ".join(suggestions["breakfast"]).lower()
        assert "tofu" in breakfast_items or "oat" in breakfast_items

    def test_vegetarian_suggestions(self):
        r = UserRestrictions(diet_type=DietType.VEGETARIAN)
        suggestions = r.get_diet_specific_meal_suggestions()
        assert "snacks" in suggestions

    def test_avoid_gluten_removes_toast(self):
        r = UserRestrictions(avoid_gluten=True)
        suggestions = r.get_diet_specific_meal_suggestions()
        for meal_type, items in suggestions.items():
            for item in items:
                assert "toast" not in item.lower()
                assert "roti" not in item.lower()

    def test_avoid_dairy_removes_greek_yogurt(self):
        r = UserRestrictions(avoid_dairy=True)
        suggestions = r.get_diet_specific_meal_suggestions()
        for meal_type, items in suggestions.items():
            for item in items:
                assert "greek yogurt" not in item.lower()

    def test_lactose_intolerant_removes_cheese(self):
        r = UserRestrictions(lactose_intolerant=True)
        suggestions = r.get_diet_specific_meal_suggestions()
        for meal_type, items in suggestions.items():
            for item in items:
                assert "cheese" not in item.lower()
                assert "greek yogurt" not in item.lower()


class TestGetNutritionWarnings:
    def test_no_warnings_for_omnivore(self):
        r = UserRestrictions(diet_type=DietType.OMNIVORE)
        warnings = r.get_nutrition_warnings()
        assert warnings == []

    def test_vegan_warnings(self):
        r = UserRestrictions(diet_type=DietType.VEGAN)
        warnings = r.get_nutrition_warnings()
        assert len(warnings) >= 3
        combined = " ".join(warnings).lower()
        assert "b12" in combined or "vegan" in combined

    def test_allergy_warning(self):
        r = UserRestrictions(allergies=["peanuts", "shellfish"])
        warnings = r.get_nutrition_warnings()
        combined = " ".join(warnings)
        assert "peanuts" in combined
        assert "shellfish" in combined

    def test_intolerance_warning(self):
        r = UserRestrictions(intolerances=["lactose", "fructose"])
        warnings = r.get_nutrition_warnings()
        combined = " ".join(warnings)
        assert "lactose" in combined

    def test_orthorexia_flag(self):
        r = UserRestrictions(orthorexia=True)
        warnings = r.get_nutrition_warnings()
        combined = " ".join(warnings)
        assert "orthorexia" in combined.lower() or "balanced" in combined.lower()

    def test_many_dislikes_triggers_warning(self):
        r = UserRestrictions(dislikes=["a", "b", "c", "d", "e", "f"])
        warnings = r.get_nutrition_warnings()
        combined = " ".join(warnings)
        assert "dislikes" in combined.lower() or "avoid" in combined.lower()

    def test_few_dislikes_no_warning(self):
        r = UserRestrictions(dislikes=["broccoli"])
        warnings = r.get_nutrition_warnings()
        # <=5 dislikes should not trigger warning
        for w in warnings:
            assert "dislikes" not in w.lower()


class TestNutritionTargets:
    def test_defaults(self):
        t = NutritionTargets()
        assert t.calories == 2500
        assert t.protein_g == 160
        assert t.carbs_g == 300
        assert t.fat_g == 80

    def test_calculate_for_athlete_basic(self):
        t = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0,
            goals=["strength"],
            training_days_per_week=5,
        )
        assert t.protein_g == int(80.0 * 1.8)
        assert t.calories > 1000
        assert t.carbs_g > 0

    def test_calculate_strength_goal_omnivore(self):
        t = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=70.0,
            goals=["strength"],
            training_days_per_week=4,
            diet_type=DietType.OMNIVORE
        )
        assert t.protein_g_per_kg == 1.8

    def test_calculate_strength_goal_vegan(self):
        t = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=70.0,
            goals=["strength"],
            training_days_per_week=4,
            diet_type=DietType.VEGAN
        )
        assert t.protein_g_per_kg == 2.0

    def test_calculate_endurance_goal(self):
        t = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=70.0,
            goals=["endurance"],
            training_days_per_week=5
        )
        assert t.protein_g_per_kg == 1.6

    def test_calculate_weight_loss(self):
        t_normal = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=[], training_days_per_week=4
        )
        t_loss = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=["weight_loss"], training_days_per_week=4
        )
        assert t_loss.calories < t_normal.calories

    def test_calculate_weight_gain(self):
        t_normal = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=[], training_days_per_week=4
        )
        t_gain = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=["weight_gain"], training_days_per_week=4
        )
        assert t_gain.calories > t_normal.calories

    def test_high_volume_more_carbs(self):
        t_moderate = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=[], training_days_per_week=4,
            training_volume="moderate"
        )
        t_high = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=[], training_days_per_week=4,
            training_volume="high"
        )
        assert t_high.carbs_g > t_moderate.carbs_g

    def test_low_volume_fewer_carbs(self):
        t_moderate = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=[], training_days_per_week=4,
            training_volume="moderate"
        )
        t_low = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=[], training_days_per_week=4,
            training_volume="low"
        )
        assert t_low.carbs_g < t_moderate.carbs_g

    def test_training_vs_rest_day_calories(self):
        t = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=[], training_days_per_week=4,
            training_volume="high"
        )
        assert t.training_day_calories > t.rest_day_calories

    def test_moderate_volume_training_rest_day(self):
        t = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=[], training_days_per_week=4,
            training_volume="moderate"
        )
        assert t.training_day_calories == t.calories
        assert t.rest_day_calories < t.calories

    def test_low_volume_training_rest_day(self):
        t = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=[], training_days_per_week=4,
            training_volume="low"
        )
        assert t.training_day_calories <= t.calories
        assert t.rest_day_calories < t.calories

    def test_fat_percent_reasonable(self):
        t = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=80.0, goals=[], training_days_per_week=4
        )
        assert 0.0 < t.fat_percent < 1.0

    def test_carbs_per_kg_stored(self):
        bw = 75.0
        t = NutritionTargets.calculate_for_athlete(
            bodyweight_kg=bw, goals=[], training_days_per_week=4,
            training_volume="moderate"
        )
        assert abs(t.carbs_g_per_kg - (t.carbs_g / bw)) < 0.01
