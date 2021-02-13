from dataclasses import dataclass

from stonks_bot.helper.math import round_currency_scalar


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
        percent = ((res_div - 1) * 100).round(2)

        return percent
