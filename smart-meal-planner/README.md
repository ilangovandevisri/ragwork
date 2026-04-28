# Smart Meal Planner — AI-Powered Multi-Agent System

An intelligent meal planning system using **Multi-Agent Collaboration (MCP)**, **Retrieval-Augmented Generation (RAG)**, and **FastAPI + Streamlit**.

---

## Architecture

```
User Browser
     │
     ▼
[Streamlit Frontend :8501]
     │  HTTP REST
     ▼
[FastAPI Backend :8000]
     │
     ├──► Agent 1: UserInputAgent   → validates preferences → SQLite
     ├──► Agent 2: RetrievalAgent   → RAG query → FAISS vector DB
     ├──► Agent 3: NutritionAgent   → assembles meal plan + macros
     └──► Agent 4: ValidationAgent  → allergen/diet/calorie checks
                                          │
                                    Tool Layer
                                    ├── nutrition_api.py (mock)
                                    └── calorie_calculator.py
```

---

## Folder Structure

```
smart-meal-planner/
├── backend/
│   ├── __init__.py
│   ├── main.py          # FastAPI app + endpoints
│   ├── models.py        # Pydantic + SQLAlchemy models
│   ├── database.py      # SQLite setup
│   └── agents/
│       ├── user_input_agent.py
│       ├── retrieval_agent.py
│       ├── nutrition_agent.py
│       ├── validation_agent.py
│       └── orchestrator.py
├── rag/
│   ├── embeddings.py    # OpenAI or HuggingFace embeddings
│   ├── vector_store.py  # FAISS index build/load
│   └── pipeline.py      # Full RAG pipeline
├── tools/
│   ├── nutrition_api.py      # Mock nutrition database
│   └── calorie_calculator.py # Calorie distribution + scoring
├── data/
│   └── recipes.json     # 20 recipes dataset
├── frontend/
│   └── app.py           # Streamlit UI
├── scripts/
│   ├── build_index.py   # Pre-build FAISS index
│   ├── test_pipeline.py # End-to-end pipeline test
│   └── evaluate.py      # Evaluation metrics
├── logs/                # Auto-created log files
├── main.py              # Server entry point
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup Instructions

### 1. Clone and install dependencies

```bash
cd smart-meal-planner
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:
- For **OpenAI** (best results): set `OPENAI_API_KEY=sk-...` and `LLM_PROVIDER=openai`
- For **local/free** testing: keep `LLM_PROVIDER=local` (uses HuggingFace embeddings + mock LLM)

### 3. Build the vector index (one-time)

```bash
python scripts/build_index.py
```

### 4. Start the backend

```bash
python main.py
```

API docs: http://localhost:8000/docs

### 5. Start the frontend (new terminal)

```bash
cd smart-meal-planner
streamlit run frontend/app.py
```

UI: http://localhost:8501

---

## API Examples

### Save user preferences
```bash
curl -X POST http://localhost:8000/user-input \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "alice",
    "diet_type": "veg",
    "calorie_limit": 1800,
    "allergies": ["gluten"],
    "health_conditions": ["diabetes"]
  }'
```

### Generate meal plan
```bash
curl "http://localhost:8000/meal-plan?user_id=alice"
```

### Submit feedback
```bash
curl -X POST http://localhost:8000/feedback \
  -H "Content-Type: application/json" \
  -d '{"user_id": "alice", "rating": 4, "comments": "Great variety!"}'
```

---

## Sample Output

```json
{
  "user_id": "alice",
  "meal_plan": {
    "breakfast": {
      "name": "Chia Pudding",
      "calories": 260,
      "protein": 8,
      "carbs": 32,
      "fat": 12,
      "health_tags": ["high-fiber", "omega-3", "diabetes-friendly"]
    },
    "lunch": {
      "name": "Lentil Soup",
      "calories": 380,
      "protein": 22,
      "carbs": 58,
      "fat": 4,
      "health_tags": ["high-fiber", "diabetes-friendly", "heart-healthy"]
    },
    "dinner": {
      "name": "Vegetable Stir Fry with Tofu",
      "calories": 380,
      "protein": 20,
      "carbs": 40,
      "fat": 14,
      "health_tags": ["high-protein", "balanced", "heart-healthy"]
    },
    "snack": {
      "name": "Hummus with Veggie Sticks",
      "calories": 160,
      "protein": 6,
      "carbs": 20,
      "fat": 7,
      "health_tags": ["high-fiber", "diabetes-friendly"]
    },
    "total_calories": 1180,
    "total_protein": 56,
    "notes": "Calorie target met. Protein adequate. Fiber is good. Meals selected are low-glycemic and diabetes-friendly."
  },
  "personalization_score": 0.82,
  "validation_passed": true,
  "validation_notes": []
}
```

---

## Running Tests

```bash
# End-to-end pipeline test (no HTTP)
python scripts/test_pipeline.py

# Evaluation metrics
python scripts/evaluate.py
```

---

## Future Improvements

1. **Optimization Agent** — iteratively refine plans based on user feedback history
2. **Weekly planning** — generate 7-day plans with variety enforcement
3. **Grocery list generation** — aggregate ingredients across the week
4. **Real nutrition API** — integrate Nutritionix or USDA FoodData Central
5. **User authentication** — JWT-based auth for multi-user production use
6. **Recipe image generation** — DALL-E integration for visual meal cards
7. **Portion size adjustment** — dynamic scaling based on BMI/activity level
8. **Multi-language support** — localized meal plans for different cuisines
