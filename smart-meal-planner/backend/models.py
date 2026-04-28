"""
Pydantic models for request/response validation and SQLAlchemy ORM models.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.orm import DeclarativeBase



class Base(DeclarativeBase):
    pass


class UserPreferenceDB(Base):
    """Stores user dietary preferences in SQLite."""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    diet_type = Column(String)           # veg / non-veg / vegan
    calorie_limit = Column(Integer)
    allergies = Column(JSON)             # list of allergens
    health_conditions = Column(JSON)     # list of conditions
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MealPlanDB(Base):
    """Stores generated meal plans."""
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    plan = Column(JSON)                  # full meal plan dict
    total_calories = Column(Float)
    personalization_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class FeedbackDB(Base):
    """Stores user feedback on meal plans."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    meal_plan_id = Column(Integer)
    rating = Column(Integer)             # 1-5
    comments = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)




class UserInputRequest(BaseModel):
    """User dietary preferences submitted via POST /user-input."""
    user_id: str = Field(..., description="Unique user identifier")
    diet_type: str = Field(..., description="veg | non-veg | vegan")
    calorie_limit: int = Field(..., ge=1000, le=5000, description="Daily calorie target")
    allergies: List[str] = Field(default=[], description="List of allergens to avoid")
    health_conditions: List[str] = Field(default=[], description="e.g. diabetes, hypertension")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user_001",
                "diet_type": "veg",
                "calorie_limit": 1800,
                "allergies": ["gluten"],
                "health_conditions": ["diabetes"]
            }
        }
    }


class MealItem(BaseModel):
    """A single meal entry in the plan."""
    name: str
    calories: int
    protein: float
    carbs: float
    fat: float
    fiber: float
    ingredients: List[str]
    instructions: str
    health_tags: List[str]


class DailyMealPlan(BaseModel):
    """Full day meal plan."""
    breakfast: MealItem
    lunch: MealItem
    dinner: MealItem
    snack: MealItem
    total_calories: int
    total_protein: float
    total_carbs: float
    total_fat: float
    notes: str


class MealPlanResponse(BaseModel):
    """Response from GET /meal-plan."""
    user_id: str
    meal_plan: DailyMealPlan
    personalization_score: float = Field(..., description="0-1 score of how well plan fits user")
    validation_passed: bool
    validation_notes: List[str]
    generated_at: str


class FeedbackRequest(BaseModel):
    """User feedback submitted via POST /feedback."""
    user_id: str
    meal_plan_id: Optional[int] = None
    rating: int = Field(..., ge=1, le=5)
    comments: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "user_001",
                "rating": 4,
                "comments": "Great plan but I'd prefer more variety at breakfast."
            }
        }
    }


class FeedbackResponse(BaseModel):
    message: str
    feedback_id: int


class HealthCheckResponse(BaseModel):
    status: str
    version: str
