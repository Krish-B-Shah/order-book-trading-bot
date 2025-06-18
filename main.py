from order_book import Order, OrderBook
from strategy import MarketMakingStrategy

# Initialize order book and market making strategy
book = OrderBook()
bot = MarketMakingStrategy()

# Simulate initial market conditions
# Fake orders to populate the book
book.add_order(Order(order_id=1, side="sell", price=101, quantity=105, order_type="limit"))
book.add_order(Order(order_id=2, side="buy", price=99, quantity=100, order_type="market"))
book.add_order(Order(order_id=999, side="sell", price=101, quantity=5, order_type="market", owner=bot))
# Get current best bid/ask
current_bid = 99
current_ask = 101

for _ in range(10):
    bot_orders = bot.generate_orders(current_bid, current_ask)
    for order in bot_orders:
        book.add_order(order)
    book.match()
    print(f"P&L: {bot.pNL:.2f} | Cash: {bot.cash:.2f} | Inventory: {bot.inventory}")
    print("-" * 50)


# Print trades
print("\nTrades executed:")
for trade in book.trade_log:
    print(trade)

# Show what's left
print("\nRemaining Order Book:")
book.print_book()
