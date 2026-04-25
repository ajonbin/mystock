# Quantitative Stock T+0 System (做T工具)

A quantitative trading system designed for single-stock intraday/swing trading (做T), featuring mean-reversion strategies, incremental data caching, and an interactive dashboard.

## Features
- **Multi-Source Data**: Fetches historical and real-time data from **AkShare** (A-shares) and **yfinance** (US/Global).
- **Incremental Caching**: Uses a local **SQLite** database to store historical data, fetching only missing increments from the network to ensure fast startup.
- **Dual Strategy Modes**:
    - **Standard**: Strict conditions (AND logic) for conservative trading.
    - **Aggressive**: Looser conditions (OR logic) to maintain activity during trends.
- **Realistic Backtesting**: 
    - Simulates "Core + Trading" position management.
    - Enforces **100-share lot size** and minimum trade units.
    - Strictly **cash-limited** buying power simulation.
    - Support for custom start dates.
- **Multilingual Support**: Full UI support for **Simplified Chinese** (default) and **English**.
- **Unified Price Adjustment**: User-selectable price adjustment (QFQ/HFQ/None) applied consistently across charts and backtests.

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Dashboard**:
   ```bash
   streamlit run app.py
   ```

## Project Structure
- `app.py`: Main Streamlit application and UI logic.
- `data/`: 
    - `data_provider.py`: Logic for fetching data from network APIs.
    - `storage.py`: SQLite-based local caching layer.
- `strategy/`: 
    - `strategy.py`: Technical indicator calculation (via `pandas_ta`) and signal generation.
- `backtest/`: 
    - `backtester.py`: Loop-based trade simulation and performance metrics.
- `utils/`: 
    - `i18n.py`: Internationalization support.

## Strategy & Signals
For a detailed explanation of strategy parameters, signal triggers, and the "Core + Trading" logic, please refer to:
- [**STRATEGY.md**](./STRATEGY.md) (Detailed Strategy Guide)

## Strategy Logic (Summary)
- **Standard Mode**:
    - **Buy**: Price < Bollinger Lower Band **AND** RSI < Oversold Threshold.
    - **Sell**: Price > Bollinger Upper Band **AND** RSI > Overbought Threshold.
- **Aggressive Mode**:
    - **Buy**: Price < Bollinger Lower Band **OR** (Price < EMA20 **AND** RSI < Oversold+5).
    - **Sell**: Price > Bollinger Upper Band **OR** (Price > EMA20 **AND** RSI > Overbought-5).
- **Risk Control**: Long-term trend filtering using EMA60.
