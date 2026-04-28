"""
Vector Store module — builds and manages the FAISS index for recipe retrieval.
Loads recipes from data/recipes.json, embeds them, and persists the index to disk.
"""

import os
import json
import logging
from typing import List, Dict, Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from rag.embeddings import get_embeddings, recipe_to_text

logger = logging.getLogger(__name__)

FAISS_INDEX_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "faiss_index")
RECIPES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "recipes.json")


def load_recipes() -> List[Dict[str, Any]]:
    """Load recipes from the JSON dataset."""
    with open(RECIPES_PATH, "r") as f:
        return json.load(f)
    

def build_vector_store(force_rebuild: bool = False) -> FAISS:
    """
    Build or load the FAISS vector store.
    
    - If index exists on disk and force_rebuild=False, loads from disk.
    - Otherwise, embeds all recipes and saves the index.
    
    Returns:
        FAISS vector store instance
    """
    embeddings = get_embeddings()

    if os.path.exists(FAISS_INDEX_PATH) and not force_rebuild:
        logger.info("Loading existing FAISS index from disk.")
        return FAISS.load_local(
            FAISS_INDEX_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

    logger.info("Building new FAISS index from recipes...")
    recipes = load_recipes()

    documents = []
    for recipe in recipes:
        text = recipe_to_text(recipe)
        doc = Document(
            page_content=text,
            metadata={
                "id": recipe["id"],
                "name": recipe["name"],
                "type": recipe["type"],
                "diet": recipe["diet"],
                "calories": recipe["calories"],
                "protein": recipe["protein"],
                "carbs": recipe["carbs"],
                "fat": recipe["fat"],
                "fiber": recipe["fiber"],
                "allergens": recipe["allergens"],
                "health_tags": recipe["health_tags"],
                "ingredients": recipe["ingredients"],
                "instructions": recipe["instructions"]
            }
        )
        documents.append(doc)

  
    vector_store = FAISS.from_documents(documents, embeddings)

   
    os.makedirs(FAISS_INDEX_PATH, exist_ok=True)
    vector_store.save_local(FAISS_INDEX_PATH)
    logger.info(f"FAISS index built with {len(documents)} recipes and saved.")

    return vector_store



_vector_store: FAISS = None


def get_vector_store() -> FAISS:
    """Return the singleton vector store, building it if needed."""
    global _vector_store
    if _vector_store is None:
        _vector_store = build_vector_store()
    return _vector_store

