from typing import List, Dict, Any
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer # type: ignore
import logging

logger = logging.getLogger(__name__)

# Define the embedding dimension for the model being used
KNOWLEDGE_EMBEDDING_DIMENSION = 384 # For 'all-MiniLM-L6-v2'

class SimpleKnowledgeEmbedder:
    """A simple embedder for KnowledgeData using SentenceTransformers."""
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            self.model = SentenceTransformer(model_name)
            logger.info(f"SimpleKnowledgeEmbedder initialized with model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model '{model_name}': {e}. Ensure sentence-transformers is installed and model is valid.")
            # In a real app, might raise this or have a fallback.
            self.model = None 

    def __call__(self, model_instance: BaseModel) -> List[float]:
        """Generates an embedding for a KnowledgeData instance.
        Focuses on the 'content' field, which is expected to be a dictionary.
        """
        if not self.model:
            logger.warning("Embedder model not loaded. Returning zero vector.")
            return [0.0] * KNOWLEDGE_EMBEDDING_DIMENSION # Return a zero vector of the expected dimension

        if not hasattr(model_instance, 'content') or not isinstance(model_instance.content, dict):
            logger.warning(f"KnowledgeData instance (ID: {getattr(model_instance, 'knowledge_id', 'N/A')}) lacks a 'content' dictionary. Returning zero vector.")
            return [0.0] * KNOWLEDGE_EMBEDDING_DIMENSION

        # Concatenate key-value pairs from the content dictionary to form a representative text string.
        # This is a basic approach; more sophisticated text preparation might be needed for optimal embeddings.
        text_parts = []
        for key, value in model_instance.content.items():
            text_parts.append(f"{str(key)}: {str(value)}")
        text_to_embed = ". ".join(text_parts)
        
        if not text_to_embed.strip():
            logger.warning(f"KnowledgeData instance (ID: {getattr(model_instance, 'knowledge_id', 'N/A')}) has empty content for embedding. Returning zero vector.")
            return [0.0] * KNOWLEDGE_EMBEDDING_DIMENSION

        try:
            embedding = self.model.encode(text_to_embed).tolist()
            # logger.debug(f"Generated embedding for KnowledgeData ID: {getattr(model_instance, 'knowledge_id', 'N/A')}")
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding for KnowledgeData ID: {getattr(model_instance, 'knowledge_id', 'N/A')}: {e}")
            return [0.0] * KNOWLEDGE_EMBEDDING_DIMENSION 