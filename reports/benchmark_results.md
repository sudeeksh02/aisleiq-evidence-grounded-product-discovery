# Benchmark results

## Evaluation boundary

Catalog: 958 product groups aggregated from source reviews. The benchmark has 2832 synthetic title, price-ceiling and review-aspect queries (428 held-out test rows). Each query has one weak positive label pointing to its source product. These are metadata-derived labels, not customer queries or human judgments. Product IDs are split before evaluation; all query variants for a product remain in one split.

The synthetic query/product association class distribution is one positive per generated query (2,832 total); no independently judged negative or graded relevance labels exist. The LambdaMART training pool retained 1,870 query groups and 134,147 candidate pairs: 1,870 generated positives and 132,277 generated negatives. It skipped 109 training and 31 validation queries when the target was absent after candidate retrieval/filtering. Separately, source-provided review sentiment labels are positive 166,581, negative 28,232, neutral 10,239 (205,052 total); these are uploader labels, not ranking judgments.

This metadata-template task strongly favors exact lexical overlap and does not establish natural-language relevance quality. No click, conversion, or human preference data is available. Dense retrieval was measured with `sentence-transformers/all-MiniLM-L6-v2` and FAISS. CEGR uses the same retriever and deterministic catalog/review features. LambdaMART was trained only as a documented weak-supervision experiment; the resulting model was selected at validation iteration 1 and is not a customer-relevance model.

## Category-wise test results

Categories with at least five test queries are included; very small groups are omitted due to unstable estimates.

| category | method | queries | recall@10 | mrr@10 | ndcg@10 | constraint_violation_rate | evidence_coverage | mean_latency_ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| home | bm25 | 9 | 1.0000 | 1.0000 | 1.0000 | 0.0981 | nan | 6.3574 |
| home | cegr | 9 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.0000 | 9.8102 |
| laptop | bm25 | 6 | 1.0000 | 1.0000 | 1.0000 | 0.1722 | nan | 10.6647 |
| laptop | cegr | 6 | 1.0000 | 1.0000 | 1.0000 | 0.0000 | 0.2667 | 11.0263 |
| mobile | bm25 | 23 | 1.0000 | 1.0000 | 1.0000 | 0.1367 | nan | 8.0832 |
| mobile | cegr | 23 | 1.0000 | 0.9565 | 0.9679 | 0.0000 | 0.5217 | 8.1685 |
| television | bm25 | 15 | 1.0000 | 1.0000 | 1.0000 | 0.1408 | nan | 5.5996 |
| television | cegr | 15 | 1.0000 | 0.9000 | 0.9262 | 0.0000 | 0.5218 | 7.8625 |
| unknown | bm25 | 372 | 1.0000 | 0.9933 | 0.9950 | 0.1290 | nan | 4.4496 |
| unknown | cegr | 372 | 0.9543 | 0.9449 | 0.9473 | 0.0000 | 0.2320 | 9.9120 |

## Index and machine conditions

Index build/cold-start cost: 99.362s; Python traced peak during construction: 357,373,100 bytes; process RSS after indexing: 217,518,080 bytes; physical RAM: 7,866,085,376 bytes; platform: Windows 11; AMD Ryzen 5 5500U with Radeon Graphics; 12 logical threads; Python 3.14.0. The measured mean CEGR request path is 25.89 ms and p95 is 83.86 ms; p95 includes initial per-product aspect-cache work. These are local single-process measurements, not platform-scale estimates.

## Test metrics

| split | method | queries | recall@5 | recall@10 | mrr@10 | ndcg@3 | ndcg@10 | constraint_violation_rate | attribute_coverage | evidence_coverage | mean_latency_ms | retrieval_latency_ms | ranking_latency_ms | p95_latency_ms |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| test | bm25 | 428 | 1.0000 | 1.0000 | 0.9942 | 0.9957 | 0.9957 | 0.1296 | nan | nan | 5.1091 | 4.6243 | 0.0000 | 8.8314 |
| test | hybrid | 428 | 1.0000 | 1.0000 | 0.9926 | 0.9945 | 0.9945 | 0.1351 | nan | nan | 5.3350 | 5.0554 | 0.0000 | 9.3145 |
| test | dense | 428 | 1.0000 | 1.0000 | 0.9938 | 0.9954 | 0.9954 | 0.1351 | nan | nan | 4.7765 | 4.5056 | 0.0000 | 8.3725 |
| test | cegr | 428 | 0.9603 | 0.9603 | 0.9463 | 0.9499 | 0.9499 | 0.0000 | 0.0327 | 0.2529 | 25.8903 | 5.1982 | 20.5242 | 83.8575 |
| test | cegr_no_constraints | 428 | 1.0000 | 1.0000 | 0.9844 | 0.9884 | 0.9884 | 0.1360 | 0.0276 | 0.2558 | 9.8952 | 5.1593 | 4.5660 | 14.5442 |
| test | cegr_no_reviews | 428 | 0.9603 | 0.9603 | 0.9544 | 0.9560 | 0.9560 | 0.0000 | 0.0323 | 0.0000 | 7.7217 | 5.1899 | 2.3632 | 12.1207 |
| test | cegr_lambdamart | 428 | 0.9603 | 0.9603 | 0.9579 | 0.9586 | 0.9586 | 0.0000 | 0.0306 | 0.2526 | 23.9220 | 8.5225 | 15.1034 | 38.2196 |

## Reproduction

Run `python scripts/download_data.py`, `python scripts/validate_data.py`, `python scripts/build_dataset.py`, `python scripts/generate_benchmark.py`, then `python scripts/run_experiments.py`. Chart: `reports/generated/retrieval_metrics.png`.
