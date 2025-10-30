"""
Utility functions for the order book trading bot
"""

import random
import time
from typing import List, Dict, Any


def generate_order_id():
    """Generate a unique order ID"""
    return int(time.time() * 1000000) + random.randint(0, 999999)


def validate_order(order_data: Dict[str, Any]) -> bool:
    """Validate order data"""
    required_fields = ['side', 'price', 'quantity', 'order_type']
    for field in required_fields:
        if field not in order_data:
            return False

    if order_data['side'] not in ['buy', 'sell']:
        return False

    if order_data['order_type'] not in ['limit', 'market']:
        return False

    if order_data['quantity'] <= 0:
        return False

    if order_data['order_type'] == 'limit' and order_data['price'] <= 0:
        return False

    return True


def format_price(price: float) -> str:
    """Format price for display"""
    return f"${price:.2f}"


def format_timestamp(timestamp: float) -> str:
    """Format timestamp for display"""
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))


def calculate_mid_price(bid: float, ask: float) -> float:
    """Calculate mid price from bid and ask"""
    return (bid + ask) / 2


def calculate_spread(bid: float, ask: float) -> float:
    """Calculate spread from bid and ask"""
    return ask - bid


def calculate_spread_percentage(bid: float, ask: float) -> float:
    """Calculate spread as percentage of mid price"""
    mid = calculate_mid_price(bid, ask)
    if mid == 0:
        return 0.0
    return calculate_spread(bid, ask) / mid * 100
