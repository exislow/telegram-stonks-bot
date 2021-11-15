from typing import Union, Any

from pandas import Series


def round_currency_scalar(value: float) -> float:
    dec_positions = 2 if value >= 1 or value <= -1 else 4

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

