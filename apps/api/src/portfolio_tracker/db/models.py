from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    isin: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    instrument_type: Mapped[str] = mapped_column(String(16), nullable=False)  # equity|etf|mf
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True)
    mf_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mf_category_source: Mapped[str | None] = mapped_column(String(16), nullable=True)  # amfi|user|default
    yahoo_symbol: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scheme_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    needs_category: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="instrument")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("dedupe_key", name="uq_transactions_dedupe_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    trade_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    side: Mapped[str] = mapped_column(String(8), nullable=False)  # buy|sell
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    fees: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source: Mapped[str] = mapped_column(String(8), nullable=False)  # csv|api
    dedupe_key: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    instrument: Mapped["Instrument"] = relationship(back_populates="transactions")


class HoldingsSnapshot(Base):
    __tablename__ = "holdings_snapshot"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), nullable=False, unique=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    avg_price: Mapped[float] = mapped_column(Float, nullable=False)
    as_of: Mapped[str] = mapped_column(String(10), nullable=False)


class Price(Base):
    __tablename__ = "prices"
    __table_args__ = (UniqueConstraint("symbol", "price_date", name="uq_prices_symbol_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    price_date: Mapped[str] = mapped_column(String(10), nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # yahoo|amfi


class BenchmarkMap(Base):
    __tablename__ = "benchmark_map"

    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    benchmark_index: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # default|user


class BenchmarkPrice(Base):
    __tablename__ = "benchmark_prices"
    __table_args__ = (UniqueConstraint("index_symbol", "price_date", name="uq_benchmark_prices"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    index_symbol: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    price_date: Mapped[str] = mapped_column(String(10), nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
