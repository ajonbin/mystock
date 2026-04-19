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
    def __init__(self, core_ratio=0.5, initial_cash=10000):
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
        core_qty = (core_cash // (first_price * 100)) * 100
        
        if core_qty > 0:
            core_pos = core_qty
            actual_core_cash = core_qty * first_price
            cash -= actual_core_cash
            trades.append({
                'date': df.index[0], 
                'action': 'BUY', 
                'price': first_price, 
                'qty': core_pos,
                'amount': actual_core_cash,
                'cash_left': cash,
                'total_qty': core_pos
            })
        
        # Trading Loop
        for i in range(len(df)):
            row = df.iloc[i]
            price = row['close']
            
            # Skip invalid prices (can happen with QFQ on old data)
            if price <= 0:
                total_value = cash + (core_pos + trading_pos) * price
                equity.append(total_value)
                continue
            signal = 'HOLD'
            if row['close'] < row['bb_lower'] and row['rsi'] < strategy.rsi_low:
                signal = 'BUY'
            elif row['close'] > row['bb_upper'] and row['rsi'] > strategy.rsi_high:
                signal = 'SELL'
            
            # Execute Trading Portion
            if signal == 'BUY' and cash > 0:
                # Buy trading position using a percentage of total equity
                # Aim to use ~20% of total current value for each trade if possible
                target_buy_amt = total_value * 0.2
                # But don't exceed current cash
                buy_amt_limit = min(target_buy_amt, cash)
                
                # Enforce lot size: n*100, min 100
                buy_qty = (buy_amt_limit // (price * 100)) * 100
                
                if buy_qty >= 100:
                    trading_pos += buy_qty
                    actual_buy_amt = buy_qty * price
                    cash -= actual_buy_amt
                    trades.append({
                        'date': df.index[i], 
                        'action': 'BUY', 
                        'price': price, 
                        'qty': buy_qty,
                        'amount': actual_buy_amt,
                        'cash_left': cash,
                        'total_qty': core_pos + trading_pos
                    })
            elif signal == 'SELL' and trading_pos > 0:
                # Sell all trading position
                sell_amt = trading_pos * price
                cash += sell_amt
                trades.append({
                    'date': df.index[i], 
                    'action': 'SELL', 
                    'price': price, 
                    'qty': trading_pos,
                    'amount': sell_amt,
                    'cash_left': cash,
                    'total_qty': core_pos # After selling all trading pos, only core remains
                })
                trading_pos = 0
                
            total_value = cash + (core_pos + trading_pos) * price
            equity.append(total_value)
            
        equity_curve = pd.Series(equity, index=df.index)
        
        # Metrics
        final_equity = equity_curve.iloc[-1]
        total_return = (final_equity / self.initial_cash) - 1
        bh_return = (df['close'].iloc[-1] / df['close'].iloc[0]) - 1
        max_drawdown = (equity_curve / equity_curve.cummax() - 1).min()
        
        final_price = df['close'].iloc[-1]
        metrics = {
            'Total Return': f"{total_return:.2%}",
            'Buy & Hold Return': f"{bh_return:.2%}",
            'Max Drawdown': f"{max_drawdown:.2%}",
            'Final Value': f"{final_equity:.2f}",
            'Trade Count': len(trades),
            'Cash': f"{cash:.2f}",
            'Core Value': f"{core_pos * final_price:.2f}",
            'Trading Value': f"{trading_pos * final_price:.2f}"
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
