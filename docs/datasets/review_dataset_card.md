# Dataset card: Flipkart Product Customer Reviews

**Source:** Kaggle dataset by Nirali Vaghani, version 1: https://www.kaggle.com/datasets/niraliivaghani/flipkart-product-customer-reviews-dataset

**Retrieved artifact:** `Dataset-SA.csv`; 205,052 rows and 6 columns in the downloaded archive. CSV SHA-256 is recorded in local `data/raw/provenance.json` (raw file is not committed).

**Fields:** product name, product price, 1–5 rating, review title/body fields (`Review`, `Summary`), and source sentiment label. The data card attributes collection to web scraping in December 2022. The file has 958 distinct product names, 34,375 duplicate full rows, 24,664 missing review texts and 11 missing summaries. The uploader’s page description says 104 products and 205,053 rows; the downloaded version differs.

**Uses:** local product-name catalog, review aspect evidence prototype, synthetic title-query retrieval smoke test.

**Not appropriate for:** claims about current inventory/prices; customer search relevance; genuine customer query generation; unbiased population sentiment; purchase propensity; user personalization; production-scale estimates.

**License/provenance:** Kaggle page lists DbCL v1.0. Consult the license and uploader’s terms before redistribution. No raw rows are published by this repository. Source descriptions are not independently audited.
