# backtest_report.py

from main import get_market_data_stream, plot_results, print_simulation_summary, create_random_market_order
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

def compute_metrics(results):
    pnl = results["pnl"]
    trades = results["trades"]

    total_trades = len(trades)
    final_pnl = pnl[-1] if pnl else 0
    max_drawdown = max((max(pnl[:i+1]) - v for i, v in enumerate(pnl)), default=0)

    returns = pd.Series(pnl).diff().dropna()
    sharpe_ratio = returns.mean() / returns.std() * (len(returns) ** 0.5) if not returns.empty else 0

    return {
        "final_pnl": round(final_pnl, 2),
        "total_trades": total_trades,
        "sharpe": round(sharpe_ratio, 2),
        "max_drawdown": round(max_drawdown, 2)
    }

def generate_html_report(symbol, metrics):
    html = f"""
    <html>
    <head><title>Backtest Report - {symbol}</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>📊 Backtest Report - {symbol}</h1>
        <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>Performance Summary</h2>
        <ul>
            <li><b>Final P&L:</b> ${metrics['final_pnl']}</li>
            <li><b>Total Trades:</b> {metrics['total_trades']}</li>
            <li><b>Sharpe Ratio:</b> {metrics['sharpe']}</li>
            <li><b>Max Drawdown:</b> ${metrics['max_drawdown']}</li>
        </ul>

        <h2>📉 P&L and Market Graph</h2>
        <img src="backtest_summary.png" width="100%" />
    </body>
    </html>
    """

    with open("backtest_report.html", "w") as f:
        f.write(html)
    print("✅ Report saved to backtest_report.html")

if __name__ == "__main__":
    print("🚀 Running Backtest...")
    results = run_backtest(symbol="AAPL", num_rounds=1000)
    print("📈 Plotting Results...")
    plt.ioff()  # Turn off interactive plotting
    plot_results(results["rounds"], results["pnl"], results["cash"], results["inventory"], results["trades"], results["prices"])
    plt.savefig("backtest_summary.png")
    print("📊 Computing Metrics...")
    metrics = compute_metrics(results)
    generate_html_report("AAPL", metrics)
