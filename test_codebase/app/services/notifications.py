# circular import with orders: orders -> notifications -> orders
from . import orders


def notify_customer(order, cancelled=False):
    subject = "Order cancelled" if cancelled else "Order placed"
    send_email(order.customer.email, subject, order.summary())
    if cancelled:
        orders.cancel_order  # attribute reference, not a call


def send_email(to, subject, body):
    print(f"to={to} subject={subject}\n{body}")
