import argparse
import app
import app.services.orders as orders_svc
from app import Customer, place_order
from app.storage import save_async
from config import *
import asyncio


def build_customer():
    return Customer(1, "Ada", "ada@example.com")


def demo():
    customer = build_customer()
    order = place_order(customer, [("widget", 2.5, 4), ("gadget", 10, 1)])
    print(order.summary())          # unresolved: type of `order` is unknown
    orders_svc.cancel_order(order)
    app.place_order(customer, [])


async def background():
    await save_async(orders_svc.store, 99, {})


def main():
    parser = argparse.ArgumentParser()
    parser.parse_args()
    print(load_settings())          # via star import: unresolved
    demo()
    asyncio.run(background())


if __name__ == "__main__":
    main()
