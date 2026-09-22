import json
from datetime import datetime
from domain.models.product import Product
from infrastucture.db.db_manager import DBManager


class ProductCase:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager

    def _row_to_product(self, r):
        keys = r.keys()
        return Product(
            r["product_id"], r["name"], r["barcode"], r["price"], r["stock"],
            r["unit_type"] if "unit_type" in keys else "unidad",
            r["unit"] if "unit" in keys else "unidad",
            r["created_at"] if "created_at" in keys else "",
            r["updated_at"] if "updated_at" in keys else "",
            r["group_name"] if "group_name" in keys else "",
            r["cost"] if "cost" in keys else 0.0,
            r["margin_percent"] if "margin_percent" in keys else 20.0,
            r["rounded_price"] if "rounded_price" in keys else r["price"],
            r["round_enabled"] if "round_enabled" in keys else 0,
            r["round_to"] if "round_to" in keys else 100,
            r["package_cost"] if "package_cost" in keys else 0.0,
            r["package_units"] if "package_units" in keys else 0,
            r["is_package"] if "is_package" in keys else 0,
            r["paused"] if "paused" in keys else 0,
            r["expiry_date"] if "expiry_date" in keys else "",
        )

    def add_product(self, name, barcode, price, stock,
                    unit_type="unidad", unit="unidad",
                    group_name="", cost=0.0, margin_percent=20.0,
                    rounded_price=0.0, round_enabled=0, round_to=100,
                    package_cost=0.0, package_units=0, is_package=0,
                    paused=0, expiry_date=""):
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not rounded_price or rounded_price <= 0:
            rounded_price = price
        cur.execute(
            "INSERT INTO products (name, barcode, price, stock, unit_type, unit, "
            "created_at, updated_at, group_name, cost, margin_percent, "
            "rounded_price, round_enabled, round_to, package_cost, package_units, "
            "is_package, paused, expiry_date) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, barcode, price, stock, unit_type, unit, now, now,
             group_name, cost, margin_percent,
             rounded_price, round_enabled, round_to,
             package_cost, package_units, is_package, paused, expiry_date))
        conn.commit()
        pid = cur.lastrowid
        return pid

    def list_products(self):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products")
        rows = cur.fetchall()
        return [self._row_to_product(r) for r in rows]

    def list_active_products(self):
        """Solo productos no pausados (para PAGOS)."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE paused = 0 OR paused IS NULL")
        rows = cur.fetchall()
        return [self._row_to_product(r) for r in rows]

    def get_product(self, product_id):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
        r = cur.fetchone()
        if not r:
            return None
        return self._row_to_product(r)

    def update_product(self, product_id, name, barcode, price, stock,
                       unit_type="unidad", unit="unidad",
                       group_name="", cost=0.0, margin_percent=20.0,
                       rounded_price=0.0, round_enabled=0, round_to=100,
                       package_cost=0.0, package_units=0, is_package=0,
                       paused=0, expiry_date="",
                       register_history=True):
        conn = self.db.get_connection()
        cur = conn.cursor()

        # Obtener precio anterior para historial
        cur.execute("SELECT price, rounded_price FROM products WHERE product_id = ?",
                    (product_id,))
        row = cur.fetchone()
        old_price = row["price"] if row else 0.0
        old_rounded = row["rounded_price"] if row else 0.0

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not rounded_price or rounded_price <= 0:
            rounded_price = price

        cur.execute(
            "UPDATE products SET name=?, barcode=?, price=?, stock=?, unit_type=?, "
            "unit=?, updated_at=?, group_name=?, cost=?, margin_percent=?, "
            "rounded_price=?, round_enabled=?, round_to=?, package_cost=?, "
            "package_units=?, is_package=?, paused=?, expiry_date=? "
            "WHERE product_id=?",
            (name, barcode, price, stock, unit_type, unit, now,
             group_name, cost, margin_percent,
             rounded_price, round_enabled, round_to,
             package_cost, package_units, is_package, paused, expiry_date,
             product_id))
        conn.commit()

        # Registrar cambio de precio si cambió
        if register_history:
            cambio_precio = abs(old_price - price) > 0.001
            cambio_redondeo = abs(old_rounded - rounded_price) > 0.001
            if cambio_precio or cambio_redondeo:
                self.register_price_change(
                    product_id, old_price, price, old_rounded, rounded_price)

    def register_price_change(self, product_id, old_price, new_price,
                              old_rounded=0.0, new_rounded=0.0):
        """Guarda un cambio de precio en el historial."""
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO price_history (product_id, date, old_price, new_price, "
                "old_rounded_price, new_rounded_price) VALUES (?,?,?,?,?,?)",
                (product_id, now, old_price, new_price, old_rounded, new_rounded))
            conn.commit()
        except Exception:
            pass

    def get_price_history(self, product_id):
        """Devuelve lista de dicts con el historial de precios de un producto."""
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT * FROM price_history WHERE product_id = ? ORDER BY date DESC",
            (product_id,))
        rows = cur.fetchall()
        result = []
        for r in rows:
            keys = r.keys()
            result.append({
                "id": r["id"],
                "product_id": r["product_id"],
                "date": r["date"],
                "old_price": r["old_price"] if "old_price" in keys else 0.0,
                "new_price": r["new_price"] if "new_price" in keys else 0.0,
                "old_rounded_price": r["old_rounded_price"] if "old_rounded_price" in keys else 0.0,
                "new_rounded_price": r["new_rounded_price"] if "new_rounded_price" in keys else 0.0,
            })
        return result

    def get_all_price_history(self):
        """Devuelve todo el historial con el nombre del producto."""
        cur = self.db.get_connection().cursor()
        cur.execute('''
            SELECT ph.*, p.name AS product_name, p.barcode AS product_barcode
            FROM price_history ph
            LEFT JOIN products p ON ph.product_id = p.product_id
            ORDER BY ph.date DESC
        ''')
        rows = cur.fetchall()
        result = []
        for r in rows:
            keys = r.keys()
            result.append({
                "id": r["id"],
                "product_id": r["product_id"],
                "product_name": r["product_name"] if "product_name" in keys else "(producto eliminado)",
                "product_barcode": r["product_barcode"] if "product_barcode" in keys else "",
                "date": r["date"],
                "old_price": r["old_price"] if "old_price" in keys else 0.0,
                "new_price": r["new_price"] if "new_price" in keys else 0.0,
                "old_rounded_price": r["old_rounded_price"] if "old_rounded_price" in keys else 0.0,
                "new_rounded_price": r["new_rounded_price"] if "new_rounded_price" in keys else 0.0,
            })
        return result

    def delete_price_history_for_product(self, product_id):
        """Borra el historial de un producto (por si quiere limpiarlo)."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
        conn.commit()

    def delete_product(self, product_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        # Eliminar el historial del producto antes de borrarlo
        cur.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
        cur.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
        conn.commit()

    def set_group_name(self, product_ids, group_name):
        if not product_ids:
            return
        conn = self.db.get_connection()
        cur = conn.cursor()
        for pid in product_ids:
            cur.execute("UPDATE products SET group_name = ? WHERE product_id = ?",
                        (group_name, pid))
        conn.commit()

    # ============ SUGERENCIA DE PAQUETE ============
    def find_last_package_for_name(self, name):
        """
        Busca el último producto con nombre similar que tenga datos de paquete.
        Devuelve dict {package_cost, package_units, name} o None.
        """
        if not name or not str(name).strip():
            return None
        name_lower = str(name).strip().lower()
        try:
            cur = self.db.get_connection().cursor()
            # Buscar productos con is_package = 1 cuyo nombre sea similar
            cur.execute('''
                SELECT name, package_cost, package_units
                FROM products
                WHERE is_package = 1 AND package_units > 0
                ORDER BY updated_at DESC
            ''')
            rows = cur.fetchall()
            from difflib import SequenceMatcher
            mejor = None
            mejor_score = 0.0
            for r in rows:
                p_name = (r["name"] or "").lower()
                if not p_name:
                    continue
                ratio = SequenceMatcher(None, name_lower, p_name).ratio()
                if name_lower in p_name or p_name in name_lower:
                    ratio = max(ratio, 0.8)
                if ratio > mejor_score and ratio >= 0.6:
                    mejor_score = ratio
                    mejor = {
                        "name": r["name"],
                        "package_cost": r["package_cost"] or 0.0,
                        "package_units": r["package_units"] or 0,
                    }
            return mejor
        except Exception:
            return None

    # ============ BORRADOR ============
    def save_product_draft(self, data):
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