# Industry problem: product discovery with explicit constraints

## Scope

Shopping search has to map short, ambiguous natural-language needs to a large, incomplete and changing catalog. A useful result must simultaneously identify the intended product class, retrieve candidates despite vocabulary mismatch, respect hard requirements such as budget, and help a person evaluate subjective attributes such as battery life from review evidence. A ranking can be relevant on average and still be unusable when it violates a stated budget or asserts a benefit that the source data never measured.

This project focuses on a reproducible, offline version of that problem: query understanding, catalog retrieval, deterministic hard-constraint filtering, review evidence extraction, and explanations whose quotations retain source review IDs. It is a research prototype using a public historical review dataset. It does not reproduce Flipkart’s private systems, internal data, traffic, or production ranking decisions.

## Publicly documented engineering context

Flipkart’s public engineering articles describe ranking as a staged pipeline rather than one opaque score. Its unified ranking article discusses candidate sourcing, filtering, personalized ranking, score calibration, and the challenge of comparing sponsored and organic recommendations. The reported production experiment concerns its Similar Products widget, not this prototype: [The Science of Unified Ranking](https://blog.flipkart.tech/the-science-of-unified-ranking-integrating-ads-and-organic-recommendations-8cc24113ef21).

Flipkart’s autosuggestion article frames query suggestions as a relevance problem with latency-sensitive scoring and user intent signals: [Multi-Objective Optimisation in Suggestions Ranking @ Flipkart](https://blog.flipkart.tech/multi-objective-optimisation-in-suggestions-ranking-flipkart-49099b951eae). These examples motivate separating retrieval, filtering and ranking, and measuring latency, while the implementation and data here remain independent.

## AisleIQ problem statement

Given a natural-language request and a catalog built from the available source data, return products that:

1. Match the requested category and terms.
2. Obey parsed price bounds when the catalog has a price.
3. Show which requested attributes are present in catalog text.
4. Present only verbatim excerpts from associated source reviews as evidence.
5. Disclose missing prices, attributes, or review evidence, and lower confidence when evidence is sparse.

The current review CSV has product names, prices, ratings, review text, summaries and dataset sentiment labels. It does not have genuine customer queries, product descriptions/specifications, query-product relevance judgments, impressions, clicks, purchases, seller data, or delivery data. The system does not infer those fields from a product’s source order or manufacture engagement labels.

## Quality and operational concerns

- Hard constraints must be checked before soft ranking. Unknown prices cannot be treated as verified budget compliance.
- Lexical retrieval is fast and precise for catalog vocabulary but misses paraphrases and synonyms.
- Dense retrieval may improve semantic matching but adds model download, memory and CPU latency costs.
- Review sentiment is aspect-specific and noisy. Aspect dictionaries are transparent heuristics, not trained classifiers or human annotations.
- Relevance metrics need query-level judgments. The included title-derived benchmark is only a weak, synthetic smoke-test task.
- A local benchmark does not establish production-scale throughput or quality.
