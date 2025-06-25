from order_book import Order, OrderBook
import order_book
from strategy import MarketMakingStrategy
from matplotlib import pyplot as plt
from typing import List
import random
import yfinance as yf



def get_initial_price():
    try:
        ticker = yf.Ticker("AMZN")
        price_data = ticker.history(period="1d", interval="1m")
        if not price_data.empty:
            latest_price = float(price_data["Close"].iloc[-1])
            print(f"📈 Using live AMZN price: ${latest_price:.2f}")
            return latest_price
        else:
            print(f"⚠️ No live data available, using default price: $100.00")
            return 100.0
    except ImportError:
        print(f"⚠️ yfinance not available, using default price: $100.00")
        return 100.0
    except Exception as e:
        print(f"⚠️ Error fetching live data: {e}")
        print(f"Using default price: $100.00")
        return 100.0


def simulate_market_conditions(base_price):
    # Simulate some market conditions
    price_change = random.uniform(-2.0, 2.0)
    current_price = base_price + price_change
    
    # Create realistic bid-ask spread
    spread = random.uniform(0.5, 2.0)
    bid = current_price - spread / 2
    ask = current_price + spread / 2

    return current_price, bid, ask  # Simulated mid-price around $100

# book = OrderBook()
# bot = MarketMakingStrategy(order_book=book)
def plot_results(rounds: List[int], pnl_history: List[float], 
                cash_history: List[float], inventory_history: List[int],
                trade_log: List[dict]) -> None:
    """Create comprehensive visualization of trading results"""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
    
    # P&L over time
    ax1.plot(rounds, pnl_history, marker='o', linewidth=2, markersize=4, color='blue')
    ax1.set_title("Profit & Loss Over Time", fontsize=14, fontweight='bold')
    ax1.set_xlabel("Round")
    ax1.set_ylabel("P&L ($)")
    ax1.axhline(0, color='red', linestyle='--', alpha=0.7)
    ax1.grid(True, alpha=0.3)
    
    # Cash over time
    ax2.plot(rounds, cash_history, marker='s', color='green', linewidth=2, markersize=4)
    ax2.set_title("Cash Position Over Time", fontsize=14, fontweight='bold')
    ax2.set_xlabel("Round")
    ax2.set_ylabel("Cash ($)")
    ax2.grid(True, alpha=0.3)
    
    # Inventory over time
    ax3.plot(rounds, inventory_history, marker='^', color='orange', linewidth=2, markersize=4)
    ax3.set_title("Inventory Over Time", fontsize=14, fontweight='bold')
    ax3.set_xlabel("Round")
    ax3.set_ylabel("Inventory (units)")
    ax3.axhline(0, color='black', linestyle='--', alpha=0.7)
    ax3.grid(True, alpha=0.3)
    
    # Trade prices over time
    if trade_log:
        trade_prices = [trade['price'] for trade in trade_log]
        trade_rounds = list(range(1, len(trade_prices) + 1))
        ax4.plot(trade_rounds, trade_prices, marker='d', color='purple', linewidth=2, markersize=4)
        ax4.set_title("Trade Prices Over Time", fontsize=14, fontweight='bold')
        ax4.set_xlabel("Trade Number")
        ax4.set_ylabel("Price ($)")
        ax4.grid(True, alpha=0.3)
    else:
        ax4.text(0.5, 0.5, 'No Trades Executed', ha='center', va='center', transform=ax4.transAxes)
        ax4.set_title("Trade Prices Over Time", fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.show()
    
def create_random_market_order(order_book: OrderBook):
    side = random.choice(["buy", "sell"])
    quantity = random.randint(1, 5)

    return Order(
        order_id=order_book.next_order_id(),
        side=side,
        price=0,
        quantity=quantity,
        order_type="market"
    )

def print_simulation_summary(bot: MarketMakingStrategy, order_book: OrderBook) -> None:
    print("\n🏁 SIMULATION COMPLETE!")
    print("=" * 60)
    print(f"Final P&L: ${bot.pnl:.2f}")
    print(f"Final Cash: ${bot.cash:.2f}")
    print(f"Final Inventory: {bot.inventory}")
    print(f"Total Trades: {len(order_book.trade_log)}")
    
    # Show recent trades
    if order_book.trade_log:
        print(f"\n📋 Recent Trade History:")
        recent_trades = order_book.trade_log[-5:]  # Show last 5 trades
        for i, trade in enumerate(recent_trades, 1):
            timestamp_str = f"{trade['timestamp']:.0f}"
            print(f"  {i}: ${trade['price']:.2f} x {trade['quantity']} @ {timestamp_str}")
        if len(order_book.trade_log) > 5:
            print(f"  ... and {len(order_book.trade_log) - 5} more trades")


def run_simulation():
    print("🚀 Market Making Trading Bot Simulation")
    print("=" * 60)
    
    # Get initial price
    initial_price = get_initial_price()
    
    order_book = OrderBook()
    bot = MarketMakingStrategy(
        starting_cash=10000,
        order_book=order_book,
        max_inventory=10,
        spread=2.0
    )
    
    # Simulation parameters
    try:
        num_rounds = int(input("\n🎯 Enter number of simulation rounds: "))
    except ValueError:
        print("Invalid input, using default of 50 rounds")
        num_rounds = 50
        
    market_order_probability = 0.3  # 30% chance of market order each round
    
    # Tracking variables
    rounds: List[int] = []
    pnl_history: List[float] = []
    cash_history: List[float] = []
    inventory_history: List[int] = []
    current_price = initial_price
    
    print(f"\n🎮 Running {num_rounds} rounds of simulation...")
    print("=" * 60)
    
    # Main simulation loop
    for round_num in range(num_rounds):
        print(f"\n🔄 Round {round_num + 1}/{num_rounds}")
        
        # Simulate market conditions
        current_price, bid, ask = simulate_market_conditions(current_price)
        print(f"📊 Market: Bid=${bid:.2f}, Ask=${ask:.2f}, Mid=${current_price:.2f}")
        
        # Generate and place bot orders
        bot_orders = bot.generate_orders(bid, ask, order_type="limit")
        for order in bot_orders:
            order_book.add_order(order)
            print(f"🤖 Bot placed: {order}")
        
        # Simulate random market activity
        if random.random() < market_order_probability:
            market_order = create_random_market_order(order_book)
            print(f"🌊 Market order: {market_order}")
            order_book.add_order(market_order)
    
        # Match orders
        order_book.match(current_price)
        
        # Record metrics
        status = bot.get_status()
        rounds.append(round_num + 1)
        pnl_history.append(status["pnl"])
        cash_history.append(status["cash"])
        inventory_history.append(status["inventory"])
        
        print(f"📈 Status: P&L=${status['pnl']:.2f}, Cash=${status['cash']:.2f}, Inventory={status['inventory']}")
        print("-" * 50)
    
    # Print final results
    print_simulation_summary(bot, order_book)
    
    # Show remaining orders in book
    order_book.print_book()
    
    # Create visualizations
    print("\n📊 Generating performance charts...")
    plot_results(rounds, pnl_history, cash_history, inventory_history, order_book.trade_log)
    
    # Optional data export
    export_choice = input("\n💾 Export order and trade history to CSV? (y/n): ").lower().strip()
    if export_choice == 'y':
        order_book.export_orders("order_history.csv")
        order_book.export_trades("trade_history.csv")
        print("✅ Data exported successfully!")


if __name__ == "__main__":
    run_simulation()