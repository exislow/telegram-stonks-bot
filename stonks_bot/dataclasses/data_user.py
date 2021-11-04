from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class DataUser:
    username: str
    is_bot: bool
    first_name: str
    id: int
    language_code: str
