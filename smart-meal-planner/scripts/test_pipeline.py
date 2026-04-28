"""
End-to-end pipeline test — runs the full multi-agent system without the HTTP layer.
Useful for debugging and verifying the system works before starting the server.

Usage: python scripts/test_pipeline.py
"""

import os
import sys
import json
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

from backend.agents.orchestrator import MealPlanOrchestrator

# ─── Test Cases ───────────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "Diabetic Vegetarian",
        "input": {
            "user_id": "test_001",
            "diet_type": "veg",
            "calorie_limit": 1800,
            "allergies": ["gluten"],
            "health_conditions": ["diabetes"]
        }
    },
    {
        "name": "Vegan No Conditions",
        "input": {
            "user_id": "test_002",
            "diet_type": "vegan",
            "calorie_limit": 2200,
            "allergies": [],
            "health_conditions": []
        }
    },
    {
        "name": "Non-Veg Hypertension",
        "input": {
            "user_id": "test_003",
            "diet_type": "non-veg",
            "calorie_limit": 2000,
            "allergies": ["dairy"],
            "health_conditions": ["hypertension"]
        }
    }
]


def run_tests():
    orchestrator = MealPlanOrchestrator()

    for tc in TEST_CASES:
        print(f"\n{'='*60}")
        print(f"TEST: {tc['name']}")
        print(f"{'='*60}")

        try:
            result = orchestrator.run(tc["input"])

            mp = result["meal_plan"]
            print(f"Breakfast : {mp['breakfast']['name']} ({mp['breakfast']['calories']} cal)")
            print(f"Lunch     : {mp['lunch']['name']} ({mp['lunch']['calories']} cal)")
            print(f"Dinner    : {mp['dinner']['name']} ({mp['dinner']['calories']} cal)")
            print(f"Snack     : {mp['snack']['name']} ({mp['snack']['calories']} cal)")
            print(f"Total Cal : {mp['total_calories']} / {tc['input']['calorie_limit']}")
            print(f"Protein   : {mp['total_protein']}g")
            print(f"Score     : {result['personalization_score']:.1%}")
            print(f"Validation: {'PASS ✓' if result['validation_passed'] else 'FAIL ✗'}")
            if result["validation_notes"]:
                print(f"Notes     : {result['validation_notes']}")
            print(f"AI Notes  : {mp['notes'][:120]}...")

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("All tests complete.")


if __name__ == "__main__":
    run_tests()
