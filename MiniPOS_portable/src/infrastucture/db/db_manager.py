import sqlite3
from sqlite3 import Connection
import os
from typing import Optional
from datetime import datetime


class DBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[Connection] = None

    def connect(self):
        dir_path = os.path.dirname(self.db_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        if not os.path.exists(self.db_path):
            self._create_database()
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._check_barcode_column()
        self._check_unit_columns()
        self._check_timestamp_columns()
        self._check_sales_tables()
        self._check_credit_columns()
        self._check_settings_table()

    def _create_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, barcode TEXT DEFAULT '',
            price REAL NOT NULL, stock REAL NOT NULL DEFAULT 0,
            unit_type TEXT DEFAULT 'unidad', unit TEXT DEFAULT 'unidad',
            created_at TEXT DEFAULT '', updated_at TEXT DEFAULT '')''')
        conn.commit()
        conn.close()

    def _check_barcode_column(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        cols = [c[1] for c in cur.fetchall()]
        if 'barcode' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN barcode TEXT DEFAULT ''")
            self.conn.commit()

    def _check_unit_columns(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        cols = [c[1] for c in cur.fetchall()]
        if 'unit_type' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN unit_type TEXT DEFAULT 'unidad'")
            self.conn.commit()
        if 'unit' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN unit TEXT DEFAULT 'unidad'")
            self.conn.commit()

    def _check_timestamp_columns(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        cols = [c[1] for c in cur.fetchall()]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if 'created_at' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN created_at TEXT DEFAULT ''")
            cur.execute("UPDATE products SET created_at = ? WHERE created_at = '' OR created_at IS NULL", (now,))
            self.conn.commit()
        if 'updated_at' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN updated_at TEXT DEFAULT ''")
            cur.execute("UPDATE products SET updated_at = ? WHERE updated_at = '' OR updated_at IS NULL", (now,))
            self.conn.commit()

    def _check_sales_tables(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS sales (
            sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL, total REAL NOT NULL,
            payment_method TEXT DEFAULT 'Efectivo', notes TEXT DEFAULT '')''')
        cur.execute('''CREATE TABLE IF NOT EXISTS sale_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL, product_id INTEGER,
            product_name TEXT NOT NULL, barcode TEXT DEFAULT '',
            quantity REAL NOT NULL, unit TEXT DEFAULT 'unidad',
            unit_price REAL NOT NULL, subtotal REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(sale_id))''')
        self.conn.commit()

    def _check_credit_columns(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(sales)")
        cols = [c[1] for c in cur.fetchall()]
        if 'customer_name' not in cols:
            cur.execute("ALTER TABLE sales ADD COLUMN customer_name TEXT DEFAULT ''")
            self.conn.commit()
        if 'is_credit' not in cols:
            cur.execute("ALTER TABLE sales ADD COLUMN is_credit INTEGER DEFAULT 0")
            self.conn.commit()
        if 'is_paid' not in cols:
            cur.execute("ALTER TABLE sales ADD COLUMN is_paid INTEGER DEFAULT 1")
            self.conn.commit()

    def _check_settings_table(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT DEFAULT '')''')
        self.conn.commit()

    # ---- Utilidades de settings ----
    def get_setting(self, key, default=None):
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        cur = self.conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))
        self.conn.commit()

    def get_connection(self):
        if not self.conn:
            self.connect()
        return self.conn

    def close_connection(self):
        if self.conn:
            self.conn.close()
            self.conn = None