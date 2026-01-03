"""Search and retrieval interface for RAG."""

from typing import TypedDict

from .vectorstore import get_vectorstore


class RetrievalResult(TypedDict):
    """Type for retrieval results."""
    text: str
    metadata: dict
    distance: float


def search(
    collection,
    query: str,
    n_results: int = 5,
    where: dict | None = None,
) -> list[RetrievalResult]:
    """
    Perform vector similarity search.
    
    Args:
        collection: ChromaDB collection
        query: Search query text
        n_results: Number of results to return
        where: Optional metadata filter
        
    Returns:
        List of retrieval results with text, metadata, and distance
    """
    query_params = {
        "query_texts": [query],
        "n_results": n_results,
    }
    
    if where:
        query_params["where"] = where
    
    results = collection.query(**query_params)
    
    # Format results
    formatted = []
    for i in range(len(results["documents"][0])):
        formatted.append({
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            "distance": results["distances"][0][i] if results["distances"] else 0.0,
        })
    
    return formatted


def retrieve_context(
    query: str,
    n_results: int = 5,
    persist_dir: str = "./vectordb",
    collection_name: str = "knowledge_base",
    max_context_length: int = 3000,
) -> str:
    """
    Retrieve relevant context for a query.
    
    This is a convenience function that combines search results
    into a single context string for LLM consumption.
    
    Args:
        query: Search query
        n_results: Number of chunks to retrieve
        persist_dir: Vector store directory
        collection_name: Collection name
        max_context_length: Maximum length of combined context
        
    Returns:
        Combined context string from relevant documents
    """
    collection = get_vectorstore(persist_dir, collection_name)
    results = search(collection, query, n_results)
    
    context_parts = []
    current_length = 0
    
    for result in results:
        text = result["text"]
        source = result["metadata"].get("source", "unknown")
        
        # Format with source attribution
        formatted = f"[Source: {source}]\n{text}\n"
        
        if current_length + len(formatted) > max_context_length:
            break
        
        context_parts.append(formatted)
        current_length += len(formatted)
    
    return "\n---\n".join(context_parts)


def search_with_scores(
    collection,
    query: str,
    n_results: int = 5,
    score_threshold: float = 0.5,
) -> list[RetrievalResult]:
    """
    Search with a minimum similarity score threshold.
    
    Args:
        collection: ChromaDB collection
        query: Search query
        n_results: Maximum number of results
        score_threshold: Minimum similarity score (0-1, higher is more similar)
        
    Returns:
        Filtered list of results above threshold
    """
    results = search(collection, query, n_results)
    
    # Filter by score (ChromaDB returns distances, lower is better)
    # Convert distance to similarity score (1 - distance for cosine)
    filtered = [
        r for r in results
        if (1 - r["distance"]) >= score_threshold
    ]
    
    return filtered
