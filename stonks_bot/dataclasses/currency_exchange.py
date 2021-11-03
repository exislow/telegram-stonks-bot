from dataclasses import dataclass
from dataclasses_json import dataclass_json
from datetime import datetime


@dataclass_json
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
