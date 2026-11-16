from __future__ import annotations

from pydantic import BaseModel, Field


class Review(BaseModel):
    review_id: str
    text: str
    rating: float | None = None
    sentiment_label: str | None = None


class Product(BaseModel):
    product_id: str
    title: str
    category: str = "unknown"
    price: float | None = None
    rating: float | None = None
    description: str = ""
    attributes: dict[str, str] = Field(default_factory=dict)
    reviews: list[Review] = Field(default_factory=list)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    category: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class Intent(BaseModel):
    raw_query: str
    category: str | None = None
    use_case: str | None = None
    max_price: float | None = None
    min_price: float | None = None
    required_attributes: list[str] = Field(default_factory=list)
    preferred_attributes: list[str] = Field(default_factory=list)
    negated_attributes: list[str] = Field(default_factory=list)


class RankedProduct(BaseModel):
    product: Product
    score: float
    constraint_satisfied: bool
    matched_attributes: list[str]
    supporting_reviews: list[Review]
    pros: list[str]
    cons: list[str]
    explanation: list[str]
    confidence: float
    uncertainty: list[str]
