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
        
        # Adaptive trading parameters
        self.inventory_skew_factor = 0.04  # Increased from 0.02 to 0.04 for better rebalancing
        self.volatility_window = 20
        self.price_history = []
        self.volatility = 0.0
        
        # Drawdown protection
        self.peak_equity = starting_cash
        self.max_drawdown_dollars = 50.0
        self.max_drawdown_percent = 0.03
        self.auto_throttle_enabled = True
        
        # Performance tracking
        self.trade_history = []
        self.winning_trades = 0
        self.losing_trades = 0

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

            # Only place sell order if we're not at max short inventory
        if self.inventory > -self.max_inventory:
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

        return orders

    def updateProfitAndLoss(self, trade_price, trade_quantity, side, current_price):
        """Execute a trade and update position/cash with performance tracking"""
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
        old_pnl = self.pnl
        self.pnl = (self.cash + unrealized_pnl) - self.starting_cash

        # Calculate trade P&L (difference in total P&L)
        trade_pnl = self.pnl - old_pnl
        
        # Update performance metrics
        self.update_performance_metrics(trade_pnl)

        # Inventory penalty: if inventory is too high, penalize P&L
        if abs(self.inventory) > self.max_inventory * 0.8:
            penalty = abs(self.inventory) * 0.5  # $0.5 penalty per excess unit
            self.pnl -= penalty
            print(f"⚠️ Inventory penalty applied: -${penalty:.2f} (Inventory: {self.inventory})")

        print(f"💰 Trade executed: {side.upper()} {trade_quantity} @ ${trade_price:.2f}")
        print(f"📊 Cash: ${self.cash:.2f} | Inventory: {self.inventory} | P&L: ${self.pnl:.2f} | Trade P&L: ${trade_pnl:.2f}")

    def calculate_volatility(self, current_price):
        """Calculate market volatility based on price history"""
        self.price_history.append(current_price)
        
        # Keep only the last N price points
        if len(self.price_history) > self.volatility_window:
            self.price_history.pop(0)
        
        # Calculate volatility (standard deviation of returns)
        if len(self.price_history) >= 2:
            returns = []
            for i in range(1, len(self.price_history)):
                if self.price_history[i-1] != 0:
                    return_val = (self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1]
                    returns.append(return_val)
            
            if returns:
                import statistics
                self.volatility = statistics.stdev(returns)
            else:
                self.volatility = 0.0
        else:
            self.volatility = 0.0
        
        return self.volatility
    
    def should_throttle_trading(self):
        """Check if trading should be throttled due to drawdown"""
        if not self.auto_throttle_enabled:
            return False
        
        # Calculate current equity
        current_equity = self.cash + (self.inventory * 150.0)  # Simplified price assumption
        
        # Update peak equity
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity
        
        # Calculate drawdown
        if self.peak_equity > 0:
            current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
        else:
            current_drawdown = 0.0
        
        # Check dollar drawdown
        if self.pnl < -self.max_drawdown_dollars:
            print(f"🛑 Trading stopped: P&L below threshold (${self.pnl:.2f} < -${self.max_drawdown_dollars})")
            return True
        
        # Check percentage drawdown
        if current_drawdown > self.max_drawdown_percent:
            print(f"🛑 Trading stopped: Drawdown above threshold ({current_drawdown:.2%} > {self.max_drawdown_percent:.2%})")
            return True
        
        return False
    
    def calculate_adaptive_spread(self, base_spread, volatility):
        """Calculate adaptive spread based on market volatility"""
        if volatility > 0.02:  # High volatility threshold
            spread_multiplier = 2.0 + (volatility / 0.02)
            print(f"📈 High volatility detected ({volatility:.4f}) - widening spreads by {spread_multiplier:.1f}x")
        elif volatility > 0.005:  # Moderate volatility threshold
            spread_multiplier = 1.0 + (volatility / 0.02)
            print(f"📊 Moderate volatility ({volatility:.4f}) - widening spreads by {spread_multiplier:.1f}x")
        else:
            # Low volatility - use normal spreads
            spread_multiplier = 1.0
        
        return base_spread * spread_multiplier
    
    def update_performance_metrics(self, trade_pnl):
        """Update performance tracking metrics"""
        self.trade_history.append({
            'pnl': trade_pnl,
            'inventory': self.inventory,
            'equity': self.cash + (self.inventory * 150.0)  # Simplified price assumption
        })
        
        # Update win/loss counts
        if trade_pnl > 0:
            self.winning_trades += 1
        elif trade_pnl < 0:
            self.losing_trades += 1
        
        # Keep only recent history for performance calculation
        if len(self.trade_history) > 50:
            self.trade_history.pop(0)
    
    def print_performance_summary(self):
        """Print comprehensive performance summary"""
        total_trades = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        print(f"\n📊 PERFORMANCE SUMMARY")
        print(f"=" * 50)
        print(f"💰 Total P&L: ${self.pnl:.2f}")
        print(f"🎯 Win Rate: {win_rate:.1f}% ({self.winning_trades}/{total_trades})")
        print(f"📈 Volatility: {self.volatility:.4f}")
        print(f"📋 Position: {self.inventory} shares")
        print(f"💵 Cash: ${self.cash:.2f}")
        print(f"=" * 50)

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