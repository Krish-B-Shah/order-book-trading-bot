from order_book import Order
import random
import time

class MarketMakingStrategy:
    def __init__(self, starting_cash=10000):
        self.cash = starting_cash
        self.inventory = 0
        self.order_id_counter = 100
        self.pNL = 0

    def generate_orders(self, current_bid, current_ask, order_type="limit"):
        if order_type != "limit":
            buy_price = current_ask
            sell_price = current_bid
            quantity = 1  # Simple 1-unit order
            orders = [
                Order(order_id=self._next_id(), side="buy", price=buy_price, quantity=quantity, order_type=order_type, owner=self),
                Order(order_id=self._next_id(), side="sell", price=sell_price, quantity=quantity, order_type=order_type, owner=self)
            ]
        else:
            # Calculate mid price
            mid_price = (current_bid + current_ask) / 2
            
            # Place a buy order slightly below the mid price
            buy_price = mid_price - 1
            sell_price = mid_price + 1
            quantity = 1  # Simple 1-unit order

            orders = [
                Order(order_id=self._next_id(), side="buy", price=buy_price, quantity=quantity, order_type=order_type, owner=self),
                Order(order_id=self._next_id(), side="sell", price=sell_price, quantity=quantity, order_type=order_type, owner=self)
            ]
        return orders

    def _next_id(self):
        self.order_id_counter += 1
        return self.order_id_counter
    
    def updateProfitAndLoss(self, trade_price, trade_quantity, side):
        if side == "buy":
            self.inventory += trade_quantity
            self.cash -= trade_price * trade_quantity
        elif side == "sell":
            self.inventory -= trade_quantity
            self.cash += trade_price * trade_quantity
        
        # Update P&L
        self.pNL = self.cash + (self.inventory * trade_price) - 10000  # Assuming starting cash is 10,000
        if self.pNL < 0:
            print(f"⚠️ Warning: Negative P&L of {self.pNL:.2f}")
        else:
            print(f"✅ P&L is {self.pNL:.2f}")
