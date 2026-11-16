from __future__ import annotations

from pathlib import Path

import numpy as np

from aisleiq.models import Intent, Product, RankedProduct
from aisleiq.ranking import rank_candidates
from aisleiq.retrieval import tokens
from aisleiq.reviews import product_aspects

FEATURE_NAMES = [
    "rrf_score",
    "rrf_rank",
    "query_token_coverage",
    "category_match",
    "budget_fit",
    "catalog_aspect_coverage",
    "review_aspect_coverage",
]


def features(
    intent: Intent, product: Product, raw_score: float, rank: int, max_score: float
) -> list[float]:
    query_tokens = set(tokens(intent.raw_query))
    title_tokens = set(tokens(product.title))
    overlap = len(query_tokens & title_tokens) / max(1, len(query_tokens))
    category_match = float(not intent.category or intent.category in product.category)
    if intent.max_price is not None:
        budget_fit = float(product.price is not None and product.price <= intent.max_price)
    elif intent.min_price is not None:
        budget_fit = float(product.price is not None and product.price >= intent.min_price)
    else:
        budget_fit = 0.5
    requested = intent.required_attributes + intent.preferred_attributes
    aspects = product_aspects(product)
    all_text = (
        product.title + " " + product.description + " " + " ".join(product.attributes.values())
    ).lower()
    catalog_count = sum(a.replace("_", " ") in all_text for a in requested)
    review_count = sum(a in aspects for a in requested)
    denom = max(1, len(requested))
    return [
        raw_score / max_score if max_score else 0.0,
        1 / max(1, rank),
        overlap,
        category_match,
        budget_fit,
        catalog_count / denom,
        review_count / denom,
    ]


def load_ranker(path: Path):
    try:
        import lightgbm as lgb

        if path.exists():
            model = lgb.Booster(model_file=str(path))
            if model.feature_name() != FEATURE_NAMES:
                return None
            return model
    except Exception:
        return None
    return None


def rerank(
    intent: Intent,
    candidates: list[tuple[Product, float]],
    model,
    *,
    enforce_constraints: bool = True,
    use_reviews: bool = True,
) -> list[RankedProduct]:
    ranked = rank_candidates(
        intent, candidates, enforce_constraints=enforce_constraints, use_reviews=use_reviews
    )
    if model is None or not ranked:
        return ranked
    lookup = {product.product_id: score for product, score in candidates}
    retrieval_ranks = {
        product.product_id: rank for rank, (product, _) in enumerate(candidates, start=1)
    }
    max_score = max(lookup.values(), default=1.0) or 1.0
    matrix = np.asarray(
        [
            features(
                intent,
                item.product,
                lookup[item.product.product_id],
                retrieval_ranks[item.product.product_id],
                max_score,
            )
            for i, item in enumerate(ranked)
        ],
        dtype=np.float32,
    )
    predictions = model.predict(matrix)
    low, high = float(np.min(predictions)), float(np.max(predictions))
    for item, pred in zip(ranked, predictions):
        item.score = float((pred - low) / (high - low)) if high > low else 0.5
        item.explanation.insert(
            0,
            "Reranked with a LambdaMART model trained on synthetic metadata-derived relevance labels.",
        )
    return sorted(ranked, key=lambda item: item.score, reverse=True)
