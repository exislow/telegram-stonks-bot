from dataclasses import dataclass
from dataclasses_json import dataclass_json

from stonks_bot.helper.math import round_currency_scalar


@dataclass_json
@dataclass
class PriceDaily:
    open: float
    high: float
    low: float
    close: float

    @property
    def diff(self) -> float:
        return round_currency_scalar(self.close - self.open)

    @property
    def percent(self) -> float:
        res_div = self.close / self.open
        percent = round((res_div - 1) * 100, 2)

        return percent
