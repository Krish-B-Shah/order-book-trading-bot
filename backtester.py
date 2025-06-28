# backtest_report.py
from main import get_market_data_stream, plot_results, print_simulation_summary
from order_book import OrderBook
from strategy import MarketMakingStrategy
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import os

def run_backtest(symbol="AAPL", num_rounds=1000, starting_cash=10000, spread=0.10):
    market_data = get_market_data_stream(symbol, num_rounds)
    order_book = OrderBook()
    bot = MarketMakingStrategy(starting_cash=starting_cash, order_book=order_book, max_inventory=10, spread=spread)

    rounds = []
    pnl_history = []
    cash_history = []
    inventory_history = []
    market_prices = []

    for i in range(min(num_rounds, len(market_data))):
        data = market_data[i]
        bid = data["bid"]
        ask = data["ask"]
        price = data["price"]

        bot_orders = bot.generate_orders(bid, ask)
        for order in bot_orders:
            order_book.add_order(order)

        # Simulate 2 market orders per round
        from main import create_random_market_order
        for _ in range(2):
            order = create_random_market_order(order_book, data)
            order_book.add_order(order)

        order_book.match(price)
        status = bot.get_status()
        rounds.append(i + 1)
        pnl_history.append(status["pnl"])
        cash_history.append(status["cash"])
        inventory_history.append(status["inventory"])
        market_prices.append(price)

    return {
        "rounds": rounds,
        "pnl": pnl_history,
        "cash": cash_history,
        "inventory": inventory_history,
        "prices": market_prices,
        "trades": order_book.trade_log,
        "bot": bot,
        "order_book": order_book
    }
