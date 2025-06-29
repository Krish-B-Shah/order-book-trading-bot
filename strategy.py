from order_book import Order, OrderBook
from typing import List, Dict, Any, Optional
import random

class MarketMakingStrategy:
    def __init__(self, starting_cash: float = 10000, order_book: Optional[OrderBook] = None, 
                 max_inventory: int = 10, spread: float = 5.0):
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
            market_spread = current_ask - current_bid
            
            # Use a percentage of the market spread (more realistic)
            spread_multiplier = 0.3  # 30% of market spread
            half_spread = (market_spread * spread_multiplier) / 2
            
            # Ensure minimum spread for profitability
            min_spread = 0.01  # $0.01 minimum
            half_spread = max(half_spread, min_spread / 2)
            
            buy_price = mid_price - half_spread
            sell_price = mid_price + half_spread

        quantity = 1

        # More conservative inventory management
        if self.inventory < self.max_inventory:
            buy_order = Order(
                order_id=self._next_id(),
                side="buy",
                price=buy_price,
                quantity=quantity,
                order_type=order_type,
                owner=self
            )
            orders.append(buy_order)
            self.active_orders.append(buy_order.order_id)

        # Dynamic sell order placement based on inventory
        if self.inventory > 0:
            # If we have positive inventory, always try to sell
            sell_order = Order(
                order_id=self._next_id(),
                side="sell",
                price=sell_price,
                quantity=quantity,
                order_type=order_type,
                owner=self
            )
            orders.append(sell_order)
            self.active_orders.append(sell_order.order_id)
        elif self.inventory == 0:
            # If neutral, place sell order with 70% probability
            if random.random() < 0.7:
                sell_order = Order(
                    order_id=self._next_id(),
                    side="sell",
                    price=sell_price,
                    quantity=quantity,
                    order_type=order_type,
                    owner=self
                )
                orders.append(sell_order)
                self.active_orders.append(sell_order.order_id)
        # If negative inventory, don't place sell orders

        return orders

    def updateProfitAndLoss(self, trade_price, trade_quantity, side, current_price):
        if side == "buy":
            self.inventory += trade_quantity
            self.cash -= trade_price * trade_quantity
        elif side == "sell":
            self.inventory -= trade_quantity
            self.cash += trade_price * trade_quantity

        # Calculate unrealized P&L based on last trade price
        last_price = self.order_book.get_last_trade_price() if self.order_book else 100.0
        if last_price is None:
            last_price = 100.0
            
        unrealized_pnl = self.inventory * last_price
        self.pnl = (self.cash + unrealized_pnl) - self.starting_cash

        # Inventory penalty: if inventory is too high, penalize P&L
        if abs(self.inventory) > self.max_inventory * 0.8:
            penalty = abs(self.inventory) * 0.1  # Reduced from $0.5 to $0.1 penalty per excess unit
            self.pnl -= penalty
            print(f"⚠️ Inventory penalty applied: -${penalty:.2f} (Inventory: {self.inventory})")
        
        print(f"💰 Trade executed: {side.upper()} {trade_quantity} @ ${trade_price:.2f}")
        print(f"📊 Cash: ${self.cash:.2f} | Inventory: {self.inventory} | P&L: ${self.pnl:.2f}")
    def cancel_all_orders(self) -> None:
        if not self.order_book:
            return
            
        for order_id in self.active_orders[:]:  # Copy list to avoid modification during iteration
            if self.order_book.cancel_order(order_id):
                self.active_orders.remove(order_id)

    def get_status(self) -> Dict[str, Any]:
        return {
            "cash": self.cash,
            "inventory": self.inventory,
            "pnl": self.pnl,
            "active_orders": len(self.active_orders)
        }