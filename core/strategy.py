"""
Implements Smart Money Concepts trading logic with scalping approach.
"""

import pandas as pd
from typing import Optional, Dict
from datetime import datetime
import MetaTrader5 as mt5

from analysis.indicators import Indicators
from analysis.smc_logic import SMCAnalyzer
from analysis.liquidity import LiquidityAnalyzer
from config.risk_management import RiskManager
from utils.logger_config import get_logger

logger = get_logger(__name__)


class ScalpingStrategy:
    """Main strategy class implementing SMC-based scalping logic."""
    
    def __init__(self, settings, db):
        self.settings = settings
        self.db = db
        self.indicators = Indicators(settings)
        self.smc = SMCAnalyzer(settings)
        self.liquidity = LiquidityAnalyzer(settings)
        self.risk_manager = RiskManager(settings)
        
        # Signal scoring weights
        self.weights = {
            'liquidity_sweep': 3.0,
            'fvg': 2.5,
            'order_block': 2.0,
            'choch': 2.5,
            'rsi': 1.5,
            'volume': 1.0,
            'trend': 1.5
        }
    
    def detect_signal(self, symbol: str, df: pd.DataFrame) -> Optional[Dict]:
        """
        Main signal detection method.
        
        Args:
            symbol: Trading symbol
            df: OHLCV DataFrame
            
        Returns:
            Signal dictionary with direction, entry, SL, TP, score, and components
        """
        if df is None or len(df) < self.settings.MIN_BARS_REQUIRED:
            return None
        
        try:
            # Calculate all indicators
            df = self.indicators.calculate_all(df)
            
            # Initialize signal components
            signal_components = {
                'liquidity_sweep': False,
                'fvg': False,
                'order_block': False,
                'choch': False,
                'rsi_confirmed': False,
                'volume_confirmed': False,
                'trend_aligned': False
            }
            
            # Detect liquidity sweeps
            liquidity_sweep = self.liquidity.detect_sweep(df)
            if liquidity_sweep:
                signal_components['liquidity_sweep'] = True
                logger.debug(f"{symbol}: Liquidity sweep detected - {liquidity_sweep['direction']}")
            
            # Detect Fair Value Gaps
            fvg = self.smc.detect_fvg(df)
            if fvg:
                signal_components['fvg'] = True
                logger.debug(f"{symbol}: FVG detected at {fvg['price']:.5f}")
            
            # Detect Order Blocks
            order_block = self.smc.detect_order_block(df)
            if order_block:
                signal_components['order_block'] = True
                logger.debug(f"{symbol}: Order block detected - {order_block['type']}")
            
            # Detect Change of Character
            choch = self.smc.detect_choch(df)
            if choch:
                signal_components['choch'] = True
                logger.debug(f"{symbol}: CHOCH detected - {choch['direction']}")
            
            # Check RSI confirmation
            current_rsi = df['rsi'].iloc[-1]
            if current_rsi < self.settings.RSI_OVERSOLD:
                signal_components['rsi_confirmed'] = True
                direction_hint = 'BUY'
            elif current_rsi > self.settings.RSI_OVERBOUGHT:
                signal_components['rsi_confirmed'] = True
                direction_hint = 'SELL'
            else:
                direction_hint = None
            
            # Volume confirmation
            if df['volume_ratio'].iloc[-1] > 1.5:
                signal_components['volume_confirmed'] = True
            
            # Trend alignment
            if df['ema_20'].iloc[-1] > df['ema_50'].iloc[-1]:
                signal_components['trend_aligned'] = 'BULLISH'
            else:
                signal_components['trend_aligned'] = 'BEARISH'
            
            # Calculate signal score
            score = self._calculate_signal_score(signal_components)
            
            # Determine trade direction
            direction = self._determine_direction(
                signal_components, 
                liquidity_sweep, 
                choch, 
                direction_hint,
                df
            )
            
            if direction is None or score < 5.0:  # Minimum score threshold
                return None
            
            # Calculate entry, SL, TP
            current_price = df['close'].iloc[-1]
            atr = df['atr'].iloc[-1]
            
            if direction == 'BUY':
                entry = current_price
                stop_loss = entry - (atr * self.settings.ATR_MULTIPLIER)
                take_profit = entry + (atr * self.settings.ATR_MULTIPLIER * self.settings.MIN_RISK_REWARD)
            else:  # SELL
                entry = current_price
                stop_loss = entry + (atr * self.settings.ATR_MULTIPLIER)
                take_profit = entry - (atr * self.settings.ATR_MULTIPLIER * self.settings.MIN_RISK_REWARD)
            
            signal = {
                'valid': True,
                'symbol': symbol,
                'direction': direction,
                'entry': entry,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'score': score,
                'components': signal_components,
                'atr': atr,
                'timestamp': datetime.now()
            }
            
            # Log signal to database
            self.db.log_signal(signal)
            
            return signal
            
        except Exception as e:
            logger.error(f"Error detecting signal for {symbol}: {e}", exc_info=True)
            return None
    
    def _calculate_signal_score(self, components: Dict) -> float:
        """Calculate weighted signal score."""
        score = 0.0
        
        if components['liquidity_sweep']:
            score += self.weights['liquidity_sweep']
        if components['fvg']:
            score += self.weights['fvg']
        if components['order_block']:
            score += self.weights['order_block']
        if components['choch']:
            score += self.weights['choch']
        if components['rsi_confirmed']:
            score += self.weights['rsi']
        if components['volume_confirmed']:
            score += self.weights['volume']
        if components['trend_aligned']:
            score += self.weights['trend']
        
        return score
    
    def _determine_direction(
        self, 
        components: Dict, 
        liquidity_sweep: Optional[Dict],
        choch: Optional[Dict],
        rsi_hint: Optional[str],
        df: pd.DataFrame
    ) -> Optional[str]:
        """Determine trade direction based on signals."""
        bullish_votes = 0
        bearish_votes = 0
        
        # Liquidity sweep direction (contrarian)
        if liquidity_sweep:
            if liquidity_sweep['direction'] == 'LOW':
                bullish_votes += 3
            else:
                bearish_votes += 3
        
        # CHOCH direction
        if choch:
            if choch['direction'] == 'BULLISH':
                bullish_votes += 2
            else:
                bearish_votes += 2
        
        # RSI hint
        if rsi_hint == 'BUY':
            bullish_votes += 2
        elif rsi_hint == 'SELL':
            bearish_votes += 2
        
        # Trend alignment
        if components['trend_aligned'] == 'BULLISH':
            bullish_votes += 1
        elif components['trend_aligned'] == 'BEARISH':
            bearish_votes += 1
        
        # Price action (last 3 candles momentum)
        recent_closes = df['close'].iloc[-3:].values
        if recent_closes[-1] > recent_closes[0]:
            bullish_votes += 1
        else:
            bearish_votes += 1
        
        if bullish_votes > bearish_votes:
            return 'BUY'
        elif bearish_votes > bullish_votes:
            return 'SELL'
        else:
            return None
    
    def confirm_trade(self, symbol: str, signal: Dict) -> bool:
        """
        Final confirmation before trade execution.
        
        Args:
            symbol: Trading symbol
            signal: Signal dictionary
            
        Returns:
            True if trade should be executed
        """
        try:
            # Risk management validation
            validation = self.risk_manager.validate_trade(
                symbol=symbol,
                entry_price=signal['entry'],
                stop_loss=signal['stop_loss'],
                take_profit=signal['take_profit'],
                direction=signal['direction']
            )
            
            if not validation['valid']:
                logger.info(f"Trade validation failed: {validation['reason']}")
                return False
            
            # Check daily loss limit
            if not self.risk_manager.check_daily_loss_limit(self.db):
                logger.warning("Daily loss limit reached. No new trades.")
                return False
            
            # Check spread
            from core.market_data import MarketData
            market_data = MarketData(self.settings)
            spread_pips = market_data.get_spread_pips(symbol)
            
            if spread_pips > 3.0:  # Max 3 pips spread for scalping
                logger.info(f"Spread too high: {spread_pips:.1f} pips")
                return False
            
            logger.info(f"Trade confirmed for {symbol}: {signal['direction']} | Score: {signal['score']:.1f} | R:R: {validation.get('risk_reward', 0):.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error confirming trade: {e}", exc_info=True)
            return False