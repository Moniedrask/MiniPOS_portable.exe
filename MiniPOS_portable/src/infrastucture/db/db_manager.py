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
                base = os.path.abspath(os.path.join(
                    os.path.dirname(__file__), '..', '..', '..'))
            db_path = os.path.join(base, 'data', 'ventas.db')

        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.conn = None
        self._init_db()

    # ============================================================
    # CONEXIÓN
    # ============================================================
    def get_connection(self):
        """Conexión persistente (compatible con código viejo que la usa)."""
        if self.conn is None:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            try:
                self.conn.execute("PRAGMA foreign_keys = ON")
                self.conn.execute("PRAGMA journal_mode=WAL")
                self.conn.execute("PRAGMA synchronous=NORMAL")
            except Exception:
                pass
        return self.conn

    def close_connection(self):
        """Cierra la conexión (para exportar/importar BD)."""
        if self.conn is not None:
            try:
                self.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    # Alias de compatibilidad
    def close(self):
        self.close_connection()

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
                barcode TEXT DEFAULT '',
                price REAL NOT NULL DEFAULT 0,
                stock REAL NOT NULL DEFAULT 0,
                unit_type TEXT DEFAULT 'unidad',
                unit TEXT DEFAULT 'unidad',
                created_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT '',
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
                barcode TEXT DEFAULT '',
                quantity REAL NOT NULL DEFAULT 0,
                unit TEXT DEFAULT 'unidad',
                unit_price REAL NOT NULL DEFAULT 0,
                subtotal REAL NOT NULL DEFAULT 0,
                returned_qty REAL DEFAULT 0,
                FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE
            )
        ''')

        # ---------- PAGOS MIXTOS (idea 3) ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS sale_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                method TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE
            )
        ''')

        # ---------- HISTORIAL DE PRECIOS (idea 28) ----------
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

        # ---------- SESIONES DE CAJA (idea 2) ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cash_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
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

        # ---------- MOVIMIENTOS DE CAJA (idea 2, Fase 6) ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cash_movements (
                movement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                notes TEXT DEFAULT '',
                FOREIGN KEY (session_id) REFERENCES cash_sessions(session_id) ON DELETE SET NULL
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
                value TEXT DEFAULT ''
            )
        ''')

        # ---------- BORRADORES ----------
        cur.execute('''
            CREATE TABLE IF NOT EXISTS product_draft (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS cart_draft (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL
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
        cur.execute("CREATE INDEX IF NOT EXISTS idx_cash_movements_session ON cash_movements(session_id)")

        conn.commit()

        # Migraciones suaves
        self._safe_migrations()

    # ============================================================
    # MIGRACIONES SUAVES (para no perder datos existentes)
    # ============================================================
    def _safe_migrations(self):
        conn = self.get_connection()
        cur = conn.cursor()

        def add_col_if_missing(table, col, ddl):
            try:
                cur.execute(f"PRAGMA table_info({table})")
                cols = [r["name"] for r in cur.fetchall()]
                if col not in cols:
                    cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
                    conn.commit()
            except Exception:
                pass

        # Productos
        for col, ddl in [
            ("barcode", "TEXT DEFAULT ''"),
            ("unit_type", "TEXT DEFAULT 'unidad'"),
            ("unit", "TEXT DEFAULT 'unidad'"),
            ("created_at", "TEXT DEFAULT ''"),
            ("updated_at", "TEXT DEFAULT ''"),
            ("group_name", "TEXT DEFAULT ''"),
            ("cost", "REAL DEFAULT 0"),
            ("margin_percent", "REAL DEFAULT 20"),
            ("rounded_price", "REAL DEFAULT 0"),
            ("round_enabled", "INTEGER DEFAULT 0"),
            ("round_to", "INTEGER DEFAULT 100"),
            ("package_cost", "REAL DEFAULT 0"),
            ("package_units", "INTEGER DEFAULT 0"),
            ("is_package", "INTEGER DEFAULT 0"),
            ("paused", "INTEGER DEFAULT 0"),
            ("expiry_date", "TEXT DEFAULT ''"),
        ]:
            add_col_if_missing("products", col, ddl)

        # Ventas
        for col, ddl in [
            ("subtotal", "REAL DEFAULT 0"),
            ("discount", "REAL DEFAULT 0"),
            ("customer_name", "TEXT DEFAULT ''"),
            ("is_credit", "INTEGER DEFAULT 0"),
            ("is_paid", "INTEGER DEFAULT 1"),
            ("amount_paid", "REAL DEFAULT 0"),
            ("display_offset", "INTEGER DEFAULT 0"),
            ("is_returned", "INTEGER DEFAULT 0"),
        ]:
            add_col_if_missing("sales", col, ddl)

        # Items
        add_col_if_missing("sale_items", "returned_qty", "REAL DEFAULT 0")
        add_col_if_missing("sale_items", "unit", "TEXT DEFAULT 'unidad'")
        add_col_if_missing("sale_items", "barcode", "TEXT DEFAULT ''")

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
                (key, str(value)))
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
            self.close_connection()
            src = sqlite3.connect(self.db_path)
            dst = sqlite3.connect(dest_path)
            with dst:
                src.backup(dst)
            dst.close()
            src.close()
            self.get_connection()
            return True, "Backup realizado"
        except Exception as e:
            try:
                self.get_connection()
            except Exception:
                pass
            return False, str(e)