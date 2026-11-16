from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

from aisleiq.models import Product


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.docs = [tokens(d) for d in docs]
        self.k1, self.b = k1, b
        self.lengths = [len(d) for d in self.docs]
        self.avg_len = sum(self.lengths) / max(1, len(self.lengths))
        self.tf = [Counter(d) for d in self.docs]
        df = Counter(t for doc in self.docs for t in set(doc))
        self.idf = {t: math.log(1 + (len(docs) - n + 0.5) / (n + 0.5)) for t, n in df.items()}

    def score(self, query: str) -> np.ndarray:
        result = np.zeros(len(self.docs), dtype=np.float32)
        for term in set(tokens(query)):
            idf = self.idf.get(term, 0.0)
            for i, tf in enumerate(self.tf):
                freq = tf.get(term, 0)
                if freq:
                    denom = freq + self.k1 * (
                        1 - self.b + self.b * self.lengths[i] / max(1, self.avg_len)
                    )
                    result[i] += idf * freq * (self.k1 + 1) / denom
        return result


class DenseEncoder:
    """CPU sentence-transformers encoder; exact cosine fallback is explicit when unavailable."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self.error: str | None = None
        try:
            import torch

            torch.set_num_threads(min(4, torch.get_num_threads()))
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(model_name, device="cpu")
        except Exception as exc:  # optional model, keep lexical service usable
            self.error = f"Dense model unavailable: {type(exc).__name__}: {exc}"

    def encode(self, texts: list[str]) -> np.ndarray | None:
        if self.model is None:
            return None
        return np.asarray(
            self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False),
            dtype=np.float32,
        )


class Retriever:
    def __init__(self, products: list[Product], use_dense: bool = True):
        self.products = products
        self.docs = [
            f"{p.title} {p.category} {p.description} {' '.join(p.attributes.values())}"
            for p in products
        ]
        self.bm25 = BM25(self.docs)
        self.encoder = DenseEncoder() if use_dense else None
        self.vectors = self.encoder.encode(self.docs) if self.encoder else None
        self.faiss_index = None
        if self.vectors is not None:
            try:
                import faiss

                self.faiss_index = faiss.IndexFlatIP(self.vectors.shape[1])
                self.faiss_index.add(self.vectors)
            except ImportError:
                self.faiss_index = None

    @staticmethod
    def _order(scores: np.ndarray, n: int) -> list[int]:
        return np.argsort(-scores)[:n].tolist()

    def retrieve(
        self, query: str, n: int = 100, mode: str = "hybrid", query_vector: np.ndarray | None = None
    ) -> list[tuple[int, float]]:
        lexical = self.bm25.score(query)
        if mode == "bm25":
            return [(i, float(lexical[i])) for i in self._order(lexical, n)]
        encoded = (
            np.asarray([query_vector])
            if query_vector is not None
            else self.encoder.encode([query])
            if self.encoder and self.vectors is not None
            else None
        )
        qvec = encoded[0] if encoded is not None else None
        if self.vectors is not None and qvec is not None and self.faiss_index is not None:
            dense_scores, dense_ids = self.faiss_index.search(
                qvec.reshape(1, -1), min(n, len(self.products))
            )
            dense = None
            dense_order = [
                (int(idx), float(score))
                for idx, score in zip(dense_ids[0], dense_scores[0])
                if idx >= 0
            ]
        else:
            dense = self.vectors @ qvec if self.vectors is not None and qvec is not None else None
            dense_order = (
                [(i, float(dense[i])) for i in self._order(dense, n)] if dense is not None else []
            )
        if mode == "dense":
            return dense_order
        # RRF is rank-based, avoiding uncalibrated score-scale comparisons.
        ranks: dict[int, float] = {}
        for channel in (self._order(lexical, n), [idx for idx, _ in dense_order]):
            for rank, idx in enumerate(channel, start=1):
                ranks[idx] = ranks.get(idx, 0.0) + 1 / (60 + rank)
        return sorted(ranks.items(), key=lambda pair: pair[1], reverse=True)[:n]
