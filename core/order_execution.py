"""
Handles MT5 order placement, modification, and closing.
"""

import MetaTrader5 as mt5
from typing import Optional, Dict
from datetime import datetime

from config.risk_management import RiskManager
from utils.logger_config import get_logger

logger = get_logger(__name__)


class OrderExecutor:
    """Handles all MT5 order operations."""
    
    def __init__(self, settings, db):
        self.settings = settings
        self.db = db
        self.risk_manager = RiskManager(settings)
    
    def execute_trade(
        self, 
        symbol: str, 
        signal: Dict, 
        account_balance: float
    ) -> Optional[Dict]:
        """
        Execute a trade based on signal.
        
        Args:
            symbol: Trading symbol
            signal: Signal dictionary with entry, SL, TP
            account_balance: Current account balance
            
        Returns:
            Trade result dictionary or None if failed
        """
        try:
            direction = signal['direction']
            entry_price = signal['entry']
            stop_loss = signal['stop_loss']
            take_profit = signal['take_profit']
            
            # Calculate position size
            sl_pips = self.risk_manager.calculate_stop_loss_pips(
                entry_price, stop_loss, symbol
            )
            lot_size = self.risk_manager.calculate_position_size(
                symbol, account_balance, sl_pips
            )
            
            if lot_size <= 0:
                logger.error(f"Invalid lot size calculated: {lot_size}")
                return None
            
            # Prepare order request
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"Symbol info not available for {symbol}")
                return None
            
            # Normalize prices
            point = symbol_info.point
            stop_loss = round(stop_loss / point) * point
            take_profit = round(take_profit / point) * point
            
            # Set order type
            order_type = mt5.ORDER_TYPE_BUY if direction == 'BUY' else mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).ask if direction == 'BUY' else mt5.symbol_info_tick(symbol).bid
            
            # Create order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "sl": stop_loss,
                "tp": take_profit,
                "deviation": self.settings.MAX_SLIPPAGE,
                "magic": 234000,
                "comment": f"Charles's_SMC_Scalper_{signal['score']:.1f}",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send order
            logger.info(f"Sending order: {direction} {lot_size} lots {symbol} @ {price:.5f}")
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"Order send failed: {mt5.last_error()}")
                return None
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order failed: {result.retcode} - {result.comment}")
                return None
            
            # Log successful trade
            trade_data = {
                'ticket': result.order,
                'symbol': symbol,
                'type': direction,
                'volume': lot_size,
                'open_price': result.price,
                'sl': stop_loss,
                'tp': take_profit,
                'open_time': datetime.now(),
                'magic': 234000,
                'comment': request['comment'],
                'signal_score': signal['score']
            }
            
            self.db.log_trade(trade_data)
            
            logger.info(f"✅✅✅ Order executed successfully | Ticket: {result.order} | Price: {result.price:.5f}")
            
            return trade_data
            
        except Exception as e:
            logger.error(f"❌❌❌ Error executing trade: {e}", exc_info=True)
            return None
    
    
    def close_position(self, ticket: int, reason: str = "Manual close") -> bool:
        """Close an open position."""
        try:
            # Ensure MT5 is initialized in this thread
            if not mt5.initialize():
                mt5.initialize()
            
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                logger.warning(f"Position {ticket} not found")
                return False

            position = position[0]
            symbol = position.symbol
            symbol_info = mt5.symbol_info_tick(symbol)
            if symbol_info is None:
                logger.error(f"❌ No tick data for {symbol} — cannot close position.")
                return False

            # Determine opposite order type
            close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = symbol_info.bid if position.type == mt5.ORDER_TYPE_BUY else symbol_info.ask

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": position.volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": self.settings.MAX_SLIPPAGE,
                "magic": 234000,
                "comment": reason,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"❌ order_send() returned None: {mt5.last_error()}")
                return False
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ Failed to close {symbol} (ticket {ticket}): {result.comment}")
                return False
            logger.error(f"⚙️ Order Send Result for {symbol}: {result}")

            # Log closure
            profit = position.profit
            self.db.update_trade_close(ticket, result.price, profit, datetime.now(), reason)
            logger.info(f"✅ Closed position {ticket} ({symbol}) | Profit: ${profit:.2f} | Reason: {reason}")
            return True

        except Exception as e:
            logger.error(f"❌ Error closing position {ticket}: {e}", exc_info=True)
            return False

    
    def modify_position(
        self, 
        ticket: int, 
        new_sl: Optional[float] = None, 
        new_tp: Optional[float] = None
    ) -> bool:
        """
        Modify stop loss and/or take profit of an open position.
        
        Args:
            ticket: Position ticket number
            new_sl: New stop loss price
            new_tp: New take profit price
            
        Returns:
            True if modified successfully
        """
        try:
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                return False
            
            position = position[0]
            symbol = position.symbol
            
            # Use current values if not provided
            sl = new_sl if new_sl is not None else position.sl
            tp = new_tp if new_tp is not None else position.tp
            
            # Normalize prices
            symbol_info = mt5.symbol_info(symbol)
            point = symbol_info.point
            sl = round(sl / point) * point
            tp = round(tp / point) * point
            
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": symbol,
                "sl": sl,
                "tp": tp,
                "position": ticket,
            }
            
            result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.warning(f" Failed to modify position {ticket}")
                return False
            
            logger.debug(f"Position {ticket} modified | SL: {sl:.5f} | TP: {tp:.5f}")
            return True
            
        except Exception as e:
            logger.error(f"Error modifying position {ticket}: {e}", exc_info=True)
            return False
    
    def partial_close(self, ticket: int, close_percent: float) -> bool:
        """
        Partially close a position.
        
        Args:
            ticket: Position ticket number
            close_percent: Percentage to close (0-100)
            
        Returns:
            True if partially closed successfully
        """
        try:
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                return False
            
            position = position[0]
            symbol = position.symbol
            
            # Calculate volume to close
            close_volume = position.volume * (close_percent / 100.0)
            
            # Round to volume step
            symbol_info = mt5.symbol_info(symbol)
            volume_step = symbol_info.volume_step
            close_volume = round(close_volume / volume_step) * volume_step
            
            if close_volume < symbol_info.volume_min:
                logger.warning(f"Close volume {close_volume} below minimum")
                return False
            
            # Determine close type
            close_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(symbol).ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": close_volume,
                "type": close_type,
                "position": ticket,
                "price": price,
                "deviation": self.settings.MAX_SLIPPAGE,
                "magic": 234000,
                "comment": f"Partial close {close_percent}%",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                return False
            
            logger.info(f"✅ Partial close {close_percent}% of position {ticket} | Volume: {close_volume}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error partial closing position: {e}", exc_info=True)
            return False