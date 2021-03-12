from dateutil import parser


def formatter_date(datetime_str: str) -> str:
    dt = parser.isoparse(datetime_str)

    return dt.strftime('%m-%d')


def formatter_shorten_1(text: str) -> str:
    return text[:-1]


def formatter_offset_1(text: str) -> str:
    return text[1:]


def formatter_no_plus(text: str) -> str:
    return text.replace('+', '')


def formatter_conditional_no_dec(text: str) -> str:
    val = float(text)
    result = int(val) if val >= 100 or val <= -100 else val

    return str(result)


def formatter_percent(text: str) -> str:
    result = formatter_shorten_1(text)
    result = formatter_conditional_no_dec(result)

    return result
