import sqlite3
import pandas as pd
import os

class StockStorage:
    def __init__(self, db_path="data/stock_data.db"):
        self.db_path = db_path
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def get_table_name(self, symbol: str, period: str, interval: str) -> str:
        # Clean symbol and params for table name
        clean_symbol = symbol.replace(".", "_").replace("-", "_")
        return f"stock_{clean_symbol}_{period}_{interval}"

    def save_data(self, symbol: str, period: str, interval: str, df: pd.DataFrame):
        if df.empty:
            return
        
        table_name = self.get_table_name(symbol, period, interval)
        with sqlite3.connect(self.db_path) as conn:
            # We use if_exists='replace' if we want to overwrite, 
            # but since we merge in the client, we can just replace the whole table for that symbol/period/interval
            df.to_sql(table_name, conn, if_exists='replace', index=True)

    def load_data(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
        table_name = self.get_table_name(symbol, period, interval)
        with sqlite3.connect(self.db_path) as conn:
            try:
                df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
                if not df.empty and 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)
                return df
            except Exception:
                # Table might not exist
                return pd.DataFrame()
