"""
utils/helpers.py - Helper Utilities
Common utility functions for the trading bot.
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
from typing import Dict, List


def pips_to_price(symbol: str, pips: float) -> float:
    """
    Convert pips to price value.
    
    Args:
        symbol: Trading symbol
        pips: Number of pips
        
    Returns:
        Price value
    """
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return pips * 0.0001
    
    point = symbol_info.point
    
    # Handle 3 and 5 digit brokers
    if symbol_info.digits == 3 or symbol_info.digits == 5:
        return pips * point * 10
    else:
        return pips * point


def price_to_pips(symbol: str, price_diff: float) -> float:
    """
    Convert price difference to pips.
    
    Args:
        symbol: Trading symbol
        price_diff: Price difference
        
    Returns:
        Number of pips
    """
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return price_diff / 0.0001
    
    point = symbol_info.point
    
    if symbol_info.digits == 3 or symbol_info.digits == 5:
        pip_value = point * 10
    else:
        pip_value = point
    
    return price_diff / pip_value


def format_currency(value: float) -> str:
    """Format currency value."""
    return f"${value:,.2f}"


def format_percentage(value: float) -> str:
    """Format percentage value."""
    return f"{value:.2f}%"


def calculate_risk_reward(entry: float, sl: float, tp: float, direction: str) -> float:
    """Calculate risk:reward ratio."""
    if direction == 'BUY':
        risk = entry - sl
        reward = tp - entry
    else:
        risk = sl - entry
        reward = entry - tp
    
    if risk <= 0:
        return 0.0
    
    return reward / risk


def is_market_hours(symbol: str = 'EURUSD') -> bool:
    """
    Check if current time is within major market hours.
    
    Args:
        symbol: Trading symbol
        
    Returns:
        True if within major trading hours
    """
    now = datetime.now()
    hour = now.hour
    day = now.weekday()
    
    # Weekend
    if day >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Major forex sessions (approximate)
    # Asian: 00:00-09:00
    # London: 08:00-17:00
    # New York: 13:00-22:00
    
    # Trading allowed from Sunday 22:00 to Friday 22:00
    return True  # Simplified - implement full session logic if needed


def timeframe_to_minutes(timeframe: int) -> int:
    """Convert MT5 timeframe constant to minutes."""
    timeframe_map = {
        mt5.TIMEFRAME_M1: 1,
        mt5.TIMEFRAME_M5: 5,
        mt5.TIMEFRAME_M15: 15,
        mt5.TIMEFRAME_M30: 30,
        mt5.TIMEFRAME_H1: 60,
        mt5.TIMEFRAME_H4: 240,
        mt5.TIMEFRAME_D1: 1440
    }
    return timeframe_map.get(timeframe, 5)


def minutes_to_timeframe(minutes: int) -> int:
    """Convert minutes to MT5 timeframe constant."""
    if minutes <= 1:
        return mt5.TIMEFRAME_M1
    elif minutes <= 5:
        return mt5.TIMEFRAME_M5
    elif minutes <= 15:
        return mt5.TIMEFRAME_M15
    elif minutes <= 30:
        return mt5.TIMEFRAME_M30
    elif minutes <= 60:
        return mt5.TIMEFRAME_H1
    elif minutes <= 240:
        return mt5.TIMEFRAME_H4
    else:
        return mt5.TIMEFRAME_D1


def validate_symbol(symbol: str) -> bool:
    """Check if symbol is available for trading."""
    symbol_info = mt5.symbol_info(symbol)
    
    if symbol_info is None:
        return False
    
    if not symbol_info.visible:
        # Try to make it visible
        if not mt5.symbol_select(symbol, True):
            return False
    
    return True


def get_account_info_summary() -> Dict:
    """Get formatted account information summary."""
    account = mt5.account_info()
    
    if account is None:
        return {}
    
    return {
        'login': account.login,
        'server': account.server,
        'balance': account.balance,
        'equity': account.equity,
        'margin': account.margin,
        'free_margin': account.margin_free,
        'margin_level': account.margin_level if account.margin > 0 else 0,
        'profit': account.profit,
        'currency': account.currency
    }


def calculate_position_duration(open_time: datetime, close_time: datetime = None) -> str:
    """Calculate and format position duration."""
    if close_time is None:
        close_time = datetime.now()
    
    duration = close_time - open_time
    
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60
    
    if duration.days > 0:
        return f"{duration.days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    else:
        return f"{minutes}m {seconds}s"


def batch_process(items: List, batch_size: int = 10):
    """
    Process items in batches.
    
    Args:
        items: List of items to process
        batch_size: Size of each batch
        
    Yields:
        Batches of items
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safely divide two numbers, returning default if denominator is zero."""
    return numerator / denominator if denominator != 0 else default


def round_to_step(value: float, step: float) -> float:
    """Round value to nearest step."""
    return round(value / step) * step


def normalize_symbol_name(symbol: str) -> str:
    """Normalize symbol name (remove suffixes, standardize format)."""
    # Remove common broker suffixes
    symbol = symbol.replace('.a', '').replace('.b', '').replace('_', '')
    symbol = symbol.replace('.', '').replace('-', '')
    return symbol.upper()