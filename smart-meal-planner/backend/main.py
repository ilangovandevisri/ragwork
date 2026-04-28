"""
FastAPI Backend — Smart Meal Planner
Exposes three endpoints:
  POST /user-input   → Save user preferences
  GET  /meal-plan    → Generate and return a meal plan
  POST /feedback     → Submit feedback on a meal plan
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import (
    UserInputRequest, MealPlanResponse, FeedbackRequest, FeedbackResponse,
    HealthCheckResponse, UserPreferenceDB, MealPlanDB, FeedbackDB, DailyMealPlan, MealItem
)
from backend.database import get_db, init_db
from backend.agents.orchestrator import MealPlanOrchestrator


os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log")
    ]
)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Smart Meal Planner API started.")
    yield


app = FastAPI(
    title="Smart Meal Planner API",
    description="AI-powered multi-agent meal planning system using MCP and RAG",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Singleton orchestrator (agents are stateless, safe to reuse)
orchestrator = MealPlanOrchestrator()




@app.get("/health", response_model=HealthCheckResponse, tags=["System"])
def health_check():
    """Check if the API is running."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/user-input", tags=["User"])
def save_user_input(request: UserInputRequest, db: Session = Depends(get_db)):
    """
    Save or update user dietary preferences.
    
    This is the first step — call this before requesting a meal plan.
    """
    logger.info(f"POST /user-input — user_id={request.user_id}")

    # Upsert user preferences
    existing = db.query(UserPreferenceDB).filter_by(user_id=request.user_id).first()

    if existing:
        existing.diet_type = request.diet_type
        existing.calorie_limit = request.calorie_limit
        existing.allergies = request.allergies
        existing.health_conditions = request.health_conditions
        existing.updated_at = datetime.utcnow()
        db.commit()
        return {"message": "User preferences updated.", "user_id": request.user_id}
    else:
        pref = UserPreferenceDB(
            user_id=request.user_id,
            diet_type=request.diet_type,
            calorie_limit=request.calorie_limit,
            allergies=request.allergies,
            health_conditions=request.health_conditions
        )
        db.add(pref)
        db.commit()
        return {"message": "User preferences saved.", "user_id": request.user_id}


@app.get("/meal-plan", response_model=MealPlanResponse, tags=["Meal Plan"])
def get_meal_plan(
    user_id: str = Query(..., description="User ID to generate meal plan for"),
    db: Session = Depends(get_db)
):
    """
    Generate a personalized meal plan for the given user.
    
    Requires the user to have submitted preferences via POST /user-input first.
    Runs the full multi-agent pipeline: Input → Retrieval → Nutrition → Validation.
    """
    logger.info(f"GET /meal-plan — user_id={user_id}")

    # Load user preferences from DB
    pref = db.query(UserPreferenceDB).filter_by(user_id=user_id).first()
    if not pref:
        raise HTTPException(
            status_code=404,
            detail=f"No preferences found for user '{user_id}'. Call POST /user-input first."
        )

    
    raw_input = {
        "user_id": pref.user_id,
        "diet_type": pref.diet_type,
        "calorie_limit": pref.calorie_limit,
        "allergies": pref.allergies or [],
        "health_conditions": pref.health_conditions or []
    }

    
    try:
        result = orchestrator.run(raw_input)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Pipeline error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Meal plan generation failed. Check logs.")

   
    plan_record = MealPlanDB(
        user_id=user_id,
        plan=result["meal_plan"],
        total_calories=result["meal_plan"]["total_calories"],
        personalization_score=result["personalization_score"]
    )
    db.add(plan_record)
    db.commit()
    db.refresh(plan_record)

  
    mp = result["meal_plan"]

    def to_meal_item(meal_dict: dict) -> MealItem:
        return MealItem(
            name=meal_dict["name"],
            calories=meal_dict["calories"],
            protein=meal_dict["protein"],
            carbs=meal_dict["carbs"],
            fat=meal_dict["fat"],
            fiber=meal_dict["fiber"],
            ingredients=meal_dict["ingredients"],
            instructions=meal_dict["instructions"],
            health_tags=meal_dict["health_tags"]
        )

    daily_plan = DailyMealPlan(
        breakfast=to_meal_item(mp["breakfast"]),
        lunch=to_meal_item(mp["lunch"]),
        dinner=to_meal_item(mp["dinner"]),
        snack=to_meal_item(mp["snack"]),
        total_calories=mp["total_calories"],
        total_protein=mp["total_protein"],
        total_carbs=mp["total_carbs"],
        total_fat=mp["total_fat"],
        notes=mp["notes"]
    )

    return MealPlanResponse(
        user_id=result["user_id"],
        meal_plan=daily_plan,
        personalization_score=result["personalization_score"],
        validation_passed=result["validation_passed"],
        validation_notes=result["validation_notes"],
        generated_at=result["generated_at"]
    )


@app.post("/feedback", response_model=FeedbackResponse, tags=["Feedback"])
def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """
    Submit feedback on a generated meal plan.
    
    Rating: 1 (poor) to 5 (excellent).
    Feedback is stored and can be used to improve future recommendations.
    """
    logger.info(f"POST /feedback — user_id={request.user_id}, rating={request.rating}")

    feedback = FeedbackDB(
        user_id=request.user_id,
        meal_plan_id=request.meal_plan_id,
        rating=request.rating,
        comments=request.comments
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return FeedbackResponse(
        message=f"Thank you for your feedback! Rating {request.rating}/5 recorded.",
        feedback_id=feedback.id
    )


@app.get("/history/{user_id}", tags=["User"])
def get_user_history(user_id: str, db: Session = Depends(get_db)):
    """Get the last 5 meal plans generated for a user."""
    plans = (
        db.query(MealPlanDB)
        .filter_by(user_id=user_id)
        .order_by(MealPlanDB.created_at.desc())
        .limit(5)
        .all()
    )
    if not plans:
        raise HTTPException(status_code=404, detail=f"No history found for user '{user_id}'.")

    return [
        {
            "id": p.id,
            "total_calories": p.total_calories,
            "personalization_score": p.personalization_score,
            "created_at": p.created_at.isoformat()
        }
        for p in plans
    ]
