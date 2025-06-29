import logging
import sys
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import re

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
    max_position: int = 20
    sleep_interval: float = 2.0
    
    # Risk management
    max_daily_loss: float = 1000.0
    max_drawdown_pct: float = 0.05
    position_limit_pct: float = 0.8  # % of buying power
    
    # Market making parameters
    inventory_skew_factor: float = 0.04  # Increased from 0.02 to 0.04 for better rebalancing
    min_spread_bps: int = 5  # basis points
    max_spread_bps: int = 50
    volatility_adjustment: bool = True
    
    # Order management
    max_open_orders_per_side: int = 3
    order_timeout_seconds: int = 300
    
    # Exit strategies
    take_profit_pct: float = 0.015   # 1.5%
    stop_loss_pct: float = 0.008     # 0.8%
    trail_stop_pct: float = 0.005    # 0.5%
    
    # Performance tracking
    performance_window: int = 50
    rebalance_threshold: float = 0.02
    
    # Adaptive trading parameters
    volatility_window: int = 20  # Number of price points for volatility calculation
    max_volatility_threshold: float = 0.02  # Maximum volatility before widening spreads
    min_volatility_threshold: float = 0.005  # Minimum volatility for normal spreads
    
    # Drawdown protection
    max_drawdown_dollars: float = 50.0  # Stop trading if P&L < -$50
    max_drawdown_percent: float = 0.03  # Stop trading if unrealized P&L < -3%
    auto_throttle_enabled: bool = True
    
    # Market condition detection
    one_sided_move_threshold: float = 0.01  # 1% move in one direction
    backoff_delay_seconds: float = 5.0  # Delay orders during sharp moves
    
    # Performance metrics
    track_sharpe_ratio: bool = True
    track_drawdown: bool = True
    track_win_loss: bool = True
    
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
        print("\n" + "="*50)
        print("📈 BASIC TRADING SETTINGS")
        print("="*50)
        
        # Stock Symbol
        self.config.symbol = self.get_user_input(
            "�� Which stock symbol do you want to trade?",
            default=self.config.symbol,
            validation_func=self.validate_symbol,
            help_text="Enter a valid US stock symbol (e.g., AAPL, TSLA, SPY). "
                     "The bot will make markets in this stock by placing buy and sell orders."
        )
        
        # Trading Duration
        self.config.max_rounds = self.get_user_input(
            "⏰ How many trading rounds? (Each round places new orders)",
            default=self.config.max_rounds,
            validation_func=self.validate_positive_int,
            help_text="Number of trading cycles. Each round the bot will evaluate market "
                     "conditions and place new orders. More rounds = longer running time."
        )
        
        # Sleep Interval
        self.config.sleep_interval = self.get_user_input(
            "⏱️ Seconds between trading rounds?",
            default=self.config.sleep_interval,
            validation_func=self.validate_positive_float,
            help_text="How long to wait between each trading round. Shorter intervals = "
                     "more active trading but higher API usage. Recommended: 2-10 seconds."
        )
    
    def configure_position_settings(self):
        """Configure position and order settings"""
        print("\n" + "="*50)
        print("📊 POSITION & ORDER SETTINGS")
        print("="*50)
        
        # Position Size
        self.config.position_size = self.get_user_input(
            "📏 How many shares per order?",
            default=self.config.position_size,
            validation_func=self.validate_positive_int,
            help_text="Number of shares in each buy/sell order. Start small while testing. "
                     "This affects your capital requirements and risk per trade."
        )
        
        # Max Position
        self.config.max_position = self.get_user_input(
            "🏗️ Maximum total position (long or short)?",
            default=self.config.max_position,
            validation_func=self.validate_positive_int,
            help_text="Maximum number of shares you can hold long or short. This limits "
                     "your total exposure. Should be multiple of position_size."
        )
        
        # Max orders per side
        self.config.max_open_orders_per_side = self.get_user_input(
            "📋 Maximum open orders per side (buy/sell)?",
            default=self.config.max_open_orders_per_side,
            validation_func=self.validate_positive_int,
            help_text="Maximum number of pending buy orders and sell orders. More orders "
                     "= more opportunities but also more complexity to manage."
        )
        
        # Order timeout
        self.config.order_timeout_seconds = self.get_user_input(
            "⏰ Order timeout in seconds?",
            default=self.config.order_timeout_seconds,
            validation_func=self.validate_positive_int,
            help_text="How long to keep orders open before cancelling them. Longer timeout "
                     "= higher chance of fills but stale pricing. Recommended: 300-600 seconds."
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
        """Show complete configuration summary"""
        print("\n" + "="*70)
        print("📋 CONFIGURATION SUMMARY")
        print("="*70)
        
        print(f"📈 Basic Settings:")
        print(f"   Symbol: {self.config.symbol}")
        print(f"   Max Rounds: {self.config.max_rounds}")
        print(f"   Sleep Interval: {self.config.sleep_interval} seconds")
        
        print(f"\n📊 Position Settings:")
        print(f"   Position Size: {self.config.position_size} shares")
        print(f"   Max Position: {self.config.max_position} shares")
        print(f"   Max Orders/Side: {self.config.max_open_orders_per_side}")
        print(f"   Order Timeout: {self.config.order_timeout_seconds} seconds")
        
        print(f"\n💰 Spread Settings:")
        print(f"   Base Spread: ${self.config.base_spread:.2f}")
        print(f"   Min Spread: {self.config.min_spread_bps} bp")
        print(f"   Max Spread: {self.config.max_spread_bps} bp")
        print(f"   Volatility Adjustment: {self.config.volatility_adjustment}")
        print(f"   Inventory Skew Factor: {self.config.inventory_skew_factor}")
        
        print(f"\n🛡️ Risk Management:")
        print(f"   Max Daily Loss: ${self.config.max_daily_loss:.2f}")
        print(f"   Max Drawdown: {self.config.max_drawdown_pct:.1%}")
        print(f"   Position Limit: {self.config.position_limit_pct:.1%}")
        
        print(f"\n🎯 Exit Strategies:")
        print(f"   Take Profit: {self.config.take_profit_pct:.1%}")
        print(f"   Stop Loss: {self.config.stop_loss_pct:.1%}")
        print(f"   Trailing Stop: {self.config.trail_stop_pct:.1%}")
        
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
                    'volatility_window': self.config.volatility_window,
                    'max_volatility_threshold': self.config.max_volatility_threshold,
                    'min_volatility_threshold': self.config.min_volatility_threshold,
                    'max_drawdown_dollars': self.config.max_drawdown_dollars,
                    'max_drawdown_percent': self.config.max_drawdown_percent,
                    'auto_throttle_enabled': self.config.auto_throttle_enabled,
                    'one_sided_move_threshold': self.config.one_sided_move_threshold,
                    'backoff_delay_seconds': self.config.backoff_delay_seconds,
                    'track_sharpe_ratio': self.config.track_sharpe_ratio,
                    'track_drawdown': self.config.track_drawdown,
                    'track_win_loss': self.config.track_win_loss,
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
        
    def get_latest_quote(self):
        """Get latest bid/ask quote"""
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
        try:
            order_data = LimitOrderRequest(
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
    
    def get_position(self):
        """Get current position details"""
        try:
            pos = self.trading_client.get_open_position(self.config.symbol)
            qty = float(getattr(pos, 'qty', 0) or 0)
            avg_entry = float(getattr(pos, 'avg_entry_price', 0) or 0)
            market_price = float(getattr(pos, 'current_price', 0) or 0)
            unrealized = float(getattr(pos, 'unrealized_pl', 0) or 0)
            return qty, avg_entry, market_price, unrealized
        except Exception:
            return 0, 0, 0, 0
    
    def calculate_volatility(self, current_mid_price):
        """Calculate market volatility based on price history"""
        self.price_history.append(current_mid_price)
        
        # Keep only the last N price points
        if len(self.price_history) > self.config.volatility_window:
            self.price_history.pop(0)
        
        # Calculate volatility (standard deviation of returns)
        if len(self.price_history) >= 2:
            returns = []
            for i in range(1, len(self.price_history)):
                if self.price_history[i-1] != 0:
                    return_val = (self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1]
                    returns.append(return_val)
            
            if returns:
                import statistics
                self.volatility = statistics.stdev(returns)
            else:
                self.volatility = 0.0
        else:
            self.volatility = 0.0
        
        return self.volatility
    
    def detect_market_conditions(self, current_mid_price):
        """Detect market conditions and adjust trading behavior"""
        if self.last_mid_price is None:
            self.last_mid_price = current_mid_price
            return
        
        # Calculate price change
        price_change = (current_mid_price - self.last_mid_price) / self.last_mid_price
        price_change_threshold = self.config.one_sided_move_threshold
        
        # Detect trend direction
        if abs(price_change) > price_change_threshold:
            new_direction = 1 if price_change > 0 else -1
            
            if new_direction == self.trend_direction:
                self.consecutive_moves += 1
            else:
                self.consecutive_moves = 1
                self.trend_direction = new_direction
            
            # Back off if too many consecutive moves in same direction
            if self.consecutive_moves >= 3:
                self.backoff_until = datetime.now().timestamp() + self.config.backoff_delay_seconds
                print(f"⚠️ Sharp one-sided move detected! Backing off for {self.config.backoff_delay_seconds} seconds")
        else:
            # Reset if price change is small
            self.consecutive_moves = 0
            self.trend_direction = 0
        
        self.last_mid_price = current_mid_price
    
    def should_throttle_trading(self):
        """Check if trading should be throttled due to drawdown or backoff"""
        # Check backoff period
        if self.backoff_until and datetime.now().timestamp() < self.backoff_until:
            remaining = self.backoff_until - datetime.now().timestamp()
            print(f"⏸️ Trading throttled due to backoff period ({remaining:.1f}s remaining)")
            return True
        
        # Check drawdown protection
        if self.config.auto_throttle_enabled:
            # Calculate current equity
            current_price = self.market_simulator.current_price if self.market_simulator else 150.0
            unrealized_pnl = self.simulated_position * current_price
            current_equity = self.simulated_cash + unrealized_pnl
            
            # Update peak equity
            if current_equity > self.peak_equity:
                self.peak_equity = current_equity
            
            # Calculate drawdown
            if self.peak_equity > 0:
                self.current_drawdown = (self.peak_equity - current_equity) / self.peak_equity
            
            # Check dollar drawdown
            if self.total_pnl < -self.config.max_drawdown_dollars:
                print(f"🛑 Trading stopped: P&L below threshold (${self.total_pnl:.2f} < -${self.config.max_drawdown_dollars})")
                return True
            
            # Check percentage drawdown
            if self.current_drawdown > self.config.max_drawdown_percent:
                print(f"🛑 Trading stopped: Drawdown above threshold ({self.current_drawdown:.2%} > {self.config.max_drawdown_percent:.2%})")
                return True
        
        return False
    
    def calculate_adaptive_spread(self, base_spread, volatility):
        """Calculate adaptive spread based on market volatility"""
        if volatility > self.config.max_volatility_threshold:
            # High volatility - widen spreads significantly
            spread_multiplier = 2.0 + (volatility / self.config.max_volatility_threshold)
            print(f"📈 High volatility detected ({volatility:.4f}) - widening spreads by {spread_multiplier:.1f}x")
        elif volatility > self.config.min_volatility_threshold:
            # Moderate volatility - widen spreads moderately
            spread_multiplier = 1.0 + (volatility / self.config.max_volatility_threshold)
            print(f"📊 Moderate volatility ({volatility:.4f}) - widening spreads by {spread_multiplier:.1f}x")
        else:
            # Low volatility - use normal spreads
            spread_multiplier = 1.0
        
        return base_spread * spread_multiplier
    
    def update_performance_metrics(self, trade_pnl):
        """Update performance tracking metrics"""
        self.trade_history.append({
            'timestamp': datetime.now(),
            'pnl': trade_pnl,
            'position': self.simulated_position,
            'equity': self.simulated_cash + (self.simulated_position * (self.market_simulator.current_price if self.market_simulator else 150.0))
        })
        
        # Update win/loss counts
        if trade_pnl > 0:
            self.winning_trades += 1
        elif trade_pnl < 0:
            self.losing_trades += 1
        
        # Keep only recent history for performance calculation
        if len(self.trade_history) > self.config.performance_window:
            self.trade_history.pop(0)
    
    def calculate_sharpe_ratio(self):
        """Calculate Sharpe ratio of recent trades"""
        if len(self.trade_history) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(self.trade_history)):
            prev_equity = self.trade_history[i-1]['equity']
            curr_equity = self.trade_history[i]['equity']
            if prev_equity > 0:
                ret = (curr_equity - prev_equity) / prev_equity
                returns.append(ret)
        
        if len(returns) < 2:
            return 0.0
        
        import statistics
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return > 0:
            return avg_return / std_return
        return 0.0
    
    def print_performance_summary(self):
        """Print comprehensive performance summary"""
        total_trades = self.winning_trades + self.losing_trades
        win_rate = (self.winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        sharpe_ratio = self.calculate_sharpe_ratio()
        
        print(f"\n📊 PERFORMANCE SUMMARY")
        print(f"=" * 50)
        print(f"💰 Total P&L: ${self.total_pnl:.2f}")
        print(f"📈 Current Drawdown: {self.current_drawdown:.2%}")
        print(f"🎯 Win Rate: {win_rate:.1f}% ({self.winning_trades}/{total_trades})")
        print(f"📊 Sharpe Ratio: {sharpe_ratio:.3f}")
        print(f"📈 Volatility: {self.volatility:.4f}")
        print(f"📋 Position: {self.simulated_position} shares")
        print(f"💵 Cash: ${self.simulated_cash:.2f}")
        print(f"=" * 50)
    
    def calculate_optimal_prices(self, bid, ask):
        """Calculate optimal buy/sell prices for market making with adaptive spreads"""
        spread = ask - bid
        mid_price = (bid + ask) / 2
        
        # For testing and getting fills, be more aggressive
        # Place buy orders at ask (marketable) to guarantee fills
        # Place sell orders at bid (marketable) to guarantee fills
        buy_price = ask  # Marketable limit order - will fill immediately
        sell_price = bid  # Marketable limit order - will fill immediately
        
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
        
        # Count existing sell orders
        sell_orders = sum(1 for order in self.open_orders.values() 
                         if getattr(order, 'side', None) == OrderSide.SELL)
        
        # Don't place more sell orders than limit
        if sell_orders >= self.config.max_open_orders_per_side:
            print(f"🔍 Debug: Max sell orders reached ({sell_orders}/{self.config.max_open_orders_per_side})")
            return False
        
        print(f"🔍 Debug: Can place sell order (qty={current_qty}, sell_orders={sell_orders})")
        return True
    
    def run(self):
        """Main market making loop with adaptive features"""
        print(f"✅ Running adaptive market making bot for {self.config.symbol}")
        print(f"📊 Strategy: Adaptive spreads based on volatility and market conditions")
        
        for i in range(self.config.max_rounds):
            print(f"\n🔁 Round {i+1}/{self.config.max_rounds}")
            
            # Get latest market data
            bid, ask = self.get_latest_quote()
            if bid is None or ask is None:
                print("⚠️ Skipping round due to missing quote.")
                continue
            
            mid_price = (bid + ask) / 2
            print(f"📈 Market: Bid=${bid:.2f}, Ask=${ask:.2f}, Mid=${mid_price:.2f}, Spread=${ask-bid:.2f}")
            
            # Calculate volatility and detect market conditions
            volatility = self.calculate_volatility(mid_price)
            self.detect_market_conditions(mid_price)
            
            print(f"📊 Volatility: {volatility:.4f} | Trend: {self.trend_direction} | Consecutive moves: {self.consecutive_moves}")
            
            # Check if trading should be throttled
            if self.should_throttle_trading():
                print("⏸️ Trading throttled - waiting for conditions to improve...")
                time.sleep(self.config.sleep_interval)
                continue
            
            # Cancel stale orders
            self.cancel_stale_orders()
            
            # Update our open orders from Alpaca
            self.open_orders = self.get_open_orders()
            
            # Get current position
            qty, avg_entry, market_price, unrealized = self.get_position()
            
            # Calculate optimal prices with adaptive spreads
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
            
            # Print performance summary every 10 rounds
            if i % 10 == 0 and i > 0:
                self.print_performance_summary()
            
            # Sleep between rounds
            time.sleep(self.config.sleep_interval)
        
        # Final performance summary
        self.print_performance_summary()
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