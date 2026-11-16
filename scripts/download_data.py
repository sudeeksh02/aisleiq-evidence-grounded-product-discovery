#!/usr/bin/env python3
"""Download the public Kaggle review archive; no login/cookies or scraping required."""

from __future__ import annotations

import hashlib
import json
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
URL = "https://www.kaggle.com/api/v1/datasets/download/niraliivaghani/flipkart-product-customer-reviews-dataset?datasetVersionNumber=1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    archive = RAW / "flipkart-reviews.zip"
    request = urllib.request.Request(URL, headers={"User-Agent": "AisleIQ/0.1 dataset-fetcher"})
    with urllib.request.urlopen(request, timeout=90) as response, archive.open("wb") as out:
        while chunk := response.read(1024 * 1024):
            out.write(chunk)
    with zipfile.ZipFile(archive) as zf:
        members = [m for m in zf.infolist() if Path(m.filename).name.lower() == "dataset-sa.csv"]
        if not members:
            raise RuntimeError(
                f"Dataset-SA.csv not present; archive contains {[m.filename for m in zf.infolist()]}"
            )
        target = RAW / "Dataset-SA.csv"
        with zf.open(members[0]) as src, target.open("wb") as dst:
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)
    metadata = {
        "source": "https://www.kaggle.com/datasets/niraliivaghani/flipkart-product-customer-reviews-dataset",
        "dataset_version": 1,
        "download_endpoint": URL,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive_sha256": sha256(archive),
        "csv_sha256": sha256(target),
        "archive_bytes": archive.stat().st_size,
        "csv_bytes": target.stat().st_size,
        "file": target.name,
    }
    (RAW / "provenance.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
