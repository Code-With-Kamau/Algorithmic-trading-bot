"""
Detects liquidity sweeps, pools, and grabs.
"""

import pandas as pd
from typing import Optional, Dict, List
from utils.logger_config import get_logger

logger = get_logger(__name__)


class LiquidityAnalyzer:
    """Analyzes liquidity zones and sweeps."""
    
    def __init__(self, settings):
        self.settings = settings
    
    def detect_sweep(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect liquidity sweeps.
        
        A sweep occurs when price briefly breaks a significant level (high/low)
        and then reverses sharply.
        """
        if len(df) < 10:
            return None
        
        try:
            recent_df = df.tail(10)
            
            # Find recent highs and lows
            recent_high = recent_df['high'].iloc[:-1].max()
            recent_low = recent_df['low'].iloc[:-1].min()
            
            current_candle = recent_df.iloc[-1]
            prev_candle = recent_df.iloc[-2]
            
            # Calculate pip value for sweep detection
            pip_distance = self.settings.LIQUIDITY_SWEEP_PIPS * 0.0001  # Approximate
            
            # Bullish sweep (sweep low and reverse up)
            # Price goes below recent low then closes back above
            if (current_candle['low'] < recent_low and
                current_candle['close'] > recent_low + pip_distance and
                current_candle['close'] > current_candle['open']):
                
                return {
                    'direction': 'LOW',  # Swept the lows (bullish reversal)
                    'level': recent_low,
                    'sweep_price': current_candle['low'],
                    'close_price': current_candle['close'],
                    'wick_size': current_candle['close'] - current_candle['low']
                }
            
            # Bearish sweep (sweep high and reverse down)
            # Price goes above recent high then closes back below
            if (current_candle['high'] > recent_high and
                current_candle['close'] < recent_high - pip_distance and
                current_candle['close'] < current_candle['open']):
                
                return {
                    'direction': 'HIGH',  # Swept the highs (bearish reversal)
                    'level': recent_high,
                    'sweep_price': current_candle['high'],
                    'close_price': current_candle['close'],
                    'wick_size': current_candle['high'] - current_candle['close']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting liquidity sweep: {e}")
            return None
    
    def identify_liquidity_pools(self, df: pd.DataFrame) -> List[Dict]:
        """
        Identify liquidity pools (areas with equal highs/lows).
        
        These are zones where stop losses are likely clustered.
        """
        if len(df) < 20:
            return []
        
        pools = []
        
        try:
            recent_df = df.tail(50)
            
            # Find equal highs (resistance)
            tolerance = 0.0002  # 2 pips tolerance
            
            highs = recent_df['high'].values
            for i in range(len(highs) - 5):
                similar_highs = []
                base_high = highs[i]
                
                for j in range(i + 1, min(i + 20, len(highs))):
                    if abs(highs[j] - base_high) / base_high < tolerance:
                        similar_highs.append(j)
                
                # If we found 2+ similar highs, it's a liquidity pool
                if len(similar_highs) >= 2:
                    pools.append({
                        'type': 'RESISTANCE',
                        'price': base_high,
                        'touches': len(similar_highs) + 1,
                        'strength': len(similar_highs) + 1
                    })
            
            # Find equal lows (support)
            lows = recent_df['low'].values
            for i in range(len(lows) - 5):
                similar_lows = []
                base_low = lows[i]
                
                for j in range(i + 1, min(i + 20, len(lows))):
                    if abs(lows[j] - base_low) / base_low < tolerance:
                        similar_lows.append(j)
                
                if len(similar_lows) >= 2:
                    pools.append({
                        'type': 'SUPPORT',
                        'price': base_low,
                        'touches': len(similar_lows) + 1,
                        'strength': len(similar_lows) + 1
                    })
            
            return pools
            
        except Exception as e:
            logger.error(f"Error identifying liquidity pools: {e}")
            return []
    
    def detect_stop_hunt(self, df: pd.DataFrame) -> Optional[Dict]:
        """
        Detect stop hunts (aggressive liquidity grabs).
        
        Characterized by long wicks that quickly reverse.
        """
        if len(df) < 3:
            return None
        
        try:
            current = df.iloc[-1]
            prev = df.iloc[-2]
            
            body_size = abs(current['close'] - current['open'])
            
            # Bullish stop hunt: long lower wick with bullish close
            lower_wick = current['open'] - current['low'] if current['close'] > current['open'] else current['close'] - current['low']
            
            if lower_wick > body_size * 2 and current['close'] > current['open']:
                return {
                    'direction': 'BULLISH',
                    'entry_zone': current['low'] + (lower_wick * 0.3),  # 30% up from low
                    'swept_level': current['low'],
                    'wick_ratio': lower_wick / body_size if body_size > 0 else 0
                }
            
            # Bearish stop hunt: long upper wick with bearish close
            upper_wick = current['high'] - current['open'] if current['close'] < current['open'] else current['high'] - current['close']
            
            if upper_wick > body_size * 2 and current['close'] < current['open']:
                return {
                    'direction': 'BEARISH',
                    'entry_zone': current['high'] - (upper_wick * 0.3),  # 30% down from high
                    'swept_level': current['high'],
                    'wick_ratio': upper_wick / body_size if body_size > 0 else 0
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting stop hunt: {e}")
            return None
    
    def calculate_liquidity_score(self, df: pd.DataFrame) -> float:
        """
        Calculate overall liquidity score for current market conditions.
        
        Higher score = more liquidity activity = better for scalping.
        """
        try:
            score = 0.0
            
            # Check for recent sweep
            sweep = self.detect_sweep(df)
            if sweep:
                score += 3.0
            
            # Check for stop hunt
            stop_hunt = self.detect_stop_hunt(df)
            if stop_hunt:
                score += 2.5
            
            # Check liquidity pools
            pools = self.identify_liquidity_pools(df)
            score += len(pools) * 0.5
            
            # Volume analysis
            if len(df) >= 20:
                recent_volume = df['tick_volume'].iloc[-5:].mean()
                avg_volume = df['tick_volume'].iloc[-20:].mean()
                
                if recent_volume > avg_volume * 1.5:
                    score += 2.0
            
            return min(score, 10.0)  # Cap at 10
            
        except Exception as e:
            logger.error(f"Error calculating liquidity score: {e}")
            return 0.0