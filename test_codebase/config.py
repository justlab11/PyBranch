import os

DEFAULT_CURRENCY = "USD"
TAX_RATE = 0.08


def get_env(name, default=None):
    return os.environ.get(name, default)


def load_settings():
    return {
        "currency": get_env("CURRENCY", DEFAULT_CURRENCY),
        "tax_rate": TAX_RATE,
    }
