# Interview preparation notes

## Why hybrid retrieval?

Catalog titles often use exact model names, while users express goals and synonyms. BM25 is strong on rare exact terms; dense embeddings can match semantically related wording. They make complementary errors, so rank fusion can be more robust. AisleIQ’s dense path is optional and is omitted from result metrics if not installed.

## Why BM25?

It weights informative terms by inverse document frequency, saturates repeated term frequency, and normalizes for document length. It is fast, interpretable, and provides a credible baseline for exact product names.

## Why dense embeddings?

A bi-encoder maps query and product text into a shared vector space, allowing similarity despite vocabulary differences. A small sentence-transformer model can run on CPU. The cost is model memory, inference latency, and dependence on embedding quality.

## Why reciprocal rank fusion?

The BM25 and cosine scores are on different scales. RRF uses rank position: each document gets a sum of `1 / (k + rank)` across channels. It avoids score calibration and is simple to audit.

## Why hard constraints before ranking?

A product above a stated maximum budget should not win because it has excellent semantic relevance. Filter known violations before computing soft preferences. Unknown prices are uncertainty, not evidence of compliance; a production policy might abstain on these when a strict budget was supplied.

## How LambdaMART works

LambdaMART combines gradient-boosted decision trees with LambdaRank’s pairwise gradients weighted by ranking metric impact, often nDCG. Training examples must be grouped by query and have valid graded judgments. Here, the only labels are weak synthetic title matches, so training a ranking model would overstate the available evidence.

## How nDCG is calculated

For a ranked list, `DCG@k = Σ (2^rel_i - 1) / log2(i + 1)` with one-based rank. Divide by ideal DCG (the same grades sorted descending) to get nDCG in `[0,1]`. It emphasizes relevant items near the top.

## How query leakage happens

If variants of one query, or products tied to that query, appear in both train and test, evaluation memorizes the entity or wording. Split by query group (and where needed product/entity) before generating variants. This project splits synthetic records by source product ID; the retrieval corpus remains the catalog, while no relevance labels are used to fit a model.

## Confidence and calibration

Confidence should be checked against held-out outcomes: group predictions into bins, compare predicted confidence with empirical success, and report calibration error/Brier score. AisleIQ has no judged outcomes, so its number is an evidence-coverage heuristic only. It lowers when aspects/reviews are absent and explanations list the missing evidence.

## Latency and scaling

Batch encode the catalog offline; reuse one model/index; filter candidate sets before expensive reranking; cache repeated queries; use vector indexes only when corpus size warrants them; measure cold and warm latency separately. A larger service would add catalog refresh/versioning, distributed search, model lifecycle management, observability, and carefully designed offline/online evaluation. This 958-product local dataset cannot establish Flipkart-scale performance.

## Trade-offs

The project favors reproducible, traceable evidence and honest fallback behavior over a learned ranker without labels. Rule-based aspects are explainable but linguistically brittle. SQLite is simple for local runs; a Postgres URL is supported. Dense search and FAISS are optional because exact cosine is enough for the observed catalog size.
