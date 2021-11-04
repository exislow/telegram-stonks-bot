from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class DataChat:
    type: str
    id: int
    title: str
    all_members_are_administrators: bool = False
