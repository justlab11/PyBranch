import re

EMAIL_RE = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


def validate_email(email):
    if not EMAIL_RE.match(email):
        raise ValueError(f"bad email: {email}")
    return email


def validate_items(items):
    def check(item):
        name, price, qty = item
        if price < 0 or qty < 1:
            raise ValueError(f"bad item: {name}")
        return item

    return [check(i) for i in items]
