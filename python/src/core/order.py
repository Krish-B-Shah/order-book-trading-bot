import time


class Order:
    def __init__(self, order_id, side, price, quantity, order_type, owner=None, timestamp=None):
        self.order_id = order_id
        self.side = side  # "buy" or "sell"
        self.order_type = order_type  # "limit" or "market"
        self.owner = owner
        self.price = float('inf') if order_type == "market" and side == "buy" else \
                     0 if order_type == "market" and side == "sell" else price
        self.quantity = quantity
        self.timestamp = timestamp or time.time()

    def __lt__(self, other):
        if self.side == "buy":
            return (-self.price, self.timestamp) < (-other.price, other.timestamp)
        else:
            return (self.price, self.timestamp) < (other.price, other.timestamp)

    def __repr__(self) -> str:
        return f"Order({self.order_id}, {self.side}, ${self.price:.2f}, {self.quantity}, {self.order_type})"
