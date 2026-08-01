from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass
from datetime import date
from typing import Literal, TypedDict

from sqlalchemy.orm import Session

from portfolio_tracker.db.models import Instrument, Transaction

FormatName = Literal["console_tradebook"]
CONSOLE_REQUIRED = {"symbol", "trade_date", "trade_type", "quantity", "price"}


class ImportResult(TypedDict):
    format: FormatName
    new: int
    existing: int
    segment_counts: dict[str, int]
    flagged_rows: list[str]
    date_min: str | None
    date_max: str | None
    financial_years: list[str]


class FileImportOk(TypedDict):
    filename: str
    ok: Literal[True]
    format: FormatName
    new: int
    existing: int
    segment_counts: dict[str, int]
    flagged_rows: list[str]
    date_min: str | None
    date_max: str | None
    financial_years: list[str]


class FileImportErr(TypedDict):
    filename: str
    ok: Literal[False]
    code: Literal["encoding", "csv_format", "csv_parse", "empty"]
    message: str
    errors: list[str]
    action: str


class BatchImportResult(TypedDict):
    files: list[FileImportOk | FileImportErr]
    summary: dict[str, int]


REIMPORT_ACTION = (
    "This file was not imported. Export again from Zerodha Console → Reports → "
    "Tradebook (Equity or Mutual Funds), use a ≤365-day or financial-year window, "
    "UTF-8 CSV, then import this file again. Other files in the same upload are unaffected."
)


class CsvFormatError(Exception):
    pass


class CsvParseError(Exception):
    def __init__(self, message: str, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


@dataclass(frozen=True)
class ParsedRow:
    symbol: str
    isin: str | None
    instrument_type: str
    exchange: str | None
    segment: str
    trade_date: str
    side: str
    quantity: float
    price: float
    fees: float
    order_id: str | None
    dedupe_key: str


def _norm_headers(headers: list[str]) -> list[str]:
    return [header.strip().lower().replace(" ", "_") for header in headers]


def detect_format(headers: list[str]) -> FormatName:
    normalized = set(_norm_headers(headers))
    if CONSOLE_REQUIRED.issubset(normalized):
        return "console_tradebook"
    raise CsvFormatError(
        "Unrecognized CSV. Expected Zerodha Console tradebook "
        "(Reports → Tradebook → Equity or Mutual Funds)."
    )


def _parse_side(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"buy", "b"}:
        return "buy"
    if normalized in {"sell", "s"}:
        return "sell"
    raise ValueError(f"unknown trade side '{value}'")


def _parse_number(value: str, field: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"invalid {field} '{value}'") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"invalid {field} '{value}'")
    return parsed


def _parse_positive_number(value: str, field: str) -> float:
    parsed = _parse_number(value, field)
    if parsed <= 0:
        raise ValueError(f"{field} must be positive")
    return parsed


def _parse_non_negative_number(value: str, field: str) -> float:
    parsed = _parse_number(value, field)
    if parsed < 0:
        raise ValueError(f"{field} must be non-negative")
    return parsed


def _parse_trade_date(value: str) -> str:
    raw = value.strip()
    try:
        return date.fromisoformat(raw[:10]).isoformat()
    except ValueError as exc:
        raise ValueError(f"invalid trade_date '{value}'") from exc


def _instrument_type(segment: str, symbol: str, series: str) -> tuple[str, str | None]:
    if segment == "MF":
        return "mf", None
    if segment in {"", "EQ"}:
        normalized_symbol = symbol.upper()
        normalized_series = series.strip().upper()
        is_etf = (
            "ETF" in normalized_symbol
            or normalized_symbol.endswith("BEES")
            or normalized_series == "ETF"
        )
        return ("etf" if is_etf else "equity"), None
    return "equity", f"unexpected segment {segment}"


def _parse_console_row(row: dict[str, str]) -> tuple[ParsedRow, str | None]:
    symbol = row["symbol"].strip().upper()
    if not symbol:
        raise ValueError("symbol is required")
    trade_date = _parse_trade_date(row["trade_date"])
    side = _parse_side(row["trade_type"])
    quantity = _parse_positive_number(row["quantity"], "quantity")
    price = _parse_positive_number(row["price"], "price")
    fees = _parse_non_negative_number(row.get("fees") or "0", "fees")
    segment = (row.get("segment") or "EQ").strip().upper() or "EQ"
    order_id = (row.get("order_id") or row.get("trade_id") or "").strip() or None
    isin = (row.get("isin") or "").strip().upper() or None
    exchange = (row.get("exchange") or "").strip().upper() or None
    instrument_type, flag_reason = _instrument_type(
        segment, symbol, row.get("series") or ""
    )
    stable_fallback = "|".join(
        (
            exchange or "",
            format(fees, ".15g"),
            (row.get("order_execution_time") or "").strip().upper(),
            isin or "",
        )
    )
    dedupe_key = (
        f"csv:{segment}:{symbol}:{trade_date}:{side}:"
        f"{quantity}:{price}:{order_id or stable_fallback}"
    )
    return (
        ParsedRow(
            symbol=symbol,
            isin=isin,
            instrument_type=instrument_type,
            exchange=exchange,
            segment=segment,
            trade_date=trade_date,
            side=side,
            quantity=quantity,
            price=price,
            fees=fees,
            order_id=order_id,
            dedupe_key=dedupe_key,
        ),
        flag_reason,
    )


def get_or_create_instrument(
    session: Session,
    *,
    symbol: str,
    isin: str | None,
    instrument_type: str,
    exchange: str | None,
) -> Instrument:
    instrument = None
    if isin:
        instrument = session.query(Instrument).filter(Instrument.isin == isin).first()
    if instrument is None:
        instrument = session.query(Instrument).filter(Instrument.symbol == symbol).first()
    if instrument is not None:
        return instrument

    yahoo_symbol = f"{symbol}.NS" if instrument_type in {"equity", "etf"} else None
    instrument = Instrument(
        symbol=symbol,
        isin=isin,
        instrument_type=instrument_type,
        exchange=exchange,
        yahoo_symbol=yahoo_symbol,
    )
    session.add(instrument)
    session.flush()
    return instrument


def _parse_console_rows(
    rows: list[dict[str, str]],
) -> tuple[list[ParsedRow], dict[str, int], list[str]]:
    parsed_rows: list[ParsedRow] = []
    errors: list[str] = []
    segment_counts: dict[str, int] = {}
    flagged_rows: list[str] = []

    for row_number, row in enumerate(rows, start=2):
        try:
            parsed_row, flag_reason = _parse_console_row(row)
            segment_counts[parsed_row.segment] = (
                segment_counts.get(parsed_row.segment, 0) + 1
            )
            if flag_reason:
                flagged_rows.append(
                    f"row {row_number}: {parsed_row.symbol} {flag_reason}"
                )
            parsed_rows.append(parsed_row)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"row {row_number}: {exc}")

    if errors:
        raise CsvParseError("Console tradebook parse failed", errors)
    return parsed_rows, segment_counts, flagged_rows


def financial_year_label(iso_date: str) -> str:
    d = date.fromisoformat(iso_date[:10])
    start_year = d.year if d.month >= 4 else d.year - 1
    return f"FY{start_year}-{str(start_year + 1)[-2:]}"


def financial_years_spanned(date_min: str | None, date_max: str | None) -> list[str]:
    if not date_min or not date_max:
        return []
    start = date.fromisoformat(date_min[:10])
    end = date.fromisoformat(date_max[:10])
    labels: list[str] = []
    year = start.year if start.month >= 4 else start.year - 1
    while True:
        fy_start = date(year, 4, 1)
        fy_end = date(year + 1, 3, 31)
        if fy_end < start:
            year += 1
            continue
        if fy_start > end:
            break
        labels.append(f"FY{year}-{str(year + 1)[-2:]}")
        year += 1
    return labels


def import_csv(session: Session, text: str) -> ImportResult:
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise CsvFormatError("CSV has no headers")

    normalized_headers = _norm_headers(list(reader.fieldnames))
    format_name = detect_format(normalized_headers)
    raw_rows = [
        {
            normalized_headers[index]: value or ""
            for index, value in enumerate(row.values())
            if index < len(normalized_headers)
        }
        for row in reader
    ]
    parsed_rows, segment_counts, flagged_rows = _parse_console_rows(raw_rows)

    imported_keys: set[str] = set()
    new = 0
    existing = 0
    for row in parsed_rows:
        already_imported = row.dedupe_key in imported_keys or (
            session.query(Transaction)
            .filter(Transaction.dedupe_key == row.dedupe_key)
            .first()
            is not None
        )
        if already_imported:
            existing += 1
            continue

        instrument = get_or_create_instrument(
            session,
            symbol=row.symbol,
            isin=row.isin,
            instrument_type=row.instrument_type,
            exchange=row.exchange,
        )
        session.add(
            Transaction(
                instrument_id=instrument.id,
                trade_date=row.trade_date,
                side=row.side,
                quantity=row.quantity,
                price=row.price,
                fees=row.fees,
                source="csv",
                dedupe_key=row.dedupe_key,
                raw_order_id=row.order_id,
            )
        )
        imported_keys.add(row.dedupe_key)
        new += 1

    dates = [row.trade_date for row in parsed_rows]
    date_min = min(dates) if dates else None
    date_max = max(dates) if dates else None
    return {
        "format": format_name,
        "new": new,
        "existing": existing,
        "segment_counts": segment_counts,
        "flagged_rows": flagged_rows,
        "date_min": date_min,
        "date_max": date_max,
        "financial_years": financial_years_spanned(date_min, date_max),
    }


def import_csv_batch(
    session: Session, files: list[tuple[str, str]]
) -> BatchImportResult:
    out: list[FileImportOk | FileImportErr] = []
    total_new = 0
    total_existing = 0
    accepted = 0
    rejected = 0
    for filename, text in files:
        if not text.strip():
            rejected += 1
            out.append(
                {
                    "filename": filename,
                    "ok": False,
                    "code": "empty",
                    "message": "CSV file is empty",
                    "errors": [],
                    "action": REIMPORT_ACTION,
                }
            )
            continue
        nested = session.begin_nested()
        try:
            result = import_csv(session, text)
            nested.commit()
            accepted += 1
            total_new += result["new"]
            total_existing += result["existing"]
            out.append({"filename": filename, "ok": True, **result})
        except CsvFormatError as exc:
            nested.rollback()
            rejected += 1
            out.append(
                {
                    "filename": filename,
                    "ok": False,
                    "code": "csv_format",
                    "message": str(exc),
                    "errors": [],
                    "action": REIMPORT_ACTION,
                }
            )
        except CsvParseError as exc:
            nested.rollback()
            rejected += 1
            out.append(
                {
                    "filename": filename,
                    "ok": False,
                    "code": "csv_parse",
                    "message": str(exc),
                    "errors": exc.errors,
                    "action": REIMPORT_ACTION,
                }
            )
    return {
        "files": out,
        "summary": {
            "accepted": accepted,
            "rejected": rejected,
            "new": total_new,
            "existing": total_existing,
        },
    }
