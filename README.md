# Quantitative Stock T+0 System (做T工具)

A quantitative trading system designed for single-stock intraday trading (做T), featuring mean-reversion strategy, backtesting, and a real-time dashboard.

## Features
- **Data Layer**: Fetches data from AkShare (A-shares) and yfinance (US/Global).
- **Strategy Layer**: Implements EMA, RSI, ATR, and Bollinger Bands with custom signals.
- **Backtest Engine**: Simulates "Core + Trading" position management.
- **Interactive UI**: Built with Streamlit for easy parameter tuning and visualization.

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
- `app.py`: Main Streamlit application.
- `data/`: Data retrieval logic.
- `strategy/`: Strategy implementation and technical indicators.
- `backtest/`: Performance evaluation and trade simulation.
- `utils/`: Common utilities.

## Strategy Logic
- **Buy (T+ In)**: Price < Bollinger Lower Band AND RSI < 30.
- **Sell (T+ Out)**: Price > Bollinger Upper Band AND RSI > 70.
- **Risk Control**: Trend filtering using EMA60.
