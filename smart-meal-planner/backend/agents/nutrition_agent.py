"""
Agent 3: Nutrition Planning Agent
Takes retrieved recipes and assembles a balanced daily meal plan,
ensuring proper calorie distribution and nutrient balance.
"""

import os
import logging
from typing import Dict, Any, List

from tools.calorie_calculator import (
    calculate_meal_targets,
    calculate_macro_balance,
    score_meal_plan
)

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")

AGENT_PROMPT = """
You are the Nutrition Planning Agent for a Smart Meal Planner.
Your job is to:
1. Receive retrieved recipes for each meal slot (breakfast, lunch, dinner, snack)
2. Assemble them into a coherent daily meal plan
3. Verify calorie distribution matches targets (25/35/30/10 split)
4. Calculate total macronutrients (protein, carbs, fat, fiber)
5. Generate personalized nutritional notes for the user
6. Return a complete, structured meal plan

Always prioritize:
- Meeting the user's calorie target (±10% tolerance)
- Adequate protein intake (minimum 50g/day)
- Sufficient fiber (minimum 25g/day)
- Balanced macronutrient ratios
"""


class NutritionAgent:
    """
    Assembles and enriches the daily meal plan with nutritional analysis.
    """

    def __init__(self):
        self.name = "NutritionAgent"
        logger.info(f"[{self.name}] Initialized.")

    def build_meal_plan(
        self,
        retrieved_meals: Dict[str, Any],
        user_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assemble a complete daily meal plan from retrieved recipes.
        
        Args:
            retrieved_meals: Dict mapping meal_type → recipe dict
            user_profile: Validated user profile
        
        Returns:
            Complete meal plan dict with totals and notes
        """
        logger.info(f"[{self.name}] Building meal plan for user {user_profile['user_id']}")

        targets = calculate_meal_targets(user_profile["calorie_limit"])

        # Build structured meal plan
        plan = {}
        for meal_type in ["breakfast", "lunch", "dinner", "snack"]:
            recipe = retrieved_meals.get(meal_type, {})
            plan[meal_type] = {
                "name": recipe.get("name", "Unknown"),
                "calories": recipe.get("calories", 0),
                "protein": recipe.get("protein", 0),
                "carbs": recipe.get("carbs", 0),
                "fat": recipe.get("fat", 0),
                "fiber": recipe.get("fiber", 0),
                "ingredients": recipe.get("ingredients", []),
                "instructions": recipe.get("instructions", ""),
                "health_tags": recipe.get("health_tags", []),
                "calorie_target": targets.get(meal_type, 0)
            }

        # Calculate totals
        totals = {
            "calories": sum(plan[m]["calories"] for m in plan),
            "protein": round(sum(plan[m]["protein"] for m in plan), 1),
            "carbs": round(sum(plan[m]["carbs"] for m in plan), 1),
            "fat": round(sum(plan[m]["fat"] for m in plan), 1),
            "fiber": round(sum(plan[m]["fiber"] for m in plan), 1)
        }

        # Macro balance analysis
        macro_analysis = calculate_macro_balance(plan)

        # Generate nutritional notes
        notes = self._generate_notes(totals, user_profile, macro_analysis)

        # Compute personalization score
        p_score = score_meal_plan(plan, user_profile)

        result = {
            "breakfast": plan["breakfast"],
            "lunch": plan["lunch"],
            "dinner": plan["dinner"],
            "snack": plan["snack"],
            "total_calories": totals["calories"],
            "total_protein": totals["protein"],
            "total_carbs": totals["carbs"],
            "total_fat": totals["fat"],
            "total_fiber": totals["fiber"],
            "macro_balance": macro_analysis["balance"],
            "notes": notes,
            "personalization_score": p_score
        }

        logger.info(
            f"[{self.name}] Plan built: {totals['calories']} cal, "
            f"score={p_score}, user={user_profile['user_id']}"
        )
        return result

    def _generate_notes(
        self,
        totals: Dict[str, float],
        user_profile: Dict[str, Any],
        macro_analysis: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable nutritional notes using LLM or rule-based logic.
        """
        notes_parts = []
        calorie_limit = user_profile["calorie_limit"]
        diff = totals["calories"] - calorie_limit

        # Calorie note
        if abs(diff) <= calorie_limit * 0.05:
            notes_parts.append(f"Calorie target met ({totals['calories']} / {calorie_limit} kcal).")
        elif diff > 0:
            notes_parts.append(f"Slightly over calorie target by {diff} kcal. Consider smaller portions.")
        else:
            notes_parts.append(f"Slightly under calorie target by {abs(diff)} kcal. Consider a larger snack.")

        # Protein note
        if totals["protein"] < 50:
            notes_parts.append("Protein intake is low. Consider adding a protein-rich snack.")
        elif totals["protein"] > 120:
            notes_parts.append(f"High protein intake ({totals['protein']}g) — great for muscle maintenance.")
        else:
            notes_parts.append(f"Protein intake is adequate ({totals['protein']}g).")

        # Fiber note
        if totals["fiber"] < 25:
            notes_parts.append("Fiber is below recommended 25g. Add more vegetables or legumes.")
        else:
            notes_parts.append(f"Fiber intake is good ({totals['fiber']}g).")

        # Health condition specific notes
        for condition in user_profile.get("health_conditions", []):
            if condition == "diabetes":
                notes_parts.append("Meals selected are low-glycemic and diabetes-friendly.")
            elif condition == "hypertension":
                notes_parts.append("Low-sodium options prioritized for blood pressure management.")
            elif condition == "heart disease":
                notes_parts.append("Heart-healthy, omega-3 rich options included.")

        # Use LLM for enhanced notes if available
        if LLM_PROVIDER == "openai":
            try:
                llm_note = self._llm_notes(totals, user_profile)
                if llm_note:
                    notes_parts.append(llm_note)
            except Exception as e:
                logger.warning(f"[{self.name}] LLM notes failed: {e}")

        return " ".join(notes_parts)

    def _llm_notes(self, totals: Dict, user_profile: Dict) -> str:
        """Generate a personalized tip using the LLM."""
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.5, max_tokens=100)
        prompt = (
            f"Give one short, personalized nutrition tip (max 20 words) for a {user_profile['diet_type']} "
            f"user with {', '.join(user_profile.get('health_conditions', ['no conditions']))} "
            f"who consumed {totals['calories']} calories, {totals['protein']}g protein today."
        )
        response = llm.invoke(prompt)
        return response.content.strip()
