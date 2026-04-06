"""
Implements FVG, Order Blocks, CHOCH, and BOS detection.
"""

import pandas as pd
from typing import Optional, Dict
from utils.logger_config import get_logger

logger = get_logger(__name__)


class SMCAnalyzer:
    """Smart Money Concepts analyzer."""
    
    def __init__(self, settings):
        self.settings = settings
    
    def detect_fvg(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect Fair Value Gaps (imbalances).
        
        A FVG occurs when there's a gap between candle 1's high and candle 3's low (bullish)
        or candle 1's low and candle 3's high (bearish).
        """
        if len(df) < 3:
            return None
        
        try:
            # Check last 3 candles
            candle_1 = df.iloc[-3]
            candle_2 = df.iloc[-2]
            candle_3 = df.iloc[-1]
            
            # Bullish FVG: gap between candle 1 high and candle 3 low
            bullish_gap = candle_3['low'] - candle_1['high']
            if bullish_gap > self.settings.FVG_MIN_SIZE:
                return {
                    'type': 'BULLISH',
                    'top': candle_3['low'],
                    'bottom': candle_1['high'],
                    'price': (candle_3['low'] + candle_1['high']) / 2,
                    'size': bullish_gap
                }
            
            # Bearish FVG: gap between candle 1 low and candle 3 high
            bearish_gap = candle_1['low'] - candle_3['high']
            if bearish_gap > self.settings.FVG_MIN_SIZE:
                return {
                    'type': 'BEARISH',
                    'top': candle_1['low'],
                    'bottom': candle_3['high'],
                    'price': (candle_1['low'] + candle_3['high']) / 2,
                    'size': bearish_gap
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting FVG: {e}")
            return None
    
    def detect_order_block(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect Order Blocks.
        
        An order block is the last up/down candle before a strong move in opposite direction.
        """
        if len(df) < self.settings.ORDER_BLOCK_LOOKBACK:
            return None
        
        try:
            recent_df = df.tail(self.settings.ORDER_BLOCK_LOOKBACK)
            
            # Bullish Order Block: last down candle before strong up move
            for i in range(len(recent_df) - 3, 0, -1):
                current = recent_df.iloc[i]
                next_candle = recent_df.iloc[i + 1]
                
                # Check if current is bearish and next is strong bullish
                if (current['close'] < current['open'] and
                    next_candle['close'] > next_candle['open'] and
                    (next_candle['close'] - next_candle['open']) > (current['open'] - current['close']) * 1.5):
                    
                    return {
                        'type': 'BULLISH',
                        'high': current['high'],
                        'low': current['low'],
                        'price': (current['high'] + current['low']) / 2,
                        'strength': (next_candle['close'] - next_candle['open'])
                    }
            
            # Bearish Order Block: last up candle before strong down move
            for i in range(len(recent_df) - 3, 0, -1):
                current = recent_df.iloc[i]
                next_candle = recent_df.iloc[i + 1]
                
                # Check if current is bullish and next is strong bearish
                if (current['close'] > current['open'] and
                    next_candle['close'] < next_candle['open'] and
                    (next_candle['open'] - next_candle['close']) > (current['close'] - current['open']) * 1.5):
                    
                    return {
                        'type': 'BEARISH',
                        'high': current['high'],
                        'low': current['low'],
                        'price': (current['high'] + current['low']) / 2,
                        'strength': (next_candle['open'] - next_candle['close'])
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting order block: {e}")
            return None
    
    def detect_choch(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect Change of Character (CHOCH).
        
        CHOCH occurs when price breaks the previous structure (swing high/low).
        """
        if len(df) < 20:
            return None
        
        try:
            recent_df = df.tail(20)
            
            # Find swing highs and lows
            swing_highs = []
            swing_lows = []
            
            for i in range(2, len(recent_df) - 2):
                current_high = recent_df['high'].iloc[i]
                current_low = recent_df['low'].iloc[i]
                
                # Swing high: higher than 2 candles on each side
                if (current_high > recent_df['high'].iloc[i-1] and
                    current_high > recent_df['high'].iloc[i-2] and
                    current_high > recent_df['high'].iloc[i+1] and
                    current_high > recent_df['high'].iloc[i+2]):
                    swing_highs.append((i, current_high))
                
                # Swing low: lower than 2 candles on each side
                if (current_low < recent_df['low'].iloc[i-1] and
                    current_low < recent_df['low'].iloc[i-2] and
                    current_low < recent_df['low'].iloc[i+1] and
                    current_low < recent_df['low'].iloc[i+2]):
                    swing_lows.append((i, current_low))
            
            if len(swing_highs) < 1 or len(swing_lows) < 1:
                return None
            
            current_price = recent_df['close'].iloc[-1]
            last_swing_high = swing_highs[-1][1]
            last_swing_low = swing_lows[-1][1]
            
            # Bullish CHOCH: price breaks above recent swing high
            if current_price > last_swing_high:
                return {
                    'direction': 'BULLISH',
                    'level': last_swing_high,
                    'strength': (current_price - last_swing_high) / last_swing_high * 100
                }
            
            # Bearish CHOCH: price breaks below recent swing low
            if current_price < last_swing_low:
                return {
                    'direction': 'BEARISH',
                    'level': last_swing_low,
                    'strength': (last_swing_low - current_price) / last_swing_low * 100
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting CHOCH: {e}")
            return None
    
    def detect_bos(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect Break of Structure (BOS).
        
        Similar to CHOCH but confirms trend continuation.
        """
        if len(df) < 15:
            return None
        
        try:
            recent_df = df.tail(15)
            
            # Calculate recent highs and lows
            recent_high = recent_df['high'].max()
            recent_low = recent_df['low'].min()
            current_price = recent_df['close'].iloc[-1]
            
            # Bullish BOS: break above recent high in uptrend
            if current_price > recent_high * 1.0005:  # 0.05% buffer
                return {
                    'direction': 'BULLISH',
                    'level': recent_high,
                    'current_price': current_price
                }
            
            # Bearish BOS: break below recent low in downtrend
            if current_price < recent_low * 0.9995:  # 0.05% buffer
                return {
                    'direction': 'BEARISH',
                    'level': recent_low,
                    'current_price': current_price
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting BOS: {e}")
            return None
    
    def detect_market_structure_shift(self, df: pd.DataFrame) -> Optional[str]:
        """
        Detect overall market structure shift.
        
        Returns: 'BULLISH', 'BEARISH', or None
        """
        if len(df) < 50:
            return None
        
        try:
            # Simple structure analysis
            recent_closes = df['close'].tail(20)
            older_closes = df['close'].tail(50).head(30)
            
            recent_avg = recent_closes.mean()
            older_avg = older_closes.mean()
            
            # Check for structure shift
            if recent_avg > older_avg * 1.01:  # 1% higher
                return 'BULLISH'
            elif recent_avg < older_avg * 0.99:  # 1% lower
                return 'BEARISH'
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting market structure shift: {e}")
            return None