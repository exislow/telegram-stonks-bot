from decimal import Decimal
from typing import Union, Any

from pandas import Series


def round_currency_scalar(value: float) -> float:
    if value >= 1 or value <= -1:
        dec_positions = 2
    else:
        # TODO: Maybe this will fail if `value` is <0 and >-1
        d = Decimal(value).as_tuple()
        dec_positions = (len(d[1]) + d.exponent - 4) * -1

    return round(value, dec_positions)


def round_percent(value) -> float:
    percent = round(value * 100, 2)

    return percent


def change_percent(value_base: Union[int, float], value_current: Union[int, float]):
    return ((value_base - value_current) / value_base) * -1


def get_last_value_times_series(time_series: Series, index_until: Any) -> Union[int, float, str]:
    if time_series[:index_until].size > 0:
        return time_series[:index_until][-1]
    else:
        return time_series[0]
