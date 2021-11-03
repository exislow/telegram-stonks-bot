from dataclasses import dataclass
from dataclasses_json import dataclass_json
from telegram import User, Chat


@dataclass_json
@dataclass
class TrackingChat:
    chat: Chat
    cause_user: User
