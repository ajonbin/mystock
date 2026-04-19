import pandas as pd
import akshare as ak
import yfinance as yf
from datetime import datetime, timedelta


class StockDataClient:
    """
    Data client for fetching historical and real-time stock data.
    Supports A-shares (via AkShare) and Global shares (via yfinance).
    """

    @staticmethod
    def get_history(symbol: str, period: str = "daily", interval: str = "1d", start_date: str = None, end_date: str = None) -> pd.DataFrame:

        """
        Fetch historical K-line data.
        :param symbol: Stock symbol (e.g., '600519' for A-shares, 'AAPL' for US shares).
        :param period: 'daily', 'weekly', 'monthly'.
        :param interval: '1m', '5m', '15m', '30m', '60m', '1d', '1wk', '1mo'.
        :param start_date: Format 'YYYYMMDD' for AkShare, 'YYYY-MM-DD' for yfinance.
        :param end_date: Same format as start_date.
        :return: DataFrame with columns [Date, Open, High, Low, Close, Volume].
        """
        if any(char.isalpha() for char in symbol[:3]): # Simple heuristic for non-A-share symbols
            # Use yfinance for non-A-shares
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start_date, end=end_date, interval=interval)
            df.index = df.index.tz_localize(None) # Remove timezone for consistency
            return df
        else:
            # Use AkShare for A-shares
            # Mapping period for AkShare: daily, weekly, monthly
            # Mapping adjust for AkShare: qfq (front-adjusted), hfq (back-adjusted), "" (none)
            try:
                # Passing None for start_date/end_date causes empty DF, only pass if they are provided
                fetch_args = {
                    "symbol": symbol,
                    "period": period,
                    "adjust": "qfq"
                }
                if start_date:
                    fetch_args["start_date"] = start_date
                if end_date:
                    fetch_args["end_date"] = end_date

                df = ak.stock_zh_a_hist(**fetch_args)
                
                if df.empty:
                    print(f"Warning: No A-share data found for {symbol}")
                    return pd.DataFrame()

                # Expected columns: ['日期', '股票代码', '开盘', '收盘', '最高', '最低', '成交量', '成交额', '振幅', '涨跌幅', '涨跌额', '换手率'] (12 columns)
                # Ensure we have the right number of columns
                if len(df.columns) == 12:
                    df.columns = ['Date', 'Symbol', 'Open', 'Close', 'High', 'Low', 'Volume', 'Turnover', 'Amplitude', 'Pct_Change', 'Change_Amount', 'Turnover_Rate']
                elif len(df.columns) == 11:
                    df.columns = ['Date', 'Open', 'Close', 'High', 'Low', 'Volume', 'Turnover', 'Amplitude', 'Pct_Change', 'Change_Amount', 'Turnover_Rate']
                else:
                     print(f"Unexpected column count: {len(df.columns)} for {symbol}")
                     return pd.DataFrame()

                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                return df[['Open', 'High', 'Low', 'Close', 'Volume']]
            except Exception as e:
                print(f"Error fetching A-share data: {e}")
                import traceback
                traceback.print_exc()
                return pd.DataFrame()

    @staticmethod
    def get_realtime_quote(symbol: str) -> dict:
        """
        Fetch real-time quote for a symbol.
        """
        try:
            if any(char.isalpha() for char in symbol[:3]):
                ticker = yf.Ticker(symbol)
                info = ticker.fast_info
                return {
                    'symbol': symbol,
                    'price': info['last_price'],
                    'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                df = ak.stock_zh_a_spot_em()
                if df.empty:
                    return {}
                row = df[df['代码'] == symbol]
                if not row.empty:
                    return {
                        'symbol': symbol,
                        'price': row.iloc[0]['最新价'],
                        'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                return {}
        except Exception as e:
            print(f"Error fetching real-time quote for {symbol}: {e}")
            return {}

if __name__ == "__main__":
    # Quick test
    client = StockDataClient()
    print("Testing yfinance (AAPL)...")
    print(client.get_history("600036", interval="1d").tail())
    # print("Testing AkShare (600519)...")
    # print(client.get_history("600519").tail())
