import logging
import sys
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import re
import random
import math
import time

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

from config import API_KEY, SECRET_KEY

# Enhanced logging configuration
class ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

def setup_logging():
    """Setup enhanced logging with colors and file output"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # File handler
    file_handler = logging.FileHandler('market_making.log', encoding='utf-8')
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler with colors
    console_handler = logging.StreamHandler()
    console_formatter = ColoredFormatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logging.getLogger(__name__)

logger = setup_logging()

class BotStatus(Enum):
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    SHUTDOWN = "shutdown"

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

@dataclass
class TradingConfig:
    """Enhanced trading configuration with validation"""
    symbol: str = "AAPL"
    max_rounds: int = 100
    base_spread: float = 0.10
    position_size: int = 1
    max_position: int = 5  # Reduced from 20 to 5 for better risk management
    sleep_interval: float = 2.0
    
    # Simulation mode
    simulation_mode: bool = True  # Use simulated market data instead of live data
    
    # Risk management
    max_daily_loss: float = 1000.0
    max_drawdown_pct: float = 0.05
    position_limit_pct: float = 0.8  # % of buying power
    
    # Market making parameters
    inventory_skew_factor: float = 0.02
    min_spread_bps: int = 5  # basis points
    max_spread_bps: int = 50
    volatility_adjustment: bool = True
    
    # Order management
    max_open_orders_per_side: int = 2  # Reduced from 3 to 2 for better control
    order_timeout_seconds: int = 300
    
    # Exit strategies
    take_profit_pct: float = 0.015   # 1.5%
    stop_loss_pct: float = 0.008     # 0.8%
    trail_stop_pct: float = 0.005    # 0.5%
    
    # Performance tracking
    performance_window: int = 50
    rebalance_threshold: float = 0.02
    
    def __post_init__(self):
        """Validate configuration parameters"""
        if self.max_position <= 0:
            raise ValueError("max_position must be positive")
        if self.base_spread <= 0:
            raise ValueError("base_spread must be positive")
        if self.take_profit_pct <= self.stop_loss_pct:
            raise ValueError("take_profit_pct must be greater than stop_loss_pct")

class InteractiveConfigBuilder:
    """Interactive configuration builder for the market making bot"""
    
    def __init__(self):
        self.config = TradingConfig()
        self.data_client = None
        self.trading_client = None
        self.account_info = None  # Initialize account_info attribute
        self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialize Alpaca clients for validation"""
        try:
            self.data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
            self.trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
            logger.info("✅ Alpaca clients initialized for configuration")
        except Exception as e:
            logger.error(f"❌ Failed to initialize clients: {e}")
            print("⚠️ Warning: Cannot validate account or symbol data")
    
    def print_welcome(self):
        """Print welcome message and overview"""
        print("\n" + "="*70)
        print("🚀 ENHANCED MARKET MAKING BOT - INTERACTIVE SETUP")
        print("="*70)
        print("Welcome! Let's configure your market making trading bot.")
        print("This bot will automatically place buy and sell orders to capture spreads.")
        print("\n📋 We'll ask you about:")
        print("  • Stock symbol to trade")
        print("  • Position sizes and limits")
        print("  • Risk management settings")
        print("  • Trading duration and intervals")
        print("  • Exit strategies")
        print("\n💡 Press Enter for default values, or type 'help' for more info on any question.")
        print("="*70)
    
    def get_user_input(self, prompt: str, default: Any = None, 
                      validation_func: callable = None, help_text: str = None) -> Any:
        """Get user input with validation and help"""
        while True:
            if default is not None:
                display_default = f" (default: {default})"
            else:
                display_default = ""
            
            user_input = input(f"\n{prompt}{display_default}: ").strip()
            
            # Handle help request
            if user_input.lower() == 'help' and help_text:
                print(f"\n💡 Help: {help_text}")
                continue
            
            # Use default if empty
            if not user_input and default is not None:
                return default
            
            # Validate input
            if validation_func:
                try:
                    validated_value = validation_func(user_input)
                    return validated_value
                except ValueError as e:
                    print(f"❌ Invalid input: {e}")
                    continue
            
            return user_input
    
    def validate_symbol(self, symbol: str) -> str:
        """Validate stock symbol"""
        symbol = symbol.upper().strip()
        
        # Basic format validation
        if not re.match(r'^[A-Z]{1,5}$', symbol):
            raise ValueError("Symbol must be 1-5 uppercase letters")
        
        # Try to get quote if client is available
        if self.data_client:
            try:
                quote_request = StockLatestQuoteRequest(symbol_or_symbols=[symbol])
                quotes = self.data_client.get_stock_latest_quote(quote_request)
                if symbol in quotes:
                    quote = quotes[symbol]
                    print(f"✅ Found {symbol}: Bid=${quote.bid_price:.2f}, Ask=${quote.ask_price:.2f}")
                else:
                    print(f"⚠️ Warning: Could not find current quote for {symbol}")
            except Exception as e:
                print(f"⚠️ Warning: Could not validate {symbol}: {e}")
        
        return symbol
    
    def validate_positive_int(self, value: str) -> int:
        """Validate positive integer"""
        try:
            num = int(value)
            if num <= 0:
                raise ValueError("Must be a positive integer")
            return num
        except ValueError:
            raise ValueError("Must be a valid positive integer")
    
    def validate_positive_float(self, value: str) -> float:
        """Validate positive float"""
        try:
            num = float(value)
            if num <= 0:
                raise ValueError("Must be a positive number")
            return num
        except ValueError:
            raise ValueError("Must be a valid positive number")
    
    def validate_percentage(self, value: str) -> float:
        """Validate percentage (0-100) and convert to decimal"""
        try:
            num = float(value)
            if num < 0 or num > 100:
                raise ValueError("Must be between 0 and 100")
            return num / 100  # Convert to decimal
        except ValueError:
            raise ValueError("Must be a valid percentage between 0 and 100")
    
    def validate_boolean(self, value: str) -> bool:
        """Validate boolean input"""
        value = value.lower().strip()
        if value in ['y', 'yes', 'true', '1']:
            return True
        elif value in ['n', 'no', 'false', '0']:
            return False
        else:
            raise ValueError("Please enter y/yes/true or n/no/false")
    
    def get_account_info(self):
        """Get and display account information"""
        if not self.trading_client:
            return
        
        try:
            account = self.trading_client.get_account()
            print(f"\n📊 Account Information:")
            
            # Safely get account values with proper error handling
            portfolio_value = getattr(account, 'portfolio_value', None)
            cash = getattr(account, 'cash', None)
            buying_power = getattr(account, 'buying_power', None)
            daytrade_buying_power = getattr(account, 'daytrade_buying_power', None)
            pattern_day_trader = getattr(account, 'pattern_day_trader', None)
            
            # Store account info for later use
            self.account_info = {
                'portfolio_value': float(portfolio_value) if portfolio_value else None,
                'cash': float(cash) if cash else None,
                'buying_power': float(buying_power) if buying_power else None,
                'daytrade_buying_power': float(daytrade_buying_power) if daytrade_buying_power else None,
                'pattern_day_trader': pattern_day_trader
            }
            
            if portfolio_value is not None:
                print(f"   💰 Portfolio Value: ${float(portfolio_value):,.2f}")
            if cash is not None:
                print(f"   💵 Cash Available: ${float(cash):,.2f}")
            if buying_power is not None:
                print(f"   ⚡ Buying Power: ${float(buying_power):,.2f}")
            if daytrade_buying_power is not None:
                print(f"   🛡️ Day Trade Buying Power: ${float(daytrade_buying_power):,.2f}")
            if pattern_day_trader is not None:
                print(f"   📊 Pattern Day Trader: {pattern_day_trader}")
            
            # Set reasonable defaults based on account size
            if portfolio_value is not None:
                portfolio_value = float(portfolio_value)
                if portfolio_value < 1000:
                    print("⚠️ Small account detected - using conservative defaults")
                    self.config.max_daily_loss = min(50.0, portfolio_value * 0.02)
                    self.config.max_position = 5
                elif portfolio_value < 10000:
                    print("📈 Medium account detected - using moderate defaults")
                    self.config.max_daily_loss = min(200.0, portfolio_value * 0.02)
                    self.config.max_position = 10
                else:
                    print("💎 Large account detected - using standard defaults")
            else:
                print("⚠️ Warning: Could not determine portfolio value for account size logic.")
        except Exception as e:
            logger.error(f"❌ Error getting account info: {e}")
            print("⚠️ Could not retrieve account information")
    
    def configure_basic_settings(self):
        """Configure basic trading settings"""
        print("\n📋 BASIC SETTINGS")
        print("-" * 50)
        
        # Symbol
        self.config.symbol = self.get_user_input(
            "Stock symbol to trade",
            default="AAPL",
            validation_func=self.validate_symbol,
            help_text="Enter a valid stock symbol (1-5 letters, e.g., AAPL, MSFT, GOOGL)"
        )
        
        # Trading duration
        self.config.max_rounds = self.get_user_input(
            "Number of trading rounds",
            default=50,  # Reduced from 100 to 50 for faster testing
            validation_func=self.validate_positive_int,
            help_text="How many trading cycles to run (1-1000)"
        )
        
        # Sleep interval
        self.config.sleep_interval = self.get_user_input(
            "Seconds between rounds",
            default=3.0,  # Increased from 2.0 to 3.0 for more realistic pacing
            validation_func=self.validate_positive_float,
            help_text="Time to wait between trading rounds (0.5-60 seconds)"
        )
        
        # Simulation mode
        simulation_input = self.get_user_input(
            "Use simulation mode? (y/n)",
            default="y",
            validation_func=self.validate_boolean,
            help_text="Simulation mode uses fake market data for testing (y/n)"
        )
        self.config.simulation_mode = simulation_input
    
    def configure_position_settings(self):
        """Configure position and order size settings"""
        print("\n📊 POSITION SETTINGS")
        print("-" * 50)
        
        # Position size
        self.config.position_size = self.get_user_input(
            "Shares per order",
            default=1,  # Keep at 1 for conservative trading
            validation_func=self.validate_positive_int,
            help_text="Number of shares to buy/sell per order (1-100)"
        )
        
        # Max position
        self.config.max_position = self.get_user_input(
            "Maximum position size",
            default=5,  # Reduced from 20 to 5 for better risk management
            validation_func=self.validate_positive_int,
            help_text="Maximum shares to hold (long or short) at any time"
        )
        
        # Max open orders per side
        self.config.max_open_orders_per_side = self.get_user_input(
            "Maximum open orders per side",
            default=2,  # Reduced from 3 to 2 for better control
            validation_func=self.validate_positive_int,
            help_text="Maximum buy OR sell orders to have open at once"
        )
    
    def configure_spread_settings(self):
        """Configure spread and market making settings"""
        print("\n" + "="*50)
        print("💰 SPREAD & MARKET MAKING SETTINGS")
        print("="*50)
        
        # Base spread
        self.config.base_spread = self.get_user_input(
            "📏 Base spread in dollars? (difference between buy and sell price)",
            default=self.config.base_spread,
            validation_func=self.validate_positive_float,
            help_text="The profit margin you want per share. Higher spread = more profit "
                     "per trade but fewer fills. Lower spread = more fills but less profit."
        )
        
        # Min/Max spread in basis points
        print(f"\n💡 Current base spread: ${self.config.base_spread:.2f}")
        print("   You can also set minimum and maximum spreads in basis points (1 bp = 0.01%)")
        
        self.config.min_spread_bps = self.get_user_input(
            "📉 Minimum spread in basis points?",
            default=self.config.min_spread_bps,
            validation_func=self.validate_positive_int,
            help_text="Minimum spread as percentage of stock price. Prevents spreads from "
                     "being too tight. 5 bp = 0.05%. For $100 stock, 5bp = $0.05 minimum spread."
        )
        
        self.config.max_spread_bps = self.get_user_input(
            "📈 Maximum spread in basis points?",
            default=self.config.max_spread_bps,
            validation_func=self.validate_positive_int,
            help_text="Maximum spread as percentage of stock price. Prevents spreads from "
                     "being too wide. 50 bp = 0.50%. For $100 stock, 50bp = $0.50 maximum spread."
        )
        
        # Volatility adjustment
        self.config.volatility_adjustment = self.get_user_input(
            "📊 Adjust spreads based on volatility? (y/n)",
            default="y" if self.config.volatility_adjustment else "n",
            validation_func=self.validate_boolean,
            help_text="Automatically widen spreads when volatility is high and tighten when low. "
                     "This helps capture more profit during volatile periods and stay competitive "
                     "during calm periods."
        )
        
        # Inventory skew factor
        self.config.inventory_skew_factor = self.get_user_input(
            "⚖️ Inventory skew factor? (0.01-0.05 recommended)",
            default=self.config.inventory_skew_factor,
            validation_func=self.validate_positive_float,
            help_text="How much to adjust prices based on current position. Higher values "
                     "mean more aggressive rebalancing. 0.02 = 2% price adjustment per position unit."
        )
    
    def configure_risk_management(self):
        """Configure risk management settings"""
        print("\n" + "="*50)
        print("🛡️ RISK MANAGEMENT SETTINGS")
        print("="*50)
        
        # Max daily loss
        self.config.max_daily_loss = self.get_user_input(
            "💸 Maximum daily loss in dollars?",
            default=self.config.max_daily_loss,
            validation_func=self.validate_positive_float,
            help_text="Bot will stop trading if daily losses exceed this amount. "
                     "This is your safety net to prevent large losses on bad days."
        )
        
        # Max drawdown
        drawdown_pct = self.config.max_drawdown_pct * 100
        drawdown_pct = self.get_user_input(
            "📉 Maximum drawdown percentage? (5-10% recommended)",
            default=drawdown_pct,
            validation_func=self.validate_percentage,
            help_text="Bot will stop if portfolio drops this much from its peak. "
                     "Protects against sustained losses. 5% = stop if portfolio drops 5% from high."
        )
        self.config.max_drawdown_pct = drawdown_pct
        
        # Position limit as % of buying power
        position_limit_pct = self.config.position_limit_pct * 100
        position_limit_pct = self.get_user_input(
            "💼 Maximum position as % of buying power? (50-80% recommended)",
            default=position_limit_pct,
            validation_func=self.validate_percentage,
            help_text="Maximum position value as percentage of your buying power. "
                     "Prevents over-leveraging. 80% = use max 80% of available capital."
        )
        self.config.position_limit_pct = position_limit_pct
    
    def configure_exit_strategies(self):
        """Configure exit strategies"""
        print("\n" + "="*50)
        print("🎯 EXIT STRATEGY SETTINGS")
        print("="*50)
        
        print("💡 The bot can automatically create take-profit and stop-loss orders")
        
        # Take profit
        take_profit_pct = self.config.take_profit_pct * 100
        take_profit_pct = self.get_user_input(
            "🎯 Take profit percentage? (1-3% recommended)",
            default=take_profit_pct,
            validation_func=self.validate_percentage,
            help_text="Automatically sell winners when they reach this profit level. "
                     "1.5% = sell when position is up 1.5%. Higher = more profit but more risk."
        )
        self.config.take_profit_pct = take_profit_pct
        
        # Stop loss
        stop_loss_pct = self.config.stop_loss_pct * 100
        stop_loss_pct = self.get_user_input(
            "🛑 Stop loss percentage? (0.5-1% recommended)",
            default=stop_loss_pct,
            validation_func=self.validate_percentage,
            help_text="Automatically sell losers when they reach this loss level. "
                     "0.8% = sell when position is down 0.8%. Lower = less loss but more stops."
        )
        self.config.stop_loss_pct = stop_loss_pct
        
        # Validate take profit > stop loss
        if self.config.take_profit_pct <= self.config.stop_loss_pct:
            print("❌ Take profit must be greater than stop loss!")
            return self.configure_exit_strategies()
        
        # Trailing stop
        trail_stop_pct = self.config.trail_stop_pct * 100
        trail_stop_pct = self.get_user_input(
            "🔄 Trailing stop percentage? (0.3-0.7% recommended)",
            default=trail_stop_pct,
            validation_func=self.validate_percentage,
            help_text="Trailing stop follows price up but stops you out if price drops. "
                     "0.5% = sell if price drops 0.5% from its peak. Helps lock in profits."
        )
        self.config.trail_stop_pct = trail_stop_pct
    
    def configure_advanced_settings(self):
        """Configure advanced settings"""
        print("\n" + "="*50)
        print("⚙️ ADVANCED SETTINGS")
        print("="*50)
        
        advanced = self.get_user_input(
            "🔧 Configure advanced settings? (y/n)",
            default="n",
            validation_func=self.validate_boolean,
            help_text="Advanced settings for performance tracking window and rebalancing. "
                     "Most users can skip this and use defaults."
        )
        
        if not advanced:
            return
        
        # Performance window
        self.config.performance_window = self.get_user_input(
            "📊 Performance tracking window (number of trades)?",
            default=self.config.performance_window,
            validation_func=self.validate_positive_int,
            help_text="Number of recent trades to use for performance calculations. "
                     "Larger window = more stable metrics but slower to adapt."
        )
        
        # Rebalance threshold
        rebalance_threshold_pct = self.config.rebalance_threshold * 100
        rebalance_threshold_pct = self.get_user_input(
            "⚖️ Rebalancing threshold percentage?",
            default=rebalance_threshold_pct,
            validation_func=self.validate_percentage,
            help_text="Trigger rebalancing when position deviates this much from target. "
                     "2% = rebalance when position is 2% away from optimal allocation."
        )
        self.config.rebalance_threshold = rebalance_threshold_pct
    
    def show_configuration_summary(self):
        """Display final configuration summary"""
        print("\n" + "="*70)
        print("📊 CONFIGURATION SUMMARY")
        print("="*70)
        
        # Basic settings
        print(f"📋 Symbol: {self.config.symbol}")
        print(f"🎮 Mode: {'SIMULATION' if self.config.simulation_mode else 'LIVE'}")
        print(f"⏰ Trading Rounds: {self.config.max_rounds}")
        print(f"⏱️ Interval: {self.config.sleep_interval} seconds")
        
        # Position settings
        print(f"\n📈 Position Settings:")
        print(f"   • Position Size: {self.config.position_size} shares")
        print(f"   • Max Position: {self.config.max_position} shares")
        print(f"   • Max Orders per Side: {self.config.max_open_orders_per_side}")
        
        # Spread settings
        print(f"\n💰 Spread Settings:")
        print(f"   • Base Spread: ${self.config.base_spread:.2f}")
        print(f"   • Min Spread: {self.config.min_spread_bps} bps")
        print(f"   • Max Spread: {self.config.max_spread_bps} bps")
        print(f"   • Inventory Skew: {self.config.inventory_skew_factor:.3f}")
        
        # Risk management
        print(f"\n🛡️ Risk Management:")
        print(f"   • Max Daily Loss: ${self.config.max_daily_loss:.2f}")
        print(f"   • Max Drawdown: {self.config.max_drawdown_pct:.1%}")
        print(f"   • Position Limit: {self.config.position_limit_pct:.1%}")
        
        # Exit strategies
        print(f"\n🎯 Exit Strategies:")
        print(f"   • Take Profit: {self.config.take_profit_pct:.1%}")
        print(f"   • Stop Loss: {self.config.stop_loss_pct:.1%}")
        print(f"   • Trail Stop: {self.config.trail_stop_pct:.1%}")
        
        # Performance tracking
        print(f"\n📊 Performance Tracking:")
        print(f"   • Performance Window: {self.config.performance_window} rounds")
        print(f"   • Rebalance Threshold: {self.config.rebalance_threshold:.1%}")
        
        # Account info if available
        if hasattr(self, 'account_info') and self.account_info:
            print(f"\n💳 Account Information:")
            print(f"   • Buying Power: ${self.account_info.get('buying_power', 'N/A')}")
            print(f"   • Cash: ${self.account_info.get('cash', 'N/A')}")
            print(f"   • Portfolio Value: ${self.account_info.get('portfolio_value', 'N/A')}")
        
        print("="*70)
    
    def save_configuration(self):
        """Save configuration to file"""
        save_config = self.get_user_input(
            "💾 Save this configuration to file? (y/n)",
            default="y",
            validation_func=self.validate_boolean,
            help_text="Save configuration so you can reuse it later without re-entering all settings."
        )
        
        if save_config:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"market_maker_config_{self.config.symbol}_{timestamp}.json"
            
            try:
                config_dict = {
                    'symbol': self.config.symbol,
                    'max_rounds': self.config.max_rounds,
                    'base_spread': self.config.base_spread,
                    'position_size': self.config.position_size,
                    'max_position': self.config.max_position,
                    'sleep_interval': self.config.sleep_interval,
                    'max_daily_loss': self.config.max_daily_loss,
                    'max_drawdown_pct': self.config.max_drawdown_pct,
                    'position_limit_pct': self.config.position_limit_pct,
                    'inventory_skew_factor': self.config.inventory_skew_factor,
                    'min_spread_bps': self.config.min_spread_bps,
                    'max_spread_bps': self.config.max_spread_bps,
                    'volatility_adjustment': self.config.volatility_adjustment,
                    'max_open_orders_per_side': self.config.max_open_orders_per_side,
                    'order_timeout_seconds': self.config.order_timeout_seconds,
                    'take_profit_pct': self.config.take_profit_pct,
                    'stop_loss_pct': self.config.stop_loss_pct,
                    'trail_stop_pct': self.config.trail_stop_pct,
                    'performance_window': self.config.performance_window,
                    'rebalance_threshold': self.config.rebalance_threshold,
                    'created_at': datetime.now().isoformat()
                }
                
                with open(filename, 'w') as f:
                    json.dump(config_dict, f, indent=2)
                
                print(f"✅ Configuration saved to: {filename}")
                
            except Exception as e:
                print(f"❌ Error saving configuration: {e}")
    
    def confirm_start_trading(self) -> bool:
        """Final confirmation before starting trading"""
        print("\n" + "="*50)
        print("🚀 READY TO START TRADING")
        print("="*50)
        print("⚠️ IMPORTANT REMINDERS:")
        print("   • This is a paper trading account (no real money)")
        print("   • Monitor the bot actively, especially during first runs")
        print("   • You can stop the bot anytime with Ctrl+C")
        print("   • All trades and performance will be logged")
        print("   • Review the configuration summary above")
        
        start_trading = self.get_user_input(
            "✅ Start trading with this configuration? (y/n)",
            default="n",
            validation_func=self.validate_boolean,
            help_text="Final confirmation to start the market making bot. "
                     "Make sure you're comfortable with all the settings above."
        )
        
        return start_trading
    
    def build_config(self) -> Optional[TradingConfig]:
        """Main method to build configuration interactively"""
        try:
            self.print_welcome()
            
            # Get account information
            self.get_account_info()
            
            # Configure all settings
            self.configure_basic_settings()
            self.configure_position_settings()
            self.configure_spread_settings()
            self.configure_risk_management()
            self.configure_exit_strategies()
            self.configure_advanced_settings()
            
            # Show summary
            self.show_configuration_summary()
            
            # Save configuration
            self.save_configuration()
            
            # Final confirmation
            if self.confirm_start_trading():
                print("\n🎯 Configuration complete! Starting bot...")
                return self.config
            else:
                print("\n👋 Configuration cancelled. Run again when ready!")
                return None
                
        except KeyboardInterrupt:
            print("\n\n👋 Configuration cancelled by user.")
            return None
        except Exception as e:
            logger.error(f"❌ Error during configuration: {e}")
            print(f"❌ Configuration error: {e}")
            return None

# Market Data Simulator for Real-time Testing
class MarketDataSimulator:
    """Simulates realistic market data for testing"""
    
    def __init__(self, symbol: str = "AAPL", base_price: float = 150.0, volatility: float = 0.015):  # Reduced volatility from 0.02 to 0.015
        self.symbol = symbol
        self.base_price = base_price
        self.current_price = base_price
        self.volatility = volatility
        self.time_step = 0
        self.trend = 0.0
        self.market_status = "open"
        
        # More realistic spread parameters
        self.min_spread = 0.01  # $0.01 minimum spread
        self.max_spread = 0.05  # $0.05 maximum spread
        self.spread_volatility = 0.002  # Spread volatility
        
        # Market hours simulation
        self.market_open = True
        self.volume_factor = 1.0
        
        # Market microstructure parameters
        self.base_volume = 1000
        self.volume_volatility = 0.3
        
        # Market hours simulation (9:30 AM - 4:00 PM EST)
        self.market_open = 9.5  # 9:30 AM
        self.market_close = 16.0  # 4:00 PM
        
    def _generate_price_movement(self):
        """Generate realistic price movement using random walk with trend"""
        # Random walk component
        random_component = random.gauss(0, self.volatility)
        
        # Trend component (slow drift)
        self.trend += random.gauss(0, 0.001)
        self.trend = max(-0.01, min(0.01, self.trend))  # Limit trend
        
        # Noise component
        noise = random.gauss(0, self.spread_volatility)
        
        # Combine all components
        price_change = random_component + self.trend + noise
        
        # Apply price change
        self.current_price *= (1 + price_change)
        
        # Ensure price stays reasonable
        self.current_price = max(1.0, min(1000.0, self.current_price))
        
        return self.current_price
    
    def _generate_spread(self):
        """Generate realistic bid-ask spread"""
        # Base spread as percentage of price
        base_spread_pct = random.uniform(0.0001, 0.002)  # 0.01% to 0.2%
        base_spread = self.current_price * base_spread_pct
        
        # Add volatility to spread
        spread_noise = random.gauss(0, self.spread_volatility)
        spread = base_spread + spread_noise
        
        # Ensure spread is within bounds
        spread = max(self.min_spread, min(self.max_spread, spread))
        
        return spread
    
    def _simulate_market_hours_effect(self):
        """Simulate market hours effects (higher volatility at open/close)"""
        current_hour = (self.time_step % 24) + 9.5  # Start at 9:30 AM
        
        # Higher volatility at market open and close
        if current_hour < 10.5 or current_hour > 15.0:
            return 1.5  # 50% higher volatility
        elif current_hour < 11.0 or current_hour > 14.5:
            return 1.2  # 20% higher volatility
        else:
            return 1.0  # Normal volatility
    
    def get_latest_quote(self):
        """Get simulated bid/ask quote"""
        # Update price
        price = self._generate_price_movement()
        
        # Generate spread
        spread = self._generate_spread()
        
        # Apply market hours effect
        hours_multiplier = self._simulate_market_hours_effect()
        spread *= hours_multiplier
        
        # Calculate bid and ask
        mid_price = price
        bid = mid_price - (spread / 2)
        ask = mid_price + (spread / 2)
        
        # Ensure bid and ask are positive
        bid = max(0.01, bid)
        ask = max(bid + 0.01, ask)
        
        # Update time step
        self.time_step += 1
        
        return round(bid, 2), round(ask, 2)
    
    def get_market_status(self):
        """Get current market status information"""
        current_hour = (self.time_step % 24) + 9.5
        
        if 9.5 <= current_hour <= 16.0:
            status = "OPEN"
        else:
            status = "CLOSED"
            
        return {
            "symbol": self.symbol,
            "current_price": round(self.current_price, 2),
            "market_status": status,
            "time_step": self.time_step,
            "trend": round(self.trend, 4)
        }

@dataclass
class EnhancedMarketMaker:
    def __init__(self, config):
        self.config = config
        self.trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
        self.data_client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
        self.open_orders = {}  # Track all open orders
        self.order_timestamps = {}  # Track when orders were placed
        self.total_pnl = 0.0
        self.trades_count = 0
        
        # Simulation mode tracking
        self.simulated_position = 0  # Track position in simulation mode
        self.simulated_cash = 100000.0  # Starting cash for simulation
        self.simulated_orders = {}  # Track simulated orders
        self.simulated_order_id = 1000  # Start with high ID to avoid conflicts
        
        # Initialize market data simulator if in simulation mode
        if self.config.simulation_mode:
            self.market_simulator = MarketDataSimulator(
                symbol=self.config.symbol,
                base_price=150.0,  # You can adjust this
                volatility=0.015
            )
            print(f"🎮 SIMULATION MODE: Using simulated market data for {self.config.symbol}")
            print(f"💰 Starting with ${self.simulated_cash:,.2f} cash and 0 shares")
        else:
            self.market_simulator = None
            print(f"📡 LIVE MODE: Using real Alpaca market data for {self.config.symbol}")
        
    def get_latest_quote(self):
        """Get latest bid/ask quote - either simulated or live"""
        if self.config.simulation_mode and self.market_simulator:
            # Use simulated market data
            bid, ask = self.market_simulator.get_latest_quote()
            market_status = self.market_simulator.get_market_status()
            
            # Print market status every 10 steps
            if market_status["time_step"] % 10 == 0:
                print(f"🎮 Simulated Market: {market_status['market_status']} | "
                      f"Price: ${market_status['current_price']:.2f} | "
                      f"Trend: {market_status['trend']:+.4f}")
            
            return bid, ask
        else:
            # Use live Alpaca data
            try:
                request = StockLatestQuoteRequest(symbol_or_symbols=[self.config.symbol])
                quotes = self.data_client.get_stock_latest_quote(request)
                quote = quotes[self.config.symbol]
                return float(quote.bid_price), float(quote.ask_price)
            except Exception as e:
                print(f"❌ Error fetching latest quote: {e}")
                return None, None
    
    def get_open_orders(self):
        """Get all open orders for the symbol"""
        if self.config.simulation_mode:
            # Return simulated open orders
            return {order_id: order for order_id, order in self.simulated_orders.items() 
                   if order['status'] == 'open'}
        else:
            # Use real Alpaca orders
            try:
                orders = self.trading_client.get_orders()
                # Filter for our symbol and open status
                open_orders = {}
                for order in orders:
                    order_symbol = getattr(order, 'symbol', '')
                    order_status = getattr(order, 'status', '').lower()
                    order_id = getattr(order, 'id', None)
                    
                    if (order_symbol == self.config.symbol and 
                        order_status == 'open' and 
                        order_id is not None):
                        open_orders[order_id] = order
                return open_orders
            except Exception as e:
                print(f"❌ Error getting open orders: {e}")
                return {}
    
    def cancel_stale_orders(self):
        """Cancel orders that are older than timeout"""
        current_time = datetime.now()
        orders_to_cancel = []
        
        for order_id, timestamp in self.order_timestamps.items():
            if (current_time - timestamp).total_seconds() > self.config.order_timeout_seconds:
                orders_to_cancel.append(order_id)
        
        for order_id in orders_to_cancel:
            if self.config.simulation_mode:
                # Cancel simulated order
                if order_id in self.simulated_orders:
                    self.simulated_orders[order_id]['status'] = 'cancelled'
                    print(f"🛑 Cancelled simulated order {order_id}")
                    if order_id in self.order_timestamps:
                        del self.order_timestamps[order_id]
            else:
                # Cancel real Alpaca order
                try:
                    self.trading_client.cancel_order_by_id(order_id)
                    print(f"🛑 Cancelled stale order {order_id}")
                    if order_id in self.open_orders:
                        del self.open_orders[order_id]
                    if order_id in self.order_timestamps:
                        del self.order_timestamps[order_id]
                except Exception as e:
                    print(f"❌ Error cancelling stale order {order_id}: {e}")
    
    def place_limit_order(self, side, price, qty):
        """Place a limit order and track it"""
        if self.config.simulation_mode:
            # Simulate order placement
            order_id = self.simulated_order_id
            self.simulated_order_id += 1
            
            # Create simulated order
            order = {
                'id': order_id,
                'symbol': self.config.symbol,
                'side': side,
                'price': price,
                'qty': qty,
                'status': 'open',
                'order_type': 'limit'
            }
            
            self.simulated_orders[order_id] = order
            self.order_timestamps[order_id] = datetime.now()
            
            print(f"✅ Placed simulated {side} limit order for {qty} at ${price:.2f} (id={order_id})")
            
            # Simulate immediate fill for marketable orders
            current_bid, current_ask = self.get_latest_quote()
            if current_bid and current_ask:
                if side == "buy" and price >= current_ask:  # Marketable buy order
                    self._simulate_order_fill(order_id, current_ask, qty, side)
                elif side == "sell" and price <= current_bid:  # Marketable sell order
                    self._simulate_order_fill(order_id, current_bid, qty, side)
                else:
                    # For non-marketable orders, simulate some fills based on probability
                    if random.random() < 0.15:  # Reduced from 30% to 15% chance of fill for non-marketable orders
                        if side == "buy":
                            fill_price = min(price, current_ask)
                            self._simulate_order_fill(order_id, fill_price, qty, side)
                        else:  # sell
                            fill_price = max(price, current_bid)
                            self._simulate_order_fill(order_id, fill_price, qty, side)
            
            return order_id
        else:
            # Place real Alpaca order
            try:
                order_data = MarketOrderRequest(
                    symbol=self.config.symbol,
                    qty=qty,
                    side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
                    limit_price=round(price, 2),
                    time_in_force=TimeInForce.DAY
                )
                order = self.trading_client.submit_order(order_data)
                order_id = getattr(order, 'id', None)
                
                if order_id:
                    self.open_orders[order_id] = order
                    self.order_timestamps[order_id] = datetime.now()
                    print(f"✅ Placed {side} limit order for {qty} at ${price:.2f} (id={order_id})")
                    return order_id
                else:
                    print(f"✅ Placed {side} limit order for {qty} at ${price:.2f} (order: {order})")
                    return None
            except Exception as e:
                print(f"❌ Error placing {side} limit order: {e}")
                return None
    
    def _simulate_order_fill(self, order_id, fill_price, qty, side):
        """Simulate order fill and update position/cash"""
        if order_id not in self.simulated_orders:
            return
        
        order = self.simulated_orders[order_id]
        order['status'] = 'filled'
        order['filled_price'] = fill_price
        order['filled_qty'] = qty
        
        # Update position and cash
        if side == "buy":
            self.simulated_position += qty
            self.simulated_cash -= fill_price * qty
            print(f"💰 Simulated BUY fill: {qty} shares @ ${fill_price:.2f}")
        else:  # sell
            self.simulated_position -= qty
            self.simulated_cash += fill_price * qty
            print(f"💰 Simulated SELL fill: {qty} shares @ ${fill_price:.2f}")
        
        # Calculate P&L
        current_price = self.market_simulator.current_price if self.market_simulator else fill_price
        unrealized_pnl = self.simulated_position * current_price
        self.total_pnl = (self.simulated_cash + unrealized_pnl) - 100000.0
        
        print(f"📊 Position: {self.simulated_position} shares | Cash: ${self.simulated_cash:.2f} | P&L: ${self.total_pnl:.2f}")
    
    def get_position(self):
        """Get current position details"""
        if self.config.simulation_mode:
            # Return simulated position
            current_price = self.market_simulator.current_price if self.market_simulator else 150.0
            unrealized_pnl = self.simulated_position * current_price
            total_value = self.simulated_cash + unrealized_pnl
            avg_entry = 150.0  # Simplified for simulation
            
            return self.simulated_position, avg_entry, current_price, unrealized_pnl
        else:
            # Get real Alpaca position
            try:
                pos = self.trading_client.get_open_position(self.config.symbol)
                qty = float(getattr(pos, 'qty', 0) or 0)
                avg_entry = float(getattr(pos, 'avg_entry_price', 0) or 0)
                market_price = float(getattr(pos, 'current_price', 0) or 0)
                unrealized = float(getattr(pos, 'unrealized_pl', 0) or 0)
                return qty, avg_entry, market_price, unrealized
            except Exception:
                return 0, 0, 0, 0
    
    def calculate_optimal_prices(self, bid, ask):
        """Calculate optimal buy/sell prices for market making"""
        spread = ask - bid
        mid_price = (bid + ask) / 2
        
        # Use dynamic spread calculation based on market spread (like in strategy.py)
        spread_multiplier = 0.3  # 30% of market spread
        half_spread = (spread * spread_multiplier) / 2
        
        # Ensure minimum spread for profitability
        min_spread = 0.01  # $0.01 minimum
        if half_spread < min_spread / 2:
            half_spread = min_spread / 2
        
        # Calculate buy and sell prices
        buy_price = mid_price - half_spread
        sell_price = mid_price + half_spread
        
        # Ensure we have some profit margin
        if sell_price <= buy_price:
            # If no profit margin, use a small spread around mid
            buy_price = mid_price - 0.01
            sell_price = mid_price + 0.01
        
        return round(buy_price, 2), round(sell_price, 2)
    
    def should_place_buy_order(self, current_qty):
        """Determine if we should place a buy order"""
        # Don't place buy if we're at max position
        if current_qty >= self.config.max_position:
            print(f"🔍 Debug: Max position reached ({current_qty}/{self.config.max_position})")
            return False
        
        # Count existing buy orders
        if self.config.simulation_mode:
            buy_orders = sum(1 for order in self.simulated_orders.values() 
                           if order['status'] == 'open' and order['side'] == 'buy')
        else:
            buy_orders = sum(1 for order in self.open_orders.values() 
                           if getattr(order, 'side', None) == OrderSide.BUY)
        
        # Don't place more buy orders than limit
        if buy_orders >= self.config.max_open_orders_per_side:
            print(f"🔍 Debug: Max buy orders reached ({buy_orders}/{self.config.max_open_orders_per_side})")
            return False
        
        print(f"🔍 Debug: Can place buy order (qty={current_qty}, buy_orders={buy_orders})")
        return True
    
    def should_place_sell_order(self, current_qty):
        """Determine if we should place a sell order"""
        # Don't place sell if we have no shares
        if current_qty <= 0:
            print(f"🔍 Debug: No shares to sell (qty={current_qty})")
            return False
        
        # More conservative sell order placement for negative inventory
        if current_qty < 0 and random.random() > 0.3:  # 30% chance to sell when short
            print(f"🔍 Debug: Skipping sell order due to negative inventory (qty={current_qty})")
            return False
        
        # Count existing sell orders
        if self.config.simulation_mode:
            sell_orders = sum(1 for order in self.simulated_orders.values() 
                            if order['status'] == 'open' and order['side'] == 'sell')
        else:
            sell_orders = sum(1 for order in self.open_orders.values() 
                            if getattr(order, 'side', None) == OrderSide.SELL)
        
        # Don't place more sell orders than limit
        if sell_orders >= self.config.max_open_orders_per_side:
            print(f"🔍 Debug: Max sell orders reached ({sell_orders}/{self.config.max_open_orders_per_side})")
            return False
        
        print(f"🔍 Debug: Can place sell order (qty={current_qty}, sell_orders={sell_orders})")
        return True
    
    def run(self):
        """Main market making loop"""
        print(f"✅ Running market making bot for {self.config.symbol}")
        print(f"📊 Strategy: Place competitive orders near bid/ask with {self.config.base_spread} spread")
        
        for i in range(self.config.max_rounds):
            print(f"\n🔁 Round {i+1}/{self.config.max_rounds}")
            
            # Get latest market data
            bid, ask = self.get_latest_quote()
            if bid is None or ask is None:
                print("⚠️ Skipping round due to missing quote.")
                continue
            
            print(f"📈 Market: Bid=${bid:.2f}, Ask=${ask:.2f}, Spread=${ask-bid:.2f}")
            
            # Cancel stale orders
            self.cancel_stale_orders()
            
            # Update our open orders from Alpaca
            self.open_orders = self.get_open_orders()
            
            # Get current position
            qty, avg_entry, market_price, unrealized = self.get_position()
            
            # Calculate optimal prices
            buy_price, sell_price = self.calculate_optimal_prices(bid, ask)
            print(f"💰 Our prices: Buy=${buy_price:.2f}, Sell=${sell_price:.2f}, Spread=${sell_price-buy_price:.2f}")
            
            # Place buy order if conditions are met
            if self.should_place_buy_order(qty):
                buy_qty = min(self.config.position_size, self.config.max_position - qty)
                self.place_limit_order("buy", buy_price, buy_qty)
            else:
                if qty >= self.config.max_position:
                    print(f"🚫 Max position ({self.config.max_position}) reached")
                else:
                    print(f"🚫 Max buy orders ({self.config.max_open_orders_per_side}) reached")
            
            # Place sell order if conditions are met
            if self.should_place_sell_order(qty):
                sell_qty = min(self.config.position_size, qty)
                self.place_limit_order("sell", sell_price, sell_qty)
            else:
                if qty <= 0:
                    print(f"🚫 No shares to sell")
                else:
                    print(f"🚫 Max sell orders ({self.config.max_open_orders_per_side}) reached")
            
            # Print position and P&L
            print(f"📊 Position: {qty} shares @ avg ${avg_entry:.2f} | Market: ${market_price:.2f} | Unrealized P&L: ${unrealized:.2f}")
            print(f"📋 Open orders: {len(self.open_orders)}")
            
            # Sleep between rounds
            import time
            time.sleep(self.config.sleep_interval)
        
        print(f"\n🎯 Trading session complete!")
        print(f"📊 Final position: {qty} shares")
        print(f"💰 Final unrealized P&L: ${unrealized:.2f}")

# Main entry point
if __name__ == "__main__":
    builder = InteractiveConfigBuilder()
    config = builder.build_config()
    if config:
        bot = EnhancedMarketMaker(config)
        bot.run()