from order_book import Order, OrderBook
from strategy import MarketMakingStrategy
from matplotlib import pyplot as plt
import random
import yfinance as yf

ticker = yf.Ticker("AMZN")
price = ticker.history(period="5d", interval="5m")  # 5-minute resolution
latest_price = price["Close"].iloc[-1]  # Most recent price
print(f"Live AMZN price: {latest_price}")





book = OrderBook()
bot = MarketMakingStrategy(order_book=book)


rounds  = []
pnlHistory = []
NUM_ROUNDS = int(input("Enter number of simulation rounds: "))
for round_num in range(NUM_ROUNDS):
    mid_price = latest_price + random.uniform(-0.5, 0.5)  # Simulate real-world noise
    spread = 5  # You can customize this
    bid = mid_price - spread / 2
    ask = mid_price + spread / 2
    bot_orders = bot.generate_orders(bid, ask)
    for order in bot_orders:
        book.add_order(order)

    if random.random() < 0.5:
        book.add_order(Order(order_id=book.next_order_id(), side="buy", price=0, quantity=1, order_type="market"))
    if random.random() < 0.5:
        book.add_order(Order(order_id=book.next_order_id(), side="sell", price=0, quantity=1, order_type="market"))


    book.match(mid_price)
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