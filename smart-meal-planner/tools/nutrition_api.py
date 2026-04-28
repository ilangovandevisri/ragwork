"""
Nutrition API Tool — mock implementation that simulates an external nutrition database.
In production, replace with real API calls (e.g., Nutritionix, USDA FoodData Central).
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Mock nutrition database keyed by food name
NUTRITION_DB: Dict[str, Dict[str, Any]] = {
    "chicken breast": {"calories_per_100g": 165, "protein": 31, "carbs": 0, "fat": 3.6, "fiber": 0},
    "salmon": {"calories_per_100g": 208, "protein": 20, "carbs": 0, "fat": 13, "fiber": 0},
    "brown rice": {"calories_per_100g": 216, "protein": 5, "carbs": 45, "fat": 1.8, "fiber": 3.5},
    "quinoa": {"calories_per_100g": 222, "protein": 8, "carbs": 39, "fat": 3.5, "fiber": 5},
    "lentils": {"calories_per_100g": 230, "protein": 18, "carbs": 40, "fat": 0.8, "fiber": 16},
    "oats": {"calories_per_100g": 389, "protein": 17, "carbs": 66, "fat": 7, "fiber": 11},
    "eggs": {"calories_per_100g": 155, "protein": 13, "carbs": 1.1, "fat": 11, "fiber": 0},
    "spinach": {"calories_per_100g": 23, "protein": 2.9, "carbs": 3.6, "fat": 0.4, "fiber": 2.2},
    "avocado": {"calories_per_100g": 160, "protein": 2, "carbs": 9, "fat": 15, "fiber": 7},
    "greek yogurt": {"calories_per_100g": 59, "protein": 10, "carbs": 3.6, "fat": 0.4, "fiber": 0},
    "tofu": {"calories_per_100g": 76, "protein": 8, "carbs": 1.9, "fat": 4.8, "fiber": 0.3},
    "black beans": {"calories_per_100g": 132, "protein": 8.9, "carbs": 24, "fat": 0.5, "fiber": 8.7},
    "sweet potato": {"calories_per_100g": 86, "protein": 1.6, "carbs": 20, "fat": 0.1, "fiber": 3},
    "broccoli": {"calories_per_100g": 34, "protein": 2.8, "carbs": 7, "fat": 0.4, "fiber": 2.6},
    "almonds": {"calories_per_100g": 579, "protein": 21, "carbs": 22, "fat": 50, "fiber": 12.5},
    "chia seeds": {"calories_per_100g": 486, "protein": 17, "carbs": 42, "fat": 31, "fiber": 34},
    "turkey breast": {"calories_per_100g": 135, "protein": 30, "carbs": 0, "fat": 1, "fiber": 0},
    "tuna": {"calories_per_100g": 144, "protein": 30, "carbs": 0, "fat": 3.2, "fiber": 0},
}


def get_nutrition_info(food_name: str, grams: float = 100) -> Dict[str, Any]:
    """
    Retrieve nutrition info for a food item.
    
    Args:
        food_name: Name of the food
        grams: Serving size in grams (default 100g)
    
    Returns:
        Dict with nutrition facts scaled to serving size
    """
    food_key = food_name.lower().strip()
    
    # Try exact match first, then partial match
    data = NUTRITION_DB.get(food_key)
    if not data:
        for key in NUTRITION_DB:
            if food_key in key or key in food_key:
                data = NUTRITION_DB[key]
                break
    
    if not data:
        logger.warning(f"Food '{food_name}' not found in nutrition DB, using defaults.")
        return {
            "food": food_name,
            "serving_grams": grams,
            "calories": 150,
            "protein": 5,
            "carbs": 20,
            "fat": 5,
            "fiber": 2,
            "source": "estimated"
        }
    
    scale = grams / 100
    return {
        "food": food_name,
        "serving_grams": grams,
        "calories": round(data["calories_per_100g"] * scale, 1),
        "protein": round(data["protein"] * scale, 1),
        "carbs": round(data["carbs"] * scale, 1),
        "fat": round(data["fat"] * scale, 1),
        "fiber": round(data["fiber"] * scale, 1),
        "source": "mock_nutrition_db"
    }


def get_health_flags(health_conditions: list) -> Dict[str, Any]:
    """
    Returns dietary guidelines based on health conditions.
    Used by the Validation Agent to enforce health rules.
    """
    flags = {
        "max_sodium_mg": 2300,
        "max_sugar_g": 50,
        "min_fiber_g": 25,
        "preferred_tags": [],
        "avoid_tags": []
    }

    condition_rules = {
        "diabetes": {
            "max_sugar_g": 25,
            "min_fiber_g": 30,
            "preferred_tags": ["diabetes-friendly", "low-carb", "high-fiber"],
            "avoid_tags": ["high-sugar"]
        },
        "hypertension": {
            "max_sodium_mg": 1500,
            "preferred_tags": ["low-sodium", "heart-healthy"],
            "avoid_tags": ["high-sodium"]
        },
        "heart disease": {
            "preferred_tags": ["heart-healthy", "omega-3"],
            "avoid_tags": ["high-fat", "high-sodium"]
        },
        "obesity": {
            "max_sugar_g": 30,
            "preferred_tags": ["low-calorie", "high-fiber", "high-protein"],
            "avoid_tags": ["high-fat", "high-sugar"]
        }
    }

    for condition in health_conditions:
        rules = condition_rules.get(condition.lower(), {})
        for key, val in rules.items():
            if key in ("preferred_tags", "avoid_tags"):
                flags[key] = list(set(flags.get(key, []) + val))
            else:
                # Take the stricter (lower) limit
                if key in flags:
                    flags[key] = min(flags[key], val)
                else:
                    flags[key] = val

    return flags
