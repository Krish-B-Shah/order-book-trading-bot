from order_book import Order

class MarketMakingStrategy:
    def __init__(self, starting_cash=10000, order_book=None):
        self.cash = starting_cash
        self.inventory = 0
        self.pNL = 0
        self.max_inventory = 10
        self.order_book = order_book

    def _next_id(self):
        return self.order_book.next_order_id()

    def generate_orders(self, current_bid, current_ask, order_type="limit"):
        if order_type != "limit":
            buy_price = current_ask
            sell_price = current_bid
        else:
            mid_price = (current_bid + current_ask) / 2
            buy_price = mid_price - 1
            sell_price = mid_price + 1

        quantity = 1
        orders = []

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