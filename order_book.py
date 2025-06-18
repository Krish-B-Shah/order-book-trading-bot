import heapq
import time

class Order:
    def __init__(self, order_id, side, price, quantity, order_type, owner=None, timestamp=None):
        self.order_id = order_id
        self.side = side  # "buy" or "sell"
        self.order_type = order_type  # "limit" or "market"
        self.owner = owner  # Link to strategy object (e.g., bot)

        if self.order_type == "market":
            self.price = float('inf') if side == "buy" else 0
        else:
            self.price = price

        self.quantity = quantity
        self.timestamp = timestamp or time.time()

    def __lt__(self, other):
        # For heapq: buy = max-heap, sell = min-heap
        if self.side == "buy":
            return (-self.price, self.timestamp) < (-other.price, other.timestamp)
        else:
            return (self.price, self.timestamp) < (other.price, other.timestamp)


class OrderBook:
    def __init__(self):
        self.buy_orders = []   # Max-heap (by price)
        self.sell_orders = []  # Min-heap (by price)
        self.trade_log = []

    def add_order(self, order):
        if order.order_type == "market":
            if order.side == "buy" and not self.sell_orders:
                print(f"❌ Rejected market buy {order.order_id}: no sellers")
                return
            if order.side == "sell" and not self.buy_orders:
                print(f"❌ Rejected market sell {order.order_id}: no buyers")
                return

        if order.side == "buy":
            heapq.heappush(self.buy_orders, order)
        elif order.side == "sell":
            heapq.heappush(self.sell_orders, order)

    def match(self):
        while self.buy_orders and self.sell_orders:
            best_buy = self.buy_orders[0]
            best_sell = self.sell_orders[0]

            if best_buy.price >= best_sell.price:
                trade_qty = min(best_buy.quantity, best_sell.quantity)

                # ✅ Proper trade price logic
                if best_buy.order_type == "market" and best_sell.order_type != "market":
                    trade_price = best_sell.price
                elif best_sell.order_type == "market" and best_buy.order_type != "market":
                    trade_price = best_buy.price
                elif best_buy.order_type == "market" and best_sell.order_type == "market":
                    trade_price = 0  # fallback (this shouldn't happen in real markets)
                else:
                    trade_price = best_sell.price

                if trade_qty <= 0:
                    break

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
                if best_sell.quantity == 0:
                    heapq.heappop(self.sell_orders)
            else:
                break

        # Remove unmatched market orders (they must not persist)
        if self.buy_orders and self.buy_orders[0].order_type == "market":
            removed = heapq.heappop(self.buy_orders)
            print(f"⚠️ Removed unfilled market BUY order: {removed.order_id}")

        if self.sell_orders and self.sell_orders[0].order_type == "market":
            removed = heapq.heappop(self.sell_orders)
            print(f"⚠️ Removed unfilled market SELL order: {removed.order_id}")

        # Clean up empty limit orders still in heap (edge case)
        if self.buy_orders and self.buy_orders[0].quantity == 0:
            removed = heapq.heappop(self.buy_orders)
            print(f"🧹 Removed empty BUY order: {removed.order_id}")

        if self.sell_orders and self.sell_orders[0].quantity == 0:
            removed = heapq.heappop(self.sell_orders)
            print(f"🧹 Removed empty SELL order: {removed.order_id}")

    def print_book(self):
        print("Buy Orders:")
        for order in sorted(self.buy_orders, reverse=True):
            print(vars(order))
        print("Sell Orders:")
        for order in sorted(self.sell_orders):
            print(vars(order))
