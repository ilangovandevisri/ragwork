"""
Multi-Agent Orchestrator (MCP Controller)
Coordinates the four agents in sequence:
  UserInputAgent → RetrievalAgent → NutritionAgent → ValidationAgent

Also handles retry logic if validation fails.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from backend.agents.user_input_agent import UserInputAgent
from backend.agents.retrieval_agent import RetrievalAgent
from backend.agents.nutrition_agent import NutritionAgent
from backend.agents.validation_agent import ValidationAgent

logger = logging.getLogger(__name__)

MAX_RETRIES = 2  # Max times to retry if validation fails


class MealPlanOrchestrator:
    """
    Orchestrates the full multi-agent meal planning pipeline.
    
    Pipeline:
    1. UserInputAgent  → validates & normalizes user input
    2. RetrievalAgent  → fetches recipes via RAG for each meal slot
    3. NutritionAgent  → assembles and analyzes the daily meal plan
    4. ValidationAgent → validates safety, allergens, diet, calories
    
    If validation fails, retries retrieval up to MAX_RETRIES times.
    """

    def __init__(self):
        self.user_input_agent = UserInputAgent()
        self.retrieval_agent = RetrievalAgent()
        self.nutrition_agent = NutritionAgent()
        self.validation_agent = ValidationAgent()
        logger.info("[Orchestrator] All agents initialized.")

    def run(self, raw_user_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the full meal planning pipeline.
        
        Args:
            raw_user_input: Raw user preferences dict
        
        Returns:
            Complete meal plan response dict
        
        Raises:
            ValueError: If user input is invalid
            RuntimeError: If pipeline fails after all retries
        """
        logger.info("[Orchestrator] Starting meal planning pipeline.")

        # ── Step 1: User Input Agent ─────────────────────────────────────────
        logger.info("[Orchestrator] Step 1: User Input Agent")
        user_profile = self.user_input_agent.process(raw_user_input)

        # Generate queries for each meal type
        queries = {
            meal_type: self.user_input_agent.generate_query(user_profile, meal_type)
            for meal_type in ["breakfast", "lunch", "dinner", "snack"]
        }
        logger.debug(f"[Orchestrator] Generated queries: {queries}")

        # ── Steps 2-4: Retrieval → Nutrition → Validation (with retry) ───────
        last_errors = []
        for attempt in range(1, MAX_RETRIES + 2):
            logger.info(f"[Orchestrator] Attempt {attempt}/{MAX_RETRIES + 1}")

            # Step 2: Retrieval Agent
            logger.info("[Orchestrator] Step 2: Retrieval Agent")
            retrieved_meals = self.retrieval_agent.retrieve_full_day(user_profile, queries)

            # Step 3: Nutrition Agent
            logger.info("[Orchestrator] Step 3: Nutrition Agent")
            meal_plan = self.nutrition_agent.build_meal_plan(retrieved_meals, user_profile)

            # Step 4: Validation Agent
            logger.info("[Orchestrator] Step 4: Validation Agent")
            passed, errors, warnings = self.validation_agent.validate(meal_plan, user_profile)

            if passed:
                logger.info(f"[Orchestrator] Validation passed on attempt {attempt}.")
                break

            last_errors = errors
            logger.warning(
                f"[Orchestrator] Validation failed (attempt {attempt}): {errors}"
            )

            if attempt > MAX_RETRIES:
                # Deliver plan anyway with error notes (don't block user completely)
                logger.error("[Orchestrator] Max retries exceeded. Delivering plan with warnings.")
                warnings = errors + warnings
                passed = False
                break

            # Modify queries slightly for retry to get different recipes
            queries = {
                meal_type: query + " alternative healthy option"
                for meal_type, query in queries.items()
            }

        # ── Build final response ─────────────────────────────────────────────
        response = {
            "user_id": user_profile["user_id"],
            "meal_plan": {
                "breakfast": meal_plan["breakfast"],
                "lunch": meal_plan["lunch"],
                "dinner": meal_plan["dinner"],
                "snack": meal_plan["snack"],
                "total_calories": meal_plan["total_calories"],
                "total_protein": meal_plan["total_protein"],
                "total_carbs": meal_plan["total_carbs"],
                "total_fat": meal_plan["total_fat"],
                "notes": meal_plan["notes"]
            },
            "personalization_score": meal_plan.get("personalization_score", 0.0),
            "validation_passed": passed,
            "validation_notes": warnings,
            "generated_at": datetime.utcnow().isoformat()
        }

        logger.info(
            f"[Orchestrator] Pipeline complete. "
            f"User: {user_profile['user_id']}, "
            f"Score: {meal_plan.get('personalization_score')}, "
            f"Validation: {'PASS' if passed else 'FAIL'}"
        )

        return response
