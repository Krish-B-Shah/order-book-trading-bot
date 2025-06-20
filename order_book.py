import heapq
import time
import csv

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

    def add_order(self, order):
        if order.order_type == "market":
            self.execute_market_order(order)
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

    def execute_market_order(self, market_order):
        book_side = self.sell_orders if market_order.side == "buy" else self.buy_orders
        original_qty = market_order.quantity

        while market_order.quantity > 0 and book_side:
            resting_order = book_side[0]
            trade_qty = min(market_order.quantity, resting_order.quantity)
            trade_price = resting_order.price

            self.trade_log.append({
                "price": trade_price,
                "quantity": trade_qty,
                "timestamp": time.time()
            })

            if market_order.owner:
                market_order.owner.updateProfitAndLoss(trade_price, trade_qty, market_order.side)
            if resting_order.owner:
                resting_order.owner.updateProfitAndLoss(trade_price, trade_qty, resting_order.side)

            market_order.quantity -= trade_qty
            resting_order.quantity -= trade_qty

            if resting_order.quantity == 0:
                heapq.heappop(book_side)
                self.order_map.pop(resting_order.order_id, None)

        if market_order.quantity > 0:
            if market_order.quantity < original_qty:
                print(f"⚠️ Market order {market_order.order_id} partially filled, {market_order.quantity} units discarded.")
            else:
                print(f"❌ Market order {market_order.order_id} could not be filled at all.")

    def match(self):
        while self.buy_orders and self.sell_orders:
            best_buy = self.buy_orders[0]
            best_sell = self.sell_orders[0]

            if best_buy.price >= best_sell.price:
                trade_qty = min(best_buy.quantity, best_sell.quantity)
                trade_price = best_sell.price

                self.trade_log.append({
                    "price": trade_price,
                    "quantity": trade_qty,
                    "timestamp": time.time()
                })

                if best_buy.owner:
                    best_buy.owner.updateProfitAndLoss(trade_price, trade_qty, "buy")
                if best_sell.owner:
                    best_sell.owner.updateProfitAndLoss(trade_price, trade_qty, "sell")

                best_buy.quantity -= trade_qty
                best_sell.quantity -= trade_qty

                if best_buy.quantity == 0:
                    heapq.heappop(self.buy_orders)
                    self.order_map.pop(best_buy.order_id, None)
                if best_sell.quantity == 0:
                    heapq.heappop(self.sell_orders)
                    self.order_map.pop(best_sell.order_id, None)
            else:
                break

    def print_book(self):
        print("Buy Orders:")
        for order in sorted(self.buy_orders, reverse=True):
            print(vars(order))
        print("Sell Orders:")
        for order in sorted(self.sell_orders):
            print(vars(order))


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
