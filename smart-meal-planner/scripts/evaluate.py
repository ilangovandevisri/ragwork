"""
Evaluation Script — measures system performance metrics.

Metrics:
  1. Calorie Accuracy     — how close total calories are to target
  2. Allergen Safety Rate — % of plans with zero allergen violations
  3. Diet Compliance Rate — % of plans fully compliant with diet type
  4. Personalization Score — average AI personalization score
  5. Validation Pass Rate  — % of plans passing all checks

Usage: python scripts/evaluate.py
"""

import os
import sys
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from backend.agents.orchestrator import MealPlanOrchestrator

EVAL_CASES = [
    {"user_id": "eval_001", "diet_type": "veg",     "calorie_limit": 1800, "allergies": [],         "health_conditions": ["diabetes"]},
    {"user_id": "eval_002", "diet_type": "vegan",   "calorie_limit": 2000, "allergies": ["gluten"],  "health_conditions": []},
    {"user_id": "eval_003", "diet_type": "non-veg", "calorie_limit": 2200, "allergies": ["dairy"],   "health_conditions": ["hypertension"]},
    {"user_id": "eval_004", "diet_type": "veg",     "calorie_limit": 1600, "allergies": ["eggs"],    "health_conditions": ["obesity"]},
    {"user_id": "eval_005", "diet_type": "non-veg", "calorie_limit": 2500, "allergies": [],          "health_conditions": []},
]


def evaluate():
    orchestrator = MealPlanOrchestrator()

    calorie_accuracies = []
    allergen_safe = 0
    diet_compliant = 0
    p_scores = []
    validation_passed = 0

    print("Running evaluation on 5 test cases...\n")

    for case in EVAL_CASES:
        try:
            result = orchestrator.run(case)
            mp = result["meal_plan"]

            # Calorie accuracy
            target = case["calorie_limit"]
            actual = mp["total_calories"]
            accuracy = 1 - min(abs(actual - target) / target, 1.0)
            calorie_accuracies.append(accuracy)

            # Allergen safety (no allergen errors in validation notes)
            notes = result.get("validation_notes", [])
            has_allergen_error = any("ALLERGEN VIOLATION" in n for n in notes)
            if not has_allergen_error:
                allergen_safe += 1

            # Diet compliance
            has_diet_error = any("DIET VIOLATION" in n for n in notes)
            if not has_diet_error:
                diet_compliant += 1

            # Personalization score
            p_scores.append(result["personalization_score"])

            # Validation pass rate
            if result["validation_passed"]:
                validation_passed += 1

            print(
                f"  {case['user_id']}: cal={actual}/{target} "
                f"acc={accuracy:.0%} score={result['personalization_score']:.0%} "
                f"valid={'✓' if result['validation_passed'] else '✗'}"
            )

        except Exception as e:
            print(f"  {case['user_id']}: ERROR — {e}")

    n = len(EVAL_CASES)
    print(f"\n{'='*50}")
    print("EVALUATION RESULTS")
    print(f"{'='*50}")
    print(f"Calorie Accuracy     : {statistics.mean(calorie_accuracies):.1%}")
    print(f"Allergen Safety Rate : {allergen_safe}/{n} ({allergen_safe/n:.0%})")
    print(f"Diet Compliance Rate : {diet_compliant}/{n} ({diet_compliant/n:.0%})")
    print(f"Avg Personalization  : {statistics.mean(p_scores):.1%}")
    print(f"Validation Pass Rate : {validation_passed}/{n} ({validation_passed/n:.0%})")
    print(f"{'='*50}")


if __name__ == "__main__":
    evaluate()
