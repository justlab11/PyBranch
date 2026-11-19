import config


def _round(amount):
    return round(amount, 2)


def format_money(amount, currency=None):
    currency = currency or config.DEFAULT_CURRENCY
    return f"{_round(amount):.2f} {currency}"
