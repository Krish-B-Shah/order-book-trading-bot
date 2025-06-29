#!/usr/bin/env python3
"""
Simple test script to demonstrate the market data simulation
"""

import time
from live_trading import MarketDataSimulator, TradingConfig, EnhancedMarketMaker

def test_simulation():
    print("🎮 Testing Market Data Simulation")
    print("=" * 50)
    
    # Create a simple configuration
    config = TradingConfig(
        symbol="AAPL",
        max_rounds=10,
        simulation_mode=True,
        position_size=1,
        max_position=5,
        sleep_interval=1.0
    )
    
    # Create the market maker
    bot = EnhancedMarketMaker(config)
    
    print(f"🎮 Starting simulation for {config.symbol}")
    print(f"💰 Starting cash: ${bot.simulated_cash:,.2f}")
    print(f"📊 Starting position: {bot.simulated_position} shares")
    print("=" * 50)
    
    # Run a few rounds
    for i in range(config.max_rounds):
        print(f"\n🔁 Round {i+1}/{config.max_rounds}")
        
        # Get latest market data
        bid, ask = bot.get_latest_quote()
        if bid is None or ask is None:
            print("⚠️ Skipping round due to missing quote.")
            continue
        
        print(f"📈 Market: Bid=${bid:.2f}, Ask=${ask:.2f}, Spread=${ask-bid:.2f}")
        
        # Get current position
        qty, avg_entry, market_price, unrealized = bot.get_position()
        
        # Calculate optimal prices (more aggressive for testing)
        buy_price = ask  # Buy at ask (marketable)
        sell_price = bid  # Sell at bid (marketable)
        
        print(f"💰 Our prices: Buy=${buy_price:.2f}, Sell=${sell_price:.2f}")
        
        # Place buy order if we can
        if bot.should_place_buy_order(qty):
            buy_qty = min(config.position_size, config.max_position - qty)
            bot.place_limit_order("buy", buy_price, buy_qty)
        else:
            print("🚫 Cannot place buy order")
        
        # Place sell order if we can
        if bot.should_place_sell_order(qty):
            sell_qty = min(config.position_size, qty)
            bot.place_limit_order("sell", sell_price, sell_qty)
        else:
            print("🚫 Cannot place sell order")
        
        # Print current status
        print(f"📊 Position: {qty} shares | Cash: ${bot.simulated_cash:.2f} | P&L: ${bot.total_pnl:.2f}")
        print(f"📋 Open orders: {len(bot.get_open_orders())}")
        
        # Sleep between rounds
        time.sleep(config.sleep_interval)
    
    print("\n" + "=" * 50)
    print("🎯 Simulation Complete!")
    print(f"📊 Final position: {bot.simulated_position} shares")
    print(f"💰 Final cash: ${bot.simulated_cash:.2f}")
    print(f"📈 Final P&L: ${bot.total_pnl:.2f}")
    print(f"🔄 Total trades: {bot.trades_count}")
    
    # Show order history
    print("\n📋 Order History:")
    for order_id, order in bot.simulated_orders.items():
        status = order['status']
        side = order['side']
        price = order['price']
        qty = order['qty']
        print(f"  Order {order_id}: {side.upper()} {qty} @ ${price:.2f} - {status}")

if __name__ == "__main__":
    test_simulation() 