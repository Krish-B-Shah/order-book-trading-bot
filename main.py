from order_book import Order, OrderBook
from strategy import MarketMakingStrategy
from matplotlib import pyplot as plt

# episodes = list(range(1, 6))
# profits = [20, -5, 15, 10, -3]

# plt.bar(episodes, profits)
# plt.xlabel('Round')
# plt.ylabel('P&L')
# plt.title('Profit and Loss Over Time')
# plt.axhline(0, color='black', linewidth=0.8)
# plt.show()





book = OrderBook()
bot = MarketMakingStrategy(order_book=book)

# Initial market orders
book.add_order(Order(order_id=book.next_order_id(), side="buy", price=99, quantity=105, order_type="limit"))
book.add_order(Order(order_id=book.next_order_id(), side="sell", price=101, quantity=100, order_type="limit"))
book.add_order(Order(order_id=book.next_order_id(), side="sell", price=101, quantity=5, order_type="market", owner=bot))
book.add_order(Order(order_id=book.next_order_id(), side="buy", price=101, quantity=5, order_type="market", owner=bot))

# Market making loop

rounds  = []
pnlHistory = []
NUM_ROUNDS = int(input("Enter number of simulation rounds: "))
for round_num in range(NUM_ROUNDS):
    bid, ask = book.get_best_bid_ask()
    bot_orders = bot.generate_orders(bid or 98, ask or 102)
    for order in bot_orders:
        book.add_order(order)
    book.match()
    rounds.append(round_num)
    pnlHistory.append(bot.pNL)

    print(f"P&L: {bot.pNL:.2f} | Cash: {bot.cash:.2f} | Inventory: {bot.inventory}")
    print("-" * 50)

# Final state
print("\nTrades executed:")
for trade in book.trade_log:
    print(trade)


# Priting the current state of the order book
print("\nRemaining Order Book:")
book.print_book()

plt.plot(rounds, pnlHistory, marker='o')
plt.title("Bot Profit and Loss Over Time")
plt.xlabel("Round")
plt.ylabel("P&L")
plt.axhline(0, color='black', linestyle='--', linewidth=0.8)
plt.grid(True)
plt.show()

# Uncomment the following lines to export all orders to a CSV file
# book.export_all_orders("all_orders.csv")
# print("\nAll orders exported to 'all_orders.csv'.")