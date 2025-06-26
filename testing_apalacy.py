from config import API_KEY, SECRET_KEY
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.stream import TradingStream

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime

# Create a historical data client
# client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

# Create a trading client (paper trading mode)
client1 = TradingClient(API_KEY, SECRET_KEY, paper=True)
account = client1.get_account()
for key, value in account:
    print(f"{key}: {value}")

order_details = MarketOrderRequest(
    symbol="AAPL",  # You can change this to "AMZN" if needed
    qty=100,  # Number of shares to buy
    side=OrderSide.BUY,  # Buy order
  # type=OrderType.MARKET,  # Market order
    time_in_force=TimeInForce.DAY  # Order valid for the day
)

order = client1.submit_order(order_details)
trades = TradingStream(API_KEY, SECRET_KEY, paper=True)

async def handle_order_updates(order_update):
    print(f"Order Update: {order_update}")  

trades.subscribe_order_updates(handle_order_updates)
trades.run()
# Set up the historical data request
# request_params = StockBarsRequest(
#     symbol_or_symbols=["AAPL"],     # You can change this to ["AMZN"] if needed
#     timeframe=TimeFrame.Minute,
#     start=datetime(2024, 6, 24)
# )

# # Get historical bars
# bars = client.get_stock_bars(request_params)

# # Show the result
# print(bars.df.head())
