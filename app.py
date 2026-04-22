import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta, date
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

# Persist all inputs using 'key'
symbol = st.sidebar.text_input(get_text("symbol_label", L), value="600036", key="symbol")

period = st.sidebar.selectbox(
    get_text("period_label", L), 
    options=["daily", "weekly"], 
    format_func=lambda x: get_text(x, L),
    key="period"
)

interval = st.sidebar.selectbox(
    get_text("interval_label", L), 
    ["1d", "60m", "15m", "5m"], 
    index=0,
    key="interval"
)

adjust = st.sidebar.selectbox(
    get_text("adjust_label", L),
    options=["qfq", "hfq", ""],
    format_func=lambda x: get_text(f"adjust_{x}" if x else "adjust_none", L),
    key="adjust"
)

st.sidebar.subheader(get_text("params_header", L))
ema_long = st.sidebar.slider(get_text("ema_long", L), 30, 200, 60, key="ema_long")
ema_mid = st.sidebar.slider(get_text("ema_mid", L), 5, 50, 20, key="ema_mid")
rsi_low = st.sidebar.slider(get_text("rsi_low", L), 10, 40, 30, key="rsi_low")
rsi_high = st.sidebar.slider(get_text("rsi_high", L), 60, 90, 70, key="rsi_high")
bb_std = st.sidebar.slider(get_text("bb_std", L), 1.0, 3.0, 2.0, 0.1, key="bb_std")

strategy_mode = st.sidebar.selectbox(
    get_text("strategy_mode", L),
    options=["standard", "aggressive"],
    format_func=lambda x: get_text(f"mode_{x}", L),
    key="strategy_mode"
)

# Initialize Client
client = StockDataClient()
strategy = GridTStrategy(
    ema_long=ema_long, 
    ema_mid=ema_mid, 
    rsi_low=rsi_low, 
    rsi_high=rsi_high, 
    bb_std=bb_std, 
    mode=strategy_mode
)

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
    col1, col2 = st.columns([1, 2])
    latest_close = df['close'].iloc[-1]
    signal = strategy.check_signals(df)
    
    with col1:
        m1, m2 = st.columns(2)
        m1.metric(get_text("current_price", L), f"{latest_close:.2f}")
        action_text = get_text(signal.action, L)
        m2.metric(get_text("signal", L), action_text)
    
    with col2:
        # Translate signal reason
        reason_text = signal.reason
        if L == 'zh' and "Insufficient data" in reason_text:
            reason_text = get_text("insufficient_data", L)
        
        st.markdown(f"**{get_text('signal_reason', L)}**")
        st.info(reason_text)

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
    
    # Start Date Selection for Backtest
    min_date = df.index.min().date()
    max_date = df.index.max().date()
    default_start = max(min_date, date(2000, 1, 1))
    bt_start_date = st.date_input(get_text("backtest_start_date", L), value=default_start, min_value=min_date, max_value=max_date, key="bt_start_date")

    if st.button(get_text("run_backtest", L)):
        # Use the user-selected 'adjust' setting for the backtest
        bt_df = df.copy()
        
        if not bt_df.empty:
            tester = Backtester()
            res = tester.run(bt_df, strategy, start_date=bt_start_date)
            
            if res.trades.empty:
                st.warning(get_text("insufficient_capital", L))
            else:
                # Display Metrics
                st.write("---")
                m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
                m_col1.metric(get_text("total_return", L), res.metrics['Total Return'])
                m_col2.metric(get_text("buy_hold_return", L), res.metrics['Buy & Hold Return'])
                m_col3.metric(get_text("max_drawdown", L), res.metrics['Max Drawdown'])
                m_col4.metric(get_text("trade_count", L), res.metrics['Trade Count'])
                m_col5.metric(get_text("final_value", L), res.metrics['Final Value'])

                # Breakdown Row
                b_col1, b_col2, b_col3, b_col4 = st.columns(4)
                b_col1.metric(get_text("metric_cash", L), res.metrics['Cash'])
                b_col2.metric(get_text("metric_core", L), res.metrics['Core Value'])
                b_col3.metric(get_text("metric_trading", L), res.metrics['Trading Value'])

                # Equity Curve
                fig_equity = go.Figure()
                fig_equity.add_trace(go.Scatter(x=res.equity_curve.index, y=res.equity_curve, name=get_text("equity_growth", L)))
                fig_equity.update_layout(title=get_text("equity_growth", L), height=400)
                st.plotly_chart(fig_equity, use_container_width=True)

                # Trade Log
                st.write(get_text("recent_trades", L))
                trades_display = res.trades.copy()
                if not trades_display.empty:
                    # Format numeric columns
                    trades_display['price'] = trades_display['price'].map('{:.2f}'.format)
                    trades_display['amount'] = trades_display['amount'].map('{:.2f}'.format)
                    trades_display['cash_left'] = trades_display['cash_left'].map('{:.2f}'.format)
                    trades_display['total_value'] = trades_display['total_value'].map('{:.2f}'.format)
                    trades_display['total_qty'] = trades_display['total_qty'].map('{:.0f}'.format)

                    # Format Quantity with +/-
                    trades_display['qty'] = trades_display.apply(
                        lambda row: f"+{row['qty']:.0f}" if row['action'] == 'BUY' else f"-{row['qty']:.0f}", axis=1
                    )

                    # Localize actions
                    trades_display['action'] = trades_display['action'].apply(lambda x: get_text(x, L))

                    # Localize column headers
                    column_mapping = {
                        'date': get_text("col_date", L),
                        'action': get_text("col_action", L),
                        'price': get_text("col_price", L),
                        'qty': get_text("col_qty", L),
                        'total_qty': get_text("col_total_qty", L),
                        'total_value': get_text("col_total_value", L),
                        'amount': get_text("col_amount", L),
                        'cash_left': get_text("col_cash_left", L)
                    }
                    trades_display = trades_display.rename(columns=column_mapping)

                    # Apply Coloring
                    def color_rows(row):
                        action_col = get_text("col_action", L)
                        if row[action_col] == get_text("BUY", L):
                            return ['background-color: rgba(255, 0, 0, 0.2)'] * len(row)
                        elif row[action_col] == get_text("SELL", L):
                            return ['background-color: rgba(0, 255, 0, 0.2)'] * len(row)
                        return [''] * len(row)

                    styled_trades = trades_display.style.apply(color_rows, axis=1)
                    st.dataframe(styled_trades)

        else:
            st.error(get_text("no_data", L))

st.sidebar.markdown("---")
st.sidebar.write(get_text("system_status", L))
