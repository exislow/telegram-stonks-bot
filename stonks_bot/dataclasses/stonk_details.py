from dataclasses import dataclass

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class StonkDetails:
    price: float
    price_24h_high: float
    price_24h_low: float
    price_52w_high: float
    price_52w_low: float
    percent_change_1h: float
    percent_change_24h: float
    percent_change_7d: float
    percent_change_30d: float
    percent_change_52w: float
    percent_change_ytd: float
    volume: float
    market_capitalization: float
    recommendation: str
