def round_currency_scalar(value: float) -> float:
    round_size = 2 if value >= 1 or value <= -1 else 4

    return value.round(round_size)
