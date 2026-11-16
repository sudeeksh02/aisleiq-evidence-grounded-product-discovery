from __future__ import annotations

import json
import logging
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from aisleiq import database
from aisleiq.models import Product, SearchRequest
from aisleiq.query import parse_intent
from aisleiq.ranker import load_ranker, rerank
from aisleiq.retrieval import Retriever
from aisleiq.reviews import product_aspects

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("aisleiq")
ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_PATH = ROOT / "data" / "processed" / "products.jsonl"
state: dict = {
    "products": [],
    "retriever": None,
    "ranker": None,
    "last_latency_ms": 0.0,
    "request_count": 0,
}
search_cache: OrderedDict[tuple, dict] = OrderedDict()


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.initialize(PRODUCTS_PATH)
    payloads = database.all_payloads()
    products = [Product.model_validate_json(row) for row in payloads]
    state["products"] = products
    state["retriever"] = Retriever(products) if products else None
    state["ranker"] = load_ranker(ROOT / "models" / "cegr_lambdamart.txt")
    log.info(
        "catalog_loaded products=%d semantic_model=%s lambdamart=%s",
        len(products),
        bool(state["retriever"] and state["retriever"].vectors is not None),
        bool(state["ranker"]),
    )
    yield


app = FastAPI(
    title="AisleIQ",
    version="0.1.0",
    description="CEGR evidence-grounded product discovery",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("request_failed request_id=%s path=%s", request_id, request.url.path)
        response = JSONResponse(
            status_code=500, content={"detail": "Internal server error", "request_id": request_id}
        )
    elapsed = (time.perf_counter() - started) * 1000
    state["last_latency_ms"] = elapsed
    state["request_count"] += 1
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{elapsed:.2f}"
    return response


@app.get("/health")
def health():
    return {
        "status": "ok",
        "catalog_products": len(state["products"]),
        "catalog_ready": bool(state["products"]),
    }


@app.get("/api/v1/products")
def products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
):
    rows = state["products"]
    if category:
        rows = [p for p in rows if p.category == category]
    start = (page - 1) * page_size
    return {
        "items": rows[start : start + page_size],
        "page": page,
        "page_size": page_size,
        "total": len(rows),
    }


@app.get("/api/v1/products/{product_id}")
def product(product_id: str):
    row = next((p for p in state["products"] if p.product_id == product_id), None)
    if row is None:
        raise HTTPException(404, "Product not found")
    return {"product": row, "review_intelligence": product_aspects(row)}


@app.post("/api/v1/search")
def search(payload: SearchRequest):
    key = (payload.query.lower(), payload.category, payload.limit)
    if key in search_cache:
        search_cache.move_to_end(key)
        return search_cache[key]
    started = time.perf_counter()
    retriever: Retriever | None = state["retriever"]
    if not retriever:
        raise HTTPException(
            503, "Catalog is empty. Run scripts/build_dataset.py and restart the API."
        )
    intent = parse_intent(payload.query, payload.category)
    mode = "hybrid" if retriever.vectors is not None else "bm25"
    hits = retriever.retrieve(payload.query, min(len(state["products"]), 100), mode=mode)
    candidates = [(state["products"][i], score) for i, score in hits]
    unpriced = (
        sum(p.price is None for p, _ in candidates)
        if intent.max_price is not None or intent.min_price is not None
        else 0
    )
    ranked = rerank(intent, candidates, state["ranker"])[: payload.limit]
    latency = (time.perf_counter() - started) * 1000
    notices = []
    if mode == "bm25":
        notices.append("Semantic model unavailable; BM25 is used.")
    if unpriced:
        notices.append(
            f"{unpriced} retrieved candidates had no source price and were excluded because budget compliance could not be verified."
        )
    result = {
        "intent": intent,
        "retrieval_mode": mode,
        "results": ranked,
        "count": len(ranked),
        "latency_ms": round(latency, 3),
        "notices": notices,
    }
    search_cache[key] = result
    if len(search_cache) > 256:
        search_cache.popitem(last=False)
    return result


@app.post("/api/v1/compare")
def compare(product_ids: list[str]):
    if not 3 <= len(product_ids) <= 8:
        raise HTTPException(422, "Compare between 3 and 8 products")
    by_id = {p.product_id: p for p in state["products"]}
    missing = [pid for pid in product_ids if pid not in by_id]
    if missing:
        raise HTTPException(404, f"Products not found: {missing}")
    selected = [by_id[pid] for pid in product_ids]
    summaries = {p.product_id: product_aspects(p) for p in selected}
    aspects = sorted({aspect for item in summaries.values() for aspect in item})
    return {
        "products": selected,
        "attributes": {
            p.product_id: {a: summaries[p.product_id].get(a) for a in aspects} for p in selected
        },
        "missing_information": {
            p.product_id: [a for a in aspects if a not in summaries[p.product_id]] for p in selected
        },
    }


@app.post("/api/v1/recommendations/explain")
def explain(payload: SearchRequest):
    return search(payload)


@app.get("/api/v1/metrics")
def metrics():
    provenance_path = ROOT / "data" / "raw" / "provenance.json"
    provenance = json.loads(provenance_path.read_text()) if provenance_path.exists() else None
    retriever: Retriever | None = state["retriever"]
    return {
        "catalog_products": len(state["products"]),
        "retrieval_latency_last_ms": state["last_latency_ms"],
        "request_count": state["request_count"],
        "retrieval_model": retriever.encoder.model_name
        if retriever and retriever.encoder
        else "BM25 only",
        "semantic_enabled": bool(retriever and retriever.vectors is not None),
        "lambdamart_enabled": bool(state["ranker"]),
        "dataset_provenance": provenance,
        "evaluation": "Run python -m scripts.run_experiments to produce measured metrics.",
    }
