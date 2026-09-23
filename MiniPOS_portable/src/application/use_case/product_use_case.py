import json
from datetime import datetime, timedelta
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

    # ============================================================
    # CRUD BÁSICO
    # ============================================================
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

        if register_history:
            cambio_precio = abs(old_price - price) > 0.001
            cambio_redondeo = abs(old_rounded - rounded_price) > 0.001
            if cambio_precio or cambio_redondeo:
                self.register_price_change(
                    product_id, old_price, price, old_rounded, rounded_price)

    def delete_product(self, product_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
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

    # ============================================================
    # IDEA 4: PRODUCTOS PAUSADOS
    # ============================================================
    def set_paused(self, product_id, paused):
        """Pausa o reactiva un producto sin borrarlo."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE products SET paused = ? WHERE product_id = ?",
                    (1 if paused else 0, product_id))
        conn.commit()

    def set_paused_bulk(self, product_ids, paused):
        if not product_ids:
            return
        conn = self.db.get_connection()
        cur = conn.cursor()
        for pid in product_ids:
            cur.execute("UPDATE products SET paused = ? WHERE product_id = ?",
                        (1 if paused else 0, pid))
        conn.commit()

    # ============================================================
    # IDEA 28: HISTORIAL DE PRECIOS
    # ============================================================
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

    def get_all_price_history(self, start_date=None, end_date=None):
        """Devuelve todo el historial con el nombre del producto.
        Opcional: filtrar por rango de fechas.
        """
        cur = self.db.get_connection().cursor()
        sql = '''
            SELECT ph.*, p.name AS product_name, p.barcode AS product_barcode
            FROM price_history ph
            LEFT JOIN products p ON ph.product_id = p.product_id
        '''
        params = []
        if start_date and end_date:
            sql += " WHERE date(ph.date) BETWEEN ? AND ? "
            params.extend([start_date, end_date])
        sql += " ORDER BY ph.date DESC"
        cur.execute(sql, params)
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
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
        conn.commit()

    # ============================================================
    # IDEA 25 + 27: SUGERENCIA INTELIGENTE DE PAQUETE
    # ============================================================
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

    # ============================================================
    # IDEA 16: VENCIMIENTO DE PRODUCTOS
    # ============================================================
    def get_expiry_settings(self):
        """Lee configuración de alertas de vencimiento desde settings."""
        return {
            "warn_days_1": int(self.db.get_setting("expiry_warn_days_1", "15") or 15),
            "warn_days_2": int(self.db.get_setting("expiry_warn_days_2", "7") or 7),
            "offer_days": int(self.db.get_setting("expiry_offer_days", "2") or 2),
            "offer_discount": float(self.db.get_setting("expiry_offer_discount", "20") or 20),
        }

    def set_expiry_settings(self, warn_days_1, warn_days_2, offer_days, offer_discount):
        self.db.set_setting("expiry_warn_days_1", str(int(warn_days_1)))
        self.db.set_setting("expiry_warn_days_2", str(int(warn_days_2)))
        self.db.set_setting("expiry_offer_days", str(int(offer_days)))
        self.db.set_setting("expiry_offer_discount", str(float(offer_discount)))

    def get_products_with_expiry(self):
        """Devuelve todos los productos con fecha de vencimiento válida."""
        cur = self.db.get_connection().cursor()
        cur.execute("""
            SELECT * FROM products
            WHERE expiry_date IS NOT NULL AND expiry_date != ''
            ORDER BY date(expiry_date) ASC
        """)
        rows = cur.fetchall()
        return [self._row_to_product(r) for r in rows]

    def get_expiring_products(self, days=None):
        """
        Devuelve productos que vencen dentro de `days` (o el máximo
        configurado si days=None). Cada item incluye:
        - product
        - days_left (int, puede ser negativo si ya venció)
        - status: 'expired' | 'offer' | 'warn1' | 'warn2' | 'ok'
        """
        cfg = self.get_expiry_settings()
        if days is None:
            days = max(cfg["warn_days_1"], cfg["warn_days_2"], cfg["offer_days"])

        hoy = datetime.now().date()
        resultado = []
        for p in self.get_products_with_expiry():
            try:
                exp = datetime.strptime(p.expiry_date, "%Y-%m-%d").date()
            except Exception:
                continue
            days_left = (exp - hoy).days

            if days_left < 0:
                status = "expired"
            elif days_left <= cfg["offer_days"]:
                status = "offer"
            elif days_left <= cfg["warn_days_2"]:
                status = "warn2"
            elif days_left <= cfg["warn_days_1"]:
                status = "warn1"
            else:
                status = "ok"

            if status != "ok" or days_left <= days:
                resultado.append({
                    "product": p,
                    "days_left": days_left,
                    "status": status,
                })
        return resultado

    def get_expiring_count(self):
        """Cantidad de productos con alguna alerta (para badges)."""
        return len([x for x in self.get_expiring_products() if x["status"] != "ok"])

    def apply_offer_discount(self, product_id, discount_percent=None):
        """
        Aplica un descuento al precio redondeado de un producto (idea 16 → oferta).
        Guarda como cambio de precio en el historial.
        """
        cfg = self.get_expiry_settings()
        if discount_percent is None:
            discount_percent = cfg["offer_discount"]

        p = self.get_product(product_id)
        if not p:
            return False, "Producto no encontrado"

        old_price = float(p.price or 0)
        old_rounded = float(p.rounded_price or p.price or 0)
        base = old_rounded if old_rounded > 0 else old_price
        new_rounded = round(base * (1 - discount_percent / 100.0), 2)
        new_price = round(old_price * (1 - discount_percent / 100.0), 2)

        self.update_product(
            product_id, p.name, p.barcode, new_price, p.stock,
            unit_type=p.unit_type, unit=p.unit, group_name=p.group_name,
            cost=p.cost, margin_percent=p.margin_percent,
            rounded_price=new_rounded,
            round_enabled=p.round_enabled, round_to=p.round_to,
            package_cost=p.package_cost, package_units=p.package_units,
            is_package=p.is_package, paused=p.paused,
            expiry_date=p.expiry_date,
            register_history=True,
        )
        return True, f"Descuento del {discount_percent}% aplicado"

    # ============================================================
    # IDEA 5: ETIQUETAS (necesita datos del producto)
    # ============================================================
    def get_products_for_labels(self, product_ids=None):
        """
        Devuelve los productos que se van a imprimir en etiquetas.
        Si product_ids es None, devuelve todos los activos.
        """
        if product_ids:
            return [p for p in (self.get_product(pid) for pid in product_ids) if p]
        return self.list_active_products()

    # ============================================================
    # BORRADOR
    # ============================================================
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
