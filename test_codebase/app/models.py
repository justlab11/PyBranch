from .utils.formatting import format_money


class Entity:
    def __init__(self, ident):
        self.ident = ident

    def describe(self):
        return f"{type(self).__name__}#{self.ident}"


class Customer(Entity):
    def __init__(self, ident, name, email):
        super().__init__(ident)
        self.name = name
        self.email = email

    def label(self):
        return f"{self.name} <{self.email}>"


class Order(Entity):
    def __init__(self, ident, customer, items):
        super().__init__(ident)
        self.customer = customer
        self.items = items

    def subtotal(self):
        return sum(price * qty for _, price, qty in self.items)

    def summary(self):
        text = self.describe()
        return f"{text}: {format_money(self.subtotal())}"
