from app.models import Order
from app.utils import validate_items
from app.utils.validation import validate_email
from app.storage import Store
from . import billing
from .notifications import notify_customer

store = Store("orders.json")


def place_order(customer, items):
    validate_email(customer.email)
    clean = validate_items(items)
    order = Order(next_id(), customer, clean)
    total = billing.charge(order)
    store.save(order.ident, {"total": total})
    notify_customer(order)
    return order


def next_id():
    return len(store._cache) + 1


def cancel_order(order):
    billing.refund(order)
    notify_customer(order, cancelled=True)
