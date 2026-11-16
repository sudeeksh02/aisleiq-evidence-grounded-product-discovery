# Dataset research and acquisition record

## Flipkart Q2P claim

The linked IIT Bombay survey (“Mind, Matter, and Markets: A Survey of Human-Centered LLM Applications in E-commerce,” Arnav Attri, Anuj Attri and Pushpak Bhattacharyya) states in section 6.1 that a “Flipkart Q2P” dataset contains 7,500 real queries, 22,500 top-three query-product pairs and rich product metadata. Inspection of the public PDF found no data availability section, repository, downloadable archive, request procedure, schema file, or license for that dataset. Therefore the claimed counts and provenance are paper statements only; they are not independently verified, and the files could not be obtained from the cited source. The PDF is not evidence that a public downloadable dataset exists.

No access controls were bypassed. AisleIQ does not use the claimed Q2P records, and does not describe any generated query as a customer query.

## Review dataset (obtained)

- Source: [Flipkart Product Customer Reviews Dataset, Kaggle](https://www.kaggle.com/datasets/niraliivaghani/flipkart-product-customer-reviews-dataset), version 1.
- File: `Dataset-SA.csv`.
- Download: `python scripts/download_data.py` retrieves Kaggle’s public dataset archive endpoint and extracts the named CSV. No Kaggle login is needed for this version at the time verified. The script records retrieval time and SHA-256 hashes to `data/raw/provenance.json`.
- Observed file size: 33,357,584 bytes; SHA-256 `76dbf0cd862347742506769d9c1e3c5b9bcbc540076474ec8a055a2f8b43a787`.
- Observed rows and schema: 205,052 rows; `product_name`, `product_price`, `Rate`, `Review`, `Summary`, `Sentiment`.
- Missing values: 24,664 `Review`; 11 `Summary`; none in product name, price, rating, or sentiment.
- Duplicate full rows: 34,375.
- Distinct product names: 958. Kaggle’s description reports 205,053 rows and 104 products, so those page-level totals do not match this retrieved version.
- Sentiment labels as downloaded: positive 166,581 (81.24%), negative 28,232 (13.77%), neutral 10,239 (4.99%). These labels are supplied by the dataset; they are not recomputed ground truth.
- Dataset page says the content was scraped in December 2022 and labels were based on VADER with manual adjustment. This provenance is attributed to the uploader, not independently audited.
- The Kaggle data card identifies Database Contents License (DbCL) v1.0. Review the source terms before redistributing data. Raw data is ignored by Git and is not published in this repository.

## Processing and splits

The builder drops exact duplicate rows, groups on normalized product name, parses prices to numeric INR, averages numeric ratings, preserves nonempty review/summary text, and assigns each retained review a stable product-derived ID plus row sequence. It stores source review sentiment labels as supplied. Product categories are inferred from title keyword rules and otherwise marked `unknown`; this is a noisy convenience field, not a source label.

The benchmark emits synthetic `find {title}`, budget-ceiling and review-aspect queries and labels only the associated source product. Price ceilings and aspect phrases are derived from source fields. The split is by product ID (70/15/15 with seed 42), so a product’s generated query variants cannot occur across train/validation/test. Catalog products are the retrieval corpus, not interaction data. This construction measures a narrow metadata lookup task and is not a substitute for query-level customer judgments. No real Q2P query groups were available for splitting.

## Reproduction

```bash
python scripts/download_data.py
python scripts/validate_data.py
python scripts/build_dataset.py
python scripts/generate_benchmark.py
```
