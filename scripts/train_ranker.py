#!/usr/bin/env python3
"""Fit LambdaMART against documented, product-disjoint synthetic weak labels."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aisleiq.models import Product  # noqa: E402
from aisleiq.query import parse_intent  # noqa: E402
from aisleiq.ranker import FEATURE_NAMES, features  # noqa: E402
from aisleiq.ranking import rank_candidates  # noqa: E402
from aisleiq.retrieval import Retriever  # noqa: E402


def matrices(retriever: Retriever, products: list[Product], queries: pd.DataFrame):
    matrix, labels, groups = [], [], []
    query_vectors = (
        retriever.encoder.encode(queries["query"].tolist())
        if retriever.encoder and retriever.vectors is not None
        else None
    )
    for row_index, row in enumerate(queries.itertuples(index=False)):
        intent = parse_intent(row.query, row.category if row.category != "unknown" else None)
        qvec = query_vectors[row_index] if query_vectors is not None else None
        hits = retriever.retrieve(
            row.query, min(100, len(products)), mode="hybrid", query_vector=qvec
        )
        raw_candidates = [(products[i], score) for i, score in hits]
        ranked = rank_candidates(intent, raw_candidates)
        scores = {product.product_id: score for product, score in raw_candidates}
        ranks = {product.product_id: i for i, (product, _) in enumerate(raw_candidates, start=1)}
        max_score = max(scores.values(), default=1.0) or 1.0
        if len(ranked) < 2 or not any(
            item.product.product_id == row.relevant_product_id for item in ranked
        ):
            continue
        for item in ranked:
            pid = item.product.product_id
            matrix.append(features(intent, item.product, scores[pid], ranks[pid], max_score))
            labels.append(int(pid == row.relevant_product_id))
        groups.append(len(ranked))
    return np.asarray(matrix, dtype=np.float32), np.asarray(labels, dtype=np.int32), groups


def main() -> None:
    try:
        import lightgbm as lgb
    except ImportError as exc:
        raise SystemExit("Install lightgbm to train: pip install lightgbm") from exc
    products = [
        Product.model_validate_json(x)
        for x in (ROOT / "data/processed/products.jsonl").read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    queries = pd.read_csv(ROOT / "data/processed/benchmark.csv")
    train = queries[queries.split == "train"]
    valid = queries[queries.split == "validation"]
    retriever = Retriever(products)
    started = time.perf_counter()
    x_train, y_train, g_train = matrices(retriever, products, train)
    x_valid, y_valid, g_valid = matrices(retriever, products, valid)
    model = lgb.LGBMRanker(
        objective="lambdarank",
        metric="ndcg",
        eval_at=[3, 10],
        n_estimators=120,
        num_leaves=15,
        learning_rate=0.05,
        min_child_samples=10,
        subsample=0.9,
        colsample_bytree=0.9,
        n_jobs=6,
        random_state=42,
        verbosity=-1,
    )
    model.fit(
        pd.DataFrame(x_train, columns=FEATURE_NAMES),
        y_train,
        group=g_train,
        eval_set=[(pd.DataFrame(x_valid, columns=FEATURE_NAMES), y_valid)],
        eval_group=[g_valid],
        callbacks=[lgb.early_stopping(15, verbose=False)],
    )
    target = ROOT / "models" / "cegr_lambdamart.txt"
    target.parent.mkdir(exist_ok=True)
    model.booster_.save_model(str(target))
    manifest = {
        "algorithm": "LightGBM LambdaMART",
        "feature_names": FEATURE_NAMES,
        "train_queries": len(train),
        "validation_queries": len(valid),
        "train_groups": len(g_train),
        "validation_groups": len(g_valid),
        "train_rows": int(len(y_train)),
        "train_positive_labels": int(y_train.sum()),
        "validation_positive_labels": int(y_valid.sum()),
        "label_source": "weak synthetic source-product association; no clicks/purchases",
        "query_split": "product_group disjoint; train/validation/test = 70/15/15",
        "best_iteration": model.best_iteration_,
        "training_seconds": time.perf_counter() - started,
        "model_file": str(target.relative_to(ROOT)),
        "model_bytes": target.stat().st_size,
        "limitation": "Learns synthetic title/price/aspect template associations only; not customer relevance.",
    }
    (ROOT / "models" / "ranker_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
