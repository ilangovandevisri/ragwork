"""
Agent 1: User Input Agent
Validates, normalizes, and stores user dietary preferences.
Acts as the entry point for the multi-agent pipeline.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Valid values for validation
VALID_DIET_TYPES = {"veg", "non-veg", "vegan"}
KNOWN_ALLERGENS = {"gluten", "dairy", "eggs", "nuts", "tree nuts", "soy", "fish", "shellfish", "sesame", "peanuts"}
KNOWN_CONDITIONS = {"diabetes", "hypertension", "heart disease", "obesity", "celiac", "lactose intolerance"}

# Prompt template for this agent (used for logging/transparency)
AGENT_PROMPT = """
You are the User Input Agent for a Smart Meal Planner.
Your job is to:
1. Validate user dietary preferences
2. Normalize input values (lowercase, trim whitespace)
3. Flag any inconsistencies or missing data
4. Return a clean, structured user profile for downstream agents

Always be strict about validation to prevent invalid data from entering the pipeline.
"""


class UserInputAgent:
    """
    Processes and validates raw user input before passing it to the pipeline.
    """

    def __init__(self):
        self.name = "UserInputAgent"
        logger.info(f"[{self.name}] Initialized.")

    def process(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize user input.
        
        Args:
            raw_input: Dict with user_id, diet_type, calorie_limit, allergies, health_conditions
        
        Returns:
            Cleaned user profile dict with validation metadata
        
        Raises:
            ValueError: If critical fields are invalid
        """
        logger.info(f"[{self.name}] Processing input for user: {raw_input.get('user_id')}")

        errors = []
        warnings = []

        # ── Validate diet type ──────────────────────────────────────────────
        diet_type = str(raw_input.get("diet_type", "")).lower().strip()
        if diet_type not in VALID_DIET_TYPES:
            errors.append(f"Invalid diet_type '{diet_type}'. Must be one of: {VALID_DIET_TYPES}")
        
        # ── Validate calorie limit ──────────────────────────────────────────
        calorie_limit = raw_input.get("calorie_limit", 0)
        try:
            calorie_limit = int(calorie_limit)
        except (TypeError, ValueError):
            errors.append("calorie_limit must be an integer.")
            calorie_limit = 2000

        if calorie_limit < 1000:
            warnings.append("Calorie limit below 1000 may be unsafe. Adjusted to 1200.")
            calorie_limit = 1200
        elif calorie_limit > 5000:
            warnings.append("Calorie limit above 5000 is unusually high. Capped at 4000.")
            calorie_limit = 4000

        # ── Normalize allergies ─────────────────────────────────────────────
        raw_allergies = raw_input.get("allergies", [])
        allergies = [a.lower().strip() for a in raw_allergies if a]
        unknown_allergens = [a for a in allergies if a not in KNOWN_ALLERGENS]
        if unknown_allergens:
            warnings.append(f"Unrecognized allergens (will still be respected): {unknown_allergens}")

        # ── Normalize health conditions ─────────────────────────────────────
        raw_conditions = raw_input.get("health_conditions", [])
        health_conditions = [c.lower().strip() for c in raw_conditions if c]
        unknown_conditions = [c for c in health_conditions if c not in KNOWN_CONDITIONS]
        if unknown_conditions:
            warnings.append(f"Unrecognized health conditions (will be noted): {unknown_conditions}")

        # ── Raise on hard errors ────────────────────────────────────────────
        if errors:
            logger.error(f"[{self.name}] Validation errors: {errors}")
            raise ValueError(f"Input validation failed: {'; '.join(errors)}")

        # ── Build clean profile ─────────────────────────────────────────────
        profile = {
            "user_id": str(raw_input.get("user_id", "anonymous")).strip(),
            "diet_type": diet_type,
            "calorie_limit": calorie_limit,
            "allergies": allergies,
            "health_conditions": health_conditions,
            "validation_warnings": warnings,
            "agent": self.name
        }

        logger.info(f"[{self.name}] Profile validated successfully. Warnings: {warnings}")
        return profile

    def generate_query(self, profile: Dict[str, Any], meal_type: str) -> str:
        """
        Generate a natural language query for the Retrieval Agent based on user profile.
        
        Args:
            profile: Validated user profile
            meal_type: breakfast / lunch / dinner / snack
        
        Returns:
            Query string for RAG retrieval
        """
        conditions_str = (
            f" suitable for {', '.join(profile['health_conditions'])}"
            if profile["health_conditions"] else ""
        )
        allergen_str = (
            f" without {', '.join(profile['allergies'])}"
            if profile["allergies"] else ""
        )
        return (
            f"Healthy {meal_type} recipe for {profile['diet_type']} diet"
            f"{conditions_str}{allergen_str}, "
            f"approximately {int(profile['calorie_limit'] * self._meal_ratio(meal_type))} calories"
        )

    @staticmethod
    def _meal_ratio(meal_type: str) -> float:
        ratios = {"breakfast": 0.25, "lunch": 0.35, "dinner": 0.30, "snack": 0.10}
        return ratios.get(meal_type, 0.25)
