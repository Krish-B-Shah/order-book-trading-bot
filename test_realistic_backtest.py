"""
Test script to run backtester with realistic parameters
"""

from backtester import run_backtest, compute_metrics, plot_results, generate_html_report, print_performance_report
import matplotlib.pyplot as plt

def test_realistic_params():
    """Test with realistic market making parameters"""
    print("🚀 Testing Realistic Market Making Parameters")
    print("=" * 60)
    
    # Realistic parameters for AAPL market making
    symbol = "AAPL"
    num_rounds = 300           # Reduced trading frequency
    starting_cash = 10000      # $10k starting capital
    spread = 1.50             # $1.50 spread (more realistic for AAPL)
    transaction_cost = 0.005   # $0.005 per share transaction cost
    
    print(f"📊 Test Parameters:")
    print(f"   Symbol: {symbol}")
    print(f"   Rounds: {num_rounds}")
    print(f"   Starting Cash: ${starting_cash:,.2f}")
    print(f"   Spread: ${spread:.2f}")
    print(f"   Transaction Cost: ${transaction_cost:.3f} per share")
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
    print("\n🎯 REALISTIC BACKTEST RESULTS:")
    print(f"Final P&L: ${metrics['final_pnl']:.2f}")
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Sharpe Ratio: {metrics['sharpe']:.3f}")
    
    # Print detailed metrics
    if 'enhanced_metrics' in metrics:
        print_performance_report(metrics['enhanced_metrics'])
    
    # Generate plots
    print("\n📈 Generating realistic performance plots...")
    plt.ioff()
    plot_results(
        results["rounds"], 
        results["pnl"], 
        results["cash"], 
        results["inventory"], 
        results["trades"], 
        results["prices"]
    )
    plt.savefig("realistic_backtest.png", dpi=300, bbox_inches='tight')
    print("✅ Plot saved as realistic_backtest.png")
    
    # Generate HTML report
    generate_html_report(symbol, metrics)
    
    return results, metrics

if __name__ == "__main__":
    results, metrics = test_realistic_params()
