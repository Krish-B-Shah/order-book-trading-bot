from order_book import Order, OrderBook
from strategy import MarketMakingStrategy
import time

book = OrderBook()
bot = MarketMakingStrategy()

# Initial market simulation
book.add_order(Order(order_id=2, side="buy", price=99, quantity=105, order_type="limit"))
book.add_order(Order(order_id=1, side="sell", price=101, quantity=100, order_type="limit"))
book.add_order(Order(order_id=999, side="sell", price=101, quantity=5, order_type="market", owner=bot))
book.add_order(Order(order_id=1000, side="buy", price=101, quantity=5, order_type="market", owner=bot))  # changed to match resting sell

# Market making loop
current_bid = 99
current_ask = 101

for _ in range(10):
    bot_orders = bot.generate_orders(current_bid, current_ask)
    for order in bot_orders:
        book.add_order(order)
    book.match()

    print(f"P&L: {bot.pNL:.2f} | Cash: {bot.cash:.2f} | Inventory: {bot.inventory}")
    print("-" * 50)

# Final trade log and book state
print("\nTrades executed:")
for trade in book.trade_log:
    print(trade)

print("\nRemaining Order Book:")
book.print_book()
