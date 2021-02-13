from dataclasses import dataclass
from datetime import datetime


@dataclass
class CurrencyExchange:
    symbol: str
    _rate: float = 1
    fetched_at: datetime = datetime.now()

    @property
    def rate(self) -> float:
        return self._rate

    @rate.setter
    def rate(self, v: float) -> None:
        self._rate = v
        self.fetched_at = datetime.now()
