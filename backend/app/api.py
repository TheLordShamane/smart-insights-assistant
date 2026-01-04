"""API router for RAG-powered chat endpoints."""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from openai import OpenAI

from .rag.retriever import search
from .rag.vectorstore import get_vectorstore


logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------
PERSIST_DIR = os.getenv("VECTORSTORE_DIR", "./vectordb")
COLLECTION_NAME = os.getenv("VECTORSTORE_COLLECTION", "knowledge_base")
DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "5"))
MAX_TOP_K = int(os.getenv("RAG_MAX_TOP_K", "10"))
DEFAULT_SCORE_THRESHOLD = float(os.getenv("RAG_SCORE_THRESHOLD", "0.35"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _init_collection():
	"""Initialize vector store collection once."""
	return get_vectorstore(persist_dir=PERSIST_DIR, collection_name=COLLECTION_NAME)


_collection = _init_collection()
_llm_client: Optional[OpenAI] = None


def _get_llm_client() -> OpenAI:
	"""Lazy-init OpenAI client."""
	global _llm_client
	if _llm_client is None:
		api_key = os.getenv("OPENAI_API_KEY")
		if not api_key:
			raise RuntimeError("OPENAI_API_KEY is not configured")
		_llm_client = OpenAI(api_key=api_key)
	return _llm_client


# ----------------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------------
class SourceChunk(BaseModel):
	source: Optional[str] = Field(None, description="Document source identifier")
	score: Optional[float] = Field(None, description="Similarity score (higher is better)")
	text: str = Field(..., description="Retrieved chunk text")


class ChatRequest(BaseModel):
	question: str = Field(..., min_length=5, max_length=500)
	top_k: int = Field(default=DEFAULT_TOP_K, ge=1, le=MAX_TOP_K)
	score_threshold: float = Field(default=DEFAULT_SCORE_THRESHOLD, ge=0, le=1)
	filters: Dict[str, Any] = Field(
		default_factory=dict,
		description="Optional metadata filters passed to vector search",
	)

	@validator("filters")
	def ensure_filters_dict(cls, v: Dict[str, Any]) -> Dict[str, Any]:
		if v is None:
			return {}
		if not isinstance(v, dict):
			raise ValueError("filters must be an object")
		return v


class ChatResponse(BaseModel):
	answer: str
	sources: List[SourceChunk]
	latency_ms: int
	context: Optional[str] = None


# ----------------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------------
router = APIRouter(prefix="/rag", tags=["rag"])


def _build_prompt(question: str, contexts: List[Dict[str, Any]]) -> str:
	"""Compose a grounded prompt with cited context."""
	parts = []
	for item in contexts:
		source = item.get("metadata", {}).get("source", "unknown")
		parts.append(f"[Source: {source}]\n{item['text']}")

	context_block = "\n\n".join(parts)

	return (
		"You are a sales insights assistant. Use ONLY the provided context to answer. "
		"If context is insufficient, say you do not have enough information.\n\n"
		f"Context:\n{context_block}\n\n"
		f"Question: {question}\n"
		"Answer concisely:"
	)


def _retrieve(question: str, top_k: int, score_threshold: float, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
	results = search(_collection, question, n_results=top_k, where=filters or None)

	filtered = []
	for item in results:
		distance = item.get("distance", 0.0)
		score = 1 - distance
		if score >= score_threshold:
			filtered.append({**item, "score": score})
	return filtered


def _generate_answer(prompt: str) -> str:
	client = _get_llm_client()
	response = client.chat.completions.create(
		model=OPENAI_MODEL,
		messages=[
			{"role": "system", "content": "You are a concise, factual sales insights assistant."},
			{"role": "user", "content": prompt},
		],
		temperature=0.2,
		max_tokens=400,
	)
	return response.choices[0].message.content.strip()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
	"""RAG chat endpoint returning grounded answers with citations."""
	start = time.time()
	try:
		retrievals = _retrieve(request.question, request.top_k, request.score_threshold, request.filters)

		if not retrievals:
			raise HTTPException(status_code=404, detail="No relevant context found")

		prompt = _build_prompt(request.question, retrievals)
		answer = _generate_answer(prompt)

		latency_ms = int((time.time() - start) * 1000)
		sources = [
			SourceChunk(
				source=item.get("metadata", {}).get("source"),
				score=item.get("score"),
				text=item.get("text", ""),
			)
			for item in retrievals
		]

		return ChatResponse(
			answer=answer,
			sources=sources,
			latency_ms=latency_ms,
			context=None,
		)
	except HTTPException:
		raise
	except RuntimeError as exc:
		logger.error("Configuration error: %s", exc)
		raise HTTPException(status_code=500, detail=str(exc)) from exc
	except Exception as exc:  # pragma: no cover
		logger.error("RAG chat failed: %s", exc, exc_info=True)
		raise HTTPException(status_code=500, detail="RAG pipeline failed") from exc

