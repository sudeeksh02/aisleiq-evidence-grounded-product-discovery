#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

REQUIRED_ALIASES = {
    "product_name": ("Product Name", "product_name"),
    "product_price": ("Price", "product_price"),
    "rating": ("Rate", "Rating", "rating"),
    "review": ("Review", "review"),
    "summary": ("Summary", "summary"),
    "sentiment": ("Sentiment", "sentiment"),
}


def validate(path: Path) -> dict:
    frame = pd.read_csv(path)
    columns = {str(c).strip(): c for c in frame.columns}
    mapping = {
        key: next((columns[a] for a in aliases if a in columns), None)
        for key, aliases in REQUIRED_ALIASES.items()
    }
    missing = [key for key, col in mapping.items() if col is None]
    if missing:
        raise ValueError(
            f"Missing required fields {missing}; actual columns: {list(frame.columns)}"
        )
    return {
        "rows": len(frame),
        "columns": [str(c) for c in frame.columns],
        "mapping": mapping,
        "missing_required_values": {k: int(frame[v].isna().sum()) for k, v in mapping.items()},
        "distinct_products": int(frame[mapping["product_name"]].nunique(dropna=True)),
        "duplicate_full_rows": int(frame.duplicated().sum()),
        "sentiment_distribution": frame[mapping["sentiment"]]
        .fillna("missing")
        .astype(str)
        .value_counts()
        .to_dict(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="data/raw/Dataset-SA.csv", type=Path)
    args = parser.parse_args()
    result = validate(args.path)
    print(json.dumps(result, indent=2, default=str))
