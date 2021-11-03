from dataclasses import dataclass
from dataclasses_json import dataclass_json
from datetime import datetime


@dataclass_json
@dataclass
class Performance:
    price: float = 0.0
    percent: float = 0.0
    calculated_at: datetime = datetime.fromtimestamp(0)
