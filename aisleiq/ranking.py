from __future__ import annotations

from aisleiq.models import Intent, Product, RankedProduct
from aisleiq.reviews import evidence_for, product_aspects


def _attribute_text(product: Product) -> str:
    return " ".join(
        [
            product.title,
            product.description,
            *product.attributes.keys(),
            *product.attributes.values(),
        ]
    ).lower()


def rank_candidates(
    intent: Intent,
    candidates: list[tuple[Product, float]],
    *,
    enforce_constraints: bool = True,
    use_reviews: bool = True,
) -> list[RankedProduct]:
    eligible = []
    for product, retrieval_score in candidates:
        if enforce_constraints and intent.max_price is not None:
            if product.price is None or product.price > intent.max_price:
                continue
        if enforce_constraints and intent.min_price is not None:
            if product.price is None or product.price < intent.min_price:
                continue
        if enforce_constraints and intent.category:
            if product.category == "unknown" or intent.category not in product.category:
                continue
        eligible.append((product, retrieval_score))
    if not eligible and candidates:
        return []  # hard constraints never silently relax
    max_retrieval = max((s for _, s in eligible), default=0.0) or 1.0
    ranked = []
    aspects = intent.required_attributes + intent.preferred_attributes
    for product, raw_score in eligible:
        text = _attribute_text(product)
        matched = [
            a for a in aspects if a.replace("_", " ") in text or any(t in text for t in (a,))
        ]
        review_map = product_aspects(product) if use_reviews else {}
        evidence_aspects = [a for a in aspects if a in review_map]
        support, pros, cons = (
            evidence_for(product, evidence_aspects) if use_reviews else ([], [], [])
        )
        lexical = len(set(intent.raw_query.lower().split()) & set(text.split())) / max(
            1, len(set(intent.raw_query.lower().split()))
        )
        attr_coverage = len(matched) / max(1, len(aspects)) if aspects else 0.0
        ev_coverage = len(evidence_aspects) / max(1, len(aspects)) if aspects else 0.0
        # Retrieval remains the primary relevance signal on the weakly supervised catalog.
        # Evidence/preferences can re-order close candidates without overwhelming query match.
        score = (
            0.88 * raw_score / max_retrieval
            + 0.05 * attr_coverage
            + 0.04 * ev_coverage
            + 0.03 * lexical
        )
        explanation = ["Retrieved from product title and catalog text."]
        if matched:
            explanation.append(
                "Catalog text matches: " + ", ".join(a.replace("_", " ") for a in matched) + "."
            )
        if product.price is not None and intent.max_price is not None:
            explanation.append(
                f"Listed price ₹{product.price:,.0f} is within the ₹{intent.max_price:,.0f} budget."
            )
        elif intent.max_price is not None:
            explanation.append("Price is missing; budget fit cannot be verified.")
        uncertainties = []
        if not product.reviews:
            uncertainties.append("No review evidence is available for this product.")
        if not aspects:
            uncertainties.append("No explicit product preferences were detected.")
        missing = [a for a in aspects if a not in matched and a not in evidence_aspects]
        if missing:
            uncertainties.append("No supporting evidence for: " + ", ".join(missing) + ".")
        coverage = (
            (len(matched) + len(evidence_aspects)) / max(1, 2 * len(aspects)) if aspects else 0.0
        )
        confidence = max(
            0.05,
            min(
                0.95,
                (0.35 + 0.4 * coverage + 0.25 * min(raw_score / max_retrieval, 1))
                if aspects
                else 0.35,
            ),
        )
        if not support:
            confidence = min(confidence, 0.45)
        ranked.append(
            RankedProduct(
                product=product,
                score=score,
                constraint_satisfied=True,
                matched_attributes=matched,
                supporting_reviews=support,
                pros=pros,
                cons=cons,
                explanation=explanation,
                confidence=confidence,
                uncertainty=uncertainties,
            )
        )
    ranked = sorted(ranked, key=lambda r: r.score, reverse=True)
    if len(ranked) > 1:
        margin = abs(ranked[0].score - ranked[1].score) / max(abs(ranked[0].score), 1e-9)
        if margin < 0.05:
            for item in ranked:
                item.confidence *= 0.9
                item.uncertainty.append("Top ranking scores are close; the ordering is uncertain.")
    return ranked
