"""
Conservative Market Making Configuration
This configuration aims for realistic, sustainable profits
"""

from backtester import run_backtest, compute_metrics, plot_results, generate_html_report, print_performance_report
import matplotlib.pyplot as plt

def run_conservative_backtest():
    """Run backtest with very conservative, realistic parameters"""
    print("🚀 Running CONSERVATIVE Market Making Backtest")
    print("=" * 60)
    
    # MUCH more conservative parameters
    symbol = "AAPL"
    num_rounds = 100           # Fewer rounds = less over-trading
    starting_cash = 10000      # $10k starting capital
    spread = 4.00             # MUCH wider spread ($4.00 instead of $1.50)
    transaction_cost = 0.01    # Higher transaction costs (1 cent per share)
    
    print(f"📊 Conservative Parameters:")
    print(f"   Symbol: {symbol}")
    print(f"   Rounds: {num_rounds} (reduced from 250)")
    print(f"   Starting Cash: ${starting_cash:,.2f}")
    print(f"   Spread: ${spread:.2f} (increased from $1.50)")
    print(f"   Transaction Cost: ${transaction_cost:.3f} per share (doubled)")
    print(f"   Expected Trade Frequency: ~20-30% (vs 80%+ before)")
    print("=" * 60)
    
    # Run backtest
    results = run_backtest(
        symbol=symbol, 
        num_rounds=num_rounds, 
        starting_cash=starting_cash,
        spread=spread, 
        transaction_cost=transaction_cost
    )
    
    # Compute metrics
    metrics = compute_metrics(results)
    
    # Print results
    print("\n🎯 CONSERVATIVE BACKTEST RESULTS:")
    print(f"Final P&L: ${metrics['final_pnl']:.2f}")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Sharpe Ratio: {metrics['sharpe']:.3f}")
    print(f"Trade Frequency: {metrics['total_trades']}/{num_rounds} = {metrics['total_trades']/num_rounds:.1%}")
    
    # Print detailed metrics
    if 'enhanced_metrics' in metrics:
        print_performance_report(metrics['enhanced_metrics'])
    
    # Generate plots
    print("\n📈 Generating conservative performance plots...")
    plt.ioff()
    plot_results(
        results["rounds"], 
        results["pnl"], 
        results["cash"], 
        results["inventory"], 
        results["trades"], 
        results["prices"]
    )
    plt.savefig("conservative_backtest.png", dpi=300, bbox_inches='tight')
    print("✅ Plot saved as conservative_backtest.png")
    
    # Generate HTML report
    generate_html_report(symbol, metrics)
    
    print("\n" + "="*60)
    print("🔍 ANALYSIS OF RESULTS:")
    print("=" * 60)
    
    trade_freq = metrics['total_trades'] / num_rounds
    if trade_freq < 0.3:
        print("✅ Trade frequency looks realistic (<30%)")
    else:
        print("⚠️ Still trading too frequently - consider larger spread")
    
    if abs(metrics['final_pnl']) < 100:
        print("✅ P&L magnitude looks realistic")
    else:
        print("⚠️ P&L still looks too high")
    
    if metrics['sharpe'] > 0:
        print("✅ Positive Sharpe ratio - good sign")
    else:
        print("⚠️ Negative Sharpe ratio - strategy needs work")
    
    return results, metrics

if __name__ == "__main__":
    results, metrics = run_conservative_backtest()
