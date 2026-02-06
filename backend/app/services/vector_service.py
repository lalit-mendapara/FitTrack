
import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
# from sentence_transformers import SentenceTransformer # REMOVED: Causing environmental issues
from langchain_ollama import OllamaEmbeddings
from config import QDRANT_URL, QDRANT_API_KEY

# Default to a standard small model for embeddings
DEFAULT_EMBED_MODEL = "all-minilm" 
# NOTE: Ensure you have run `ollama pull all-minilm` 

class VectorService:
    """
    The Librarian: Handles interactions with the Qdrant vector database
    to retrieve food items and exercises based on semantic similarity.
    """
    
    def __init__(self):
        if not QDRANT_URL:
            print("[VectorService] Warning: QDRANT_URL is not set. Vector search will be disabled.")
            self.client = None
            return

        try:
            self.client = QdrantClient(
                url=QDRANT_URL, 
                api_key=QDRANT_API_KEY,
                timeout=10.0
            )
            
            # Use Ollama for embeddings to avoid local torch dependencies
            # We assume Ollama is running at localhost:11434 by default or OLLAMA_URL env
            ollama_base = os.getenv("OLLAMA_URL", "http://localhost:11434")
            self.embeddings = OllamaEmbeddings(
                base_url=ollama_base,
                model=DEFAULT_EMBED_MODEL
            )
            
            print(f"[VectorService] Connected to Qdrant at {QDRANT_URL}")
            print(f"[VectorService] Using Ollama Embeddings ({DEFAULT_EMBED_MODEL})")
            
        except Exception as e:
            print(f"[VectorService] Failed to initialize: {e}")
            self.client = None

    def search_food(self, query: str, limit: int = 5, threshold: float = 0.35) -> List[Dict[str, Any]]:
        """
        Search for food items semantically similar to the query.
        """
        if not self.client:
            return []

        try:
            # Generate embedding for the query using Ollama
            query_vector = self.embeddings.embed_query(query)
            
            results = self.client.query_points(
                collection_name="food_collection",
                query=query_vector,
                limit=limit,
                score_threshold=threshold,
                with_payload=True
            ).points
            
            return [point.payload for point in results]
        except Exception as e:
            print(f"[VectorService] Error searching food: {e}")
            return []

    def search_exercises(self, query: str, limit: int = 5, threshold: float = 0.35) -> List[Dict[str, Any]]:
        """
        Search for exercises semantically similar to the query.
        """
        if not self.client:
            return []

        try:
            query_vector = self.embeddings.embed_query(query)
            
            results = self.client.query_points(
                collection_name="exercise_collection",
                query=query_vector,
                limit=limit,
                score_threshold=threshold,
                with_payload=True
            ).points
            return [point.payload for point in results]
        except Exception as e:
            print(f"[VectorService] Error searching exercises: {e}")
            return []
