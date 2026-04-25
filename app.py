import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import json
import os
from datetime import timedelta, date
from data.data_provider import StockDataClient
from data.trade_storage import RealTradeStorage
from strategy.strategy import GridTStrategy
from backtest.backtester import Backtester
from utils.i18n import get_text

# Configuration
st.set_page_config(page_title="Quantitative Stock T+0 Dashboard", layout="wide")

# Settings Persistence
SETTINGS_FILE = ".stock_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                settings = json.load(f)
                # Migration and defaults
                if "symbol" in settings and "symbols_history" not in settings:
                    settings["symbols_history"] = [settings["symbol"]]
                if "current_cash" not in settings:
                    settings["current_cash"] = 100000.0
                if "current_shares" not in settings:
                    settings["current_shares"] = {}
                elif isinstance(settings["current_shares"], (int, float)):
                    # Migrate old single-value format to dict
                    settings["current_shares"] = {}
                return settings
        except Exception:
            pass
    return {"symbols_history": ["600036"], "current_cash": 100000.0, "current_shares": {}}

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings, f)
    except Exception:
        pass

settings = load_settings()
history = settings.get("symbols_history", ["600036"])

# Language Selection
if 'lang' not in st.session_state:
    st.session_state.lang = 'zh'

# Sidebar
st.sidebar.header(get_text("sidebar_header", st.session_state.lang))

# Portfolio Settings
L = st.session_state.lang 
st.sidebar.subheader(get_text("portfolio_header", L))
user_cash = st.sidebar.number_input(get_text("current_cash", L), value=float(settings.get("current_cash", 100000.0)), step=1000.0, key="user_cash")

# Language Toggle in Sidebar
lang_choice = st.sidebar.radio("Language / 语言", ["中文", "English"], 
                              index=0 if st.session_state.lang == 'zh' else 1)
st.session_state.lang = 'zh' if lang_choice == "中文" else 'en'
L = st.session_state.lang

# Persist all inputs using 'key'
if 'symbol' not in st.session_state:
    st.session_state.symbol = history[0] if history else "600036"

symbol = st.sidebar.selectbox(
    get_text("symbol_label", L),
    options=history,
    index=0 if history else None,
    key="symbol",
    accept_new_options=True
)

# Stock-specific shares input (must come AFTER symbol selection)
all_shares = settings.get("current_shares", {})
current_symbol_shares = all_shares.get(symbol, 0)
user_shares = st.sidebar.number_input(f"{get_text('current_shares', L)} ({symbol})", value=int(current_symbol_shares), step=100, key="user_shares")

# Update settings if changed
if user_cash != settings.get("current_cash") or user_shares != current_symbol_shares:
    settings["current_cash"] = user_cash
    all_shares[symbol] = user_shares
    settings["current_shares"] = all_shares
    save_settings(settings)

# Update history if symbol is new or not at the front
if symbol and (not history or history[0] != symbol):
    if symbol in history:
        history.remove(symbol)
    history.insert(0, symbol)
    history = history[:10]  # Keep max 10
    settings["symbols_history"] = history
    save_settings(settings)

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
    options=["qfq", "hfq", None],
    format_func=lambda x: get_text(f"adjust_{x}" if x else "adjust_none", L),
    key="adjust"
)

display_range = st.sidebar.selectbox(
    get_text("display_range_label", L),
    options=["3m", "6m", "1y", "all"],
    index=0,
    format_func=lambda x: get_text(x, L),
    key="display_range"
)


st.sidebar.subheader(get_text("params_header", L))
ema_long = st.sidebar.slider(get_text("ema_long", L), 30, 200, 60, key="ema_long")
ema_mid = st.sidebar.slider(get_text("ema_mid", L), 5, 50, 20, key="ema_mid")
rsi_low = st.sidebar.slider(get_text("rsi_low", L), 10, 40, 30, key="rsi_low")
rsi_high = st.sidebar.slider(get_text("rsi_high", L), 60, 90, 70, key="rsi_high")
bb_std = st.sidebar.slider(get_text("bb_std", L), 1.0, 3.0, 1.3, 0.1, key="bb_std")

strategy_mode = st.sidebar.selectbox(
    get_text("strategy_mode", L),
    options=["standard", "aggressive"],
    index=1,
    format_func=lambda x: get_text(f"mode_{x}", L),
    key="strategy_mode"
)

# Initialize Client & Storage
client = StockDataClient()
trade_storage = RealTradeStorage()
strategy = GridTStrategy(
    ema_long=ema_long, 
    ema_mid=ema_mid, 
    rsi_low=rsi_low, 
    rsi_high=rsi_high, 
    bb_std=bb_std, 
    mode=strategy_mode
)

# Tabs
tab1, tab2, tab3 = st.tabs([get_text("tab_dashboard", L), get_text("tab_strategy", L), get_text("tab_trade_log", L)])

with tab1:
    # Fetch Data
    with st.spinner(get_text("fetching_data", L)):
        df = client.get_history(symbol, period=period, interval=interval, adjust=adjust)
        if not df.empty:
            df = strategy.compute_indicators(df)
            df = strategy.generate_signals(df)

    # Main Dashboard
    st.title(f"{get_text('title', L)}: {symbol}")

    if df.empty:
        st.error(get_text("no_data", L))
    else:
        # Real-time Signal Section
        col1, col2, col3 = st.columns([1, 1, 1])
        latest_close = df['close'].iloc[-1]
        signal = strategy.check_signals(df)
        
        with col1:
            st.metric(get_text("current_price", L), f"{latest_close:.2f}")
            st.write(f"**{get_text('signal_reason', L)}**")
            # Translate signal reason
            reason_text = signal.reason
            if L == 'zh' and "Insufficient data" in reason_text:
                reason_text = get_text("insufficient_data", L)
            st.caption(reason_text)
            
        with col2:
            action_text = get_text(signal.action, L)
            st.metric(get_text("signal", L), action_text)
            if signal.action == 'BUY':
                st.error(get_text("BUY", L))
            elif signal.action == 'SELL':
                st.success(get_text("SELL", L))
            else:
                st.info(get_text("HOLD", L))

        with col3:
            st.markdown(f"### {get_text('execution_advice', L)}")
            if signal.action == 'BUY':
                # Round to nearest 100 shares
                max_buy = (user_cash // (latest_close * 100)) * 100
                if max_buy >= 100:
                    st.write(f"✅ {get_text('action_ready', L)}")
                    st.metric(get_text("can_buy", L), f"{max_buy:,.0f}")
                else:
                    st.warning(get_text("insufficient_cash_exec", L))
            elif signal.action == 'SELL':
                if user_shares >= 100:
                    st.write(f"✅ {get_text('action_ready', L)}")
                    st.metric(get_text("can_sell", L), f"{user_shares:,.0f}")
                else:
                    st.warning(get_text("no_shares_exec", L))
            else:
                st.write("☕ " + get_text("HOLD", L))

        # Visualization
        st.subheader(get_text("interactive_chart", L))
        
        # Filter for display based on selection
        if display_range == "3m":
            delta = timedelta(days=90)
        elif display_range == "6m":
            delta = timedelta(days=180)
        elif display_range == "1y":
            delta = timedelta(days=365)
        else: # "all"
            delta = None
            
        if delta:
            display_start = date.today() - delta
            df_display = df[df.index.date >= display_start]
            if df_display.empty:
                df_display = df.tail(60)
        else:
            df_display = df

        fig = go.Figure()
        
        # Candlestick
        fig.add_trace(go.Candlestick(x=df_display.index,
                        open=df_display['open'], high=df_display['high'],
                        low=df_display['low'], close=df_display['close'], name=get_text("market_data", L)))
        
        # Indicators
        fig.add_trace(go.Scatter(x=df_display.index, y=df_display['ema_long'], name=get_text("ema_long", L), line=dict(color='orange')))
        fig.add_trace(go.Scatter(x=df_display.index, y=df_display['ema_mid'], name=get_text("ema_mid", L), line=dict(color='blue')))
        fig.add_trace(go.Scatter(x=df_display.index, y=df_display['bb_upper'], name=f"{get_text('bb_std', L)} Upper", line=dict(dash='dash', color='gray')))
        fig.add_trace(go.Scatter(x=df_display.index, y=df_display['bb_lower'], name=f"{get_text('bb_std', L)} Lower", line=dict(dash='dash', color='gray')))
        
        # Signals
        buys = df_display[df_display['signal'] == 'BUY']
        sells = df_display[df_display['signal'] == 'SELL']
        
        if not buys.empty:
            fig.add_trace(go.Scatter(
                x=buys.index, 
                y=buys['low'] * 0.98,
                mode='markers',
                name=get_text("BUY", L),
                marker=dict(symbol='triangle-up', size=12, color='red', line=dict(width=1, color='DarkSlateGrey'))
            ))
            
        if not sells.empty:
            fig.add_trace(go.Scatter(
                x=sells.index, 
                y=sells['high'] * 1.02,
                mode='markers',
                name=get_text("SELL", L),
                marker=dict(symbol='triangle-down', size=12, color='green', line=dict(width=1, color='DarkSlateGrey'))
            ))
        
        fig.update_layout(xaxis_rangeslider_visible=False, height=600)
        st.plotly_chart(fig, use_container_width=True)

        # Backtest Section
        st.subheader(get_text("backtest_header", L))
        
        # Start Date Selection for Backtest
        min_date = df.index.min().date()
        max_date = df.index.max().date()
        # Default backtest to last 3 months
        default_start = max(min_date, date.today() - timedelta(days=90))
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

with tab2:
    if os.path.exists("STRATEGY.md"):
        with open("STRATEGY.md", "r", encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)
    else:
        st.write("Strategy documentation not found.")

with tab3:
    st.header(get_text("tab_trade_log", L))
    
    # Form to add new trade
    with st.expander(get_text("record_trade", L), expanded=True):
        with st.form("new_trade_form"):
            f_col1, f_col2, f_col3 = st.columns(3)
            t_date = f_col1.date_input(get_text("trade_date", L), value=date.today())
            t_symbol = f_col2.text_input(get_text("trade_symbol", L), value=symbol)
            t_action = f_col3.selectbox(get_text("trade_action", L), options=["BUY", "SELL"])
            
            f_col4, f_col5, f_col6 = st.columns(3)
            t_price = f_col4.number_input(get_text("trade_price", L), min_value=0.01, step=0.01)
            t_qty = f_col5.number_input(get_text("trade_qty", L), min_value=100, value=100, step=100)
            t_notes = f_col6.text_input(get_text("trade_notes", L))
            
            submit_trade = st.form_submit_button(get_text("save_trade", L))
            
            if submit_trade:
                trade_storage.add_trade(t_date.isoformat(), t_symbol, t_action, t_price, t_qty, t_notes)
                st.success(f"{get_text('save_trade', L)} ✅")
                # No rerun needed for simple log, but good for refresh
                st.rerun()

    # Display Trade History
    st.subheader(get_text("trade_history", L))
    history_df = trade_storage.get_trades()
    if not history_df.empty:
        # Localize column names
        disp_history = history_df.copy()
        column_mapping = {
            'date': get_text("col_date", L),
            'symbol': get_text("trade_symbol", L),
            'action': get_text("trade_action", L),
            'price': get_text("trade_price", L),
            'qty': get_text("trade_qty", L),
            'amount': get_text("col_amount", L),
            'notes': get_text("trade_notes", L)
        }
        disp_history = disp_history.rename(columns=column_mapping)
        
        # Display with coloring
        def color_trades(row):
            action_col = get_text("trade_action", L)
            if row[action_col] == 'BUY':
                return ['background-color: rgba(255, 0, 0, 0.1)'] * len(row)
            elif row[action_col] == 'SELL':
                return ['background-color: rgba(0, 255, 0, 0.1)'] * len(row)
            return [''] * len(row)

        st.dataframe(disp_history.style.apply(color_trades, axis=1), use_container_width=True)
        
        # Simple deletion UI
        with st.expander("Admin: Delete Trade"):
            del_id = st.number_input("Trade ID to delete", min_value=1, step=1)
            if st.button(get_text("confirm_delete", L)):
                trade_storage.delete_trade(del_id)
                st.rerun()
    else:
        st.info("No trades recorded yet.")

st.sidebar.markdown("---")
st.sidebar.write(get_text("system_status", L))
