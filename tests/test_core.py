from aisleiq.models import Intent, Product, Review
from aisleiq.query import parse_intent
from aisleiq.ranking import rank_candidates
from aisleiq.retrieval import BM25
from aisleiq.reviews import evidence_for, review_aspects


def test_price_unit_and_category():
    intent = parse_intent("gaming laptop below ₹80k with good battery life")
    assert intent.category == "laptop"
    assert intent.max_price == 80000
    assert intent.use_case == "gaming"
    assert "battery" in intent.preferred_attributes


def test_price_range_direction_and_negation():
    intent = parse_intent("phone above 20,000 without poor battery")
    assert intent.min_price == 20000
    assert "battery" in intent.negated_attributes


def test_bm25_prefers_matching_title():
    bm25 = BM25(["wireless noise cancelling headphones", "cotton summer shirt"])
    assert int(bm25.score("noise cancelling headphones").argmax()) == 0


def test_review_aspect_evidence_is_source_text():
    source = Review(review_id="source-1", text="Battery life is great and lasts long", rating=5)
    result = review_aspects([source])
    assert result["battery"]["sentiment"] == "positive"
    evidence, pros, _ = evidence_for(
        Product(product_id="p", title="phone", reviews=[source]), ["battery"]
    )
    assert evidence[0].text == source.text
    assert "battery" in pros[0]


def test_budget_filter_removes_over_budget_and_discloses_unknown():
    intent = Intent(raw_query="phone under 100", max_price=100)
    candidates = [
        (Product(product_id="cheap", title="phone", price=90), 1.0),
        (Product(product_id="costly", title="phone", price=200), 0.9),
    ]
    result = rank_candidates(intent, candidates)
    assert [row.product.product_id for row in result] == ["cheap"]
    unknown = rank_candidates(intent, [(Product(product_id="unknown", title="phone"), 1.0)])
    assert unknown == []
