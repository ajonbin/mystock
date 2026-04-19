import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.data_provider import StockDataClient
from strategy.strategy import GridTStrategy
from backtest.backtester import Backtester

# Configuration
st.set_page_config(page_title="Quantitative Stock T+0 Dashboard", layout="wide")

# Sidebar
st.sidebar.header("Strategy Settings")
symbol = st.sidebar.text_input("Stock Symbol (e.g., 600036 or AAPL)", "600036")
period = st.sidebar.selectbox("Period", ["daily", "weekly"])
interval = st.sidebar.selectbox("Interval", ["1d", "60m", "15m", "5m"], index=0)

st.sidebar.subheader("Parameters")
ema_long = st.sidebar.slider("EMA Long", 30, 200, 60)
ema_mid = st.sidebar.slider("EMA Mid", 5, 50, 20)
rsi_low = st.sidebar.slider("RSI Oversold", 10, 40, 30)
rsi_high = st.sidebar.slider("RSI Overbought", 60, 90, 70)
bb_std = st.sidebar.slider("BB Std Dev", 1.0, 3.0, 2.0, 0.1)

# Initialize Client
client = StockDataClient()
strategy = GridTStrategy(ema_long=ema_long, ema_mid=ema_mid, rsi_low=rsi_low, rsi_high=rsi_high, bb_std=bb_std)

# Fetch Data
with st.spinner("Fetching data..."):
    df = client.get_history(symbol, period=period, interval=interval)
    if not df.empty:
        df = strategy.compute_indicators(df)

# Main Dashboard
st.title(f"Quantitative Doing T System: {symbol}")

if df.empty:
    st.error("No data found for the selected symbol.")
else:
    # Real-time Signal Section
    col1, col2, col3 = st.columns(3)
    latest_close = df['close'].iloc[-1]
    signal = strategy.check_signals(df)
    
    col1.metric("Current Price", f"{latest_close:.2f}")
    col2.metric("Signal", signal.action)
    col3.metric("Signal Reason", signal.reason)

    # Visualization
    st.subheader("Interactive Price & Indicators")
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(x=df.index,
                    open=df['open'], high=df['high'],
                    low=df['low'], close=df['close'], name="Market Data"))
    
    # Indicators
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_long'], name="EMA Long", line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_mid'], name="EMA Mid", line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['bb_upper'], name="BB Upper", line=dict(dash='dash', color='gray')))
    fig.add_trace(go.Scatter(x=df.index, y=df['bb_lower'], name="BB Lower", line=dict(dash='dash', color='gray')))
    
    fig.update_layout(xaxis_rangeslider_visible=False, height=600)
    st.plotly_chart(fig, use_container_width=True)

    # Backtest Section
    st.subheader("Strategy Backtest (Core + Trading)")
    if st.button("Run Full Backtest"):
        tester = Backtester()
        res = tester.run(df, strategy)
        
        # Display Metrics
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("Total Return", res.metrics['Total Return'])
        m_col2.metric("Buy & Hold", res.metrics['Buy & Hold Return'])
        m_col3.metric("Max Drawdown", res.metrics['Max Drawdown'])
        m_col4.metric("Trade Count", res.metrics['Trade Count'])
        
        # Equity Curve
        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(x=res.equity_curve.index, y=res.equity_curve, name="Strategy Equity"))
        fig_equity.update_layout(title="Equity Growth (Initial 100k)", height=400)
        st.plotly_chart(fig_equity, use_container_width=True)
        
        # Trade Log
        st.write("Recent Trades:")
        st.dataframe(res.trades.tail(10))

st.sidebar.markdown("---")
st.sidebar.write("System Status: Online")
