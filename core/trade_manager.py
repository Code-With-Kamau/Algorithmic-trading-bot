"""
core/trade_manager.py - Trade Management Module
Manages open positions: trailing stops, breakeven, partial closes.
"""

import MetaTrader5 as mt5
from typing import List, Dict
from datetime import datetime

from utils.logger_config import get_logger

logger = get_logger(__name__)


class TradeManager:
    """Manages open trades and applies trade management rules."""
    
    def __init__(self, settings, executor, db):
        self.settings = settings
        self.executor = executor
        self.db = db
        self.managed_positions = {}  # Track management state
    
    def manage_open_trades(self):
        """Main method to manage all open positions."""
        try:
            positions = mt5.positions_get()
            if positions is None or len(positions) == 0:
                return
            
            for position in positions:
                if position.magic != 234000:  # Only manage our bot's trades
                    continue
                
                ticket = position.ticket
                
                # Initialize tracking if new position
                if ticket not in self.managed_positions:
                    self.managed_positions[ticket] = {
                        'breakeven_moved': False,
                        'partial_closed': False,
                        'max_profit': 0.0
                    }
                
                # Apply management strategies
                self._apply_breakeven(position)
                self._apply_trailing_stop(position)
                self._apply_partial_close(position)
                
        except Exception as e:
            logger.error(f"Error managing trades: {e}", exc_info=True)
    
    def _apply_breakeven(self, position):
        """Move stop loss to breakeven when in profit."""
        try:
            ticket = position.ticket
            
            # Skip if already moved to breakeven
            if self.managed_positions[ticket]['breakeven_moved']:
                return
            
            symbol = position.symbol
            symbol_info = mt5.symbol_info(symbol)
            point = symbol_info.point
            
            # Calculate pips in profit
            if position.type == mt5.ORDER_TYPE_BUY:
                current_price = mt5.symbol_info_tick(symbol).bid
                pips_in_profit = (current_price - position.price_open) / point
                
                if pips_in_profit >= self.settings.BREAKEVEN_PIPS * 10:  # Multiply by 10 for 5-digit brokers
                    new_sl = position.price_open + (5 * point * 10)  # +5 pips from entry
                    
                    if new_sl > position.sl:
                        if self.executor.modify_position(ticket, new_sl=new_sl):
                            self.managed_positions[ticket]['breakeven_moved'] = True
                            logger.info(f"✓ Breakeven set for {ticket} at {new_sl:.5f}")
            
            else:  # SELL
                current_price = mt5.symbol_info_tick(symbol).ask
                pips_in_profit = (position.price_open - current_price) / point
                
                if pips_in_profit >= self.settings.BREAKEVEN_PIPS * 10:
                    new_sl = position.price_open - (5 * point * 10)  # -5 pips from entry
                    
                    if new_sl < position.sl or position.sl == 0:
                        if self.executor.modify_position(ticket, new_sl=new_sl):
                            self.managed_positions[ticket]['breakeven_moved'] = True
                            logger.info(f"--✅ Breakeven set for {ticket} at {new_sl:.5f}")
        
        except Exception as e:
            logger.error(f"Error applying breakeven: {e}")
    
    def _apply_trailing_stop(self, position):
        """Apply trailing stop loss."""
        try:
            if not self.settings.USE_TRAILING_STOP:
                return
            
            ticket = position.ticket
            symbol = position.symbol
            symbol_info = mt5.symbol_info(symbol)
            point = symbol_info.point
            
            trailing_distance = self.settings.TRAILING_STOP_PIPS * 10 * point
            
            if position.type == mt5.ORDER_TYPE_BUY:
                current_price = mt5.symbol_info_tick(symbol).bid
                new_sl = current_price - trailing_distance
                
                # Only move SL up, never down
                if new_sl > position.sl:
                    self.executor.modify_position(ticket, new_sl=new_sl)
                    logger.debug(f"Trailing stop updated for {ticket}: {new_sl:.5f}")
            
            else:  # SELL
                current_price = mt5.symbol_info_tick(symbol).ask
                new_sl = current_price + trailing_distance
                
                # Only move SL down, never up
                if new_sl < position.sl or position.sl == 0:
                    self.executor.modify_position(ticket, new_sl=new_sl)
                    logger.debug(f"Trailing stop updated for {ticket}: {new_sl:.5f}")
        
        except Exception as e:
            logger.error(f"Error applying trailing stop: {e}")
    
    def _apply_partial_close(self, position):
        """Close partial position at specified R:R ratio."""
        try:
            ticket = position.ticket
            
            # Skip if already partially closed
            if self.managed_positions[ticket]['partial_closed']:
                return
            
            # Calculate current R:R ratio
            if position.type == mt5.ORDER_TYPE_BUY:
                current_price = mt5.symbol_info_tick(position.symbol).bid
                risk = position.price_open - position.sl
                reward = current_price - position.price_open
            else:
                current_price = mt5.symbol_info_tick(position.symbol).ask
                risk = position.sl - position.price_open
                reward = position.price_open - current_price
            
            if risk <= 0:
                return
            
            rr_ratio = reward / risk
            
            # Close partial position when target R:R reached
            if rr_ratio >= self.settings.PARTIAL_CLOSE_AT_RR:
                if self.executor.partial_close(ticket, self.settings.PARTIAL_CLOSE_PERCENT):
                    self.managed_positions[ticket]['partial_closed'] = True
                    logger.info(f"✅+✅+✅ Partial close executed for {ticket} at {rr_ratio:.1f}R")
        
        except Exception as e:
            logger.error(f"Error applying partial close: {e}")
    
    def close_all_trades(self, reason: str = "Close all"):
        """Close all open positions."""
        if not mt5.initialize():
            mt5.initialize()
            logger.info(f"MT5 initialized: {mt5.terminal_info()}")

        try:
            positions = mt5.positions_get()
            if positions is None or len(positions) == 0:
                logger.info("No positions to close")
                return
            
            closed_count = 0
            failed_count = 0
            
            for position in positions:
                # Only close positions created by this bot (magic number 234000)
                if position.magic == 234000:
                    logger.info(f"Attempting to close position {position.ticket} - {position.symbol}")
                    
                    if self.executor.close_position(position.ticket, "manual_close"):
                        closed_count += 1
                        logger.info(f"✅::✅ Successfully closed position {position.ticket}")
                    else:
                        failed_count += 1
                        logger.warning(f"❌::❌ Failed to close position {position.ticket}")
            
            logger.info(f"Close all complete: {closed_count} closed, {failed_count} failed. Reason: {reason}")
            
            # Clear managed positions tracking
            self.managed_positions.clear()
            
        except Exception as e:
            logger.error(f"Error closing all trades: {e}", exc_info=True)
    
    def get_open_positions_summary(self) -> List[Dict]:
        """Get summary of all open positions."""
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            summary = []
            for position in positions:
                if position.magic != 234000:
                    continue
                
                summary.append({
                    'ticket': position.ticket,
                    'symbol': position.symbol,
                    'type': 'BUY' if position.type == mt5.ORDER_TYPE_BUY else 'SELL',
                    'volume': position.volume,
                    'open_price': position.price_open,
                    'current_price': position.price_current,
                    'sl': position.sl,
                    'tp': position.tp,
                    'profit': position.profit,
                    'open_time': datetime.fromtimestamp(position.time),
                    'comment': position.comment
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting positions summary: {e}")
            return []
    def get_total_floating_pnl(self) -> float:
        """
        Calculate total floating P/L for all open positions.
        
        Returns:
            Total floating profit/loss
        """
        try:
            positions = mt5.positions_get()
            if positions is None or len(positions) == 0:
                return 0.0
            
            total_pnl = 0.0
            for position in positions:
                if position.magic == 234000:  # Only our bot's positions
                    total_pnl += position.profit
            
            return total_pnl
            
        except Exception as e:
            logger.error(f"Error calculating floating P/L: {e}")
            return 0.0

    def close_profitable_positions(self, reason: str = "Close profitable") -> dict:
        """
        Close only positions that are in profit.
        
        Returns:
            Dict with statistics of closed positions
        """
        try:
            positions = mt5.positions_get()
            if positions is None or len(positions) == 0:
                logger.info("No positions to close")
                return {
                    'success': True,
                    'closed_count': 0,
                    'total_profit': 0.0,
                    'skipped_count': 0
                }
            
            closed_count = 0
            skipped_count = 0
            total_profit = 0.0
            failed_count = 0
            
            for position in positions:
                # Only close positions created by this bot
                if position.magic == 234000:
                    # Check if position is profitable
                    if position.profit > 0:
                        logger.info(f"Closing profitable position {position.ticket} - Profit: ${position.profit:.2f}")
                        
                        if self.executor.close_position(position.ticket, reason):
                            closed_count += 1
                            total_profit += position.profit
                            logger.info(f"✅^^✅ Closed position {position.ticket} with profit ${position.profit:.2f}")
                        else:
                            failed_count += 1
                            logger.warning(f"❌^^❌Failed to close position {position.ticket}")
                    else:
                        skipped_count += 1
                        logger.info(f"Skipping losing position {position.ticket} - P/L: ${position.profit:.2f}")
            
            logger.info(f"Close profitable complete: {closed_count} closed (${total_profit:.2f}), {skipped_count} skipped, {failed_count} failed")
            
            # Clear managed positions tracking for closed ones
            for ticket in list(self.managed_positions.keys()):
                position = mt5.positions_get(ticket=ticket)
                if position is None or len(position) == 0:
                    del self.managed_positions[ticket]
            
            return {
                'success': True,
                'closed_count': closed_count,
                'total_profit': total_profit,
                'skipped_count': skipped_count,
                'failed_count': failed_count
            }
            
        except Exception as e:
            logger.error(f"Error closing profitable positions: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }