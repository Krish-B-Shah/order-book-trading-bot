import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import get_market_data_stream, plot_results, print_simulation_summary
from core.order_book import OrderBook
from strategies.market_maker import MarketMakingStrategy
from backtest.analytics import PerformanceCalculator, print_performance_report
from backtest.execution_sim import create_random_market_order
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
import os


def run_backtest(symbol="AAPL", num_rounds=1000, starting_cash=10000, spread=2.00, transaction_cost=0.005):
    """
    Run backtest with realistic parameters
    
    Args:
        spread: Bid-ask spread in dollars (default: $2.00 for AAPL)
        transaction_cost: Transaction cost per share (default: $0.005 = 0.5 cents)
    """
    market_data = get_market_data_stream(symbol, num_rounds)
    order_book = OrderBook()
    bot = MarketMakingStrategy(starting_cash=starting_cash, order_book=order_book, max_inventory=10, spread=spread, transaction_cost=transaction_cost)

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

        # Simulate market orders with reduced frequency (more realistic)
        # Only generate market orders 30% of the time to avoid excessive trading
        import random
        if random.random() < 0.3:  # 30% chance of market activity per round
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
    enhanced = metrics.get('enhanced_metrics')
    
    html = f"""
    <html>
    <head>
        <title>Enhanced Backtest Report - {symbol}</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin: 20px 0; }}
            .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 4px solid #007bff; }}
            .metric-value {{ font-size: 1.5em; font-weight: bold; color: #007bff; }}
            .metric-label {{ color: #666; font-size: 0.9em; }}
            .section {{ margin: 30px 0; }}
            .good {{ color: #28a745; }}
            .warning {{ color: #ffc107; }}
            .danger {{ color: #dc3545; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 Enhanced Backtest Report - {symbol}</h1>
            <p><b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <div class="section">
                <h2>🎯 Key Performance Indicators</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-label">Final P&L</div>
                        <div class="metric-value">${metrics['final_pnl']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Total Trades</div>
                        <div class="metric-value">{metrics['total_trades']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Sharpe Ratio</div>
                        <div class="metric-value {'good' if enhanced and enhanced.sharpe_ratio > 1.0 else 'warning' if enhanced and enhanced.sharpe_ratio > 0.5 else 'danger'}">{enhanced.sharpe_ratio if enhanced else metrics['sharpe']}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max Drawdown</div>
                        <div class="metric-value {'good' if enhanced and enhanced.max_drawdown < 5 else 'warning' if enhanced and enhanced.max_drawdown < 15 else 'danger'}">{enhanced.max_drawdown if enhanced else metrics['max_drawdown']}%</div>
                    </div>
                </div>
            </div>"""
    
    if enhanced:
        html += f"""
            <div class="section">
                <h2>📈 Return Metrics</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-label">Total Return</div>
                        <div class="metric-value">{enhanced.total_return}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Annualized Return</div>
                        <div class="metric-value">{enhanced.annualized_return}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Volatility</div>
                        <div class="metric-value">{enhanced.volatility}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Sortino Ratio</div>
                        <div class="metric-value">{enhanced.sortino_ratio}</div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>⚠️ Risk Metrics</h2>
                <div class="metric-grid">
                    <div class="metric-card">
                        <div class="metric-label">Calmar Ratio</div>
                        <div class="metric-value">{enhanced.calmar_ratio}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Max DD Duration</div>
                        <div class="metric-value">{enhanced.max_drawdown_duration} periods</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">VaR (95%)</div>
                        <div class="metric-value">{enhanced.var_95}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value">{enhanced.win_rate}%</div>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>🔍 Performance Assessment</h2>
                <ul>
                    <li><b>Sharpe Ratio:</b> {'EXCELLENT (>2.0)' if enhanced.sharpe_ratio > 2.0 else 'GOOD (1.0-2.0)' if enhanced.sharpe_ratio > 1.0 else 'ACCEPTABLE (0.5-1.0)' if enhanced.sharpe_ratio > 0.5 else 'POOR (<0.5)'}</li>
                    <li><b>Max Drawdown:</b> {'EXCELLENT (<5%)' if enhanced.max_drawdown < 5 else 'GOOD (5-10%)' if enhanced.max_drawdown < 10 else 'ACCEPTABLE (10-20%)' if enhanced.max_drawdown < 20 else 'HIGH RISK (>20%)'}</li>
                    <li><b>Profit Factor:</b> {enhanced.profit_factor if enhanced.profit_factor > 0 else 'N/A'}</li>
                </ul>
            </div>"""
    
    html += f"""
            <div class="section">
                <h2>📊 P&L and Market Chart</h2>
                <img src="backtest_summary.png" style="width: 100%; max-width: 800px; border-radius: 8px;" />
            </div>
        </div>
    </body>
    </html>
    """

    with open("backtest_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ Enhanced HTML report saved to backtest_report.html")


if __name__ == "__main__":
    symbol = input("Enter symbol (default: AAPL): ").strip().upper() or "AAPL"
    num_rounds = int(input("Enter number of rounds (default: 500): ") or 500)  # Reduced default rounds
    spread = float(input("Enter spread in dollars (default: 2.00): ") or 2.00)  # Realistic spread
    print("🚀 Running Backtest with more realistic parameters...")
    print(f"📊 Symbol: {symbol}, Rounds: {num_rounds}, Spread: ${spread:.2f}")
    
    results = run_backtest(symbol=symbol, num_rounds=num_rounds, spread=spread)
    print("📈 Plotting Results...")
    plt.ioff()
    plot_results(results["rounds"], results["pnl"], results["cash"], results["inventory"], results["trades"], results["prices"])
    plt.savefig("backtest_summary.png")
    print("📊 Computing Enhanced Metrics...")
    metrics = compute_metrics(results)
    
    # Print detailed performance report to console
    if 'enhanced_metrics' in metrics:
        print_performance_report(metrics['enhanced_metrics'])
    
    generate_html_report(symbol, metrics)
