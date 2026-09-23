import os
import sqlite3
import sys


class DBManager:
    def __init__(self, db_path=None):
        if db_path is None:
            # Detectar ruta portable
            if getattr(sys, 'frozen', False):
                base = os.path.dirname(sys.executable)
            else:
                base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            db_path = os.path.join(base, 'data', 'ventas.db')

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    # ============================================================
    # CONEXIÓN
    # ============================================================
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    # ============================================================
    # INICIALIZACIÓN
    # ============================================================
    def _init_db(self):
        conn = self.get_connection()
        cur = conn.cursor()

        # ---------- PRODUCTOS ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                barcode TEXT,
                price REAL NOT NULL DEFAULT 0,
                stock INTEGER NOT NULL DEFAULT 0,
                unit_type TEXT DEFAULT 'unidad',
                unit TEXT DEFAULT 'unidad',
                created_at TEXT,
                updated_at TEXT,
                group_name TEXT DEFAULT '',
                cost REAL DEFAULT 0,
                margin_percent REAL DEFAULT 20,
                rounded_price REAL DEFAULT 0,
                round_enabled INTEGER DEFAULT 0,
                round_to INTEGER DEFAULT 100,
                package_cost REAL DEFAULT 0,
                package_units INTEGER DEFAULT 0,
                is_package INTEGER DEFAULT 0,
                paused INTEGER DEFAULT 0,
                expiry_date TEXT DEFAULT ''
            )
        ''')

        # ---------- VENTAS ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total REAL NOT NULL DEFAULT 0,
                subtotal REAL DEFAULT 0,
                discount REAL DEFAULT 0,
                payment_method TEXT DEFAULT 'Efectivo',
                notes TEXT DEFAULT '',
                customer_name TEXT DEFAULT '',
                is_credit INTEGER DEFAULT 0,
                is_paid INTEGER DEFAULT 1,
                amount_paid REAL DEFAULT 0,
                display_offset INTEGER DEFAULT 0,
                is_returned INTEGER DEFAULT 0
            )
        ''')

        # ---------- ITEMS DE VENTA ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS sale_items (
                item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER,
                product_name TEXT,
                barcode TEXT,
                quantity REAL NOT NULL DEFAULT 0,
                unit TEXT DEFAULT 'unidad',
                unit_price REAL NOT NULL DEFAULT 0,
                subtotal REAL NOT NULL DEFAULT 0,
                returned_qty REAL DEFAULT 0,
                FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE
            )
        ''')

        # ---------- PAGOS MIXTOS ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS sale_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                method TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE
            )
        ''')

        # ---------- HISTORIAL DE PRECIOS ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                old_price REAL DEFAULT 0,
                new_price REAL DEFAULT 0,
                old_rounded_price REAL DEFAULT 0,
                new_rounded_price REAL DEFAULT 0,
                FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
            )
        ''')

        # ---------- CAJA (BASE DE CAJA) ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cash_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                open_date TEXT NOT NULL,
                close_date TEXT,
                initial_amount REAL DEFAULT 0,
                final_expected REAL DEFAULT 0,
                final_counted REAL DEFAULT 0,
                difference REAL DEFAULT 0,
                notes TEXT DEFAULT '',
                is_open INTEGER DEFAULT 1
            )
        ''')

        # ---------- DEVOLUCIONES (idea 10) ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS returns (
                return_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                reason TEXT DEFAULT '',
                total_returned REAL DEFAULT 0,
                return_type TEXT DEFAULT 'producto',
                FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS return_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                return_id INTEGER NOT NULL,
                product_id INTEGER,
                product_name TEXT,
                quantity REAL NOT NULL DEFAULT 0,
                unit_price REAL NOT NULL DEFAULT 0,
                subtotal REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (return_id) REFERENCES returns(return_id) ON DELETE CASCADE
            )
        ''')

        # ---------- CONFIGURACIÓN ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # ---------- BORRADORES ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS product_draft (
                id INTEGER PRIMARY KEY,
                data TEXT,
                updated_at TEXT
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS cart_draft (
                id INTEGER PRIMARY KEY,
                data TEXT,
                updated_at TEXT
            )
        ''')

        # ---------- ÍNDICES ----------
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_date ON sales(date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales(customer_name)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sale_items_sale ON sale_items(sale_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_sale_payments_sale ON sale_payments(sale_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_price_history_product ON price_history(product_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_products_paused ON products(paused)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_products_expiry ON products(expiry_date)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_returns_sale ON returns(sale_id)")

        conn.commit()
        conn.close()

        # Migraciones suaves (por si la BD ya existía sin estas columnas)
        self._safe_migrations()

    # ============================================================
    # MIGRACIONES SUAVES
    # ============================================================
    def _safe_migrations(self):
        conn = self.get_connection()
        cur = conn.cursor()

        def add_column_if_missing(table, column, ddl):
            try:
                cur.execute(f"PRAGMA table_info({table})")
                cols = [r["name"] for r in cur.fetchall()]
                if column not in cols:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
                    conn.commit()
            except Exception:
                pass

        # Productos
        add_column_if_missing("products", "group_name", "TEXT DEFAULT ''")
        add_column_if_missing("products", "cost", "REAL DEFAULT 0")
        add_column_if_missing("products", "margin_percent", "REAL DEFAULT 20")
        add_column_if_missing("products", "rounded_price", "REAL DEFAULT 0")
        add_column_if_missing("products", "round_enabled", "INTEGER DEFAULT 0")
        add_column_if_missing("products", "round_to", "INTEGER DEFAULT 100")
        add_column_if_missing("products", "package_cost", "REAL DEFAULT 0")
        add_column_if_missing("products", "package_units", "INTEGER DEFAULT 0")
        add_column_if_missing("products", "is_package", "INTEGER DEFAULT 0")
        add_column_if_missing("products", "paused", "INTEGER DEFAULT 0")
        add_column_if_missing("products", "expiry_date", "TEXT DEFAULT ''")
        add_column_if_missing("products", "unit_type", "TEXT DEFAULT 'unidad'")
        add_column_if_missing("products", "unit", "TEXT DEFAULT 'unidad'")

        # Ventas
        add_column_if_missing("sales", "subtotal", "REAL DEFAULT 0")
        add_column_if_missing("sales", "discount", "REAL DEFAULT 0")
        add_column_if_missing("sales", "customer_name", "TEXT DEFAULT ''")
        add_column_if_missing("sales", "is_credit", "INTEGER DEFAULT 0")
        add_column_if_missing("sales", "is_paid", "INTEGER DEFAULT 1")
        add_column_if_missing("sales", "amount_paid", "REAL DEFAULT 0")
        add_column_if_missing("sales", "display_offset", "INTEGER DEFAULT 0")
        add_column_if_missing("sales", "is_returned", "INTEGER DEFAULT 0")

        # Items
        add_column_if_missing("sale_items", "returned_qty", "REAL DEFAULT 0")
        add_column_if_missing("sale_items", "unit", "TEXT DEFAULT 'unidad'")

        conn.close()

    # ============================================================
    # CONFIGURACIÓN (settings)
    # ============================================================
    def get_setting(self, key, default=None):
        try:
            cur = self.get_connection().cursor()
            cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cur.fetchone()
            if row is None:
                return default
            return row["value"]
        except Exception:
            return default

    def set_setting(self, key, value):
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, str(value))
            )
            conn.commit()
        except Exception:
            pass

    def get_all_settings(self):
        try:
            cur = self.get_connection().cursor()
            cur.execute("SELECT key, value FROM settings")
            return {r["key"]: r["value"] for r in cur.fetchall()}
        except Exception:
            return {}

    def delete_setting(self, key):
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM settings WHERE key = ?", (key,))
            conn.commit()
        except Exception:
            pass

    # ============================================================
    # BACKUP / RESTORE
    # ============================================================
    def backup_to(self, dest_path):
        try:
            src = sqlite3.connect(self.db_path)
            dst = sqlite3.connect(dest_path)
            with dst:
                src.backup(dst)
            dst.close()
            src.close()
            return True, "Backup realizado"
        except Exception as e:
            return False, str(e)

    def close(self):
        # No hay conexión persistente, nada que cerrar
        pass
