import sqlite3
from sqlite3 import Connection
import os
from typing import Optional

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
        self._check_sales_tables()   # ✅ NUEVO

    def _create_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT DEFAULT '',
                price REAL NOT NULL,
                stock INTEGER NOT NULL
            );
        ''')
        conn.commit()
        conn.close()

    def _check_barcode_column(self):
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'barcode' not in columns:
            cursor.execute("ALTER TABLE products ADD COLUMN barcode TEXT DEFAULT ''")
            self.conn.commit()

    def _check_sales_tables(self):
        """Crea las tablas de ventas si no existen (para la v2.0)."""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total REAL NOT NULL,
                payment_method TEXT DEFAULT 'Efectivo',
                notes TEXT DEFAULT ''
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sale_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER,
                product_name TEXT NOT NULL,
                barcode TEXT DEFAULT '',
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                subtotal REAL NOT NULL,
                FOREIGN KEY (sale_id) REFERENCES sales(sale_id)
            );
        ''')
        self.conn.commit()

    def get_connection(self):
        if not self.conn:
            self.connect()
        return self.conn

    def close_connection(self):
        if self.conn:
            self.conn.close()
            self.conn = None