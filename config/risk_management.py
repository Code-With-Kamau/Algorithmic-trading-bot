"""
config/risk_management.py - Risk Management Module
Handles position sizing, risk calculations, and trade validation.
"""

import MetaTrader5 as mt5
from typing import Optional


class RiskManager:
    """Manages risk and position sizing for trades."""
    
    def __init__(self, settings):
        self.settings = settings
    
    def calculate_position_size(
        self, 
        symbol: str, 
        account_balance: float, 
        stop_loss_pips: float
    ) -> float:
        """
        Calculate position size based on risk percentage and stop loss.
        
        Args:
            symbol: Trading symbol
            account_balance: Current account balance
            stop_loss_pips: Stop loss distance in pips
            
        Returns:
            Lot size to trade
        """
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return 0.0
        
        # Calculate risk amount in account currency
        risk_amount = account_balance * (self.settings.RISK_PERCENT / 100.0)
        
        # Convert pips to price
        point = symbol_info.point
        if symbol_info.digits == 3 or symbol_info.digits == 5:
            pip_value = point * 10
        else:
            pip_value = point
        
        stop_loss_price = stop_loss_pips * pip_value
        
        # Calculate lot size
        # Risk amount = lot size * contract size * stop loss in price
        contract_size = symbol_info.trade_contract_size
        
        if stop_loss_price == 0:
            return symbol_info.volume_min
        
        lot_size = risk_amount / (contract_size * stop_loss_price)
        
        # Round to volume step
        volume_step = symbol_info.volume_step
        lot_size = round(lot_size / volume_step) * volume_step
        
        # Ensure within min/max limits
        lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
        
        return lot_size
    
    def calculate_stop_loss_pips(self, entry_price: float, stop_loss_price: float, symbol: str) -> float:
        """Calculate stop loss distance in pips."""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return 0.0
        
        point = symbol_info.point
        if symbol_info.digits == 3 or symbol_info.digits == 5:
            pip_value = point * 10
        else:
            pip_value = point
        
        pips = abs(entry_price - stop_loss_price) / pip_value
        return pips
    
    def validate_trade(
        self, 
        symbol: str, 
        entry_price: float, 
        stop_loss: float, 
        take_profit: float,
        direction: str
    ) -> dict:
        """
        Validate trade parameters before execution.
        
        Returns:
            Dict with 'valid' boolean and 'reason' string
        """
        # Calculate risk:reward ratio
        if direction == 'BUY':
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # SELL
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        if risk <= 0:
            return {'valid': False, 'reason': 'Invalid stop loss'}
        
        risk_reward = reward / risk
        
        if risk_reward < self.settings.MIN_RISK_REWARD:
            return {
                'valid': False, 
                'reason': f'R:R ratio {risk_reward:.2f} below minimum {self.settings.MIN_RISK_REWARD}'
            }
        
        # Check if max open trades exceeded
        positions = mt5.positions_get(symbol=symbol)
        if positions is not None and len(positions) >= self.settings.MAX_OPEN_TRADES:
            return {
                'valid': False,
                'reason': f'Max open trades ({self.settings.MAX_OPEN_TRADES}) reached'
            }
        
        return {'valid': True, 'reason': 'Trade validated', 'risk_reward': risk_reward}
    
    def check_daily_loss_limit(self, db) -> bool:
        """
        Check if daily loss limit has been reached.
        
        Returns:
            True if trading allowed, False if limit reached
        """
        daily_pnl = db.get_daily_pnl()
        
        if daily_pnl is None:
            return True
        
        account_info = mt5.account_info()
        if account_info is None:
            return False
        
        max_loss = account_info.balance * (self.settings.MAX_DAILY_LOSS / 100.0)
        
        if daily_pnl < -max_loss:
            return False
        
        return True
    
    def calculate_pip_value(self, symbol: str, lot_size: float) -> float:
        """Calculate the value of one pip for given lot size."""
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return 0.0
        
        point = symbol_info.point
        if symbol_info.digits == 3 or symbol_info.digits == 5:
            pip_value = point * 10
        else:
            pip_value = point
        
        contract_size = symbol_info.trade_contract_size
        pip_value_money = lot_size * contract_size * pip_value
        
        return pip_value_money