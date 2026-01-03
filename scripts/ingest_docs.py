"""
One-time script to ingest all documents into the vector store.

Usage:
    python scripts/ingest_docs.py
    python scripts/ingest_docs.py --docs-dir ./docs --persist-dir ./vectordb
"""

import argparse
import sys
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.rag.chunker import chunk_document
from app.rag.vectorstore import get_vectorstore, add_documents, get_collection_stats


SUPPORTED_EXTENSIONS = {".md", ".txt", ".html"}


def load_document(filepath: Path) -> str:
    """Load a document from file."""
    return filepath.read_text(encoding="utf-8")


def ingest_file(collection, filepath: Path, chunk_size: int = 500):
    """Ingest a single file into the vector store."""
    text = load_document(filepath)
    chunks = chunk_document(text, chunk_size=chunk_size)
    
    # Generate unique IDs and metadata for each chunk
    ids = [f"{filepath.stem}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "source": str(filepath),
            "filename": filepath.name,
            "chunk_index": i,
            "total_chunks": len(chunks),
        }
        for i in range(len(chunks))
    ]
    
    add_documents(collection, chunks, metadatas, ids)
    return len(chunks)


def ingest_directory(
    docs_dir: Path,
    persist_dir: str = "./vectordb",
    collection_name: str = "knowledge_base",
    chunk_size: int = 500,
):
    """
    Ingest all documents from a directory into the vector store.
    
    Args:
        docs_dir: Directory containing documents
        persist_dir: Directory to persist vector database
        collection_name: Name of the collection
        chunk_size: Size of text chunks
    """
    collection = get_vectorstore(persist_dir, collection_name)
    
    total_files = 0
    total_chunks = 0
    
    for ext in SUPPORTED_EXTENSIONS:
        for filepath in docs_dir.rglob(f"*{ext}"):
            try:
                num_chunks = ingest_file(collection, filepath, chunk_size)
                total_files += 1
                total_chunks += num_chunks
                print(f"✓ Ingested {filepath}: {num_chunks} chunks")
            except Exception as e:
                print(f"✗ Failed to ingest {filepath}: {e}")
    
    print(f"\n{'='*50}")
    print(f"Ingestion complete!")
    print(f"  Files processed: {total_files}")
    print(f"  Total chunks: {total_chunks}")
    
    stats = get_collection_stats(collection)
    print(f"  Collection size: {stats['count']} documents")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest documents into the vector store"
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Directory containing documents to ingest",
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default="./vectordb",
        help="Directory to persist the vector database",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default="knowledge_base",
        help="Name of the vector store collection",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Size of text chunks in characters",
    )
    
    args = parser.parse_args()
    
    if not args.docs_dir.exists():
        print(f"Error: Documents directory '{args.docs_dir}' does not exist")
        print("Please create the directory and add some documents first.")
        sys.exit(1)
    
    ingest_directory(
        docs_dir=args.docs_dir,
        persist_dir=args.persist_dir,
        collection_name=args.collection,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
