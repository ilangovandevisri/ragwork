"""
Embedding module — generates vector embeddings for recipe documents.
Supports both OpenAI embeddings and local SentenceTransformers (no API key needed).
"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "local")


def get_embeddings():
    """
    Returns the appropriate LangChain embeddings object based on LLM_PROVIDER env var.
    - "openai"  → OpenAIEmbeddings (requires OPENAI_API_KEY)
    - "local"   → HuggingFaceEmbeddings with all-MiniLM-L6-v2 (free, runs locally)
    """
    if LLM_PROVIDER == "openai":
        try:
            from langchain_openai import OpenAIEmbeddings
            logger.info("Using OpenAI embeddings.")
            return OpenAIEmbeddings(model="text-embedding-3-small")
        except Exception as e:
            logger.warning(f"OpenAI embeddings failed ({e}), falling back to local.")

    # Local fallback using sentence-transformers
    from langchain_community.embeddings import HuggingFaceEmbeddings
    logger.info("Using local HuggingFace embeddings (all-MiniLM-L6-v2).")
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )


def recipe_to_text(recipe: dict) -> str:
    """
    Convert a recipe dict to a rich text string for embedding.
    Including all relevant fields improves retrieval quality.
    """
    return (
        f"Recipe: {recipe['name']}. "
        f"Type: {recipe['type']}. "
        f"Diet: {', '.join(recipe['diet'])}. "
        f"Calories: {recipe['calories']}. "
        f"Protein: {recipe['protein']}g, Carbs: {recipe['carbs']}g, Fat: {recipe['fat']}g, Fiber: {recipe['fiber']}g. "
        f"Allergens: {', '.join(recipe['allergens']) if recipe['allergens'] else 'none'}. "
        f"Health tags: {', '.join(recipe['health_tags'])}. "
        f"Ingredients: {', '.join(recipe['ingredients'])}. "
        f"Instructions: {recipe['instructions']}"
    )

