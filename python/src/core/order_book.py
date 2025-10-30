import heapq
import time
import csv
from .order import Order
from .matching_engine import MatchingEngine


class OrderBook:
    def __init__(self):
        self.global_order_id = 0
        self.buy_orders = []
        self.sell_orders = []
        self.trade_log = []
        self.order_map = {}   
        self.all_orders = [] 

    def next_order_id(self):
        self.global_order_id += 1
        return self.global_order_id
    def get_last_trade_price(self):
        if self.trade_log:
            return self.trade_log[-1]['price']
        return None

    def add_order(self, order):
        if order.order_type == "market":
            self.execute_market_order(order, current_price=self.get_last_trade_price() or 100.0)
            self.all_orders.append(order)
            return

        if order.order_id in self.order_map:
            raise ValueError(f"Duplicate Order ID: {order.order_id}")

        self.order_map[order.order_id] = order
        self.all_orders.append(order)

        if order.side == "buy":
            heapq.heappush(self.buy_orders, order)
        elif order.side == "sell":
            heapq.heappush(self.sell_orders, order)

    def cancel_order(self, order_id):
        order = self.order_map.get(order_id)
        if order is None:
            print(f"❌ Order ID {order_id} not found. Cannot cancel.")
            return False

        if order.side == "buy":
            self.buy_orders = [o for o in self.buy_orders if o.order_id != order_id]
            heapq.heapify(self.buy_orders)
        elif order.side == "sell":
            self.sell_orders = [o for o in self.sell_orders if o.order_id != order_id]
            heapq.heapify(self.sell_orders)

        del self.order_map[order_id]
        print(f"✅ Canceled order {order_id}")
        return True

    def amend_order(self, order_id, new_price=None, new_quantity=None):
        order = self.order_map.get(order_id)
        if order is None:
            print(f"❌ Order ID {order_id} not found. Cannot amend.")
            return False

        if order.side == "buy":
            self.buy_orders = [o for o in self.buy_orders if o.order_id != order_id]
            heapq.heapify(self.buy_orders)
        elif order.side == "sell":
            self.sell_orders = [o for o in self.sell_orders if o.order_id != order_id]
            heapq.heapify(self.sell_orders)

        if new_price is not None:
            order.price = new_price
        if new_quantity is not None:
            order.quantity = new_quantity

        self.add_order(order)
        print(f"✅ Amended order {order_id}")
        return True

    def get_best_bid_ask(self):
        best_bid = self.buy_orders[0].price if self.buy_orders else None
        best_ask = self.sell_orders[0].price if self.sell_orders else None
        return best_bid, best_ask

    def execute_market_order(self, market_order, current_price=None):
        book_side = self.sell_orders if market_order.side == "buy" else self.buy_orders
        MatchingEngine.execute_market_order(market_order, book_side, self.trade_log, self.order_map, current_price)

  
    def match(self, current_price):
        MatchingEngine.match_orders(self.buy_orders, self.sell_orders, self.trade_log, self.order_map, current_price)

    def print_book(self) -> None:
            """Print current state of the order book"""
            print("\n📊 ORDER BOOK:")
            print("=" * 50)
            print("BUY ORDERS (sorted by price desc):")
            if self.buy_orders:
                for order in sorted(self.buy_orders, key=lambda x: x.price, reverse=True):
                    print(f"  {order}")
            else:
                print("  No buy orders")
                
            print("\nSELL ORDERS (sorted by price asc):")
            if self.sell_orders:
                for order in sorted(self.sell_orders, key=lambda x: x.price):
                    print(f"  {order}")
            else:
                print("  No sell orders")
            print("=" * 50)


    def export_all_orders(self, filename="order_history.csv"):
        with open(filename, mode='w', newline='') as csvfile:
            fieldNames = ["Order ID", "Side", "Price", "Quantity", "Order Type", "Owner", "Timestamp"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldNames)
            writer.writeheader()
            for order in self.all_orders:
                writer.writerow({
                    "Order ID": order.order_id,
                    "Side": order.side,
                    "Price": order.price,
                    "Quantity": order.quantity,
                    "Order Type": order.order_type,
                    "Owner": str(order.owner) if order.owner else None,
                    "Timestamp": order.timestamp
                })
        print(f"Order history exported to {filename}")

    def export_orders(self, filename: str = "order_history.csv") -> None:
        """Export all orders to CSV file"""
        with open(filename, mode='w', newline='') as csvfile:
            fieldnames = ["Order_ID", "Side", "Price", "Quantity", "Order_Type", "Owner", "Timestamp"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for order in self.all_orders:
                writer.writerow({
                    "Order_ID": order.order_id,
                    "Side": order.side,
                    "Price": order.price,
                    "Quantity": order.quantity,
                    "Order_Type": order.order_type,
                    "Owner": order.owner.__class__.__name__ if order.owner else "None",
                    "Timestamp": order.timestamp
                })
        print(f"📄 Order history exported to {filename}")

    def export_trades(self, filename: str = "trade_history.csv") -> None:
        """Export all trades to CSV file"""
        with open(filename, mode='w', newline='') as csvfile:
            fieldnames = ["Price", "Quantity", "Timestamp", "Buyer_ID", "Seller_ID"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for trade in self.trade_log:
                writer.writerow(trade)
        print(f"📄 Trade history exported to {filename}")
