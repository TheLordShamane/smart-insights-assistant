"""Text chunking utilities for document processing."""

from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_document(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
    separators: list[str] | None = None,
) -> list[str]:
    """
    Split text into overlapping chunks for embedding.
    
    Args:
        text: The document text to split
        chunk_size: Maximum size of each chunk in characters
        chunk_overlap: Number of characters to overlap between chunks
        separators: List of separators to use for splitting (priority order)
    
    Returns:
        List of text chunks
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", " ", ""]
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators,
        length_function=len,
    )
    
    return splitter.split_text(text)


def chunk_documents(
    documents: list[dict],
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[dict]:
    """
    Chunk multiple documents while preserving metadata.
    
    Args:
        documents: List of dicts with 'text' and 'metadata' keys
        chunk_size: Maximum size of each chunk
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of dicts with chunked text and updated metadata
    """
    chunked_docs = []
    
    for doc in documents:
        text = doc.get("text", "")
        metadata = doc.get("metadata", {})
        
        chunks = chunk_document(text, chunk_size, chunk_overlap)
        
        for i, chunk in enumerate(chunks):
            chunked_docs.append({
                "text": chunk,
                "metadata": {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                },
            })
    
    return chunked_docs
