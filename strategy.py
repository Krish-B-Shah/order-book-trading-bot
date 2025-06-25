from order_book import Order, OrderBook
from typing import List, Dict, Any, Optional

class MarketMakingStrategy:
    def __init__(self, starting_cash: float = 10000, order_book: Optional[OrderBook] = None, 
                 max_inventory: int = 10, spread: float = 2.0):
        self.starting_cash = starting_cash
        self.cash = starting_cash
        self.inventory = 0
        self.pnl = 0.0
        self.max_inventory = max_inventory
        self.spread = spread
        self.order_book = order_book
        self.active_orders: List[int] = []  # Track active order IDs

    def _next_id(self):
        if not self.order_book:
            raise ValueError("Order book is not initialized.")
        return self.order_book.next_order_id()

    def generate_orders(self, current_bid, current_ask, order_type="limit"):
        orders = []
        if order_type == "market":
            # For market orders, use current bid/ask directly
            buy_price = current_ask
            sell_price = current_bid
        else:
            # For limit orders, place inside the spread
            mid_price = (current_bid + current_ask) / 2
            half_spread = self.spread / 2
            buy_price = mid_price - half_spread
            sell_price = mid_price + half_spread

        quantity = 1
        
        if self.inventory < self.max_inventory:
            orders.append(Order(order_id=self._next_id(), side="buy", price=buy_price, quantity=quantity, order_type=order_type, owner=self))

        if self.inventory > -self.max_inventory:
            orders.append(Order(order_id=self._next_id(), side="sell", price=sell_price, quantity=quantity, order_type=order_type, owner=self))

        return orders

    def updateProfitAndLoss(self, trade_price, trade_quantity, side):
        if side == "buy":
            self.inventory += trade_quantity
            self.cash -= trade_price * trade_quantity
        elif side == "sell":
            self.inventory -= trade_quantity
            self.cash += trade_price * trade_quantity

        mid_price = self.order_book.get_last_trade_price() or 100.0
        self.pNL = self.cash + (self.inventory * mid_price) - 10000
        
        if self.pNL < 0:
            print(f"⚠️ Warning: Negative P&L of {self.pNL:.2f}")
        else:
            print(f"✅ P&L is {self.pNL:.2f}")