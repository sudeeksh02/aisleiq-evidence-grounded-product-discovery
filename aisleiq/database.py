from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy import Index, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class ProductRow(Base):
    __tablename__ = "products"
    product_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(500), index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    price: Mapped[float | None]
    payload: Mapped[str] = mapped_column(Text)


Index("ix_products_category_price", ProductRow.category, ProductRow.price)
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./data/aisleiq.db")
engine = create_engine(
    DB_URL, connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
)
Session = sessionmaker(bind=engine)


def initialize(products_path: Path) -> int:
    Base.metadata.create_all(engine)
    if not products_path.exists():
        return 0
    with Session.begin() as session:
        session.query(ProductRow).delete()
        count = 0
        for line in products_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            session.add(
                ProductRow(
                    product_id=item["product_id"],
                    title=item["title"],
                    category=item["category"],
                    price=item["price"],
                    payload=line,
                )
            )
            count += 1
    return count


def all_payloads() -> list[str]:
    with Session() as session:
        return list(session.scalars(select(ProductRow.payload).order_by(ProductRow.product_id)))


def get_payload(product_id: str) -> str | None:
    with Session() as session:
        return session.scalar(select(ProductRow.payload).where(ProductRow.product_id == product_id))
