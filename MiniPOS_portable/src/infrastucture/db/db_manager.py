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

        try:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
        except Exception:
            pass

        # Migraciones existentes
        self._check_barcode_column()
        self._check_unit_columns()
        self._check_timestamp_columns()
        self._check_group_column()
        self._check_cost_columns()
        self._check_fase5_columns()
        self._check_price_history_table()
        self._check_sales_tables()
        self._check_credit_columns()
        self._check_payment_column()
        self._check_display_offset_column()
        self._check_discount_column()
        self._check_settings_table()
        self._check_drafts_tables()

        # ========== FASE 6 ==========
        self._check_cash_sessions_table()
        self._check_sale_payments_table()
        self._check_customer_payments_table()
        self._check_cash_movements_table()

    def _create_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, barcode TEXT DEFAULT '',
            price REAL NOT NULL, stock REAL NOT NULL DEFAULT 0,
            unit_type TEXT DEFAULT 'unidad', unit TEXT DEFAULT 'unidad',
            created_at TEXT DEFAULT '', updated_at TEXT DEFAULT '',
            group_name TEXT DEFAULT '',
            cost REAL DEFAULT 0, margin_percent REAL DEFAULT 20,
            rounded_price REAL DEFAULT 0, round_enabled INTEGER DEFAULT 0,
            round_to INTEGER DEFAULT 100,
            package_cost REAL DEFAULT 0, package_units INTEGER DEFAULT 0,
            is_package INTEGER DEFAULT 0,
            paused INTEGER DEFAULT 0,
            expiry_date TEXT DEFAULT '')''')
        c.execute('''CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            old_price REAL DEFAULT 0,
            new_price REAL DEFAULT 0,
            old_rounded_price REAL DEFAULT 0,
            new_rounded_price REAL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(product_id))''')
        conn.commit()
        conn.close()

    # ===== Migraciones existentes (Fases 1-5) =====
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

    def _check_group_column(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        cols = [c[1] for c in cur.fetchall()]
        if 'group_name' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN group_name TEXT DEFAULT ''")
            self.conn.commit()

    def _check_cost_columns(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        cols = [c[1] for c in cur.fetchall()]
        if 'cost' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN cost REAL DEFAULT 0")
            self.conn.commit()
        if 'margin_percent' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN margin_percent REAL DEFAULT 20")
            self.conn.commit()

    def _check_fase5_columns(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(products)")
        cols = [c[1] for c in cur.fetchall()]

        if 'rounded_price' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN rounded_price REAL DEFAULT 0")
            cur.execute("UPDATE products SET rounded_price = price WHERE rounded_price = 0")
            self.conn.commit()
        if 'round_enabled' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN round_enabled INTEGER DEFAULT 0")
            self.conn.commit()
        if 'round_to' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN round_to INTEGER DEFAULT 100")
            self.conn.commit()
        if 'package_cost' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN package_cost REAL DEFAULT 0")
            self.conn.commit()
        if 'package_units' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN package_units INTEGER DEFAULT 0")
            self.conn.commit()
        if 'is_package' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN is_package INTEGER DEFAULT 0")
            self.conn.commit()
        if 'paused' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN paused INTEGER DEFAULT 0")
            self.conn.commit()
        if 'expiry_date' not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN expiry_date TEXT DEFAULT ''")
            self.conn.commit()

    def _check_price_history_table(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            old_price REAL DEFAULT 0,
            new_price REAL DEFAULT 0,
            old_rounded_price REAL DEFAULT 0,
            new_rounded_price REAL DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(product_id))''')
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

    def _check_payment_column(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(sales)")
        cols = [c[1] for c in cur.fetchall()]
        if 'amount_paid' not in cols:
            cur.execute("ALTER TABLE sales ADD COLUMN amount_paid REAL DEFAULT 0")
            cur.execute("UPDATE sales SET amount_paid = total WHERE is_paid = 1")
            self.conn.commit()

    def _check_display_offset_column(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(sales)")
        cols = [c[1] for c in cur.fetchall()]
        if 'display_offset' not in cols:
            cur.execute("ALTER TABLE sales ADD COLUMN display_offset INTEGER DEFAULT 0")
            self.conn.commit()

    def _check_discount_column(self):
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(sales)")
        cols = [c[1] for c in cur.fetchall()]
        if 'discount' not in cols:
            cur.execute("ALTER TABLE sales ADD COLUMN discount REAL DEFAULT 0")
            self.conn.commit()
        if 'subtotal' not in cols:
            cur.execute("ALTER TABLE sales ADD COLUMN subtotal REAL DEFAULT 0")
            cur.execute("UPDATE sales SET subtotal = total WHERE subtotal = 0")
            self.conn.commit()

    def _check_settings_table(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT DEFAULT '')''')
        self.conn.commit()

    def _check_drafts_tables(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS cart_draft (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            data TEXT NOT NULL,
            updated_at TEXT NOT NULL)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS product_draft (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            data TEXT NOT NULL,
            updated_at TEXT NOT NULL)''')
        self.conn.commit()

    # ========== FASE 6 ==========
    def _check_cash_sessions_table(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS cash_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            opened_at TEXT NOT NULL,
            closed_at TEXT DEFAULT '',
            initial_cash REAL DEFAULT 0,
            counted_cash REAL DEFAULT 0,
            difference REAL DEFAULT 0,
            notes TEXT DEFAULT '')''')
        self.conn.commit()

    def _check_sale_payments_table(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS sale_payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            method TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(sale_id))''')
        self.conn.commit()

    def _check_customer_payments_table(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS customer_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            customer_name TEXT DEFAULT '',
            sale_id INTEGER,
            method TEXT DEFAULT 'Efectivo',
            amount REAL NOT NULL)''')
        self.conn.commit()

    def _check_cash_movements_table(self):
        cur = self.conn.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS cash_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            notes TEXT DEFAULT '')''')
        self.conn.commit()

    # ===== Utilidades =====
    def get_setting(self, key, default=None):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))
        conn.commit()

    def get_connection(self):
        if not self.conn:
            self.connect()
        return self.conn

    def close_connection(self):
        if self.conn:
            try:
                self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            self.conn.close()
            self.conn = None