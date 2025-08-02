from main import get_market_data_stream, plot_results, print_simulation_summary, create_random_market_order
from order_book import OrderBook
from strategy import MarketMakingStrategy
from performance_metrics import PerformanceCalculator, print_performance_report
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
            if order is not None:
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
    """
    Compute comprehensive performance metrics using the enhanced calculator
    """
    pnl = results["pnl"]
    trades = results["trades"]
    
    total_trades = len(trades)
    final_pnl = pnl[-1] if pnl else 0
    
    # Use enhanced performance calculator
    calculator = PerformanceCalculator(risk_free_rate=0.02)  # 2% risk-free rate
    
    # Extract individual trade P&Ls for trade-based metrics
    trade_pnls = []
    if trades:
        for trade in trades:
            if 'pnl' in trade:
                trade_pnls.append(trade['pnl'])
            elif 'price' in trade and 'quantity' in trade:
                # Estimate trade P&L if not directly available
                # This is a simplified estimation - you may need to adjust based on your trade structure
                pass
    
    # Calculate all metrics
    metrics = calculator.calculate_all_metrics(
        pnl_series=pnl,
        trade_returns=None,  # We'll use P&L-based calculations for now
        starting_capital=10000,  # Should match your backtester starting capital
        periods_per_year=252,    # Assuming daily data
        time_period_days=len(pnl)  # Number of simulation rounds as days
    )
    
    # Legacy format for HTML report compatibility
    return {
        "final_pnl": round(final_pnl, 2),
        "total_trades": total_trades,
        "sharpe": metrics.sharpe_ratio,
        "max_drawdown": round(final_pnl - min(pnl) if pnl else 0, 2),  # Legacy max DD calculation
        "enhanced_metrics": metrics  # Store enhanced metrics for detailed reporting
    }


def generate_html_report(symbol, metrics):
    html = f"""
    <html>
    <head><title>Backtest Report - {symbol}</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>Backtest Report - {symbol}</h1>
        <p><b>Date:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <h2>Performance Summary</h2>
        <ul>
            <li><b>Final P&L:</b> ${metrics['final_pnl']}</li>
            <li><b>Total Trades:</b> {metrics['total_trades']}</li>
            <li><b>Sharpe Ratio:</b> {metrics['sharpe']}</li>
            <li><b>Max Drawdown:</b> ${metrics['max_drawdown']}</li>
        </ul>

        <h2>P&L and Market Graph</h2>
        <img src="backtest_summary.png" width="100%" />
    </body>
    </html>
    """

    with open("backtest_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Report saved to backtest_report.html")


if __name__ == "__main__":
    symbol = input("Enter symbol (default: AAPL): ").strip().upper() or "AAPL"
    num_rounds = int(input("Enter number of rounds (default: 1000): ") or 1000)
    print("🚀 Running Backtest...")
    results = run_backtest(symbol=symbol, num_rounds=num_rounds)
    print("📈 Plotting Results...")
    plt.ioff()
    plot_results(results["rounds"], results["pnl"], results["cash"], results["inventory"], results["trades"], results["prices"])
    plt.savefig("backtest_summary.png")
    print("📊 Computing Metrics...")
    metrics = compute_metrics(results)
    generate_html_report(symbol, metrics)
