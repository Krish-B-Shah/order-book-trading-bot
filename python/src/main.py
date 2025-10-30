from .core.order_book import Order, OrderBook
from .strategies.market_maker import MarketMakingStrategy
from matplotlib import pyplot as plt
from typing import List
import random
import yfinance as yf
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest, StockLatestQuoteRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
from .config import API_KEY, SECRET_KEY
import time
import pandas as pd
import heapq

class AlpacaMarketDataProvider:
    # Importting the market data from alpaca that is used to get the current quote and historical bars. 
    def __init__(self, api_key, secret_key):
        self.data_client = StockHistoricalDataClient(api_key, secret_key)
        self.api_key = api_key
        self.secret_key = secret_key
        
    def get_current_quote(self, symbol): # This function is used to get the current quote of the stock. Or in the easy terms the bid and ask price of the stock.
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=[symbol]) # Requesting the current quote of the stock.
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
            print(f"Error fetching current quote: {e}")
            return None
    
    def get_historical_bars(self, symbol, timeframe, start, end): # This function is used to get the historical bars of the stock.
        try:
            request = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=timeframe,
                start=start,
                end=end
            )
            bars = self.data_client.get_stock_bars(request)
            
            # Handle the response properly - check if it's a valid response
            if bars and hasattr(bars, 'df'):
                df = bars.df
                if df is not None and not df.empty:
                    df = df.reset_index()
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
            print(f"Error fetching historical data: {e}")
            return None

def get_initial_price_and_quote(symbol = "AAPL"):  # This function is used to calculate the initial price and quote of the stock.
    data_provider = AlpacaMarketDataProvider(API_KEY, SECRET_KEY) # Getting the data provider of the stock.  
    print(f"Fetching real-time data for {symbol}...") # Printing the symbol that is being fetched.
    quote = data_provider.get_current_quote(symbol) # Getting the current quote of the stock.
    
    if quote: # If the quote is not None then it will print the quote.
        mid_price = (quote['bid'] + quote['ask']) / 2
        print(f"Using live {symbol} data from Alpaca:") # Printing the symbol that is being fetched.
        print(f"   Bid: ${quote['bid']:.2f} (Size: {quote['bid_size']})") # Printing the bid price of the stock.
        print(f"   Ask: ${quote['ask']:.2f} (Size: {quote['ask_size']})") # Printing the ask price of the stock.
        print(f"   Mid: ${mid_price:.2f}") # Printing the mid price of the stock.
        print(f"   Timestamp: {quote['timestamp']}") # Printing the timestamp of the quote.
        return {
            'price': mid_price,
            'bid': quote['bid'],
            'ask': quote['ask'],
            'source': 'alpaca'
        }
    
    try:
        print(f"Falling back to yfinance for {symbol}...") # Printing the symbol that is being fetched.
        ticker = yf.Ticker(symbol) # Getting the ticker of the stock.
        price_data = ticker.history(period="1d", interval="1m") # Getting the price data of the stock.
        
        if not price_data.empty: # If the price data is not empty then it will print the price data.
            latest_price = float(price_data["Close"].iloc[-1]) # Getting the latest price of the stock.
            spread = latest_price * 0.001  # 0.1% spread
            bid = latest_price - spread/2 # Getting the bid price of the stock.
            ask = latest_price + spread/2 # Getting the ask price of the stock.
            
            print(f"Using yfinance {symbol} price: ${latest_price:.2f}")
            return {
                'price': latest_price,
                'bid': bid,
                'ask': ask,
                'source': 'yfinance'
            }
    except Exception as e:
        print(f"yfinance error: {e}")
    
    # Final fallback to default
    print(f"All data sources failed, using default price")
    default_price = 150.0 if symbol == "AAPL" else 100.0
    spread = default_price * 0.002
    return {
        'price': default_price,
        'bid': default_price - spread/2,
        'ask': default_price + spread/2,
        'source': 'default'
    }

def get_market_data_stream(symbol, num_rounds): # This function is used to get the market data stream of the stock. 
    data_provider = AlpacaMarketDataProvider(API_KEY, SECRET_KEY) # Getting the data provider of the stock.
    user_start_time = input("Enter the start time of the stock (YYYY-MM-DD HH:MM): or press enter to use default (5 days ago)") # Getting the start time of the stock from the user.
    user_end_time = input("Enter the end time of the stock (YYYY-MM-DD HH:MM): or press enter to use default (now)") # Getting the end time of the stock from the user.
    start_time = datetime.now() - timedelta(days=5) if not user_start_time else datetime.strptime(user_start_time, "%Y-%m-%d %H:%M") # Getting the start time of the stock.
    end_time = datetime.now() if not user_end_time else datetime.strptime(user_end_time, "%Y-%m-%d %H:%M") # Getting the end time of the stock.

    print(f"Fetching historical data for {symbol} from {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%Y-%m-%d %H:%M')}...")
    historical_data = data_provider.get_historical_bars(
        symbol=symbol,
        timeframe=TimeFrame.Minute,
        start=start_time,
        end=end_time
    )
    
    # Validate historical data length
    if historical_data:
        print(f"Historical data received: {len(historical_data)} bars")
        if len(historical_data) >= num_rounds:
            # Use recent historical data
            selected_data = historical_data[-num_rounds:]  # Take last N bars
            print(f"Using {len(selected_data)} historical data points from Alpaca for {symbol}")
            
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
            print(f"Data used for {symbol} from: {market_data[0]['source']}")
            return market_data
        else:
            print(f"Insufficient historical data: {len(historical_data)} bars < {num_rounds} required")
    else:
        print(f"No historical data available for {symbol}")
    
    # Fallback to synthetic data based on current price
    print(f"Generating synthetic market data for {symbol}...")
    initial_data = get_initial_price_and_quote(symbol)
    synthetic_data = generate_synthetic_market_data(initial_data['price'], num_rounds, symbol)
    print(f"Data used for {symbol} from: {synthetic_data[0]['source']}")
    return synthetic_data


# Used when the market data is not available from the alpaca api.
def generate_synthetic_market_data(base_price: float, num_rounds: int, symbol: str):
    """Generate realistic synthetic market data with symbol-specific volatility"""
    data = []
    current_price = base_price
    
    # Symbol-specific volatility mapping for more realistic data
    vol_map = {
        'AAPL': 0.002,    # Apple - moderate volatility
        'TSLA': 0.006,    # Tesla - high volatility
        'NVDA': 0.005,    # NVIDIA - high volatility
        'GME': 0.01,      # GameStop - very high volatility
        'MSFT': 0.002,    # Microsoft - moderate volatility
        'GOOGL': 0.002,   # Google - moderate volatility
        'AMZN': 0.003,    # Amazon - moderate-high volatility
        'META': 0.004,    # Meta - high volatility
        'NFLX': 0.005,    # Netflix - high volatility
        'AMD': 0.006,     # AMD - high volatility
        'SPY': 0.001,     # S&P 500 ETF - low volatility
        'QQQ': 0.002,     # NASDAQ ETF - moderate volatility
        'IWM': 0.003,     # Russell 2000 ETF - moderate-high volatility
        'VTI': 0.001,     # Total Market ETF - low volatility
        'VOO': 0.001,     # S&P 500 ETF - low volatility
        'ARKK': 0.008,    # ARK Innovation ETF - very high volatility
        'PLTR': 0.007,    # Palantir - very high volatility
        'COIN': 0.009,    # Coinbase - very high volatility
        'RBLX': 0.006,    # Roblox - high volatility
        'SNOW': 0.005,    # Snowflake - high volatility
        'CRWD': 0.006,    # CrowdStrike - high volatility
        'ZM': 0.004,      # Zoom - moderate-high volatility
        'SHOP': 0.007,    # Shopify - very high volatility
        'SQ': 0.008,      # Square - very high volatility
        'UBER': 0.005,    # Uber - high volatility
        'LYFT': 0.006,    # Lyft - high volatility
        'DASH': 0.007,    # DoorDash - very high volatility
        'ABNB': 0.006,    # Airbnb - high volatility
        'SPOT': 0.005,    # Spotify - high volatility
        'PINS': 0.006,    # Pinterest - high volatility
        'SNAP': 0.008,    # Snapchat - very high volatility
        'TWTR': 0.005,    # Twitter - high volatility
        'DIS': 0.003,     # Disney - moderate-high volatility
        'NFLX': 0.005,    # Netflix - high volatility
        'CMCSA': 0.002,   # Comcast - moderate volatility
        'VZ': 0.002,      # Verizon - moderate volatility
        'T': 0.002,       # AT&T - moderate volatility
        'JPM': 0.002,     # JPMorgan Chase - moderate volatility
        'BAC': 0.003,     # Bank of America - moderate-high volatility
        'WFC': 0.003,     # Wells Fargo - moderate-high volatility
        'GS': 0.003,      # Goldman Sachs - moderate-high volatility
        'JNJ': 0.002,     # Johnson & Johnson - moderate volatility
        'PFE': 0.003,     # Pfizer - moderate-high volatility
        'UNH': 0.002,     # UnitedHealth - moderate volatility
        'HD': 0.002,      # Home Depot - moderate volatility
        'LOW': 0.002,     # Lowe's - moderate volatility
        'COST': 0.002,    # Costco - moderate volatility
        'WMT': 0.002,     # Walmart - moderate volatility
        'TGT': 0.003,     # Target - moderate-high volatility
        'CVS': 0.003,     # CVS Health - moderate-high volatility
        'UNP': 0.002,     # Union Pacific - moderate volatility
        'CAT': 0.003,     # Caterpillar - moderate-high volatility
        'DE': 0.003,      # Deere - moderate-high volatility
        'XOM': 0.003,     # Exxon Mobil - moderate-high volatility
        'CVX': 0.003,     # Chevron - moderate-high volatility
        'KO': 0.002,      # Coca-Cola - moderate volatility
        'PEP': 0.002,     # PepsiCo - moderate volatility
        'PG': 0.002,      # Procter & Gamble - moderate volatility
        'CL': 0.002,      # Colgate-Palmolive - moderate volatility
        'KMB': 0.002,     # Kimberly-Clark - moderate volatility
        'GIS': 0.002,     # General Mills - moderate volatility
        'K': 0.002,       # Kellogg - moderate volatility
        'HSY': 0.002,     # Hershey - moderate volatility
        'MCD': 0.002,     # McDonald's - moderate volatility
        'SBUX': 0.003,    # Starbucks - moderate-high volatility
        'YUM': 0.003,     # Yum! Brands - moderate-high volatility
        'CMG': 0.004,     # Chipotle - high volatility
        'NKE': 0.003,     # Nike - moderate-high volatility
        'UA': 0.004,      # Under Armour - high volatility
        'LULU': 0.005,    # Lululemon - high volatility
        'ROKU': 0.008,    # Roku - very high volatility
        'TTD': 0.007,     # Trade Desk - very high volatility
        'MELI': 0.006,    # MercadoLibre - high volatility
        'SE': 0.008,      # Sea Limited - very high volatility
        'BABA': 0.005,    # Alibaba - high volatility
        'JD': 0.005,      # JD.com - high volatility
        'PDD': 0.007,     # Pinduoduo - very high volatility
        'TCEHY': 0.004,   # Tencent - moderate-high volatility
        'NIO': 0.008,     # NIO - very high volatility
        'XPEV': 0.008,    # XPeng - very high volatility
        'LI': 0.007,      # Li Auto - very high volatility
        'BIDU': 0.005,    # Baidu - high volatility
        'TME': 0.006,     # Tencent Music - high volatility
        'NTES': 0.004,    # NetEase - moderate-high volatility
        'BILI': 0.007,    # Bilibili - very high volatility
        'DOGE': 0.015,    # Dogecoin - extremely high volatility
        'BTC': 0.012,     # Bitcoin - extremely high volatility
        'ETH': 0.013,     # Ethereum - extremely high volatility
        'ADA': 0.014,     # Cardano - extremely high volatility
        'SOL': 0.016,     # Solana - extremely high volatility
        'DOT': 0.015,     # Polkadot - extremely high volatility
        'LINK': 0.014,    # Chainlink - extremely high volatility
        'UNI': 0.015,     # Uniswap - extremely high volatility
        'MATIC': 0.016,   # Polygon - extremely high volatility
        'AVAX': 0.017,    # Avalanche - extremely high volatility
        'ATOM': 0.014,    # Cosmos - extremely high volatility
        'FTT': 0.018,     # FTX Token - extremely high volatility
        'LUNA': 0.019,    # Terra - extremely high volatility
        'SHIB': 0.020,    # Shiba Inu - extremely high volatility
        'XRP': 0.013,     # Ripple - extremely high volatility
        'LTC': 0.012,     # Litecoin - extremely high volatility
        'BCH': 0.013,     # Bitcoin Cash - extremely high volatility
        'XLM': 0.014,     # Stellar - extremely high volatility
        'VET': 0.015,     # VeChain - extremely high volatility
        'TRX': 0.014,     # TRON - extremely high volatility
        'EOS': 0.013,     # EOS - extremely high volatility
        'AAVE': 0.016,    # Aave - extremely high volatility
        'COMP': 0.015,    # Compound - extremely high volatility
        'MKR': 0.014,     # Maker - extremely high volatility
        'YFI': 0.017,     # Yearn Finance - extremely high volatility
        'SUSHI': 0.018,   # SushiSwap - extremely high volatility
        'CRV': 0.016,     # Curve - extremely high volatility
        '1INCH': 0.017,   # 1inch - extremely high volatility
        'ALPHA': 0.018,   # Alpha Finance - extremely high volatility
        'PERP': 0.019,    # Perpetual Protocol - extremely high volatility
        'RUNE': 0.015,    # THORChain - extremely high volatility
        'KSM': 0.014,     # Kusama - extremely high volatility
        'DYDX': 0.016,    # dYdX - extremely high volatility
        'IMX': 0.017,     # Immutable X - extremely high volatility
        'OP': 0.015,      # Optimism - extremely high volatility
        'ARB': 0.016,     # Arbitrum - extremely high volatility
        'ZKS': 0.017,     # zkSync - extremely high volatility
        'STRK': 0.018,    # Starknet - extremely high volatility
        'SUI': 0.019,     # Sui - extremely high volatility
        'APT': 0.016,     # Aptos - extremely high volatility
        'SEI': 0.017,     # Sei - extremely high volatility
        'INJ': 0.018,     # Injective - extremely high volatility
        'TIA': 0.019,     # Celestia - extremely high volatility
        'JUP': 0.020,     # Jupiter - extremely high volatility
        'WIF': 0.021,     # dogwifhat - extremely high volatility
        'BONK': 0.022,    # Bonk - extremely high volatility
        'PEPE': 0.023,    # Pepe - extremely high volatility
        'FLOKI': 0.024,   # Floki - extremely high volatility
        'DOGE': 0.015,    # Dogecoin - extremely high volatility
        'SHIB': 0.020,    # Shiba Inu - extremely high volatility
        'BABYDOGE': 0.025, # Baby Doge - extremely high volatility
        'SAFEMOON': 0.026, # SafeMoon - extremely high volatility
        'ELON': 0.027,    # Dogelon Mars - extremely high volatility
        'HOKK': 0.028,    # Hokkaidu Inu - extremely high volatility
        'KISHU': 0.029,   # Kishu Inu - extremely high volatility
        'SAMO': 0.030,    # Samoyedcoin - extremely high volatility
        'CORGI': 0.031,   # Corgi Inu - extremely high volatility
        'SHIBX': 0.032,   # Shiba X - extremely high volatility
        'DOGEKING': 0.033, # Doge King - extremely high volatility
        'MOONDOGE': 0.034, # Moon Doge - extremely high volatility
        'SPACEDOGE': 0.035, # Space Doge - extremely high volatility
        'GALAXYDOGE': 0.036, # Galaxy Doge - extremely high volatility
        'COSMICDOGE': 0.037, # Cosmic Doge - extremely high volatility
        'STELLARDOGE': 0.038, # Stellar Doge - extremely high volatility
        'NEBULADOGE': 0.039, # Nebula Doge - extremely high volatility
        'QUANTUMDOGE': 0.040, # Quantum Doge - extremely high volatility
        'HOLOGRAPHICDOGE': 0.041, # Holographic Doge - extremely high volatility
        'NEURALDOGE': 0.042, # Neural Doge - extremely high volatility
        'CYBERDOGE': 0.043, # Cyber Doge - extremely high volatility
        'NANODOGE': 0.044, # Nano Doge - extremely high volatility
        'PICODOGE': 0.045, # Pico Doge - extremely high volatility
        'FEMTODOG': 0.046, # Femto Dog - extremely high volatility
        'ATTODOG': 0.047,  # Atto Dog - extremely high volatility
        'ZEPTODOG': 0.048, # Zepto Dog - extremely high volatility
        'YOCTODOG': 0.049, # Yocto Dog - extremely high volatility
        'PLANCKDOG': 0.050 # Planck Dog - extremely high volatility
    }
    
    # Get volatility for symbol, default to 0.002 if not in map
    volatility = vol_map.get(symbol, 0.002)
    print(f"Using volatility of {volatility:.3f} for {symbol}")
    
    for i in range(num_rounds):
        # Random walk with symbol-specific volatility
        price_change_pct = random.gauss(0, volatility)
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
    # 10% chance to skip creating a market order (simulates no market interest)
    if random.random() < 0.1:
        return None
    side = random.choices(["buy", "sell"], weights=[0.7, 0.3])[0]  # more buys than sells
    quantity = random.randint(1, 10)

    # Simulate more realistic slippage (up to 0.5)
    slip = random.uniform(0, 0.5)
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
    """Enhanced summary with market data source info and validation"""
    print("\nSIMULATION COMPLETE!")
    print("=" * 70)
    print(f"Symbol: {market_data_info.get('symbol', 'Unknown')}")
    print(f"Data Source: {market_data_info.get('primary_source', 'Unknown')}")
    
    # Display validation information
    validation = market_data_info.get('validation', {})
    if validation:
        print(f"Data Points: {validation.get('num_points', 'Unknown')}")
        print(f"Price Range: ${validation.get('price_range', 0):.2f}")
        print(f"Volatility: {validation.get('price_volatility', 0):.3f}")
        print(f"Price Range: ${validation.get('min_price', 0):.2f} - ${validation.get('max_price', 0):.2f}")
        if 'warning' in validation:
            print(f"Warning: {validation['warning']}")
    
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
        print(f"\nRecent Trade History:")
        recent_trades = order_book.trade_log[-5:]
        for i, trade in enumerate(recent_trades, 1):
            timestamp_str = f"{trade['timestamp']:.0f}"
            print(f"  {i}: ${trade['price']:.2f} x {trade['quantity']} @ {timestamp_str}")
        if len(order_book.trade_log) > 5:
            print(f"  ... and {len(order_book.trade_log) - 5} more trades")

def validate_market_data(market_data_stream: List[dict], symbol: str) -> dict:
    """Validate market data quality and provide insights"""
    if not market_data_stream:
        return {'valid': False, 'message': 'No market data available'}
    
    data_source = market_data_stream[0]['source']
    num_points = len(market_data_stream)
    
    # Check price range
    prices = [data['price'] for data in market_data_stream]
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price
    price_volatility = price_range / min_price if min_price > 0 else 0
    
    validation_info = {
        'valid': True,
        'symbol': symbol,
        'data_source': data_source,
        'num_points': num_points,
        'price_range': price_range,
        'price_volatility': price_volatility,
        'min_price': min_price,
        'max_price': max_price,
        'message': f"Success: {symbol} data validated: {num_points} points from {data_source}"
    }
    
    # Add warnings for potential issues
    if data_source == 'synthetic' and price_volatility < 0.01:
        validation_info['warning'] = f"Low volatility detected for {symbol} - may indicate similar patterns"
    elif num_points < 10:
        validation_info['warning'] = f"Limited data points ({num_points}) for {symbol}"
    
    return validation_info

def run_simulation():
    print("Market Making Trading Bot Simulation with Real Market Data")
    print("=" * 70)

    # Get symbol from user
    symbol = input("Enter stock symbol (default: AAPL): ").upper().strip()
    if not symbol:
        symbol = "AAPL"

    # Get initial market data
    initial_market_data = get_initial_price_and_quote(symbol)
    
    try:
        num_rounds = int(input(f"\nEnter number of simulation rounds (default: 50): "))
    except (ValueError, EOFError):
        print("Using default of 50 rounds")
        num_rounds = 50

    # Get market data stream
    market_data_stream = get_market_data_stream(symbol, num_rounds)
    
    # Validate market data quality
    validation_info = validate_market_data(market_data_stream, symbol)
    print(f"\n{validation_info['message']}")
    if 'warning' in validation_info:
        print(f"Warning: {validation_info['warning']}")
    
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

    print(f"\nRunning {min(num_rounds, len(market_data_stream))} rounds with {symbol} data...")
    print("=" * 70)

    for round_num in range(1, min(num_rounds + 1, len(market_data_stream) + 1)):
        if round_num - 1 >= len(market_data_stream):
            break
        market_data = market_data_stream[round_num - 1]
        current_price = market_data['price']
        bid = market_data['bid']
        ask = market_data['ask']

        print(f"\nRound {round_num}: {symbol} Price=${current_price:.2f}, Bid=${bid:.2f}, Ask=${ask:.2f}")
        print(f"   Source: {market_data['source']}")

        # Bot places new limit orders
        bot_orders = bot.generate_orders(bid, ask, order_type="limit")
        for order in bot_orders:
            order_book.add_order(order)
            print(f"Bot placed: {order}")

        # Simulate market activity with realistic orders
        num_market_orders = random.randint(1, 3)
        for _ in range(num_market_orders):
            market_order = create_random_market_order(order_book, market_data)
            if market_order:
                print(f"Market order: {market_order}")
                order_book.add_order(market_order)

        # Execute matching
        matches_made = order_book.match(current_price)
        print(f"Made {matches_made} matches")

        # Track performance
        status = bot.get_status()
        rounds.append(round_num)
        pnl_history.append(status["pnl"])
        cash_history.append(status["cash"])
        inventory_history.append(status["inventory"])
        market_prices.append(current_price)

        print(f"Status: P&L=${status['pnl']:.2f}, Cash=${status['cash']:.2f}, Inventory={status['inventory']}")
        print("-" * 60)
        
        #time.sleep(1)  # Add a 1-second delay between rounds

        # Add small delay for realism (comment out for faster simulation)
        # time.sleep(0.1)

    # Simulation summary
    market_data_info = {
        'symbol': symbol,
        'primary_source': market_data_stream[0]['source'] if market_data_stream else 'unknown',
        'validation': validation_info
    }
    
    print_simulation_summary(bot, order_book, market_data_info)
    order_book.print_book()

    print("\nGenerating performance charts...")
    plot_results(rounds, pnl_history, cash_history, inventory_history, 
                order_book.trade_log, market_prices)

    # Export data
    export_choice = input("\nExport order and trade history to CSV? (y/n): ").lower().strip()
    if export_choice == 'y':
        order_book.export_orders(f"{symbol}_order_history.csv")
        order_book.export_trades(f"{symbol}_trade_history.csv")
        print("Data exported successfully!")

# --- PATCH OrderBook.match for partial/missed fills ---
def match_with_realism(self, current_price):
    while self.buy_orders and self.sell_orders:
        best_buy = self.buy_orders[0]
        best_sell = self.sell_orders[0]

        # 10% chance to miss a match entirely
        if random.random() < 0.1:
            break

        if best_buy.price >= best_sell.price:
            trade_qty = min(best_buy.quantity, best_sell.quantity)
            # 20% chance to only fill part of the order
            if random.random() < 0.2:
                trade_qty = max(1, int(trade_qty * random.uniform(0.2, 0.8)))
            trade_price = best_sell.price

            self.trade_log.append({
                "price": trade_price,
                "quantity": trade_qty,
                "timestamp": time.time()
            })

            if best_buy.owner:
                best_buy.owner.updateProfitAndLoss(trade_price, trade_qty, "buy", current_price)
            if best_sell.owner:
                best_sell.owner.updateProfitAndLoss(trade_price, trade_qty, "sell", current_price)

            best_buy.quantity -= trade_qty
            best_sell.quantity -= trade_qty

            if best_buy.quantity == 0:
                heapq.heappop(self.buy_orders)
                self.order_map.pop(best_buy.order_id, None)
            if best_sell.quantity == 0:
                heapq.heappop(self.sell_orders)
                self.order_map.pop(best_sell.order_id, None)
        else:
            break

OrderBook.match = match_with_realism

if __name__ == "__main__":
    while True:
        run_simulation()
        cont = input("\nRun another simulation? (y/n): ").lower().strip()
        if cont != 'y':
            print("Thanks for using the Market Making Bot! Goodbye!")
            break
    print("Exiting...")
