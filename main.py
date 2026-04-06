"""
main.py - High-Frequency SMC Scalping Bot
Main entry point for the trading system.
Initializes MT5 connection, starts Flask dashboard, and runs trading loop.
"""

import asyncio
import signal
import sys
import threading
import time
from dotenv import load_dotenv
import MetaTrader5 as mt5

from config.settings import Settings
from core.market_data import MarketData
from core.strategy import ScalpingStrategy
from core.order_execution import OrderExecutor
from core.trade_manager import TradeManager
from database.database import Database
from utils.logger_config import setup_logger
from web.app import create_app

# Load environment variables
load_dotenv()

# Initialize logger
logger = setup_logger()

class TradingBot:
    """Main trading bot orchestrator."""
    
    def __init__(self):
        self.settings = Settings()
        self.running = False
        self.bot_active = True  # Bot can run (separate from auto_mode)
        self.auto_mode = True
        self.db = Database()
        self.market_data = None
        self.strategy = None
        self.executor = None
        self.trade_manager = None
        self.close_positions_on_exit = False  # New flag to control exit behavior
        
    def initialize_mt5(self) -> bool:
        """Initialize MT5 connection."""
        logger.info("Initializing MT5 connection...")
        
        if not mt5.initialize(
            login=self.settings.MT5_LOGIN,
            password=self.settings.MT5_PASSWORD,
            server=self.settings.MT5_SERVER
        ):
            logger.error(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("Failed to get account info")
            return False
            
        logger.info(f"Connected to MT5 | Account: {account_info.login} | Balance: ${account_info.balance:.2f}")
        return True
    
    def initialize_components(self):
        """Initialize all trading components."""
        self.market_data = MarketData(self.settings)
        self.strategy = ScalpingStrategy(self.settings, self.db)
        self.executor = OrderExecutor(self.settings, self.db)
        self.trade_manager = TradeManager(self.settings, self.executor, self.db)
        logger.info("All components initialized successfully")
    
    async def trading_loop(self):
        """Main trading loop - runs continuously."""
        logger.info("Starting trading loop...")
        
        while self.running:
            try:
                # Check if bot is active
                if not self.bot_active:
                    await asyncio.sleep(1)
                    continue
                
                if not self.auto_mode:
                    await asyncio.sleep(1)
                    continue
                
                # Get current market data for all symbols
                for symbol in self.settings.SYMBOLS:
                    # Double-check bot is still active (could change mid-loop)
                    if not self.bot_active or not self.running:
                        break
                    
                    # Fetch market data
                    candles = self.market_data.get_candles(
                        symbol, 
                        self.settings.TIMEFRAME, 
                        self.settings.LOOKBACK_BARS
                    )
                    
                    if candles is None or len(candles) < self.settings.MIN_BARS_REQUIRED:
                        continue
                    
                    # Check for trading signal
                    signal = self.strategy.detect_signal(symbol, candles)
                    
                    if signal and signal['valid']:
                        logger.info(f"Signal detected for {symbol}: {signal['direction']} | Score: {signal['score']:.2f}")
                        
                        # Execute trade if conditions met
                        if self.strategy.confirm_trade(symbol, signal):
                            trade_result = self.executor.execute_trade(
                                symbol=symbol,
                                signal=signal,
                                account_balance=mt5.account_info().balance
                            )
                            
                            if trade_result:
                                logger.info(f"Trade executed: {trade_result}")
                
                # Manage existing trades (only if bot is active)
                if self.bot_active:
                    self.trade_manager.manage_open_trades()
                
                # Sleep based on strategy timeframe
                await asyncio.sleep(self.settings.LOOP_DELAY)
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}", exc_info=True)
                await asyncio.sleep(5)
    
    def start_flask_dashboard(self):
        """Start Flask web dashboard in separate thread."""
        app = create_app(self)
        dashboard_thread = threading.Thread(
            target=lambda: app.run(
                host='0.0.0.0',
                port=5000,
                debug=False,
                use_reloader=False
            ),
            daemon=True
        )
        dashboard_thread.start()
        logger.info("Flask dashboard started at http://localhost:5000")
    
    def stop_bot(self):
        """Stop the bot without closing positions."""
        logger.info("Stopping bot (positions will remain open)...")
        self.bot_active = False
        logger.info("Bot stopped. Positions remain open.")
    
    def start_bot(self):
        """Start the bot."""
        logger.info("Starting bot...")
        self.bot_active = True
        logger.info("Bot started and active.")
    
    def shutdown(self, signum=None, frame=None):
        """Graceful shutdown handler."""
        logger.info("Shutdown signal received...")
        self.running = False
        
        # Only close positions if explicitly requested
        if self.close_positions_on_exit:
            logger.info("Closing all open positions...")
            if self.trade_manager:
                self.trade_manager.close_all_trades("Bot shutdown - close requested")
        else:
            logger.info("Leaving positions open (use dashboard to close if needed)")
        
        # Shutdown MT5
        mt5.shutdown()
        logger.info("MT5 connection closed")
        logger.info("Bot stopped successfully")
        sys.exit(0)
    
    def run(self):
        """Main run method."""
        # Register signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        
        logger.info("=" * 60)
        logger.info("SMC SCALPING BOT - STARTING")
        logger.info("=" * 60)
        
        # Initialize MT5
        if not self.initialize_mt5():
            logger.error("Failed to initialize MT5. Exiting.")
            sys.exit(1)
        
        # Initialize database
        self.db.initialize()
        
        # Initialize trading components
        self.initialize_components()
        
        # Start Flask dashboard
        self.start_flask_dashboard()
        
        # Start trading loop
        self.running = True
        
        try:
            asyncio.run(self.trading_loop())
        except KeyboardInterrupt:
            self.shutdown()


if __name__ == "__main__":
    bot = TradingBot()
    bot.run()