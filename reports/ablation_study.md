# Ablation study

All values use the held-out synthetic metadata-derived test split. They are not causal estimates for customer relevance.

| Variant | Recall@10 | MRR@10 | nDCG@10 | Constraint violation | Attribute coverage | Evidence coverage | Mean latency ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| bm25 | 1.0000 | 0.9942 | 0.9957 | 0.1296 | n/a | n/a | 5.1091 |
| hybrid | 1.0000 | 0.9926 | 0.9945 | 0.1351 | n/a | n/a | 5.3350 |
| dense | 1.0000 | 0.9938 | 0.9954 | 0.1351 | n/a | n/a | 4.7765 |
| cegr | 0.9603 | 0.9463 | 0.9499 | 0.0000 | 0.0327 | 0.2529 | 25.8903 |
| cegr_no_constraints | 1.0000 | 0.9844 | 0.9884 | 0.1360 | 0.0276 | 0.2558 | 9.8952 |
| cegr_no_reviews | 0.9603 | 0.9544 | 0.9560 | 0.0000 | 0.0323 | 0.0000 | 7.7217 |
| cegr_lambdamart | 0.9603 | 0.9579 | 0.9586 | 0.0000 | 0.0306 | 0.2526 | 23.9220 |

Removing constraints is evaluated on synthetic budget queries whose ceilings are derived from the target product's source price. Removing evidence disables review features. Removing dense retrieval is the BM25-only baseline; removing BM25 is the dense-only baseline. The LambdaMART row compares the weakly supervised learned ranker with deterministic CEGR. It was selected at validation iteration 1 and its test MRR remains below BM25. It is not a customer relevance model. Synthetic labels are source-product associations derived from metadata, never clicks or purchase data.
