from dataclasses import dataclass
from dataclasses_json import dataclass_json

from stonks_bot.dataclasses.data_chat import DataChat
from stonks_bot.dataclasses.data_user import DataUser


@dataclass_json
@dataclass
class TrackingChat:
    chat: DataChat
    cause_user: DataUser
