# Error analysis

## Measured errors on the held-out synthetic split

The 428-query test set contains exactly one weak source-product target per query. BM25, dense and hybrid each retrieved the target in their top 10 for all 428 queries. CEGR and CEGR + LambdaMART each missed 17 targets at top 10 (Recall@10 0.9603). The deterministic CEGR MRR@10 was 0.9463; LambdaMART reached 0.9579, still below BM25 (0.9942). These misses belong to the synthetic title/metadata task, not observed customer searches.

By inferred category, the 17 CEGR top-10 misses are concentrated in the `unknown` title-derived category (17/372 queries, Recall@10 0.9543). Other categories have fewer than 30 test examples and show Recall@10 1.0, but these small samples do not establish category reliability. In those categories, CEGR MRR still fell below 1.0 for mobile and television queries, indicating that the target was retrieved but demoted.

## Constraint/evidence trade-off

CEGR reduced the known synthetic constraint violation rate from 0.1296 for BM25 to 0.0000, while lowering Recall@10 from 1.0000 to 0.9603 and increasing mean measured request-path latency from 5.11 ms to 25.89 ms. Removing hard constraints restored Recall@10 to 1.0000 and restored violation rate to 0.1360. This confirms the filter is doing work on generated budget/category cases, but the benchmark does not quantify customer satisfaction from that trade-off.

Evidence features exposed review excerpts for 25.3% of the top ten result slots on this set. This is coverage, not evidence correctness scoring: no human judgments exist. Removing review scoring yielded MRR@10 0.9544 versus 0.9463 for full CEGR, so the current heuristic evidence score slightly harms ordering on this synthetic test while adding traceable review signals. The learned ranker is also slower than plain retrieval and performs below BM25.

## Likely failure modes (not separately labeled)

- The exact title in the generated query creates unusually strong lexical overlap and masks vocabulary-gap failures.
- Generic title tokens and aliases can conflate distinct products or categories.
- Category inference is a simple title keyword rule; `unknown` affects 372/428 test queries.
- Review aspect terms are dictionary matches and can overcount ambiguous uses of words such as “screen” or “quality.”
- Polarity uses a short word list and star rating; negation, sarcasm, multilingual reviews and mixed statements can be misclassified.
- Budget thresholds are synthetic values derived from the target price, not user budgets.

Per-query rankings are not currently serialized. All listed aggregate measurements are from `reports/generated/metrics.json` and `category_metrics.json`; no error examples or model wins are fabricated.
