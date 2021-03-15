import json
from json import JSONEncoder
from typing import Union, Any

from dateutil import parser

from stonks_bot.helper.math import round_currency_scalar


def formatter_date(datetime_str: str) -> str:
    dt = parser.isoparse(datetime_str)

    return dt.strftime('%m-%d')


def formatter_shorten_1(text: str) -> str:
    return text[:-1]


def formatter_offset_1(text: str) -> str:
    return text[1:]


def formatter_no_plus(text: str) -> str:
    return text.replace('+', '')


def formatter_conditional_no_dec(val: Union[str, float]) -> str:
    val = float(val) if isinstance(val, str) else val
    if 1 > val > -1:
        result = round(val, 4)
    elif val >= 100 or val <= -100:
        result = int(val)
    elif isinstance(val, float):
        result = round(val, 2)
    else:
        result = val

    return str(result)


def formatter_percent(text: str) -> str:
    result = formatter_shorten_1(text)
    result = formatter_conditional_no_dec(result)

    return result


def formatter_round_currency_scalar(val: Union[str, float]) -> str:
    val = float(val) if isinstance(val, str) else val
    val = round_currency_scalar(val)
    val = formatter_conditional_no_dec(val)

    return val


def formatter_to_json(val: Any) -> str:
    return json.dumps(val, indent=2, ensure_ascii=False, cls=TelegramEncoder)


class TelegramEncoder(JSONEncoder):
    def default(self, o):
        return o.to_dict()
