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

    def run(self, df: pd.DataFrame, strategy: GridTStrategy, start_date=None) -> BacktestResult:
        """
        Execute backtest.
        :param df: Prepared DataFrame with indicators (or full history).
        :param start_date: Optional date to begin trading simulation.
        :return: BacktestResult object.
        """
        # Calculate indicators for the whole df to ensure warmup/stability
        df = strategy.compute_indicators(df)
        
        # Filter for trading range if start_date is provided
        if start_date:
            # Handle string or date object
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date).date()
            sim_df = df[df.index.date >= start_date]
        else:
            sim_df = df

        # Filter out invalid prices (can happen with QFQ on old data)
        # Reality check: You can't trade at zero or negative prices
        sim_df = sim_df[sim_df['close'] > 0]

        if sim_df.empty:
            return BacktestResult(pd.DataFrame(), pd.Series(), {})

        # Simple loop-based simulation for 'Core + Trading'
        cash = self.initial_cash
        core_pos = 0
        trading_pos = 0
        total_pos = 0
        equity = []
        trades = []
        
        # Initial core position (buy at first available day in sim_df)
        first_price = sim_df.iloc[0]['close']
        preferred_core_cash = self.initial_cash * self.core_ratio
        
        # Enforce lot size: n*100, min 100. 
        # If preferred amount is less than 100 shares, try to buy at least 100 shares 
        # if it doesn't exceed 80% of total initial cash.
        core_qty = (preferred_core_cash // (first_price * 100)) * 100
        if core_qty < 100 and self.initial_cash * 0.8 >= (first_price * 100):
            core_qty = 100
            
        if core_qty > 0:
            core_pos = core_qty
            actual_core_cash = core_qty * first_price
            cash -= actual_core_cash
            trades.append({
                'date': sim_df.index[0], 
                'action': 'BUY', 
                'price': first_price, 
                'qty': core_pos,
                'amount': actual_core_cash,
                'cash_left': cash,
                'total_qty': core_pos,
                'total_value': cash + core_pos * first_price
            })
        
        # Trading Loop
        signals_df = strategy.generate_signals(sim_df)
        
        for i in range(len(sim_df)):
            row = sim_df.iloc[i]
            price = row['close']
            
            # Current total value
            current_total_value = cash + (core_pos + trading_pos) * price

            # Skip invalid prices
            if price <= 0:
                equity.append(current_total_value)
                continue

            signal = signals_df.iloc[i]['signal']
            
            # Execute Trading Portion
            if signal == 'BUY' and cash > 0:
                # Buy trading position using half of remaining cash (Reality based)
                buy_amt_limit = cash * 0.5
                
                # Ensure we use at least enough for 100 shares if we have it
                if buy_amt_limit < price * 100 and cash >= price * 100:
                    buy_amt_limit = min(price * 100, cash * 0.9)

                # Enforce lot size: n*100, min 100
                buy_qty = (buy_amt_limit // (price * 100)) * 100
                
                if buy_qty >= 100:
                    trading_pos += buy_qty
                    actual_buy_amt = buy_qty * price
                    cash -= actual_buy_amt
                    trades.append({
                        'date': sim_df.index[i], 
                        'action': 'BUY', 
                        'price': price, 
                        'qty': buy_qty,
                        'amount': actual_buy_amt,
                        'cash_left': cash,
                        'total_qty': core_pos + trading_pos,
                        'total_value': cash + (core_pos + trading_pos) * price
                    })
            elif signal == 'SELL' and trading_pos > 0:
                # Sell all trading position
                sell_amt = trading_pos * price
                cash += sell_amt
                trades.append({
                    'date': sim_df.index[i], 
                    'action': 'SELL', 
                    'price': price, 
                    'qty': trading_pos,
                    'amount': sell_amt,
                    'cash_left': cash,
                    'total_qty': core_pos, # After selling all trading pos, only core remains
                    'total_value': cash + core_pos * price
                })
                trading_pos = 0
                
            equity.append(cash + (core_pos + trading_pos) * price)
            
        equity_curve = pd.Series(equity, index=sim_df.index)
        
        # Metrics
        if equity_curve.empty:
             return BacktestResult(pd.DataFrame(), pd.Series(), {})

        final_equity = equity_curve.iloc[-1]
        total_return = (final_equity / self.initial_cash) - 1
        bh_return = (sim_df['close'].iloc[-1] / sim_df['close'].iloc[0]) - 1
        max_drawdown = (equity_curve / equity_curve.cummax() - 1).min()
        
        final_price = sim_df['close'].iloc[-1]
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
