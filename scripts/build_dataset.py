#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aisleiq.models import Product, Review
from scripts.validate_data import validate


def normalize_price(value: object) -> float | None:
    text = re.sub(r"[^\d.]", "", str(value))
    try:
        amount = float(text)
        return amount if amount > 0 else None
    except ValueError:
        return None


def category_for(name: str) -> str:
    text = name.lower()
    for category, terms in {
        "mobile": ("phone", "mobile", "smartphone"),
        "laptop": ("laptop", "notebook"),
        "headphones": ("headphone", "earphone", "earbud"),
        "television": ("tv", "television"),
        "camera": ("camera", "dslr"),
        "fashion": ("shirt", "dress", "jeans", "kurta", "saree"),
        "home": ("mattress", "chair", "sofa", "curtain"),
    }.items():
        if any(term in text for term in terms):
            return category
    return "unknown"


def build(source: Path, target: Path) -> list[Product]:
    report = validate(source)
    frame = pd.read_csv(source).drop_duplicates().fillna("")
    cols = report["mapping"]
    products = []
    for name, rows in frame.groupby(cols["product_name"], sort=True):
        title = str(name).strip()
        if not title:
            continue
        rid = hashlib.sha256(title.casefold().encode()).hexdigest()[:16]
        prices = [normalize_price(v) for v in rows[cols["product_price"]]]
        prices = [p for p in prices if p is not None]
        ratings = pd.to_numeric(rows[cols["rating"]], errors="coerce").dropna()
        reviews = []
        for i, (_, row) in enumerate(rows.iterrows()):
            review = " ".join(
                str(row[c]).strip()
                for c in (cols["review"], cols["summary"])
                if str(row[c]).strip()
            )
            if not review:
                continue
            try:
                rating = float(row[cols["rating"]])
            except (TypeError, ValueError):
                rating = None
            reviews.append(
                Review(
                    review_id=f"{rid}-{i}",
                    text=review[:2000],
                    rating=rating,
                    sentiment_label=str(row[cols["sentiment"]]).strip().lower() or None,
                )
            )
        products.append(
            Product(
                product_id=rid,
                title=title,
                category=category_for(title),
                price=sorted(prices)[len(prices) // 2] if prices else None,
                rating=float(ratings.mean()) if len(ratings) else None,
                reviews=reviews,
            )
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(p.model_dump_json() for p in products) + "\n", encoding="utf-8")
    report.update(
        {
            "products_written": len(products),
            "source_file": str(source),
            "output_file": str(target),
            "review_records_written": sum(len(p.reviews) for p in products),
        }
    )
    target.with_suffix(".manifest.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )
    return products


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/raw/Dataset-SA.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/products.jsonl"))
    args = parser.parse_args()
    result = build(args.input, args.output)
    print(f"Wrote {len(result)} products to {args.output}")
