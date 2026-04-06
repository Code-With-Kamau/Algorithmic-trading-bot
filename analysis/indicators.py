"""
Calculates RSI, ATR, EMAs, and other technical indicators.
"""

import pandas as pd
import numpy as np


class Indicators:
    """Technical indicators calculator."""
    
    def __init__(self, settings):
        self.settings = settings
    
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all indicators on the DataFrame."""
        df = df.copy()
        
        # RSI
        df['rsi'] = self.calculate_rsi(df['close'], self.settings.RSI_PERIOD)
        
        # ATR
        df['atr'] = self.calculate_atr(df, self.settings.ATR_PERIOD)
        
        # EMAs
        df['ema_20'] = self.calculate_ema(df['close'], 20)
        df['ema_50'] = self.calculate_ema(df['close'], 50)
        df['ema_200'] = self.calculate_ema(df['close'], 200)
        
        # Volume analysis
        df['volume_sma'] = df['tick_volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['tick_volume'] / df['volume_sma']
        
        # Price momentum
        df['momentum'] = df['close'] - df['close'].shift(10)
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (2 * bb_std)
        df['bb_lower'] = df['bb_middle'] - (2 * bb_std)
        
        return df
    
    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average."""
        return series.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def calculate_sma(series: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average."""
        return series.rolling(window=period).mean()
    
    @staticmethod
    def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Calculate MACD indicator."""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return pd.DataFrame({
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        })
    
    @staticmethod
    def calculate_stochastic(df: pd.DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> pd.DataFrame:
        """Calculate Stochastic Oscillator."""
        low_min = df['low'].rolling(window=period).min()
        high_max = df['high'].rolling(window=period).max()
        
        k_percent = 100 * ((df['close'] - low_min) / (high_max - low_min))
        k_smooth = k_percent.rolling(window=smooth_k).mean()
        d_smooth = k_smooth.rolling(window=smooth_d).mean()
        
        return pd.DataFrame({
            'stoch_k': k_smooth,
            'stoch_d': d_smooth
        })
    
    @staticmethod
    def detect_divergence(price: pd.Series, indicator: pd.Series, lookback: int = 20) -> dict:
        """Detect bullish/bearish divergence."""
        # Find recent highs and lows
        price_highs = price.rolling(window=5, center=True).max()
        price_lows = price.rolling(window=5, center=True).min()
        
        is_price_high = price == price_highs
        is_price_low = price == price_lows
        
        # Simplified divergence detection
        recent_data = price.tail(lookback)
        recent_indicator = indicator.tail(lookback)
        
        if len(recent_data) < 10:
            return {'bullish': False, 'bearish': False}
        
        # Bullish divergence: price making lower lows, indicator making higher lows
        price_trend = recent_data.iloc[-1] < recent_data.iloc[0]
        indicator_trend = recent_indicator.iloc[-1] > recent_indicator.iloc[0]
        bullish_div = price_trend and indicator_trend
        
        # Bearish divergence: price making higher highs, indicator making lower highs
        price_trend_up = recent_data.iloc[-1] > recent_data.iloc[0]
        indicator_trend_down = recent_indicator.iloc[-1] < recent_indicator.iloc[0]
        bearish_div = price_trend_up and indicator_trend_down
        
        return {'bullish': bullish_div, 'bearish': bearish_div}