from __future__ import annotations

import re
from collections import defaultdict

from aisleiq.models import Product, Review

ASPECT_TERMS = {
    "battery": ("battery", "backup", "charge", "charging"),
    "camera": ("camera", "photo", "picture", "selfie"),
    "display": ("display", "screen", "brightness", "resolution"),
    "performance": ("performance", "fast", "slow", "lag", "processor", "gaming"),
    "thermals": ("heat", "heating", "hot", "temperature", "cooling"),
    "build_quality": ("build", "durable", "sturdy", "quality", "broke"),
    "value": ("price", "value", "cost", "money", "worth"),
    "sound": ("sound", "audio", "speaker", "volume"),
}
POSITIVE = {
    "good",
    "great",
    "excellent",
    "love",
    "fast",
    "clear",
    "durable",
    "amazing",
    "best",
    "long",
}
NEGATIVE = {"bad", "poor", "worst", "hate", "slow", "weak", "issue", "problem", "short", "overheat"}
_PRODUCT_ASPECT_CACHE: dict[str, dict] = {}


def review_aspects(reviews: list[Review]) -> dict[str, dict]:
    grouped: dict[str, list[tuple[Review, float]]] = defaultdict(list)
    for review in reviews:
        words = set(re.findall(r"[a-z]+", review.text.lower()))
        for aspect, terms in ASPECT_TERMS.items():
            if any(term in review.text.lower() for term in terms):
                score = sum(w in POSITIVE for w in words) - sum(w in NEGATIVE for w in words)
                if review.rating is not None:
                    score = (
                        score + (1 if review.rating >= 4 else -1 if review.rating <= 2 else 0)
                    ) / 2
                grouped[aspect].append((review, score))
    result = {}
    for aspect, entries in grouped.items():
        average = sum(score for _, score in entries) / len(entries)
        result[aspect] = {
            "count": len(entries),
            "sentiment": "positive"
            if average > 0.15
            else "negative"
            if average < -0.15
            else "mixed",
            "evidence": [review.model_dump() for review, _ in entries[:3]],
        }
    return result


def evidence_for(product: Product, aspects: list[str]) -> tuple[list[Review], list[str], list[str]]:
    summaries = product_aspects(product)
    pros, cons, support = [], [], []
    for aspect in aspects:
        item = summaries.get(aspect)
        if not item:
            continue
        if item["sentiment"] == "positive":
            pros.append(
                f"Review evidence is positive on {aspect.replace('_', ' ')} ({item['count']} reviews)."
            )
        elif item["sentiment"] == "negative":
            cons.append(
                f"Review evidence is negative on {aspect.replace('_', ' ')} ({item['count']} reviews)."
            )
        support.extend(Review(**row) for row in item["evidence"])
    return support[:5], pros, cons


def product_aspects(product: Product) -> dict[str, dict]:
    if product.product_id not in _PRODUCT_ASPECT_CACHE:
        _PRODUCT_ASPECT_CACHE[product.product_id] = review_aspects(product.reviews)
    return _PRODUCT_ASPECT_CACHE[product.product_id]
