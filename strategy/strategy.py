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

        # Standardize mode logic to avoid duplication
        signals_df = self.generate_signals(df.tail(self.ema_long + 1))
        if signals_df.empty:
             return TradingSignal('HOLD', close, "Insufficient data")

        latest_signal = signals_df.iloc[-1]
        action = latest_signal['signal']

        # Reconstruct reason for UI
        if action == 'BUY':
            if self.mode == "aggressive":
                 reason = f"Agg: close({close:.2f}) < BBL({latest['bb_lower']:.2f}) or RSI({latest['rsi']:.1f}) < {self.rsi_low+5:.0f}"
            else:
                 reason = f"Std: close({close:.2f}) < BBL({latest['bb_lower']:.2f}) & RSI({latest['rsi']:.1f}) < {self.rsi_low:.0f}"
        elif action == 'SELL':
            if self.mode == "aggressive":
                 reason = f"Agg: close({close:.2f}) > BBU({latest['bb_upper']:.2f}) or RSI({latest['rsi']:.1f}) > {self.rsi_high-5:.0f}"
            else:
                 reason = f"Std: close({close:.2f}) > BBU({latest['bb_upper']:.2f}) & RSI({latest['rsi']:.1f}) > {self.rsi_high:.0f}"
        else:
            reason = "Neutral conditions"

        return TradingSignal(action, close, reason)

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Vectorized or efficient signal generation for the entire dataframe.
        Returns a dataframe with a 'signal' column ('BUY', 'SELL', 'HOLD').
        """
        if df.empty:
            return df

        df = df.copy()
        df['signal'] = 'HOLD'

        if self.mode == "aggressive":
            buy_cond = (df['close'] < df['bb_lower']) | ((df['close'] < df['ema_mid']) & (df['rsi'] < self.rsi_low + 5))
            sell_cond = (df['close'] > df['bb_upper']) | ((df['close'] > df['ema_mid']) & (df['rsi'] > self.rsi_high - 5))
        else:
            buy_cond = (df['close'] < df['bb_lower']) & (df['rsi'] < self.rsi_low)
            sell_cond = (df['close'] > df['bb_upper']) & (df['rsi'] > self.rsi_high)

        df.loc[buy_cond, 'signal'] = 'BUY'
        df.loc[sell_cond, 'signal'] = 'SELL'

        return df


if __name__ == "__main__":
    from data.data_provider import StockDataClient
    client = StockDataClient()
    df = client.get_history("AAPL")
    strategy = GridTStrategy()
    df_with_inds = strategy.compute_indicators(df)
    signal = strategy.check_signals(df_with_inds)
    print(f"Latest Close: {df.iloc[-1]['close']}")
    print(f"Action: {signal.action}, Reason: {signal.reason}")
