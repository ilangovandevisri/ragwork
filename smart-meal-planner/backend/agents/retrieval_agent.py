"""
Agent 2: Retrieval Agent
Uses the RAG pipeline to fetch relevant recipes from the vector database
based on user profile and meal type requirements.
"""

import logging
from typing import Dict, Any, List

from rag.pipeline import rag_query
from tools.calorie_calculator import calculate_meal_targets

logger = logging.getLogger(__name__)

AGENT_PROMPT = """
You are the Retrieval Agent for a Smart Meal Planner.
Your job is to:
1. Receive a user profile and meal type request
2. Query the RAG pipeline (FAISS vector store + LLM) to find the best matching recipe
3. Return structured recipe data for the Nutrition Planning Agent

Use semantic search to find recipes that match:
- Diet type (veg/non-veg/vegan)
- Meal type (breakfast/lunch/dinner/snack)
- Calorie targets
- Health conditions
- Allergen restrictions

Always return the most nutritionally appropriate option.
"""


class RetrievalAgent:
    """
    Retrieves recipes from the vector store using RAG for each meal slot.
    """

    def __init__(self):
        self.name = "RetrievalAgent"
        logger.info(f"[{self.name}] Initialized.")

    def retrieve_for_meal(
        self,
        user_profile: Dict[str, Any],
        meal_type: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Retrieve the best recipe for a specific meal type.
        
        Args:
            user_profile: Validated user profile from UserInputAgent
            meal_type: breakfast / lunch / dinner / snack
            query: Natural language query from UserInputAgent
        
        Returns:
            Recipe dict with full nutrition info
        """
        logger.info(f"[{self.name}] Retrieving {meal_type} for user {user_profile['user_id']}")

        # Calculate per-meal calorie target
        targets = calculate_meal_targets(user_profile["calorie_limit"])
        calorie_target = targets.get(meal_type, 400)

        # Call RAG pipeline
        result = rag_query(
            user_query=query,
            diet_type=user_profile["diet_type"],
            meal_type=meal_type,
            allergies=user_profile["allergies"],
            health_conditions=user_profile["health_conditions"],
            calorie_target=calorie_target
        )

        if "error" in result:
            logger.warning(f"[{self.name}] RAG returned error for {meal_type}: {result['error']}")
            # Return a safe fallback
            return self._fallback_recipe(meal_type, calorie_target, user_profile["diet_type"])

        logger.info(f"[{self.name}] Retrieved: {result.get('name')} for {meal_type}")
        return result

    def retrieve_full_day(self, user_profile: Dict[str, Any], queries: Dict[str, str]) -> Dict[str, Any]:
        """
        Retrieve recipes for all four meal slots.
        
        Args:
            user_profile: Validated user profile
            queries: Dict mapping meal_type → query string
        
        Returns:
            Dict mapping meal_type → recipe dict
        """
        meals = {}
        for meal_type in ["breakfast", "lunch", "dinner", "snack"]:
            query = queries.get(meal_type, f"healthy {meal_type}")
            meals[meal_type] = self.retrieve_for_meal(user_profile, meal_type, query)

        logger.info(f"[{self.name}] Full day retrieval complete for user {user_profile['user_id']}")
        return meals

    def _fallback_recipe(self, meal_type: str, calorie_target: int, diet_type: str) -> Dict[str, Any]:
        """
        Returns a generic fallback recipe when RAG retrieval fails.
        This ensures the pipeline never breaks due to missing data.
        """
        fallbacks = {
            "breakfast": {
                "name": "Simple Oatmeal",
                "type": "breakfast",
                "calories": 300,
                "protein": 8,
                "carbs": 54,
                "fat": 5,
                "fiber": 6,
                "allergens": ["gluten"],
                "health_tags": ["balanced"],
                "ingredients": ["oats", "water", "banana"],
                "instructions": "Cook oats in water, top with banana.",
                "llm_reasoning": "Fallback recipe used."
            },
            "lunch": {
                "name": "Mixed Salad",
                "type": "lunch",
                "calories": 350,
                "protein": 10,
                "carbs": 40,
                "fat": 12,
                "fiber": 8,
                "allergens": [],
                "health_tags": ["balanced", "heart-healthy"],
                "ingredients": ["mixed greens", "chickpeas", "olive oil", "lemon"],
                "instructions": "Toss greens with chickpeas and dressing.",
                "llm_reasoning": "Fallback recipe used."
            },
            "dinner": {
                "name": "Steamed Vegetables with Rice",
                "type": "dinner",
                "calories": 400,
                "protein": 12,
                "carbs": 70,
                "fat": 6,
                "fiber": 8,
                "allergens": [],
                "health_tags": ["balanced"],
                "ingredients": ["brown rice", "broccoli", "carrots", "soy sauce"],
                "instructions": "Steam vegetables, serve over rice.",
                "llm_reasoning": "Fallback recipe used."
            },
            "snack": {
                "name": "Fresh Fruit",
                "type": "snack",
                "calories": 150,
                "protein": 2,
                "carbs": 35,
                "fat": 0.5,
                "fiber": 4,
                "allergens": [],
                "health_tags": ["balanced"],
                "ingredients": ["apple", "orange"],
                "instructions": "Eat fresh fruit.",
                "llm_reasoning": "Fallback recipe used."
            }
        }
        return fallbacks.get(meal_type, fallbacks["snack"])
