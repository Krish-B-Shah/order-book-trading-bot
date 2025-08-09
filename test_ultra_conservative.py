"""
Ultra-Conservative Market Making Configuration
This configuration aims for truly realistic market making results
"""

from backtester import run_backtest, compute_metrics, plot_results, generate_html_report, print_performance_report
import matplotlib.pyplot as plt

def run_ultra_conservative_backtest():
    """Run backtest with ultra-conservative, realistic parameters"""
    print("🚀 Running ULTRA-CONSERVATIVE Market Making Backtest")
    print("=" * 65)
    
    # Ultra-conservative parameters for realistic market making
    symbol = "AAPL"
    num_rounds = 50            # Even fewer rounds
    starting_cash = 50000      # Larger capital base (more realistic for MM)
    spread = 8.00             # Much wider spread ($8.00)
    transaction_cost = 0.02    # Higher transaction costs (2 cents per share)
    
    print(f"📊 Ultra-Conservative Parameters:")
    print(f"   Symbol: {symbol}")
    print(f"   Rounds: {num_rounds} (very limited trading)")
    print(f"   Starting Cash: ${starting_cash:,.2f} (larger capital base)")
    print(f"   Spread: ${spread:.2f} (wide spread for selective trading)")
    print(f"   Transaction Cost: ${transaction_cost:.3f} per share")
    print(f"   Expected Trade Frequency: ~10-20% (very selective)")
    print("=" * 65)
    
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
    print("\n🎯 ULTRA-CONSERVATIVE BACKTEST RESULTS:")
    print(f"Final P&L: ${metrics['final_pnl']:.2f}")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Sharpe Ratio: {metrics['sharpe']:.3f}")
    print(f"Trade Frequency: {metrics['total_trades']}/{num_rounds} = {metrics['total_trades']/num_rounds:.1%}")
    print(f"P&L as % of Capital: {metrics['final_pnl']/starting_cash:.2%}")
    
    # Print detailed metrics
    if 'enhanced_metrics' in metrics:
        print_performance_report(metrics['enhanced_metrics'])
    
    # Generate plots
    print("\n📈 Generating ultra-conservative performance plots...")
    plt.ioff()
    plot_results(
        results["rounds"], 
        results["pnl"], 
        results["cash"], 
        results["inventory"], 
        results["trades"], 
        results["prices"]
    )
    plt.savefig("ultra_conservative_backtest.png", dpi=300, bbox_inches='tight')
    print("✅ Plot saved as ultra_conservative_backtest.png")
    
    # Generate HTML report
    generate_html_report(symbol, metrics)
    
    print("\n" + "="*65)
    print("🔍 REALISTIC TRADING ANALYSIS:")
    print("=" * 65)
    
    trade_freq = metrics['total_trades'] / num_rounds
    pnl_percent = metrics['final_pnl'] / starting_cash
    
    print(f"✅ Trade Frequency: {trade_freq:.1%}")
    if trade_freq < 0.25:
        print("   → GOOD: Selective trading (< 25% of opportunities)")
    else:
        print("   → Still too frequent for realistic market making")
    
    print(f"✅ P&L Percentage: {pnl_percent:.2%}")
    if pnl_percent < 0.02:  # Less than 2%
        print("   → REALISTIC: Small returns relative to capital")
    else:
        print("   → May still be too high for short-term trading")
    
    print(f"✅ Sharpe Ratio: {metrics['sharpe']:.3f}")
    if 0.5 < metrics['sharpe'] < 3.0:
        print("   → REALISTIC: Good but not excessive risk-adjusted returns")
    else:
        print("   → May indicate unrealistic performance")
    
    print(f"✅ Capital Efficiency: ${metrics['final_pnl']:.2f} profit on ${starting_cash:,.2f}")
    
    return results, metrics

if __name__ == "__main__":
    results, metrics = run_ultra_conservative_backtest()
