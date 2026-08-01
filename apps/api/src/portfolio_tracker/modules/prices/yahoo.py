from __future__ import annotations

from datetime import date
from typing import Any

import yfinance as yf


INDEX_TICKERS: dict[str, str] = {
    "Nifty 500": "^CRSLDX",
    "Nifty 100": "^CNX100",
    "Nifty Midcap 150": "NIFTYMIDCAP150.NS",
    "Nifty Smallcap 250": "NIFTYSMLCAP250.NS",
    "Nifty 50": "^NSEI",
}


class YahooFinanceProvider:
    def __init__(self, client: Any = None):
        self._client = client or yf

    def _ticker(self, symbol: str) -> Any:
        return self._client.Ticker(symbol)

    def _fetch_history(
        self, symbol: str, start: str, end: str
    ) -> list[tuple[str, float]]:
        frame = self._ticker(symbol).history(
            start=start,
            end=end,
            auto_adjust=True,
        )
        if frame is None or frame.empty:
            return []

        rows: list[tuple[str, float]] = []
        for index, row in frame.iterrows():
            day = index.strftime("%Y-%m-%d") if hasattr(index, "strftime") else str(index)[:10]
            rows.append((day, float(row["Close"])))
        return rows

    def get_history(
        self, symbol: str, start: str, end: str
    ) -> list[tuple[str, float]]:
        return self._fetch_history(symbol, start, end)

    def get_ltp(self, symbol: str) -> float | None:
        try:
            last_price = getattr(self._ticker(symbol).fast_info, "last_price", None)
            if last_price is not None:
                return float(last_price)
        except Exception:
            pass

        end = date.today().isoformat()
        history = self.get_history(symbol, "2020-01-01", end)
        return history[-1][1] if history else None
