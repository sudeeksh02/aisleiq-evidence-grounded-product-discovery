# Data flow

```mermaid
flowchart TD
  A[Kaggle public archive endpoint] --> B[data/raw/Dataset-SA.csv]
  A --> C[provenance.json: timestamps, sizes, SHA-256]
  B --> D[Schema validation + observed counts]
  D --> E[Drop exact duplicate records]
  E --> F[Normalize price, rating, product name]
  F --> G[Product groups + source reviews]
  G --> H[products.jsonl]
  H --> I[SQLite indexed catalog]
  G --> J[Synthetic title query per product]
  J --> K[Product-ID-disjoint 70/15/15 split]
  K --> L[BM25 / optional dense / CEGR evaluation]
  L --> M[metrics JSON, Markdown, chart]
```

Raw data is local and ignored by Git. The source `Sentiment` label is preserved as supplied and not silently treated as human-verified truth. Missing review text is skipped while retaining products; missing prices are represented as null. Titles are grouped case-insensitively only through the source group operation after exact string grouping; IDs hash normalized lower-case titles, so casing-only variations may need review. Review IDs are deterministic for the resulting grouped row order. The manifest records pre-deduplication source stats and output counts.
