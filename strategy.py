from order_book import Order, OrderBook
from strategy import MarketMakingStrategy

book = OrderBook()
bot = MarketMakingStrategy(order_book=book)

# Initial market orders
book.add_order(Order(order_id=book.next_order_id(), side="buy", price=99, quantity=105, order_type="limit"))
book.add_order(Order(order_id=book.next_order_id(), side="sell", price=101, quantity=100, order_type="limit"))
book.add_order(Order(order_id=book.next_order_id(), side="sell", price=101, quantity=5, order_type="market", owner=bot))
book.add_order(Order(order_id=book.next_order_id(), side="buy", price=101, quantity=5, order_type="market", owner=bot))

# Market making loop
for _ in range(10):
    bid, ask = book.get_best_bid_ask()
    bot_orders = bot.generate_orders(bid or 98, ask or 102)
    for order in bot_orders:
        book.add_order(order)
    book.match()
    print(f"P&L: {bot.pNL:.2f} | Cash: {bot.cash:.2f} | Inventory: {bot.inventory}")
    print("-" * 50)

# Final state
print("\nTrades executed:")
for trade in book.trade_log:
    print(trade)

print("\nRemaining Order Book:")
book.print_book()
