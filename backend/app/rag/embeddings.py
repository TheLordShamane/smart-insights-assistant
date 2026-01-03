"""Embedding generation utilities."""

import os
from typing import Literal

# Optional: for local embeddings without API costs
# from sentence_transformers import SentenceTransformer


EmbeddingModel = Literal["openai", "local"]


class EmbeddingService:
    """Service for generating text embeddings."""
    
    def __init__(self, model_type: EmbeddingModel = "openai"):
        """
        Initialize the embedding service.
        
        Args:
            model_type: Type of embedding model to use ("openai" or "local")
        """
        self.model_type = model_type
        self._model = None
        self._client = None
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        from openai import OpenAI
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self._client = OpenAI(api_key=api_key)
    
    def _init_local(self):
        """Initialize local sentence transformer model."""
        from sentence_transformers import SentenceTransformer
        
        # all-MiniLM-L6-v2 is a good balance of speed and quality
        self._model = SentenceTransformer("all-MiniLM-L6-v2")
    
    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        return self.embed_texts([text])[0]
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        if self.model_type == "openai":
            return self._embed_openai(texts)
        else:
            return self._embed_local(texts)
    
    def _embed_openai(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI API."""
        if self._client is None:
            self._init_openai()
        
        response = self._client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        
        return [item.embedding for item in response.data]
    
    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using local model."""
        if self._model is None:
            self._init_local()
        
        embeddings = self._model.encode(texts)
        return embeddings.tolist()


# Convenience function
def get_embeddings(
    texts: list[str],
    model_type: EmbeddingModel = "openai",
) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    
    Args:
        texts: List of texts to embed
        model_type: Type of embedding model ("openai" or "local")
        
    Returns:
        List of embedding vectors
    """
    service = EmbeddingService(model_type=model_type)
    return service.embed_texts(texts)
