"""
utils/logger_config.py - Logging Configuration
Configures rotating file and console logging.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime


def setup_logger(name: str = 'scalper_bot', log_file: str = 'logs/trading_bot.log', level: str = 'INFO'):
    """
    Configure and return a logger with rotating file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Configured logger instance
    """
    # Ensure log directory exists
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File Handler with rotation (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = None):
    """Get or create a logger instance."""
    if name:
        return logging.getLogger(f'scalper_bot.{name}')
    return logging.getLogger('scalper_bot')


class TradeLogger:
    """Specialized logger for trade-specific events."""
    
    def __init__(self, log_file: str = 'logs/trades.log'):
        self.logger = logging.getLogger('trade_logger')
        self.logger.setLevel(logging.INFO)
        
        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # File handler for trades only
        handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,
            backupCount=10
        )
        
        formatter = logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_entry(self, ticket: int, symbol: str, direction: str, price: float, 
                  volume: float, sl: float, tp: float):
        """Log trade entry."""
        self.logger.info(
            f"ENTRY | Ticket: {ticket} | {direction} {volume} {symbol} @ {price:.5f} | "
            f"SL: {sl:.5f} | TP: {tp:.5f}"
        )
    
    def log_exit(self, ticket: int, symbol: str, price: float, profit: float, reason: str):
        """Log trade exit."""
        self.logger.info(
            f"EXIT | Ticket: {ticket} | {symbol} @ {price:.5f} | "
            f"P/L: ${profit:.2f} | Reason: {reason}"
        )
    
    def log_modification(self, ticket: int, new_sl: float, new_tp: float, reason: str):
        """Log trade modification."""
        self.logger.info(
            f"MODIFY | Ticket: {ticket} | New SL: {new_sl:.5f} | "
            f"New TP: {new_tp:.5f} | Reason: {reason}"
        )