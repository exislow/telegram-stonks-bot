from dataclasses import dataclass
from datetime import datetime


@dataclass
class Performance:
    price: float = 0.0
    percent: float = 0.0
    calculated_at: datetime = datetime.fromtimestamp(0)
