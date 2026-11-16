# Model card: CEGR prototype

## Intended use

Local research prototype for retrieving catalog entries from free-text requests, filtering known hard price/category constraints, surfacing aspect-matched review text, and disclosing missing evidence.

## Components

- Query parser: regular expressions, aliases and category lexicon.
- Lexical retrieval: project-local BM25 implementation.
- Semantic retrieval: optional `sentence-transformers/all-MiniLM-L6-v2`, CPU inference, normalized cosine similarities. If unavailable, BM25-only fallback is explicit.
- Fusion: Reciprocal Rank Fusion with constant 60.
- Ranking: deterministic CEGR feature score plus an optional, checked-in LightGBM LambdaMART model. The model is trained on synthetic source-product association labels only and was selected at iteration 1 on validation; it is a learning-to-rank implementation example, not a customer relevance model.
- Review analysis: phrase lexicon for aspects and polarity plus source star rating. No generative model; excerpts are not synthesized.
- Confidence: heuristic coverage indicator. Not probability-calibrated.

## Limitations and risks

The source has no customer queries, graded relevance, or current catalog. Query parsing can miss language variants and negation scope. Aspect matching and sentiment lexicons can be wrong, especially under sarcasm, negation, or multilingual text. The synthetic benchmark rewards title overlap. The optional embedding model has not been benchmarked until the optional dependencies and weights are available. No claim is made that outputs reproduce Flipkart systems.

## Abstention behavior

Known out-of-budget items are filtered before soft scoring; unknown prices cannot be confirmed as budget-compliant and are disclosed. If all candidates fail hard constraints, search returns no result. Missing review evidence is stated, confidence is capped, and source excerpts appear only when a source row exists.
