"""
Utility script to pre-build the FAISS vector index from recipes.json.
Run this once before starting the server to avoid cold-start delay.

Usage: python scripts/build_index.py
"""

import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

from rag.vector_store import build_vector_store

if __name__ == "__main__":
    print("Building FAISS vector index from recipes...")
    vs = build_vector_store(force_rebuild=True)
    print(f"Index built successfully. Stored at: data/faiss_index/")
    
    # Quick test retrieval
    results = vs.similarity_search("healthy breakfast for diabetics", k=3)
    print(f"\nTest retrieval (top 3 for 'healthy breakfast for diabetics'):")
    for r in results:
        print(f"  - {r.metadata['name']} ({r.metadata['calories']} cal)")
