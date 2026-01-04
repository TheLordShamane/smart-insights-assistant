"""FastAPI application exposing a safe, read-only analytics endpoint."""

import logging
import os
from enum import Enum
from typing import Any, Dict, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator

from .api import router as rag_router
from .db import db_manager


# ----------------------------------------------------------------------------
# Logging configuration
# ----------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
	level=LOG_LEVEL,
	format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("app")


# ----------------------------------------------------------------------------
# Query templates and validation
# ----------------------------------------------------------------------------
class QueryType(str, Enum):
	TOP_PRODUCTS_LAST_90_DAYS = "top_products_last_90_days"
	MONTHLY_REVENUE_LAST_12M = "monthly_revenue_last_12m"
	REPEAT_PURCHASE_RATE = "repeat_purchase_rate"
	AOV_BY_SEGMENT = "avg_order_value_by_segment"
	TOP_CUSTOMERS_LTV = "top_customers_ltv"


class AskRequest(BaseModel):
	query: QueryType = Field(..., description="Predefined analytics query to run")
	params: Dict[str, Any] = Field(
		default_factory=dict,
		description="Optional parameters for the selected query template",
	)

	@validator("params")
	def ensure_params_dict(cls, v: Dict[str, Any]) -> Dict[str, Any]:
		if v is None:
			return {}
		if not isinstance(v, dict):
			raise ValueError("params must be an object")
		return v


class AskResponse(BaseModel):
	data: list[dict[str, Any]]


def _build_query(query: QueryType, params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
	"""Return SQL template and validated parameters for the given query type."""

	if query == QueryType.TOP_PRODUCTS_LAST_90_DAYS:
		limit = params.get("limit", 5)
		if not isinstance(limit, int) or limit < 1 or limit > 50:
			raise HTTPException(status_code=422, detail="limit must be an integer between 1 and 50")
		sql = (
			"""
			SELECT p.product_id,
				   p.name AS product_name,
				   SUM(oi.quantity * oi.unit_price) AS revenue
			FROM order_items oi
			JOIN products p ON p.product_id = oi.product_id
			JOIN orders o ON o.order_id = oi.order_id
			WHERE o.order_date >= now() - INTERVAL '90 days'
			GROUP BY p.product_id, p.name
			ORDER BY revenue DESC
			LIMIT :limit
			"""
		)
		return sql, {"limit": limit}

	if query == QueryType.MONTHLY_REVENUE_LAST_12M:
		sql = (
			"""
			SELECT date_trunc('month', o.order_date) AS month,
				   SUM(o.total_amount) AS revenue
			FROM orders o
			WHERE o.order_date >= date_trunc('month', now()) - INTERVAL '12 months'
			GROUP BY 1
			ORDER BY 1
			"""
		)
		return sql, {}

	if query == QueryType.REPEAT_PURCHASE_RATE:
		sql = (
			"""
			SELECT COUNT(DISTINCT CASE WHEN order_count > 1 THEN customer_id END) * 1.0 /
				   COUNT(DISTINCT customer_id) AS repeat_purchase_rate
			FROM (
				SELECT customer_id, COUNT(order_id) AS order_count
				FROM orders
				GROUP BY customer_id
			) subquery
			"""
		)
		return sql, {}

	if query == QueryType.AOV_BY_SEGMENT:
		sql = (
			"""
			SELECT c.is_premium,
				   AVG(o.total_amount) AS avg_order_value
			FROM customers c
			JOIN orders o ON o.customer_id = c.customer_id
			GROUP BY c.is_premium
			"""
		)
		return sql, {}

	if query == QueryType.TOP_CUSTOMERS_LTV:
		limit = params.get("limit", 10)
		if not isinstance(limit, int) or limit < 1 or limit > 100:
			raise HTTPException(status_code=422, detail="limit must be an integer between 1 and 100")
		sql = (
			"""
			SELECT c.customer_id,
				   c.first_name || ' ' || c.last_name AS customer_name,
				   SUM(o.total_amount) AS lifetime_value
			FROM customers c
			JOIN orders o ON o.customer_id = c.customer_id
			GROUP BY c.customer_id, c.first_name, c.last_name
			ORDER BY lifetime_value DESC
			LIMIT :limit
			"""
		)
		return sql, {"limit": limit}

	raise HTTPException(status_code=400, detail="Unsupported query type")


# ----------------------------------------------------------------------------
# FastAPI application
# ----------------------------------------------------------------------------
app = FastAPI(title="Smart Insights Assistant", version="1.0.0")
app.include_router(rag_router)


@app.get("/health")
async def health() -> dict[str, str]:
	"""Health check endpoint for liveness and DB connectivity."""
	db_ok = db_manager.health_check()
	status = "ok" if db_ok else "degraded"
	return {"status": status}


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
	"""Execute a predefined, parameterized analytics query in read-only mode."""
	logger.info("/ask request", extra={"query": request.query, "params": request.params})

	try:
		sql, safe_params = _build_query(request.query, request.params)
		rows = db_manager.execute_query(sql, safe_params)
		return AskResponse(data=rows)
	except HTTPException:
		# Let FastAPI handle HTTPException responses
		raise
	except ValueError as exc:
		logger.warning("Bad request: %s", exc)
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except Exception as exc:  # pragma: no cover - catch-all for unexpected issues
		logger.error("/ask failed: %s", exc, exc_info=True)
		raise HTTPException(status_code=500, detail="Internal server error") from exc


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):  # type: ignore[override]
	"""Catch-all handler to ensure unexpected errors are logged."""
	logger.error("Unhandled error on %s: %s", request.url.path, exc, exc_info=True)
	return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Entry point for uvicorn: uvicorn backend.app.main:app --reload
