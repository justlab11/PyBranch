from config import load_settings, TAX_RATE as RATE
from app.utils.formatting import format_money as fm


def tax_for(order):
    return order.subtotal() * RATE


def charge(order):
    total = order.subtotal() + tax_for(order)
    print("charging", fm(total, load_settings()["currency"]))
    return total


def refund(order):
    print("refunding", fm(charge(order)))
