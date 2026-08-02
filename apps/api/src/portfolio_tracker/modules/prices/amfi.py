from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Any

import httpx


HttpGet = Callable[[str], Any]


def _parse_nav_date(value: str) -> str:
    return datetime.strptime(value, "%d-%m-%Y").strftime("%Y-%m-%d")


def _normalize_category(category: str | None) -> str | None:
    if not category:
        return None
    lower_category = category.lower()
    if "flexi" in lower_category:
        return "Flexi Cap"
    if "large" in lower_category and "mid" not in lower_category:
        return "Large Cap"
    if "mid" in lower_category:
        return "Mid Cap"
    if "small" in lower_category:
        return "Small Cap"
    return category


class AmfiNavProvider:
    def __init__(self, http_get: HttpGet | None = None):
        self._http_get = http_get or self._default_get
        self._isin_scheme_codes: dict[str, str] | None = None

    def _default_get(self, url: str) -> Any:
        # Scheme list (/mf) is multi-MB; allow a longer timeout.
        timeout = 120.0 if url.rstrip("/").endswith("/mf") else 30.0
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return response.json()

    def _scheme_payload(self, scheme_code: str) -> dict[str, Any]:
        payload = self._http_get(f"https://api.mfapi.in/mf/{scheme_code}")
        return payload if isinstance(payload, dict) else {}

    def _isin_index(self) -> dict[str, str]:
        if self._isin_scheme_codes is not None:
            return self._isin_scheme_codes
        # mfapi /mf/search does not resolve ISINs; /mf list includes isinGrowth fields.
        data = self._http_get("https://api.mfapi.in/mf")
        index: dict[str, str] = {}
        if isinstance(data, list):
            for row in data:
                if not isinstance(row, dict):
                    continue
                scheme_code = row.get("schemeCode") or row.get("scheme_code")
                if scheme_code is None:
                    continue
                code = str(scheme_code)
                for key in ("isinGrowth", "isinDivReinvestment", "isin_growth"):
                    isin = row.get(key)
                    if isinstance(isin, str) and isin.strip():
                        index.setdefault(isin.strip().upper(), code)
        self._isin_scheme_codes = index
        return index

    def find_scheme_code_by_isin(self, isin: str) -> str | None:
        normalized = isin.strip().upper()
        data = self._http_get(f"https://api.mfapi.in/mf/search?q={normalized}")
        if isinstance(data, list) and data:
            scheme_code = data[0].get("schemeCode") or data[0].get("scheme_code")
            if scheme_code is not None:
                return str(scheme_code)
        return self._isin_index().get(normalized)

    def get_history(
        self, symbol: str, start: str, end: str
    ) -> list[tuple[str, float]]:
        payload = self._scheme_payload(symbol)
        rows = [
            (_parse_nav_date(item["date"]), float(item["nav"]))
            for item in payload.get("data", [])
        ]
        return sorted(row for row in rows if start <= row[0] <= end)

    def get_ltp(self, symbol: str) -> float | None:
        rows = self.get_history(symbol, "2000-01-01", date.today().isoformat())
        return rows[-1][1] if rows else None

    def get_history_by_isin(
        self, isin: str, start: str, end: str
    ) -> list[tuple[str, float]]:
        scheme_code = self.find_scheme_code_by_isin(isin)
        if scheme_code is None:
            return []
        return self.get_history(scheme_code, start, end)

    def get_ltp_by_isin(self, isin: str) -> float | None:
        scheme_code = self.find_scheme_code_by_isin(isin)
        return self.get_ltp(scheme_code) if scheme_code else None

    def resolve_category(
        self, isin: str, scheme_code: str | None = None
    ) -> tuple[str | None, str | None]:
        scheme_code = scheme_code or self.find_scheme_code_by_isin(isin)
        if scheme_code is None:
            return None, None
        meta = self._scheme_payload(scheme_code).get("meta") or {}
        category = meta.get("scheme_category") or meta.get("scheme_type")
        return _normalize_category(category), scheme_code
