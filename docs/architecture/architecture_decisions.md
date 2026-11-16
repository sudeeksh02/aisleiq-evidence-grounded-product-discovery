# Architecture decision records

## ADR 001: Modular monolith

**Decision:** one FastAPI process with explicit Python module boundaries.

**Reason:** retrieval, review parsing and catalog reads share one small dataset and model lifecycle. A single process keeps local setup simple while retaining independently understandable modules. Separate services would add network and deployment costs without evidence they are needed.

## ADR 002: SQLite by default; PostgreSQL supported

**Decision:** SQLAlchemy with a local SQLite file and portable indexed ORM model.

**Reason:** reproducible local development without a database server. `DATABASE_URL` can point at PostgreSQL. The repository’s data size does not demonstrate that Postgres is required for this prototype.

## ADR 003: Optional pretrained semantic retrieval

**Decision:** BM25 always works; sentence-transformers (`all-MiniLM-L6-v2`) and FAISS are optional extras, with exact NumPy cosine similarity as the implemented dense index path.

**Reason:** CPU and model availability vary. The API never labels lexical-only fallback as semantic. Exact cosine is adequate at this catalog size; FAISS is not needed for only 958 groups.

## ADR 004: Train LambdaMART only as weak supervision

**Decision:** include a LambdaMART experiment trained only from product-disjoint synthetic metadata labels, and do not describe it as a customer-relevance model.

**Reason:** no acquired customer query-to-product graded relevance labels exist. The title-template benchmark supplies a synthetic single positive generated from the source product title, price and review aspect. LambdaMART demonstrates grouped ranking mechanics under explicitly weak supervision. Validation chose one boosting iteration and test MRR remains below BM25, so the model has not demonstrated a relevance improvement. Product order and engagement are never labels.

## ADR 005: Heuristic confidence with abstention

**Decision:** score confidence from attribute and review evidence coverage, cap it when no source review supports the requested aspects, disclose missing evidence, and return no results when hard constraints exclude all candidates.

**Reason:** there are no calibration labels. A calibrated probability would be unsupported. The score is a relative evidence indicator and must not be read as a success probability.
