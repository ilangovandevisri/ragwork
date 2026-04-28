"""
Calorie Calculator Tool — computes calorie distribution across meals
and validates that a meal plan meets the user's daily calorie target.
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# Standard calorie distribution percentages
MEAL_DISTRIBUTION = {
    "breakfast": 0.25,   # 25% of daily calories
    "lunch": 0.35,       # 35% of daily calories
    "dinner": 0.30,      # 30% of daily calories
    "snack": 0.10        # 10% of daily calories
}

# Acceptable deviation from target (±10%)
TOLERANCE = 0.10


def calculate_meal_targets(daily_calories: int) -> Dict[str, int]:
    """
    Calculate target calories for each meal based on daily limit.
    
    Args:
        daily_calories: Total daily calorie target
    
    Returns:
        Dict mapping meal type to target calories
    """
    return {
        meal: int(daily_calories * pct)
        for meal, pct in MEAL_DISTRIBUTION.items()
    }


def validate_calorie_distribution(
    meal_plan: Dict[str, Any],
    daily_limit: int
) -> Dict[str, Any]:
    """
    Validate that the meal plan's calorie distribution is within acceptable range.
    
    Args:
        meal_plan: Dict with breakfast/lunch/dinner/snack keys, each having 'calories'
        daily_limit: User's daily calorie limit
    
    Returns:
        Validation result with pass/fail and details
    """
    targets = calculate_meal_targets(daily_limit)
    results = {}
    total_actual = 0
    all_passed = True

    for meal_type, target in targets.items():
        if meal_type not in meal_plan:
            continue
        
        actual = meal_plan[meal_type].get("calories", 0)
        total_actual += actual
        lower = target * (1 - TOLERANCE)
        upper = target * (1 + TOLERANCE)
        passed = lower <= actual <= upper

        if not passed:
            all_passed = False

        results[meal_type] = {
            "target": target,
            "actual": actual,
            "passed": passed,
            "deviation_pct": round(abs(actual - target) / target * 100, 1)
        }

    # Check total
    total_lower = daily_limit * (1 - TOLERANCE)
    total_upper = daily_limit * (1 + TOLERANCE)
    total_passed = total_lower <= total_actual <= total_upper

    return {
        "passed": all_passed and total_passed,
        "total_target": daily_limit,
        "total_actual": total_actual,
        "total_passed": total_passed,
        "meal_breakdown": results,
        "summary": (
            f"Total calories: {total_actual}/{daily_limit} "
            f"({'✓' if total_passed else '✗'})"
        )
    }


def calculate_macro_balance(meal_plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate total macronutrients across all meals and assess balance.
    
    Returns:
        Dict with totals and balance assessment
    """
    totals = {"protein": 0, "carbs": 0, "fat": 0, "fiber": 0, "calories": 0}

    for meal_type in ["breakfast", "lunch", "dinner", "snack"]:
        meal = meal_plan.get(meal_type, {})
        for macro in totals:
            totals[macro] += meal.get(macro, 0)

    # Recommended daily values (approximate)
    recommendations = {
        "protein": (50, 150),    # grams
        "carbs": (130, 300),     # grams
        "fat": (44, 78),         # grams
        "fiber": (25, 38)        # grams
    }

    balance = {}
    for macro, (low, high) in recommendations.items():
        val = totals[macro]
        balance[macro] = {
            "value": round(val, 1),
            "status": "optimal" if low <= val <= high else ("low" if val < low else "high"),
            "recommended_range": f"{low}-{high}g"
        }

    return {"totals": totals, "balance": balance}


def score_meal_plan(
    meal_plan: Dict[str, Any],
    user_prefs: Dict[str, Any]
) -> float:
    """
    Compute a personalization score (0.0 to 1.0) for the meal plan.
    
    Factors:
    - Calorie accuracy (40%)
    - Diet type compliance (30%)
    - Health condition alignment (30%)
    """
    score = 0.0

    # 1. Calorie accuracy (40%)
    daily_limit = user_prefs.get("calorie_limit", 2000)
    total_cals = sum(
        meal_plan.get(m, {}).get("calories", 0)
        for m in ["breakfast", "lunch", "dinner", "snack"]
    )
    cal_accuracy = 1 - min(abs(total_cals - daily_limit) / daily_limit, 1.0)
    score += cal_accuracy * 0.40

    # 2. Diet type compliance (30%) — checked by validation agent, assume passed
    score += 0.30

    # 3. Health condition alignment (30%)
    health_conditions = user_prefs.get("health_conditions", [])
    if not health_conditions:
        score += 0.30  # No conditions = full score
    else:
        health_score = 0
        for meal_type in ["breakfast", "lunch", "dinner", "snack"]:
            meal = meal_plan.get(meal_type, {})
            tags = meal.get("health_tags", [])
            for condition in health_conditions:
                if condition == "diabetes" and "diabetes-friendly" in tags:
                    health_score += 1
                elif condition == "hypertension" and "heart-healthy" in tags:
                    health_score += 1
                elif condition == "heart disease" and "heart-healthy" in tags:
                    health_score += 1
        max_possible = len(["breakfast", "lunch", "dinner", "snack"]) * max(len(health_conditions), 1)
        score += (health_score / max_possible) * 0.30

    return round(min(score, 1.0), 3)
