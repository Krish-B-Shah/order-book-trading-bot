"""
Execution simulation utilities for backtesting
"""

import random
from typing import List, Dict, Any
from core.order_book import OrderBook, Order


def create_random_market_order(order_book: OrderBook, market_data: dict):
    """
    Create a random market order for simulation

    Args:
        order_book: The order book instance
        market_data: Current market data with bid/ask prices

    Returns:
        Order object or None if no order created
    """
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


def simulate_market_activity(order_book: OrderBook, market_data: dict, num_orders: int = 1):
    """
    Simulate market activity by creating multiple random orders

    Args:
        order_book: The order book instance
        market_data: Current market data
        num_orders: Number of orders to potentially create
    """
    for _ in range(num_orders):
        market_order = create_random_market_order(order_book, market_data)
        if market_order:
            order_book.add_order(market_order)


def apply_realistic_matching(order_book: OrderBook, current_price: float):
    """
    Apply realistic matching with partial fills and missed matches

    Args:
        order_book: The order book instance
        current_price: Current market price
    """
    # Apply the patched matching logic with realism
    order_book.match(current_price)


def simulate_trading_round(order_book: OrderBook, market_data: dict, strategy_orders: List[Order]):
    """
    Simulate a complete trading round

    Args:
        order_book: The order book instance
        market_data: Current market data
        strategy_orders: Orders from the trading strategy

    Returns:
        Number of matches made
    """
    # Add strategy orders
    for order in strategy_orders:
        order_book.add_order(order)

    # Simulate market activity
    num_market_orders = random.randint(1, 3)
    simulate_market_activity(order_book, market_data, num_market_orders)

    # Execute matching
    matches_made = len(order_book.trade_log)  # Count before matching
    apply_realistic_matching(order_book, market_data['price'])
    matches_made = len(order_book.trade_log) - matches_made  # Count after matching

    return matches_made
