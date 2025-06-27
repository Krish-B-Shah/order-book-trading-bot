from order_book import Order, OrderBook
import order_book
from strategy import MarketMakingStrategy
from matplotlib import pyplot as plt
from typing import List
import random
import yfinance as yf
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from config import API_KEY, SECRET_KEY
import time
import pandas as pd

class AlpacaMarketDataProvider:
    """Enhanced market data provider using Alpaca API with fallbacks"""
    
    def __init__(self, api_key: str, secret_key: str):
        self.data_client = StockHistoricalDataClient(api_key, secret_key)
        self.api_key = api_key
        self.secret_key = secret_key
        
    def get_current_quote(self, symbol: str):
        """Get current bid/ask quote for a symbol"""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
            quotes = self.data_client.get_stock_latest_quote(request)
            
            if symbol in quotes:
                quote = quotes[symbol]
                return {
                    'bid': float(quote.bid_price),
                    'ask': float(quote.ask_price),
                    'bid_size': int(quote.bid_size),
                    'ask_size': int(quote.ask_size),
                    'timestamp': quote.timestamp
                }
            return None
        except Exception as e:
            print(f"⚠️ Error fetching current quote: {e}")
            return None
    
    def get_historical_bars(self, symbol: str, timeframe: TimeFrame, start: datetime, end: datetime):
        """Get historical bar data"""
        try:
            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=timeframe,
                start=start,
                end=end
            )
            bars = self.data_client.get_stock_bars(request)
            
            if bars.df is not None and not bars.df.empty:
                df = bars.df.reset_index()
                historical_data = []
                
                for _, row in df.iterrows():
                    historical_data.append({
                        'timestamp': row['timestamp'],
                        'open': float(row['open']),
                        'high': float(row['high']),
                        'low': float(row['low']),
                        'close': float(row['close']),
                        'volume': int(row['volume'])
                    })
                
                return historical_data
            return None
        except Exception as e:
            print(f"⚠️ Error fetching historical data: {e}")
            return None

def get_initial_price_and_quote(symbol: str = "AAPL"):
    """Get initial price using multiple data sources with fallbacks"""
    data_provider = AlpacaMarketDataProvider(API_KEY, SECRET_KEY)
    
    # Try Alpaca first for real-time quote
    print(f"📡 Fetching real-time data for {symbol}...")
    quote = data_provider.get_current_quote(symbol)
    
    if quote:
        mid_price = (quote['bid'] + quote['ask']) / 2
        print(f"📈 Using live {symbol} data from Alpaca:")
        print(f"   Bid: ${quote['bid']:.2f} (Size: {quote['bid_size']})")
        print(f"   Ask: ${quote['ask']:.2f} (Size: {quote['ask_size']})")
        print(f"   Mid: ${mid_price:.2f}")
        print(f"   Timestamp: {quote['timestamp']}")
        return {
            'price': mid_price,
            'bid': quote['bid'],
            'ask': quote['ask'],
            'source': 'alpaca'
        }
    
    # Fallback to yfinance
    try:
        print(f"📡 Falling back to yfinance for {symbol}...")
        ticker = yf.Ticker(symbol)
        price_data = ticker.history(period="1d", interval="1m")
        
        if not price_data.empty:
            latest_price = float(price_data["Close"].iloc[-1])
            spread = latest_price * 0.001  # 0.1% spread
            bid = latest_price - spread/2
            ask = latest_price + spread/2
            
            print(f"📈 Using yfinance {symbol} price: ${latest_price:.2f}")
            return {
                'price': latest_price,
                'bid': bid,
                'ask': ask,
                'source': 'yfinance'
            }
    except Exception as e:
        print(f"⚠️ yfinance error: {e}")
    
    # Final fallback to default
    print(f"⚠️ All data sources failed, using default price")
    default_price = 150.0 if symbol == "AAPL" else 100.0
    spread = default_price * 0.002
    return {
        'price': default_price,
        'bid': default_price - spread/2,
        'ask': default_price + spread/2,
        'source': 'default'
    }

def get_market_data_stream(symbol: str, num_rounds: int):
    """Get streaming market data for simulation"""
    data_provider = AlpacaMarketDataProvider(API_KEY, SECRET_KEY)
    
    from datetime import datetime, time as dtime

    today = datetime.now().date()
    start_time = datetime.today().replace(hour=9, minute=30, second=0, microsecond=0)
    end_time = datetime.now()


    
    print(f"📊 Fetching historical data for {symbol}...")
    historical_data = data_provider.get_historical_bars(
        symbol=symbol,
        timeframe=TimeFrame.Minute,
        start=start_time,
        end=end_time
    )
    
    if historical_data and len(historical_data) >= num_rounds:
        # Use recent historical data
        selected_data = historical_data[-num_rounds:]  # Take last N bars
        print(f"✅ Using {len(selected_data)} historical data points from Alpaca")
        
        # Convert to our expected format
        market_data = []
        for bar in selected_data:
            spread = bar['close'] * 0.001  # 0.1% spread
            market_data.append({
                'timestamp': bar['timestamp'],
                'price': bar['close'],
                'bid': bar['close'] - spread/2,
                'ask': bar['close'] + spread/2,
                'volume': bar['volume'],
                'source': 'alpaca_historical'
            })
        return market_data
    
    # Fallback to synthetic data based on current price
    print("📊 Generating synthetic market data...")
    initial_data = get_initial_price_and_quote(symbol)
    return generate_synthetic_market_data(initial_data['price'], num_rounds)

def generate_synthetic_market_data(base_price: float, num_rounds: int):
    """Generate realistic synthetic market data"""
    data = []
    current_price = base_price
    
    for i in range(num_rounds):
        # Random walk with realistic volatility
        price_change_pct = random.gauss(0, 0.002)  # 0.2% volatility per round
        current_price *= (1 + price_change_pct)
        current_price = max(current_price, base_price * 0.5)  # Don't go below 50% of base
        
        # Create realistic bid-ask spread (0.05% to 0.2%)
        spread_pct = random.uniform(0.0005, 0.002)
        spread = current_price * spread_pct
        bid = current_price - spread / 2
        ask = current_price + spread / 2
        
        data.append({
            'timestamp': datetime.now().timestamp() + i,
            'price': current_price,
            'bid': bid,
            'ask': ask,
            'volume': random.randint(100, 1000),
            'source': 'synthetic'
        })
    
    return data

def create_random_market_order(order_book: OrderBook, market_data: dict):
    side = random.choices(["buy", "sell"], weights=[0.7, 0.3])[0]  # more buys than sells
    quantity = random.randint(1, 10)

    # Simulate slippage
    slip = random.uniform(0, 0.1)
    if side == "buy":
        price = market_data['ask'] + slip
    else:
        price = market_data['bid'] - slip

    return Order(
        order_id=order_book.next_order_id(),
        side=side,
        price=round(price, 2),
        quantity=quantity,
        order_type="market"
    )

def plot_results(rounds: List[int], pnl_history: List[float], 
                cash_history: List[float], inventory_history: List[int],
                trade_log: List[dict], market_prices: List[float]) -> None:
    """Enhanced visualization with market price overlay"""
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    # P&L over time with market price
    ax1_twin = ax1.twinx()
    ax1.plot(rounds, pnl_history, marker='o', linewidth=2, markersize=4, color='blue', label='P&L')
    ax1_twin.plot(rounds, market_prices, marker='s', linewidth=1, markersize=2, color='red', alpha=0.7, label='Market Price')
    
    ax1.set_title("Profit & Loss vs Market Price", fontsize=14, fontweight='bold')
    ax1.set_xlabel("Round")
    ax1.set_ylabel("P&L ($)", color='blue')
    ax1_twin.set_ylabel("Market Price ($)", color='red')
    ax1.axhline(0, color='gray', linestyle='--', alpha=0.7)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    ax1_twin.legend(loc='upper right')
    
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
    
    # Trade prices vs market price
    if trade_log:
        trade_prices = [trade['price'] for trade in trade_log]
        trade_rounds = list(range(1, len(trade_prices) + 1))
        ax4.scatter(trade_rounds, trade_prices, marker='d', color='purple', s=50, alpha=0.8, label='Trade Prices')
        
        # Show market price trend for comparison
        if len(market_prices) > 0:
            ax4.plot(rounds, market_prices, color='red', alpha=0.5, linewidth=1, label='Market Price')
            
        ax4.set_title("Trade Prices vs Market Price", fontsize=14, fontweight='bold')
        ax4.set_xlabel("Round/Trade Number")
        ax4.set_ylabel("Price ($)")
        ax4.legend()
        ax4.grid(True, alpha=0.3)
    else:
        ax4.text(0.5, 0.5, 'No Trades Executed', ha='center', va='center', transform=ax4.transAxes)
        ax4.set_title("Trade Prices Over Time", fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.show()

def print_simulation_summary(bot: MarketMakingStrategy, order_book: OrderBook, market_data_info: dict) -> None:
    """Enhanced summary with market data source info"""
    print("\n🏁 SIMULATION COMPLETE!")
    print("=" * 70)
    print(f"Data Source: {market_data_info.get('primary_source', 'Unknown')}")
    print(f"Symbol: {market_data_info.get('symbol', 'Unknown')}")
    print(f"Final P&L: ${bot.pnl:.2f}")
    print(f"Final Cash: ${bot.cash:.2f}")
    print(f"Final Inventory: {bot.inventory}")
    print(f"Total Trades: {len(order_book.trade_log)}")
    
    # Calculate performance metrics
    if len(order_book.trade_log) > 0:
        avg_trade_price = sum(trade['price'] for trade in order_book.trade_log) / len(order_book.trade_log)
        print(f"Average Trade Price: ${avg_trade_price:.2f}")
    
    # Show recent trades
    if order_book.trade_log:
        print(f"\n📋 Recent Trade History:")
        recent_trades = order_book.trade_log[-5:]
        for i, trade in enumerate(recent_trades, 1):
            timestamp_str = f"{trade['timestamp']:.0f}"
            print(f"  {i}: ${trade['price']:.2f} x {trade['quantity']} @ {timestamp_str}")
        if len(order_book.trade_log) > 5:
            print(f"  ... and {len(order_book.trade_log) - 5} more trades")

def run_simulation():
    print("🚀 Market Making Trading Bot Simulation with Real Market Data")
    print("=" * 70)

    # Get symbol from user
    symbol = input("📊 Enter stock symbol (default: AAPL): ").upper().strip()
    if not symbol:
        symbol = "AAPL"

    # Get initial market data
    initial_market_data = get_initial_price_and_quote(symbol)
    
    try:
        num_rounds = int(input(f"\n🎯 Enter number of simulation rounds (default: 50): "))
    except (ValueError, EOFError):
        print("Using default of 50 rounds")
        num_rounds = 50

    # Get market data stream
    market_data_stream = get_market_data_stream(symbol, num_rounds)
    
    # Initialize trading components
    order_book = OrderBook()
    bot = MarketMakingStrategy(
        starting_cash=10000,
        order_book=order_book,
        max_inventory=20,  # Increased for more active trading
        spread=0.10  # Tighter spread for more realistic market making
    )

    # Tracking arrays
    rounds: List[int] = []
    pnl_history: List[float] = []
    cash_history: List[float] = []
    inventory_history: List[int] = []
    market_prices: List[float] = []

    print(f"\n🎮 Running {min(num_rounds, len(market_data_stream))} rounds with {symbol} data...")
    print("=" * 70)

    for round_num in range(1, min(num_rounds + 1, len(market_data_stream) + 1)):
        if round_num - 1 >= len(market_data_stream):
            break
        market_data = market_data_stream[round_num - 1]
        current_price = market_data['price']
        bid = market_data['bid']
        ask = market_data['ask']

        print(f"\n🔄 Round {round_num}: {symbol} Price=${current_price:.2f}, Bid=${bid:.2f}, Ask=${ask:.2f}")
        print(f"   Source: {market_data['source']}")

        # Bot places new limit orders
        bot_orders = bot.generate_orders(bid, ask, order_type="limit")
        for order in bot_orders:
            order_book.add_order(order)
            print(f"🤖 Bot placed: {order}")

        # Simulate market activity with realistic orders
        num_market_orders = random.randint(1, 3)
        for _ in range(num_market_orders):
            market_order = create_random_market_order(order_book, market_data)
            print(f"🌊 Market order: {market_order}")
            order_book.add_order(market_order)

        # Execute matching
        matches_made = order_book.match(current_price)
        print(f"⚡ Made {matches_made} matches")

        # Track performance
        status = bot.get_status()
        rounds.append(round_num)
        pnl_history.append(status["pnl"])
        cash_history.append(status["cash"])
        inventory_history.append(status["inventory"])
        market_prices.append(current_price)

        print(f"📈 Status: P&L=${status['pnl']:.2f}, Cash=${status['cash']:.2f}, Inventory={status['inventory']}")
        print("-" * 60)
        
        time.sleep(1)  # Add a 1-second delay between rounds

        # Add small delay for realism (comment out for faster simulation)
        # time.sleep(0.1)

    # Simulation summary
    market_data_info = {
        'symbol': symbol,
        'primary_source': market_data_stream[0]['source'] if market_data_stream else 'unknown'
    }
    
    print_simulation_summary(bot, order_book, market_data_info)
    order_book.print_book()

    print("\n📊 Generating performance charts...")
    plot_results(rounds, pnl_history, cash_history, inventory_history, 
                order_book.trade_log, market_prices)

    # Export data
    export_choice = input("\n💾 Export order and trade history to CSV? (y/n): ").lower().strip()
    if export_choice == 'y':
        order_book.export_orders(f"{symbol}_order_history.csv")
        order_book.export_trades(f"{symbol}_trade_history.csv")
        print("✅ Data exported successfully!")

if __name__ == "__main__":
    run_simulation()