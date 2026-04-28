"""
RAG Pipeline — query → retrieve → context → LLM → response.

This module ties together the vector store retrieval with LLM generation
to produce contextually grounded meal recommendations.
"""

import os
import logging
from typing import List, Dict, Any, Optional

from langchain_core.documents import Document

from rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")


def get_llm():
    """
    Returns the LLM instance based on LLM_PROVIDER.
    - "openai" → ChatOpenAI (gpt-4o-mini for cost efficiency)
    - "local"  → A simple mock LLM for testing without API key
    """
    if LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        logger.info("Using OpenAI ChatGPT (gpt-4o-mini).")
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=2000
        )

    # Mock LLM for local testing
    logger.info("Using MockLLM (no API key required).")
    return MockLLM()


class MockLLM:
    """
    Simple mock LLM that returns structured responses without an API call.
    Used for local development and testing.
    """
    def invoke(self, prompt: str) -> "MockResponse":
        return MockResponse(
            content="[MockLLM] This is a placeholder response. "
                    "Set LLM_PROVIDER=openai and provide OPENAI_API_KEY for real AI responses."
        )


class MockResponse:
    def __init__(self, content: str):
        self.content = content


def retrieve_recipes(
    query: str,
    diet_type: str,
    meal_type: str,
    allergies: List[str],
    k: int = 5
) -> List[Document]:
    """
    Retrieve top-k relevant recipes from the vector store.
    
    Args:
        query: Natural language query (e.g., "healthy breakfast for diabetics")
        diet_type: veg / non-veg / vegan
        meal_type: breakfast / lunch / dinner / snack
        allergies: List of allergens to exclude
        k: Number of results to retrieve
    
    Returns:
        List of LangChain Documents with recipe metadata
    """
    vs = get_vector_store()

    # Enrich query with user context for better retrieval
    enriched_query = (
        f"{meal_type} recipe for {diet_type} diet. "
        f"Query: {query}. "
        f"Avoid allergens: {', '.join(allergies) if allergies else 'none'}."
    )

    # Retrieve more than needed so we can filter
    raw_results = vs.similarity_search(enriched_query, k=k * 3)

    # Filter by diet type and meal type
    filtered = []
    for doc in raw_results:
        meta = doc.metadata
        # Check meal type
        if meta.get("type") != meal_type:
            continue
        # Check diet compatibility
        doc_diets = meta.get("diet", [])
        if diet_type == "vegan" and "vegan" not in doc_diets:
            continue
        if diet_type == "veg" and not any(d in doc_diets for d in ["veg", "vegan"]):
            continue
        # Check allergens
        doc_allergens = meta.get("allergens", [])
        if any(a.lower() in [x.lower() for x in doc_allergens] for a in allergies):
            continue
        filtered.append(doc)
        if len(filtered) >= k:
            break

    logger.info(f"Retrieved {len(filtered)} recipes for {meal_type} ({diet_type})")
    return filtered


def build_rag_context(documents: List[Document]) -> str:
    """Format retrieved documents into a context string for the LLM prompt."""
    if not documents:
        return "No matching recipes found in the database."

    context_parts = []
    for i, doc in enumerate(documents, 1):
        meta = doc.metadata
        context_parts.append(
            f"{i}. {meta['name']} ({meta['type']}, {meta['calories']} cal) — "
            f"Protein: {meta['protein']}g, Carbs: {meta['carbs']}g, Fat: {meta['fat']}g — "
            f"Tags: {', '.join(meta.get('health_tags', []))}"
        )

    return "\n".join(context_parts)


def rag_query(
    user_query: str,
    diet_type: str,
    meal_type: str,
    allergies: List[str],
    health_conditions: List[str],
    calorie_target: int
) -> Dict[str, Any]:
    """
    Full RAG pipeline: retrieve relevant recipes and use LLM to select the best one.
    
    Returns:
        Dict with selected recipe metadata and LLM reasoning
    """
    # Step 1: Retrieve
    docs = retrieve_recipes(user_query, diet_type, meal_type, allergies)

    if not docs:
        logger.warning(f"No recipes found for {meal_type}, returning fallback.")
        return {"error": f"No suitable {meal_type} recipe found for given constraints."}

    # Step 2: Build context
    context = build_rag_context(docs)

    # Step 3: Construct prompt
    prompt = f"""You are a nutrition expert. Select the BEST recipe for this user from the options below.

User Profile:
- Diet: {diet_type}
- Meal: {meal_type}
- Calorie target for this meal: {calorie_target} calories
- Allergies: {', '.join(allergies) if allergies else 'none'}
- Health conditions: {', '.join(health_conditions) if health_conditions else 'none'}

Available Recipes:
{context}

Instructions:
1. Select the single best recipe number (1, 2, 3...) that fits the user's needs.
2. Briefly explain why (1-2 sentences).
3. Respond in format: SELECTED: <number> | REASON: <reason>
"""

    # Step 4: LLM call
    llm = get_llm()
    response = llm.invoke(prompt)
    llm_output = response.content if hasattr(response, "content") else str(response)

    # Step 5: Parse LLM selection
    selected_doc = docs[0]  # default to top result
    if "SELECTED:" in llm_output:
        try:
            idx_str = llm_output.split("SELECTED:")[1].split("|")[0].strip()
            idx = int(idx_str) - 1
            if 0 <= idx < len(docs):
                selected_doc = docs[idx]
        except (ValueError, IndexError):
            pass

    meta = selected_doc.metadata
    return {
        "name": meta["name"],
        "type": meta["type"],
        "calories": meta["calories"],
        "protein": meta["protein"],
        "carbs": meta["carbs"],
        "fat": meta["fat"],
        "fiber": meta["fiber"],
        "allergens": meta["allergens"],
        "health_tags": meta["health_tags"],
        "ingredients": meta["ingredients"],
        "instructions": meta["instructions"],
        "llm_reasoning": llm_output
    }

