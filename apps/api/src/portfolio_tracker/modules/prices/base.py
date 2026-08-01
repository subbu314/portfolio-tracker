from typing import Protocol


class PriceProvider(Protocol):
    def get_history(
        self, symbol: str, start: str, end: str
    ) -> list[tuple[str, float]]: ...

    def get_ltp(self, symbol: str) -> float | None: ...
