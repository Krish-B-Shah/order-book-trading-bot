from config import API_KEY, SECRET_KEY
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.data import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AlpacaTrader:
    def __init__(self, api_key, secret_key, paper=True):
        self.trading_client = TradingClient(api_key, secret_key, paper=paper)
        self.data_client = StockHistoricalDataClient(api_key, secret_key)
        logger.info(f"Initialized Alpaca client in {'paper' if paper else 'live'} mode")
    
    def get_account_info(self):
        """Get and display account information"""
        try:
            account = self.trading_client.get_account()
            print("\n" + "="*50)
            print("ACCOUNT INFORMATION")
            print("="*50)
            print(f"Account Status: {account.status}")
            print(f"Buying Power: ${float(account.buying_power):,.2f}")
            print(f"Cash: ${float(account.cash):,.2f}")
            print(f"Portfolio Value: ${float(account.portfolio_value):,.2f}")
            print(f"Day Trade Count: {account.daytrade_buying_power}")
            print(f"Pattern Day Trader: {account.pattern_day_trader}")
            return account
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def get_current_price(self, symbol):
        """Get current price for a symbol"""
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.data_client.get_stock_latest_quote(request)
            return float(quote[symbol].bid_price)
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None
    
    def place_market_order(self, symbol, quantity, side, dry_run=True):
        """Place a market order"""
        try:
            order_details = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.DAY
            )
            
            if dry_run:
                current_price = self.get_current_price(symbol)
                estimated_cost = current_price * quantity if current_price else "Unknown"
                print(f"\n[DRY RUN] Would place order:")
                print(f"Symbol: {symbol}")
                print(f"Side: {side.value}")
                print(f"Quantity: {quantity}")
                print(f"Type: Market Order")
                print(f"Estimated Cost: ${estimated_cost}")
                return None
            else:
                order = self.trading_client.submit_order(order_details)
                logger.info(f"Order placed: {order.id}")
                return order
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def place_limit_order(self, symbol, quantity, side, limit_price, dry_run=True):
        """Place a limit order"""
        try:
            order_details = LimitOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=side,
                time_in_force=TimeInForce.DAY,
                limit_price=limit_price
            )
            
            if dry_run:
                print(f"\n[DRY RUN] Would place limit order:")
                print(f"Symbol: {symbol}")
                print(f"Side: {side.value}")
                print(f"Quantity: {quantity}")
                print(f"Limit Price: ${limit_price}")
                return None
            else:
                order = self.trading_client.submit_order(order_details)
                logger.info(f"Limit order placed: {order.id}")
                return order
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return None
    
    def get_positions(self):
        """Get and display current positions"""
        try:
            positions = self.trading_client.get_all_positions()
            
            if not positions:
                print("\nNo current positions.")
                return positions
            
            print("\n" + "="*70)
            print("CURRENT POSITIONS")
            print("="*70)
            print(f"{'Symbol':<10} {'Qty':<10} {'Avg Cost':<12} {'Current':<12} {'P&L':<12} {'P&L %':<10}")
            print("-" * 70)
            
            total_pnl = 0
            for position in positions:
                qty = float(position.qty)
                avg_cost = float(position.avg_entry_price)
                current_price = float(position.current_price)
                pnl = float(position.unrealized_pl)
                pnl_percent = float(position.unrealized_plpc) * 100
                
                total_pnl += pnl
                
                print(f"{position.symbol:<10} {qty:<10.0f} ${avg_cost:<11.2f} ${current_price:<11.2f} "
                      f"${pnl:<11.2f} {pnl_percent:<9.1f}%")
            
            print("-" * 70)
            print(f"{'TOTAL P&L:':<56} ${total_pnl:<11.2f}")
            
            return positions
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_orders(self):
        """Get and display current orders"""
        try:
            orders = self.trading_client.get_orders()
            
            if not orders:
                print("\nNo current orders.")
                return orders
            
            print("\n" + "="*80)
            print("CURRENT ORDERS")
            print("="*80)
            print(f"{'Symbol':<10} {'Side':<6} {'Qty':<8} {'Type':<8} {'Price':<10} {'Status':<12} {'Time':<20}")
            print("-" * 80)
            
            for order in orders:
                order_time = order.created_at.strftime("%Y-%m-%d %H:%M:%S")
                price = f"${float(order.limit_price):.2f}" if order.limit_price else "Market"
                
                print(f"{order.symbol:<10} {order.side.value:<6} {float(order.qty):<8.0f} "
                      f"{order.order_type.value:<8} {price:<10} {order.status.value:<12} {order_time}")
            
            return orders
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []
    
    def close_position(self, symbol, dry_run=True):
        """Close a specific position"""
        try:
            if dry_run:
                print(f"\n[DRY RUN] Would close position for {symbol}")
                return None
            else:
                result = self.trading_client.close_position(symbol)
                logger.info(f"Position closed for {symbol}")
                return result
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            return None
    
    def close_all_positions(self, dry_run=True):
        """Close all positions - use with extreme caution!"""
        try:
            if dry_run:
                positions = self.get_positions()
                if positions:
                    print(f"\n[DRY RUN] Would close {len(positions)} positions")
                    for pos in positions:
                        print(f"  - {pos.symbol}: {pos.qty} shares")
                return None
            else:
                print("\n⚠️  CLOSING ALL POSITIONS ⚠️")
                result = self.trading_client.close_all_positions(cancel_orders=True)
                logger.info("All positions closed")
                return result
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
            return None

def main():
    # Initialize trader
    trader = AlpacaTrader(API_KEY, SECRET_KEY, paper=True)
    
    # Get account information
    trader.get_account_info()
    
    # Get current positions
    trader.get_positions()
    
    # Get current orders
    trader.get_orders()
    
    # Example: Place a dry run market order (safe to run)
    trader.place_market_order("AAPL", 10, OrderSide.BUY, dry_run=True)
    
    # Example: Place a dry run limit order
    trader.place_limit_order("AAPL", 10, OrderSide.BUY, 150.00, dry_run=True)
    
    # Example: Get current price
    price = trader.get_current_price("AAPL")
    if price:
        print(f"\nCurrent AAPL price: ${price:.2f}")

if __name__ == "__main__":
    main()