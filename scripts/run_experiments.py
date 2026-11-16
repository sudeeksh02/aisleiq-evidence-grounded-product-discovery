#!/usr/bin/env python3
"""Measure retrieval on a product-disjoint, title-derived synthetic benchmark."""

from __future__ import annotations

import json
import math
import os
import statistics
import time
import platform
import tracemalloc
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aisleiq.models import Product
from aisleiq.query import parse_intent
from aisleiq.ranker import load_ranker, rerank
from aisleiq.ranking import rank_candidates
from aisleiq.retrieval import Retriever

ROOT = Path(__file__).resolve().parents[1]


def dcg(rels: list[int], k: int) -> float:
    return sum((2**rel - 1) / math.log2(i + 2) for i, rel in enumerate(rels[:k]))


def markdown_table(frame: pd.DataFrame) -> str:
    columns = list(frame.columns)
    rows = [
        [str(value) if not isinstance(value, float) else f"{value:.4f}" for value in row]
        for row in frame.itertuples(index=False, name=None)
    ]
    return (
        "| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join(["---"] * len(columns))
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
    )


def score_run(
    retriever: Retriever,
    products: list[Product],
    queries: pd.DataFrame,
    split: str,
    mode: str,
    subset_override: pd.DataFrame | None = None,
    query_vectors_by_text: dict[str, object] | None = None,
) -> dict:
    subset = subset_override if subset_override is not None else queries[queries.split == split]
    recalls5, recalls10, mrr, ndcg3, ndcg10, latencies = [], [], [], [], [], []
    violations, attr_cov, ev_cov = [], [], []
    retrieval_times, ranking_times = [], []
    by_id = {p.product_id: p for p in products}
    ranker = load_ranker(ROOT / "models/cegr_lambdamart.txt") if mode == "cegr_lambdamart" else None
    query_vectors = (
        retriever.encoder.encode(subset["query"].tolist())
        if retriever.encoder
        and retriever.vectors is not None
        and mode != "bm25"
        and query_vectors_by_text is None
        else None
    )
    for row_index, row in enumerate(subset.itertuples(index=False)):
        started = time.perf_counter()
        retrieval_mode = "bm25" if mode == "bm25" else "dense" if mode == "dense" else "hybrid"
        qvec = (
            query_vectors[row_index]
            if query_vectors is not None
            else (
                query_vectors_by_text.get(row.query)
                if query_vectors_by_text is not None and mode != "bm25"
                else None
            )
        )
        hits = retriever.retrieve(row.query, 100, mode=retrieval_mode, query_vector=qvec)
        retrieval_times.append((time.perf_counter() - started) * 1000)
        intent = parse_intent(row.query, row.category if row.category != "unknown" else None)
        if mode.startswith("cegr"):
            rank_started = time.perf_counter()
            if mode == "cegr_lambdamart":
                ranked = rerank(intent, [(products[i], s) for i, s in hits], ranker)
            else:
                ranked = rank_candidates(
                    intent,
                    [(products[i], s) for i, s in hits],
                    enforce_constraints=mode != "cegr_no_constraints",
                    use_reviews=mode != "cegr_no_reviews",
                )
            ids = [r.product.product_id for r in ranked]
            ranking_times.append((time.perf_counter() - rank_started) * 1000)
            requested = intent.required_attributes + intent.preferred_attributes
            attr_cov.append(
                sum(bool(set(requested) & set(r.matched_attributes)) for r in ranked[:10])
                / max(1, min(10, len(ranked)))
            )
            ev_cov.append(
                sum(bool(r.supporting_reviews) for r in ranked[:10]) / max(1, min(10, len(ranked)))
            )
        else:
            ids = [products[i].product_id for i, _ in hits]
            ranking_times.append(0.0)
        checked = 0
        broken = 0
        for pid in ids[:10]:
            p = by_id[pid]
            if intent.max_price is not None and p.price is not None:
                checked += 1
                broken += int(p.price > intent.max_price)
            if intent.min_price is not None and p.price is not None:
                checked += 1
                broken += int(p.price < intent.min_price)
            if intent.category and p.category != "unknown":
                checked += 1
                broken += int(intent.category not in p.category)
        violations.append(broken / checked if checked else 0.0)
        latencies.append((time.perf_counter() - started) * 1000)
        target = row.relevant_product_id
        recalls5.append(float(target in ids[:5]))
        recalls10.append(float(target in ids[:10]))
        rank = ids.index(target) + 1 if target in ids else None
        mrr.append(1 / rank if rank and rank <= 10 else 0.0)
        gains = [int(pid == target) for pid in ids]
        ideal = [1]
        ndcg3.append(dcg(gains, 3) / dcg(ideal, 3))
        ndcg10.append(dcg(gains, 10) / dcg(ideal, 10))
    return {
        "split": split,
        "method": mode,
        "queries": len(subset),
        "recall@5": statistics.mean(recalls5) if recalls5 else 0,
        "recall@10": statistics.mean(recalls10) if recalls10 else 0,
        "mrr@10": statistics.mean(mrr) if mrr else 0,
        "ndcg@3": statistics.mean(ndcg3) if ndcg3 else 0,
        "ndcg@10": statistics.mean(ndcg10) if ndcg10 else 0,
        "constraint_violation_rate": statistics.mean(violations) if violations else None,
        "attribute_coverage": statistics.mean(attr_cov) if attr_cov else None,
        "evidence_coverage": statistics.mean(ev_cov) if ev_cov else None,
        "mean_latency_ms": statistics.mean(latencies) if latencies else 0,
        "retrieval_latency_ms": statistics.mean(retrieval_times) if retrieval_times else 0,
        "ranking_latency_ms": statistics.mean(ranking_times) if ranking_times else 0,
        "p95_latency_ms": float(pd.Series(latencies).quantile(0.95)) if latencies else 0,
    }


def main() -> None:
    data_path = ROOT / "data/processed/products.jsonl"
    query_path = ROOT / "data/processed/benchmark.csv"
    products = [
        Product.model_validate_json(x)
        for x in data_path.read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    queries = pd.read_csv(query_path)
    tracemalloc.start()
    index_started = time.perf_counter()
    retriever = Retriever(products)
    index_seconds = time.perf_counter() - index_started
    _, python_peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    methods = ["bm25", "hybrid"] + (["dense"] if retriever.vectors is not None else [])
    methods += ["cegr", "cegr_no_constraints", "cegr_no_reviews"]
    if (ROOT / "models/cegr_lambdamart.txt").exists():
        methods.append("cegr_lambdamart")
    test_queries = queries[queries.split == "test"]["query"].tolist()
    encoded_test = (
        retriever.encoder.encode(test_queries)
        if retriever.encoder and retriever.vectors is not None
        else None
    )
    test_vector_map = (
        {q: encoded_test[i] for i, q in enumerate(test_queries)}
        if encoded_test is not None
        else None
    )
    metrics = [
        score_run(
            retriever, products, queries, "test", method, query_vectors_by_text=test_vector_map
        )
        for method in methods
    ]
    category_metrics = []
    test_rows = queries[queries.split == "test"]
    for category, group in test_rows.groupby("category"):
        if len(group) >= 5:
            for method in ("bm25", "cegr"):
                result = score_run(
                    retriever, products, queries, "test", method, group, test_vector_map
                )
                result["category"] = category
                category_metrics.append(result)
    report_dir = ROOT / "reports/generated"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (report_dir / "category_metrics.json").write_text(
        json.dumps(category_metrics, indent=2), encoding="utf-8"
    )
    frame = pd.DataFrame(metrics)
    fig, ax = plt.subplots(figsize=(8, 4.4))
    frame.set_index("method")[["recall@5", "mrr@10", "ndcg@10"]].plot(
        kind="bar", ax=ax, color=["#6f9d56", "#e4bb5a", "#657eab"]
    )
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("Synthetic title-query retrieval benchmark")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(report_dir / "retrieval_metrics.png", dpi=150)
    plt.close(fig)
    try:
        import psutil

        process_rss_bytes = psutil.Process().memory_info().rss
        physical_memory_bytes = psutil.virtual_memory().total
    except ImportError:
        process_rss_bytes, physical_memory_bytes = None, None
    config = {
        "seed": 42,
        "query_source": "synthetic title, price-ceiling, and review-aspect templates derived from real product metadata",
        "split": "held-out product ids; train 70%, validation 15%, test 15%",
        "catalog_products": len(products),
        "query_rows": len(queries),
        "test_rows": int((queries.split == "test").sum()),
        "dense_available": retriever.vectors is not None,
        "dense_note": retriever.encoder.error if retriever.encoder else "disabled",
        "index_build_seconds": index_seconds,
        "python_tracemalloc_peak_bytes_during_index": python_peak_bytes,
        "process_rss_bytes_after_index": process_rss_bytes,
        "physical_memory_bytes": physical_memory_bytes,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "cpu_model_observed": "AMD Ryzen 5 5500U with Radeon Graphics",
        "python_version": platform.python_version(),
        "logical_cpu_count": os.cpu_count(),
    }
    (ROOT / "reports/experiment_config.yaml").write_text(
        "\n".join(f"{k}: {json.dumps(v)}" for k, v in config.items()) + "\n", encoding="utf-8"
    )
    lines = [
        "# Benchmark results",
        "",
        "## Evaluation boundary",
        "",
        f"Catalog: {len(products)} product groups aggregated from source reviews. The benchmark has {len(queries)} synthetic title, price-ceiling and review-aspect queries ({int((queries.split == 'test').sum())} held-out test rows). Each query has one weak positive label pointing to its source product. These are metadata-derived labels, not customer queries or human judgments. Product IDs are split before evaluation; all query variants for a product remain in one split.",
        "",
        "This metadata-template task strongly favors exact lexical overlap and does not establish natural-language relevance quality. No click, conversion, or human preference data is available. Dense retrieval was measured with `sentence-transformers/all-MiniLM-L6-v2` and FAISS. CEGR uses the same retriever and deterministic catalog/review features. LambdaMART was trained only as a documented weak-supervision experiment; it must not be interpreted as customer relevance.",
        "",
        "## Category-wise test results",
        "",
        "Categories with at least five test queries are included; very small groups are omitted due to unstable estimates.",
        "",
        markdown_table(
            pd.DataFrame(category_metrics)[
                [
                    "category",
                    "method",
                    "queries",
                    "recall@10",
                    "mrr@10",
                    "ndcg@10",
                    "constraint_violation_rate",
                    "evidence_coverage",
                    "mean_latency_ms",
                ]
            ]
        )
        if category_metrics
        else "No category has five test queries.",
        "",
        "## Index and machine conditions",
        "",
        f"Index build/cold-start cost: {index_seconds:.3f}s; Python traced peak during construction: {python_peak_bytes:,} bytes; process RSS after indexing: {process_rss_bytes}; physical RAM: {physical_memory_bytes}; platform: {platform.platform()}; CPU logical threads: {os.cpu_count()}. Mean measured request latency includes warm requests; p95 includes initial per-product aspect-cache work. These are local single-process measurements, not platform-scale estimates.",
        "",
        "## Test metrics",
        "",
        markdown_table(frame),
        "",
        "## Reproduction",
        "",
        "Run `python scripts/download_data.py`, `python scripts/validate_data.py`, `python scripts/build_dataset.py`, `python scripts/generate_benchmark.py`, then `python scripts/run_experiments.py`. Chart: `reports/generated/retrieval_metrics.png`.",
        "",
    ]
    (ROOT / "reports/benchmark_results.md").write_text("\n".join(lines), encoding="utf-8")
    ablations = [
        "# Ablation study",
        "",
        "All values use the held-out synthetic metadata-derived test split. They are not causal estimates for customer relevance.",
        "",
        "| Variant | Recall@10 | MRR@10 | nDCG@10 | Constraint violation | Attribute coverage | Evidence coverage | Mean latency ms |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in metrics:

        def show(value):
            return "n/a" if value is None else f"{value:.4f}"

        ablations.append(
            f"| {item['method']} | {show(item['recall@10'])} | {show(item['mrr@10'])} | {show(item['ndcg@10'])} | {show(item['constraint_violation_rate'])} | {show(item['attribute_coverage'])} | {show(item['evidence_coverage'])} | {show(item['mean_latency_ms'])} |"
        )
    ablations += [
        "",
        "Removing constraints is evaluated on synthetic budget queries whose ceilings are derived from the target product's source price. Removing evidence disables review features. Removing dense retrieval is the BM25-only baseline; removing BM25 is the dense-only baseline. The LambdaMART row compares a weakly supervised model with the deterministic CEGR score. It used only synthetic source-product association labels and was selected at iteration 1 on validation; it is not a customer relevance model. Synthetic labels are never clicks or purchase data.",
        "",
    ]
    (ROOT / "reports/ablation_study.md").write_text("\n".join(ablations), encoding="utf-8")
    (ROOT / "reports/error_analysis.md").write_text(
        "# Error analysis\n\nPer-query ranked candidate lists are not serialized, so detailed miss examples must be recomputed by joining `data/processed/benchmark.csv` with the catalog. The synthetic title template creates high lexical overlap and can conceal vocabulary-gap failures. CEGR may trade off exact title matching for weak aspect evidence; the displayed score comparison quantifies this on the held-out split. Unknown categories, sparse metadata, missing prices, title tokens reused across products, aspect term ambiguity, and parser negation scope remain important error classes. This is a synthetic task only and does not claim customer relevance.\n",
        encoding="utf-8",
    )
    print(json.dumps({"config": config, "metrics": metrics}, indent=2))


if __name__ == "__main__":
    main()
