import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.data_provider import StockDataClient
from strategy.strategy import GridTStrategy
from backtest.backtester import Backtester
from utils.i18n import get_text

# Configuration
st.set_page_config(page_title="Quantitative Stock T+0 Dashboard", layout="wide")

# Language Selection
if 'lang' not in st.session_state:
    st.session_state.lang = 'zh'

# Sidebar
st.sidebar.header(get_text("sidebar_header", st.session_state.lang))

# Language Toggle in Sidebar
lang_choice = st.sidebar.radio("Language / 语言", ["中文", "English"], 
                              index=0 if st.session_state.lang == 'zh' else 1)
st.session_state.lang = 'zh' if lang_choice == "中文" else 'en'
L = st.session_state.lang

symbol = st.sidebar.text_input(get_text("symbol_label", L), "600036")

period_options = {
    get_text("daily", L): "daily",
    get_text("weekly", L): "weekly"
}
selected_period_text = st.sidebar.selectbox(get_text("period_label", L), list(period_options.keys()))
period = period_options[selected_period_text]

interval = st.sidebar.selectbox(get_text("interval_label", L), ["1d", "60m", "15m", "5m"], index=0)

adjust_options = {
    get_text("adjust_qfq", L): "qfq",
    get_text("adjust_hfq", L): "hfq",
    get_text("adjust_none", L): ""
}
selected_adjust_text = st.sidebar.selectbox(get_text("adjust_label", L), list(adjust_options.keys()))
adjust = adjust_options[selected_adjust_text]

st.sidebar.subheader(get_text("params_header", L))
ema_long = st.sidebar.slider(get_text("ema_long", L), 30, 200, 60)
ema_mid = st.sidebar.slider(get_text("ema_mid", L), 5, 50, 20)
rsi_low = st.sidebar.slider(get_text("rsi_low", L), 10, 40, 30)
rsi_high = st.sidebar.slider(get_text("rsi_high", L), 60, 90, 70)
bb_std = st.sidebar.slider(get_text("bb_std", L), 1.0, 3.0, 2.0, 0.1)

# Initialize Client
client = StockDataClient()
strategy = GridTStrategy(ema_long=ema_long, ema_mid=ema_mid, rsi_low=rsi_low, rsi_high=rsi_high, bb_std=bb_std)

# Fetch Data
with st.spinner(get_text("fetching_data", L)):
    df = client.get_history(symbol, period=period, interval=interval, adjust=adjust)
    if not df.empty:
        df = strategy.compute_indicators(df)

# Main Dashboard
st.title(f"{get_text('title', L)}: {symbol}")

if df.empty:
    st.error(get_text("no_data", L))
else:
    # Real-time Signal Section
    col1, col2, col3 = st.columns(3)
    latest_close = df['close'].iloc[-1]
    signal = strategy.check_signals(df)
    
    col1.metric(get_text("current_price", L), f"{latest_close:.2f}")
    
    # Translate signal action and reason
    action_text = get_text(signal.action, L)
    reason_text = signal.reason
    if L == 'zh':
        reason_text = reason_text.replace("Price", "价格").replace("BB Lower", "布林带下轨").replace("BB Upper", "布林带上轨")
        if "Insufficient data" in reason_text:
            reason_text = get_text("insufficient_data", L)
            
    col2.metric(get_text("signal", L), action_text)
    col3.metric(get_text("signal_reason", L), reason_text)

    # Visualization
    st.subheader(get_text("interactive_chart", L))
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(x=df.index,
                    open=df['open'], high=df['high'],
                    low=df['low'], close=df['close'], name=get_text("market_data", L)))
    
    # Indicators
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_long'], name=get_text("ema_long", L), line=dict(color='orange')))
    fig.add_trace(go.Scatter(x=df.index, y=df['ema_mid'], name=get_text("ema_mid", L), line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df.index, y=df['bb_upper'], name=f"{get_text('bb_std', L)} Upper", line=dict(dash='dash', color='gray')))
    fig.add_trace(go.Scatter(x=df.index, y=df['bb_lower'], name=f"{get_text('bb_std', L)} Lower", line=dict(dash='dash', color='gray')))
    
    fig.update_layout(xaxis_rangeslider_visible=False, height=600)
    st.plotly_chart(fig, use_container_width=True)

    # Backtest Section
    st.subheader(get_text("backtest_header", L))
    if st.button(get_text("run_backtest", L)):
        tester = Backtester()
        res = tester.run(df, strategy)
        
        # Display Metrics
        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
        m_col1.metric(get_text("total_return", L), res.metrics['Total Return'])
        m_col2.metric(get_text("buy_hold_return", L), res.metrics['Buy & Hold Return'])
        m_col3.metric(get_text("max_drawdown", L), res.metrics['Max Drawdown'])
        m_col4.metric(get_text("trade_count", L), res.metrics['Trade Count'])
        m_col5.metric(get_text("final_value", L), res.metrics['Final Value'])
        
        # Equity Curve
        fig_equity = go.Figure()
        fig_equity.add_trace(go.Scatter(x=res.equity_curve.index, y=res.equity_curve, name=get_text("equity_growth", L)))
        fig_equity.update_layout(title=get_text("equity_growth", L), height=400)
        st.plotly_chart(fig_equity, use_container_width=True)
        
        # Trade Log
        st.write(get_text("recent_trades", L))
        # Optional: Localize actions in trades dataframe
        trades_display = res.trades.copy()
        if not trades_display.empty:
            trades_display['action'] = trades_display['action'].apply(lambda x: get_text(x, L))
        st.dataframe(trades_display)

st.sidebar.markdown("---")
st.sidebar.write(get_text("system_status", L))
