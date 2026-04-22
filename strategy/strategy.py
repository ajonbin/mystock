import pandas as pd
import pandas_ta as ta
import numpy as np

class TradingSignal:
    def __init__(self, action, price, reason):
        self.action = action  # 'BUY', 'SELL', 'HOLD'
        self.price = price
        self.reason = reason

class GridTStrategy:
    """
    Mean-reversion strategy based on technical indicators and dynamic grid adjustment.
    """
    def __init__(self, 
                 ema_long=60, 
                 ema_mid=20, 
                 rsi_low=30, 
                 rsi_high=70, 
                 bb_std=2, 
                 atr_period=14,
                 k_atr=1.5,
                 mode="standard"):
        self.ema_long = ema_long
        self.ema_mid = ema_mid
        self.rsi_low = rsi_low
        self.rsi_high = rsi_high
        self.bb_std = bb_std
        self.atr_period = atr_period
        self.k_atr = k_atr
        self.mode = mode

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute required technical indicators using pandas_ta.
        """
        if df.empty:
            return df
            
        # Ensure column names are lowercase for pandas_ta
        df.columns = [c.lower() for c in df.columns]
        
        # EMA
        df['ema_long'] = ta.ema(df['close'], length=self.ema_long)
        df['ema_mid'] = ta.ema(df['close'], length=self.ema_mid)
        
        # RSI
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        # ATR
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=self.atr_period)
        
        # Bollinger Bands
        bb = ta.bbands(df['close'], length=self.ema_mid, lower_std=self.bb_std, upper_std=self.bb_std)
        if bb is not None:
            df['bb_lower'] = bb.iloc[:, 0]
            df['bb_upper'] = bb.iloc[:, 2]
        else:
            # Fallback or empty if calculation fails
            df['bb_lower'] = np.nan
            df['bb_upper'] = np.nan
        
        # Hurst Exponent (Approximate calculation using rolling window)
        # Note: Hurst is complex, for prototype we focus on indicators
        
        return df

    def check_signals(self, df: pd.DataFrame) -> TradingSignal:
        """
        Check for signals based on the latest data row.
        """
        if df.empty or len(df) < self.ema_long:
            return TradingSignal('HOLD', 0, "Insufficient data")

        latest = df.iloc[-1]
        close = latest['close']
        
        # Trend Filter (EMA60)
        is_uptrend = close > latest['ema_long']
        
        if self.mode == "aggressive":
            # Aggressive Mode: OR condition, looser thresholds
            # Buy Signal (T+ In): Price < BB Lower OR (Price < EMA20 AND RSI < 35)
            if (close < latest['bb_lower']) or (close < latest['ema_mid'] and latest['rsi'] < self.rsi_low + 5):
                reason = f"Agg: close({close:.2f}) < BBL({latest['bb_lower']:.2f}) or RSI({latest['rsi']:.1f}) < {self.rsi_low+5:.0f}"
                return TradingSignal('BUY', close, reason)
                
            # Sell Signal (T+ Out): Price > BB Upper OR (Price > EMA20 AND RSI > 65)
            if (close > latest['bb_upper']) or (close > latest['ema_mid'] and latest['rsi'] > self.rsi_high - 5):
                reason = f"Agg: close({close:.2f}) > BBU({latest['bb_upper']:.2f}) or RSI({latest['rsi']:.1f}) > {self.rsi_high-5:.0f}"
                return TradingSignal('SELL', close, reason)
        else:
            # Standard Mode: Strict AND condition
            if close < latest['bb_lower'] and latest['rsi'] < self.rsi_low:
                reason = f"Std: close({close:.2f}) < BBL({latest['bb_lower']:.2f}) & RSI({latest['rsi']:.1f}) < {self.rsi_low:.0f}"
                return TradingSignal('BUY', close, reason)
                
            if close > latest['bb_upper'] and latest['rsi'] > self.rsi_high:
                reason = f"Std: close({close:.2f}) > BBU({latest['bb_upper']:.2f}) & RSI({latest['rsi']:.1f}) > {self.rsi_high:.0f}"
                return TradingSignal('SELL', close, reason)
            
        return TradingSignal('HOLD', close, "Neutral conditions")

if __name__ == "__main__":
    from data.data_provider import StockDataClient
    client = StockDataClient()
    df = client.get_history("AAPL")
    strategy = GridTStrategy()
    df_with_inds = strategy.compute_indicators(df)
    signal = strategy.check_signals(df_with_inds)
    print(f"Latest Close: {df.iloc[-1]['close']}")
    print(f"Action: {signal.action}, Reason: {signal.reason}")
