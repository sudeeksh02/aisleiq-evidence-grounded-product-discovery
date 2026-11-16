from fastapi.testclient import TestClient

from aisleiq import api
from aisleiq.models import Product, Review
from aisleiq.retrieval import Retriever


def test_search_and_product_api_contract():
    product = Product(
        product_id="p1",
        title="Phone camera",
        category="mobile",
        price=20000,
        reviews=[Review(review_id="r1", text="Camera is great", rating=5)],
    )
    api.state["products"] = [product]
    api.state["retriever"] = Retriever([product], use_dense=False)
    response = TestClient(api.app).post(
        "/api/v1/search", json={"query": "phone camera", "limit": 3}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["supporting_reviews"][0]["review_id"] == "r1"
    assert TestClient(api.app).get("/health").status_code == 200


def test_empty_query_validation_and_comparison_missing_evidence():
    a = Product(product_id="a", title="Phone A", category="mobile", price=100)
    b = Product(product_id="b", title="Phone B", category="mobile", price=None)
    c = Product(product_id="c", title="Phone C", category="mobile", price=120)
    api.state["products"] = [a, b, c]
    client = TestClient(api.app)
    assert client.post("/api/v1/search", json={"query": "", "limit": 3}).status_code == 422
    response = client.post("/api/v1/compare", json=["a", "b", "c"])
    assert response.status_code == 200
    assert response.json()["products"][1]["price"] is None


def test_outside_budget_returns_no_result():
    product = Product(product_id="p2", title="Phone", category="mobile", price=900)
    api.state["products"] = [product]
    api.state["retriever"] = Retriever([product], use_dense=False)
    response = TestClient(api.app).post(
        "/api/v1/search", json={"query": "phone under 500", "limit": 3}
    )
    assert response.status_code == 200
    assert response.json()["count"] == 0
