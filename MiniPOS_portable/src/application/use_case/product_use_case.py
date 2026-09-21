import json
from datetime import datetime
from domain.models.product import Product
from infrastucture.db.db_manager import DBManager


class ProductCase:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager

    def add_product(self, name, barcode, price, stock, unit_type="unidad", unit="unidad") -> Product:
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO products (name, barcode, price, stock, unit_type, unit, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (name, barcode, price, stock, unit_type, unit, now, now))
        conn.commit()
        pid = cur.lastrowid
        return Product(pid, name, barcode, price, stock, unit_type, unit, now, now)

    def list_products(self):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products")
        rows = cur.fetchall()
        result = []
        for r in rows:
            keys = r.keys()
            result.append(Product(
                r["product_id"], r["name"], r["barcode"], r["price"], r["stock"],
                r["unit_type"] if "unit_type" in keys else "unidad",
                r["unit"] if "unit" in keys else "unidad",
                r["created_at"] if "created_at" in keys else "",
                r["updated_at"] if "updated_at" in keys else ""))
        return result

    def update_product(self, product_id, name, barcode, price, stock,
                       unit_type="unidad", unit="unidad"):
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "UPDATE products SET name=?, barcode=?, price=?, stock=?, unit_type=?, unit=?, "
            "updated_at=? WHERE product_id=?",
            (name, barcode, price, stock, unit_type, unit, now, product_id))
        conn.commit()

    def delete_product(self, product_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        conn.commit()

    # ============ BORRADOR DE PRODUCTO ============
    def save_product_draft(self, data):
        """Guarda el formulario de producto a medio llenar."""
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload = json.dumps(data, ensure_ascii=False)
            cur.execute(
                "INSERT OR REPLACE INTO product_draft (id, data, updated_at) VALUES (1, ?, ?)",
                (payload, now))
            conn.commit()
        except Exception:
            pass

    def load_product_draft(self):
        """Devuelve (dict_data, fecha) o (None, None)."""
        try:
            cur = self.db.get_connection().cursor()
            cur.execute("SELECT data, updated_at FROM product_draft WHERE id = 1")
            row = cur.fetchone()
            if not row:
                return None, None
            data = json.loads(row["data"])
            if not data:
                return None, None
            return data, row["updated_at"]
        except Exception:
            return None, None

    def clear_product_draft(self):
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM product_draft WHERE id = 1")
            conn.commit()
        except Exception:
            pass