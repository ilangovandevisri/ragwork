"""
Agent 4: Validation Agent
Ensures the generated meal plan is safe, policy-compliant, allergen-free,
and within the user's calorie limits before returning it to the user.
"""

import logging
from typing import Dict, Any, List, Tuple

from tools.nutrition_api import get_health_flags
from tools.calorie_calculator import validate_calorie_distribution

logger = logging.getLogger(__name__)

AGENT_PROMPT = """
You are the Validation Agent for a Smart Meal Planner.
Your job is to act as the final safety gate before a meal plan is delivered to the user.

You MUST verify:
1. No allergens present in any meal (hard block)
2. Diet type compliance (veg/vegan/non-veg rules strictly enforced)
3. Calorie limits satisfied (within ±10% tolerance)
4. Health condition policy compliance (e.g., diabetes → low-sugar meals)
5. Minimum nutritional standards met (protein ≥ 50g, fiber ≥ 20g)

If any hard constraint fails, flag it clearly.
If soft constraints fail, add warnings but allow the plan through.
"""

# Ingredients/tags that indicate non-veg content
NON_VEG_INDICATORS = {
    "chicken", "beef", "pork", "lamb", "turkey", "fish", "tuna", "salmon",
    "shrimp", "prawn", "crab", "lobster", "meat", "bacon", "ham", "sausage"
}

# Ingredients/tags that indicate non-vegan content (dairy/eggs)
NON_VEGAN_INDICATORS = {
    "milk", "cheese", "butter", "cream", "yogurt", "whey", "egg", "eggs",
    "honey", "dairy", "ghee"
}


class ValidationAgent:
    """
    Validates the meal plan against all user constraints and health policies.
    """

    def __init__(self):
        self.name = "ValidationAgent"
        logger.info(f"[{self.name}] Initialized.")

    def validate(
        self,
        meal_plan: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Run all validation checks on the meal plan.
        
        Args:
            meal_plan: Complete meal plan from NutritionAgent
            user_profile: Validated user profile
        
        Returns:
            Tuple of (passed: bool, errors: List[str], warnings: List[str])
        """
        logger.info(f"[{self.name}] Validating plan for user {user_profile['user_id']}")

        errors = []    # Hard failures — plan should be regenerated
        warnings = []  # Soft issues — plan can still be delivered

        meal_types = ["breakfast", "lunch", "dinner", "snack"]

        # ── Check 1: Allergen compliance ────────────────────────────────────
        allergen_errors = self._check_allergens(meal_plan, user_profile["allergies"], meal_types)
        errors.extend(allergen_errors)

        # ── Check 2: Diet type compliance ───────────────────────────────────
        diet_errors = self._check_diet_compliance(meal_plan, user_profile["diet_type"], meal_types)
        errors.extend(diet_errors)

        # ── Check 3: Calorie distribution ───────────────────────────────────
        cal_result = validate_calorie_distribution(meal_plan, user_profile["calorie_limit"])
        if not cal_result["total_passed"]:
            warnings.append(
                f"Total calories ({cal_result['total_actual']}) deviate from target "
                f"({cal_result['total_target']}) by more than 10%."
            )

        # ── Check 4: Health condition policies ──────────────────────────────
        health_warnings = self._check_health_policies(meal_plan, user_profile, meal_types)
        warnings.extend(health_warnings)

        # ── Check 5: Minimum nutrition standards ────────────────────────────
        nutrition_warnings = self._check_nutrition_minimums(meal_plan)
        warnings.extend(nutrition_warnings)

        passed = len(errors) == 0
        status = "PASSED" if passed else "FAILED"
        logger.info(
            f"[{self.name}] Validation {status} — "
            f"{len(errors)} errors, {len(warnings)} warnings"
        )

        return passed, errors, warnings

    def _check_allergens(
        self,
        meal_plan: Dict[str, Any],
        allergies: List[str],
        meal_types: List[str]
    ) -> List[str]:
        """Check that no meal contains user's allergens."""
        errors = []
        if not allergies:
            return errors

        for meal_type in meal_types:
            meal = meal_plan.get(meal_type, {})
            meal_allergens = [a.lower() for a in meal.get("allergens", [])]
            meal_ingredients = [i.lower() for i in meal.get("ingredients", [])]

            for allergen in allergies:
                allergen_lower = allergen.lower()
                # Check declared allergens
                if allergen_lower in meal_allergens:
                    errors.append(
                        f"ALLERGEN VIOLATION: {meal_type.capitalize()} '{meal.get('name')}' "
                        f"contains '{allergen}'."
                    )
                # Also check ingredients for safety
                elif any(allergen_lower in ing for ing in meal_ingredients):
                    errors.append(
                        f"ALLERGEN WARNING: {meal_type.capitalize()} '{meal.get('name')}' "
                        f"may contain '{allergen}' in ingredients."
                    )

        return errors

    def _check_diet_compliance(
        self,
        meal_plan: Dict[str, Any],
        diet_type: str,
        meal_types: List[str]
    ) -> List[str]:
        """Ensure meals comply with the user's diet type."""
        errors = []

        for meal_type in meal_types:
            meal = meal_plan.get(meal_type, {})
            ingredients = [i.lower() for i in meal.get("ingredients", [])]
            meal_name = meal.get("name", meal_type)

            if diet_type == "vegan":
                # Check for any animal products
                violations = [
                    ind for ind in (NON_VEG_INDICATORS | NON_VEGAN_INDICATORS)
                    if any(ind in ing for ing in ingredients)
                ]
                if violations:
                    errors.append(
                        f"DIET VIOLATION: {meal_type.capitalize()} '{meal_name}' "
                        f"contains non-vegan ingredient(s): {violations}"
                    )

            elif diet_type == "veg":
                # Check for meat/fish
                violations = [
                    ind for ind in NON_VEG_INDICATORS
                    if any(ind in ing for ing in ingredients)
                ]
                if violations:
                    errors.append(
                        f"DIET VIOLATION: {meal_type.capitalize()} '{meal_name}' "
                        f"contains non-vegetarian ingredient(s): {violations}"
                    )

        return errors

    def _check_health_policies(
        self,
        meal_plan: Dict[str, Any],
        user_profile: Dict[str, Any],
        meal_types: List[str]
    ) -> List[str]:
        """Check health condition-specific dietary rules."""
        warnings = []
        conditions = user_profile.get("health_conditions", [])

        if not conditions:
            return warnings

        health_flags = get_health_flags(conditions)
        preferred_tags = health_flags.get("preferred_tags", [])

        # Count how many meals have health-appropriate tags
        compliant_meals = 0
        for meal_type in meal_types:
            meal = meal_plan.get(meal_type, {})
            tags = meal.get("health_tags", [])
            if any(tag in tags for tag in preferred_tags):
                compliant_meals += 1

        compliance_rate = compliant_meals / len(meal_types)
        if compliance_rate < 0.5:
            warnings.append(
                f"Only {compliant_meals}/{len(meal_types)} meals are tagged as appropriate "
                f"for conditions: {', '.join(conditions)}. "
                f"Recommended tags: {', '.join(preferred_tags[:3])}"
            )

        return warnings

    def _check_nutrition_minimums(self, meal_plan: Dict[str, Any]) -> List[str]:
        """Check minimum daily nutritional standards."""
        warnings = []

        total_protein = meal_plan.get("total_protein", 0)
        total_fiber = meal_plan.get("total_fiber", 0)
        total_fat = meal_plan.get("total_fat", 0)

        if total_protein < 50:
            warnings.append(f"Low protein: {total_protein}g (recommended ≥ 50g/day).")
        if total_fiber < 20:
            warnings.append(f"Low fiber: {total_fiber}g (recommended ≥ 25g/day).")
        if total_fat < 20:
            warnings.append(f"Very low fat: {total_fat}g. Some healthy fats are essential.")

        return warnings
