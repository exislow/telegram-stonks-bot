from typing import Union

from dateutil import parser


def formatter_digits(price: float) -> Union[float, int]:
    return str(price) if price < 100 else str(int(price))


def formatter_date(datetime_str: str) -> str:
    dt = parser.isoparse(datetime_str)

    return dt.strftime('%m-%d')


def formatter_shorten_1(text):
    return text[:-1]
