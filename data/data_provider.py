import pandas as pd
import akshare as ak
import yfinance as yf
from datetime import datetime, timedelta
from data.storage import StockStorage


class StockDataClient:
    """
    Data client for fetching historical and real-time stock data.
    Supports A-shares (via AkShare) and Global shares (via yfinance).
    """
    def __init__(self):
        self.storage = StockStorage()

    def get_history(self, symbol: str, period: str = "daily", interval: str = "1d", start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Fetch historical K-line data with local caching.
        """
        # 1. Try to load from local storage
        df_local = self.storage.load_data(symbol, period, interval)
        
        # If specific dates are requested, we might need to bypass cache or handle it specifically
        # For the dashboard's general use, we usually want the latest data.
        
        last_date = None
        if not df_local.empty:
            last_date = df_local.index.max()
            
            # If the last date is today (or very recent), we might not need to fetch
            # But markets might be open, so we usually fetch missing days.
            if end_date is None:
                today = datetime.now().date()
                if last_date.date() >= today:
                    # If it's a daily interval and we have today's data (maybe incomplete), 
                    # we might still want to refresh the last row.
                    pass

        # 2. Determine missing range
        fetch_start = start_date
        if last_date is not None and start_date is None:
            # Fetch from the day after the last stored date
            fetch_start = (last_date + timedelta(days=1)).strftime("%Y%m%d" if not any(char.isalpha() for char in symbol[:3]) else "%Y-%m-%d")

        # 3. Fetch missing data from network
        df_new = self._fetch_from_network(symbol, period, interval, start_date=fetch_start, end_date=end_date)
        
        if df_new.empty:
            return df_local

        # 4. Merge and Save
        if df_local.empty:
            df_final = df_new
        else:
            # Combine and remove duplicates (keep newest)
            df_final = pd.concat([df_local, df_new])
            df_final = df_final[~df_final.index.duplicated(keep='last')].sort_index()

        self.storage.save_data(symbol, period, interval, df_final)
        return df_final

    def _fetch_from_network(self, symbol: str, period: str = "daily", interval: str = "1d", start_date: str = None, end_date: str = None) -> pd.DataFrame:
        """
        Core logic to fetch from yfinance or AkShare.
        """
        print(f"Fetching from network: {symbol}, start={start_date}, end={end_date}")
        if any(char.isalpha() for char in symbol[:3]): # Simple heuristic for non-A-share symbols
            # Use yfinance for non-A-shares
            try:
                ticker = yf.Ticker(symbol)
                # yfinance expects YYYY-MM-DD
                df = ticker.history(start=start_date, end=end_date, interval=interval)
                if not df.empty:
                    df.index = df.index.tz_localize(None)
                    # Standardize columns
                    df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                return df
            except Exception as e:
                print(f"Error fetching from yfinance: {e}")
                return pd.DataFrame()
        else:
            # Use AkShare for A-shares
            try:
                # AkShare expects YYYYMMDD
                if start_date and "-" in start_date:
                    start_date = start_date.replace("-", "")
                if end_date and "-" in end_date:
                    end_date = end_date.replace("-", "")

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
                    return pd.DataFrame()

                if len(df.columns) == 12:
                    df.columns = ['Date', 'Symbol', 'Open', 'Close', 'High', 'Low', 'Volume', 'Turnover', 'Amplitude', 'Pct_Change', 'Change_Amount', 'Turnover_Rate']
                elif len(df.columns) == 11:
                    df.columns = ['Date', 'Open', 'Close', 'High', 'Low', 'Volume', 'Turnover', 'Amplitude', 'Pct_Change', 'Change_Amount', 'Turnover_Rate']
                
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
                return df[['Open', 'High', 'Low', 'Close', 'Volume']]
            except Exception as e:
                print(f"Error fetching from AkShare: {e}")
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
    client = StockDataClient()
    print("Testing caching for 600036...")
    df = client.get_history("600036")
    print(f"Total rows: {len(df)}")
    print(df.tail(2))
    
    print("\nSecond call (should be faster/no new fetch if up to date):")
    df2 = client.get_history("600036")
    print(f"Total rows: {len(df2)}")
