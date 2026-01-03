"""RAG (Retrieval-Augmented Generation) module for Smart Insights Assistant."""

from .chunker import chunk_document
from .embeddings import get_embeddings
from .vectorstore import get_vectorstore, add_documents
from .retriever import search, retrieve_context

__all__ = [
    "chunk_document",
    "get_embeddings",
    "get_vectorstore",
    "add_documents",
    "search",
    "retrieve_context",
]
