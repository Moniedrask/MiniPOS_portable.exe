import sqlite3
from sqlite3 import Connection, Cursor
import os
from typing import Optional
from sqlite3 import Connection

class DBManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn: Optional[Connection] = None

    def connect(self):
        # Asegurar que el directorio existe antes de conectar
        dir_path = os.path.dirname(self.db_path)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        if not os.path.exists(self.db_path):
            self._create_database()
        
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # ✅ NUEVO: Verificar si falta la columna 'barcode' y agregarla si es necesario
        self._check_barcode_column()

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
        """Revisa si la columna 'barcode' existe. Si no, la crea para no perder datos antiguos."""
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(products)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'barcode' not in columns:
            cursor.execute("ALTER TABLE products ADD COLUMN barcode TEXT DEFAULT ''")
            self.conn.commit()

    def get_connection(self):
        if not self.conn:
            self.connect()
        return self.conn

    def close_connection(self):
        """Cierra la conexión para que los archivos de base de datos puedan ser copiados o movidos."""
        if self.conn:
            self.conn.close()
            self.conn = None
