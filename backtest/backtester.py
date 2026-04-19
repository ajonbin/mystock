import pandas as pd
import numpy as np
import plotly.graph_objects as go
from strategy.strategy import GridTStrategy

class BacktestResult:
    def __init__(self, trades, equity_curve, metrics):
        self.trades = trades
        self.equity_curve = equity_curve
        self.metrics = metrics

class Backtester:
    """
    Simulates a 'Core + Trading' position strategy.
    Core: Static long-term holding.
    Trading: Dynamic buy/sell signals for profit.
    """
    def __init__(self, core_ratio=0.5, initial_cash=100000):
        self.core_ratio = core_ratio
        self.initial_cash = initial_cash

    def run(self, df: pd.DataFrame, strategy: GridTStrategy) -> BacktestResult:
        """
        Execute backtest.
        :param df: Prepared DataFrame with indicators.
        :return: BacktestResult object.
        """
        # Prepare signals for all data points
        # For simplicity, we can't use strategy.check_signals in a loop for every row 
        # because it only checks the latest. We need a vectorized or looped signals list.
        
        # Simple loop-based simulation for 'Core + Trading'
        cash = self.initial_cash
        core_pos = 0
        trading_pos = 0
        total_pos = 0
        equity = []
        trades = []
        
        # Calculate indicators for the whole df
        df = strategy.compute_indicators(df)
        
        # Initial core position (buy at first day)
        first_price = df.iloc[0]['close']
        core_cash = self.initial_cash * self.core_ratio
        core_pos = core_cash / first_price
        cash -= core_cash
        
        # Trading Loop
        for i in range(len(df)):
            row = df.iloc[i]
            price = row['close']
            
            # Simulated Signal (vectorized logic for backtest)
            signal = 'HOLD'
            if row['close'] < row['bb_lower'] and row['rsi'] < strategy.rsi_low:
                signal = 'BUY'
            elif row['close'] > row['bb_upper'] and row['rsi'] > strategy.rsi_high:
                signal = 'SELL'
            
            # Execute Trading Portion
            if signal == 'BUY' and cash > 0:
                # Buy trading position using half of remaining cash
                buy_amt = cash * 0.5
                buy_qty = buy_amt / price
                trading_pos += buy_qty
                cash -= buy_amt
                trades.append({'date': df.index[i], 'action': 'BUY', 'price': price, 'qty': buy_qty})
            elif signal == 'SELL' and trading_pos > 0:
                # Sell all trading position
                sell_amt = trading_pos * price
                cash += sell_amt
                trades.append({'date': df.index[i], 'action': 'SELL', 'price': price, 'qty': trading_pos})
                trading_pos = 0
                
            total_value = cash + (core_pos + trading_pos) * price
            equity.append(total_value)
            
        equity_curve = pd.Series(equity, index=df.index)
        
        # Metrics
        total_return = (equity_curve.iloc[-1] / self.initial_cash) - 1
        bh_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
        max_drawdown = (equity_curve / equity_curve.cummax() - 1).min()
        
        metrics = {
            'Total Return': f"{total_return:.2%}",
            'Buy & Hold Return': f"{bh_return:.2%}",
            'Max Drawdown': f"{max_drawdown:.2%}",
            'Final Value': f"{equity_curve.iloc[-1]:.2f}",
            'Trade Count': len(trades)
        }
        
        return BacktestResult(pd.DataFrame(trades), equity_curve, metrics)

if __name__ == "__main__":
    from data.data_provider import StockDataClient
    client = StockDataClient()
    df = client.get_history("AAPL")
    strategy = GridTStrategy()
    tester = Backtester()
    res = tester.run(df, strategy)
    print(res.metrics)
