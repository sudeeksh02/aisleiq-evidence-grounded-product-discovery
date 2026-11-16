#!/usr/bin/env python3
"""Create a product-disjoint synthetic query benchmark from catalog metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import pandas as pd


def generate(input_path: Path, output: Path, seed: int = 42) -> dict:
    rng = random.Random(seed)
    products = [
        json.loads(line)
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    records = []
    aspects = {
        "battery life": ("battery", "backup"),
        "camera": ("camera", "photo"),
        "display": ("display", "screen"),
        "performance": ("performance", "fast", "slow", "gaming"),
        "thermals": ("heat", "heating", "hot"),
        "build quality": ("build", "durable", "sturdy"),
        "sound": ("sound", "audio", "speaker"),
        "value": ("price", "value", "worth"),
    }
    for product in products:
        title, category = product["title"], product["category"]
        clean = " ".join(title.split())
        base = hashlib.sha256(product["product_id"].encode()).hexdigest()[:16]
        records.append(
            {
                "query_id": base + "-title",
                "product_group": product["product_id"],
                "query": f"find {clean}",
                "category": category,
                "relevant_product_id": product["product_id"],
                "synthetic": True,
                "generation_rule": "find + source product title",
            }
        )
        price = product.get("price")
        if price:
            budget = int(price * 1.1) + 1
            records.append(
                {
                    "query_id": base + "-budget",
                    "product_group": product["product_id"],
                    "query": f"find {clean} under {budget}",
                    "category": category,
                    "relevant_product_id": product["product_id"],
                    "synthetic": True,
                    "generation_rule": "source title + 10% price ceiling derived from source price",
                }
            )
        review_text = " ".join(r["text"].lower() for r in product.get("reviews", []))
        aspect = next(
            (name for name, terms in aspects.items() if any(term in review_text for term in terms)),
            None,
        )
        if aspect:
            records.append(
                {
                    "query_id": base + "-aspect",
                    "product_group": product["product_id"],
                    "query": f"find {clean} with {aspect}",
                    "category": category,
                    "relevant_product_id": product["product_id"],
                    "synthetic": True,
                    "generation_rule": "source title + aspect phrase present in source reviews",
                }
            )
    groups = sorted({row["product_group"] for row in records})
    rng.shuffle(groups)
    n_groups = len(groups)
    split_by_group = {
        group: "train"
        if i < int(n_groups * 0.7)
        else "validation"
        if i < int(n_groups * 0.85)
        else "test"
        for i, group in enumerate(groups)
    }
    for row in records:
        row["split"] = split_by_group[row["product_group"]]
    n = len(records)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(records).to_csv(output, index=False)
    summary = {
        "rows": n,
        "unique_products": len(products),
        "splits": pd.Series([r["split"] for r in records]).value_counts().to_dict(),
        "synthetic_queries": True,
        "split_unit": "product_group; no source product appears in more than one split",
        "seed": seed,
        "output": str(output),
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("data/processed/products.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/benchmark.csv"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    print(json.dumps(generate(args.input, args.output, args.seed), indent=2))
