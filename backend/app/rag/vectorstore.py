"""Vector store interface using ChromaDB."""

import chromadb
from chromadb.config import Settings


# Default collection name
DEFAULT_COLLECTION = "knowledge_base"


def get_vectorstore(
    persist_dir: str = "./vectordb",
    collection_name: str = DEFAULT_COLLECTION,
):
    """
    Initialize ChromaDB with persistence.
    
    Args:
        persist_dir: Directory to persist the vector database
        collection_name: Name of the collection to use
        
    Returns:
        ChromaDB collection object
    """
    client = chromadb.PersistentClient(path=persist_dir)
    
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}  # Use cosine similarity
    )
    
    return collection


def add_documents(
    collection,
    chunks: list[str],
    metadatas: list[dict],
    ids: list[str],
    embeddings: list[list[float]] | None = None,
):
    """
    Add chunked documents to vector store.
    
    Args:
        collection: ChromaDB collection
        chunks: List of text chunks
        metadatas: List of metadata dicts for each chunk
        ids: List of unique IDs for each chunk
        embeddings: Optional pre-computed embeddings
    """
    if embeddings:
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings,
        )
    else:
        # ChromaDB will compute embeddings automatically
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
        )


def delete_documents(collection, ids: list[str]):
    """
    Delete documents from vector store by ID.
    
    Args:
        collection: ChromaDB collection
        ids: List of document IDs to delete
    """
    collection.delete(ids=ids)


def get_collection_stats(collection) -> dict:
    """
    Get statistics about the collection.
    
    Args:
        collection: ChromaDB collection
        
    Returns:
        Dict with collection statistics
    """
    return {
        "name": collection.name,
        "count": collection.count(),
        "metadata": collection.metadata,
    }


def clear_collection(collection):
    """
    Clear all documents from a collection.
    
    Args:
        collection: ChromaDB collection
    """
    # Get all IDs and delete them
    all_ids = collection.get()["ids"]
    if all_ids:
        collection.delete(ids=all_ids)
