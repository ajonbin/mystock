import sqlite3
import pandas as pd
import os

class RealTradeStorage:
    def __init__(self, db_path="data/stock_data.db"):
        self.db_path = db_path
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS real_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    symbol TEXT,
                    action TEXT,
                    price REAL,
                    qty INTEGER,
                    amount REAL,
                    notes TEXT
                )
            """)

    def add_trade(self, date, symbol, action, price, qty, notes=""):
        amount = price * qty
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO real_trades (date, symbol, action, price, qty, amount, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (date, symbol, action, price, qty, amount, notes))

    def get_trades(self, symbol=None):
        query = "SELECT * FROM real_trades"
        params = []
        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)
        query += " ORDER BY date DESC"
        
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(query, conn, params=params)

    def delete_trade(self, trade_id):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM real_trades WHERE id = ?", (trade_id,))
