import json
from datetime import datetime
from domain.models.sale import Sale, SaleItem


class SaleCase:
    def __init__(self, db_manager):
        self.db = db_manager

    def create_sale(self, items, payment_method="Efectivo", notes="",
                    customer_name="", is_credit=False):
        conn = self.db.get_connection()
        cur = conn.cursor()
        total = sum(i["quantity"] * i["unit_price"] for i in items)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_paid = 0 if is_credit else 1
        amount_paid = 0.0 if is_credit else total
        cur.execute(
            "INSERT INTO sales (date, total, payment_method, notes, customer_name, "
            "is_credit, is_paid, amount_paid) VALUES (?,?,?,?,?,?,?,?)",
            (now, total, payment_method, notes, customer_name,
             1 if is_credit else 0, is_paid, amount_paid))
        sale_id = cur.lastrowid
        for it in items:
            sub = it["quantity"] * it["unit_price"]
            cur.execute(
                "INSERT INTO sale_items (sale_id, product_id, product_name, barcode, "
                "quantity, unit, unit_price, subtotal) VALUES (?,?,?,?,?,?,?,?)",
                (sale_id, it["product_id"], it["product_name"], it.get("barcode", ""),
                 it["quantity"], it.get("unit", "unidad"), it["unit_price"], sub))
            if it["product_id"]:
                cur.execute("UPDATE products SET stock = stock - ? WHERE product_id = ?",
                            (it["quantity"], it["product_id"]))
        conn.commit()
        return sale_id, total

    def _rows_to_sales(self, rows):
        conn = self.db.get_connection()
        cur = conn.cursor()
        sales = []
        for s in rows:
            cur.execute("SELECT * FROM sale_items WHERE sale_id = ?", (s["sale_id"],))
            items = [SaleItem(r["item_id"], r["sale_id"], r["product_id"], r["product_name"],
                              r["barcode"], r["quantity"], r["unit_price"], r["subtotal"])
                     for r in cur.fetchall()]
            sale = Sale(s["sale_id"], s["date"], s["total"],
                        s["payment_method"], s["notes"], items)
            keys = s.keys()
            sale.customer_name = s["customer_name"] if "customer_name" in keys else ""
            sale.is_credit = s["is_credit"] if "is_credit" in keys else 0
            sale.is_paid = s["is_paid"] if "is_paid" in keys else 1
            sale.amount_paid = s["amount_paid"] if "amount_paid" in keys else 0.0
            sales.append(sale)
        return sales

    def get_sales_by_day(self, date_str):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM sales WHERE date LIKE ? ORDER BY date", (f"{date_str}%",))
        return self._rows_to_sales(cur.fetchall())

    def get_sales_by_month(self, ym):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM sales WHERE date LIKE ? ORDER BY date", (f"{ym}%",))
        return self._rows_to_sales(cur.fetchall())

    def get_all_sales(self, limit=500):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM sales ORDER BY sale_id DESC LIMIT ?", (limit,))
        return self._rows_to_sales(cur.fetchall())

    def get_credit_sales(self, only_unpaid=True):
        cur = self.db.get_connection().cursor()
        if only_unpaid:
            cur.execute("SELECT * FROM sales WHERE is_credit = 1 AND is_paid = 0 "
                        "ORDER BY customer_name, date")
        else:
            cur.execute("SELECT * FROM sales WHERE is_credit = 1 ORDER BY customer_name, date")
        return self._rows_to_sales(cur.fetchall())

    def mark_as_paid(self, sale_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE sales SET is_paid = 1, amount_paid = total WHERE sale_id = ?",
                    (sale_id,))
        conn.commit()

    def add_payment(self, sale_id, amount):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT total, amount_paid FROM sales WHERE sale_id = ?", (sale_id,))
        row = cur.fetchone()
        if not row:
            return False, "Venta no encontrada"
        total = row["total"]
        current_paid = row["amount_paid"] or 0.0
        new_paid = current_paid + amount
        if new_paid > total:
            new_paid = total
        is_paid = 1 if new_paid >= total - 0.01 else 0
        cur.execute("UPDATE sales SET amount_paid = ?, is_paid = ? WHERE sale_id = ?",
                    (new_paid, is_paid, sale_id))
        conn.commit()
        return True, "Abono registrado"

    def apply_payment_to_customer(self, name, amount):
        if not name or amount <= 0:
            return 0.0, self.get_pending_by_customer(name)
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT sale_id, total, amount_paid FROM sales "
            "WHERE is_credit = 1 AND is_paid = 0 AND customer_name = ? "
            "ORDER BY sale_id ASC", (name,))
        rows = cur.fetchall()
        restante = amount
        aplicado = 0.0
        for r in rows:
            if restante <= 0:
                break
            pendiente = r["total"] - (r["amount_paid"] or 0)
            if pendiente <= 0:
                continue
            pagar = min(pendiente, restante)
            nuevo_pagado = (r["amount_paid"] or 0) + pagar
            is_paid = 1 if nuevo_pagado >= r["total"] - 0.01 else 0
            cur.execute(
                "UPDATE sales SET amount_paid = ?, is_paid = ? WHERE sale_id = ?",
                (nuevo_pagado, is_paid, r["sale_id"]))
            restante -= pagar
            aplicado += pagar
        conn.commit()
        cur.execute(
            "SELECT COALESCE(SUM(total - amount_paid), 0) t FROM sales "
            "WHERE is_credit = 1 AND is_paid = 0 AND customer_name = ?", (name,))
        saldo = cur.fetchone()["t"]
        return aplicado, saldo

    def delete_sale(self, sale_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,))
        items = cur.fetchall()
        for it in items:
            if it["product_id"]:
                cur.execute("UPDATE products SET stock = stock + ? WHERE product_id = ?",
                            (it["quantity"], it["product_id"]))
        cur.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
        cur.execute("DELETE FROM sales WHERE sale_id = ?", (sale_id,))
        conn.commit()

    def get_pending_by_customer(self, name):
        if not name:
            return 0.0
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT COALESCE(SUM(total - amount_paid), 0) t FROM sales "
            "WHERE is_credit = 1 AND is_paid = 0 AND customer_name = ?", (name,))
        return cur.fetchone()["t"]

    def group_sales_by_customer(self, sales):
        grupos = {}
        for s in sales:
            nombre = s.customer_name.strip() if s.customer_name else "(sin nombre)"
            if nombre not in grupos:
                grupos[nombre] = {
                    "customer_name": nombre,
                    "count": 0,
                    "total": 0.0,
                    "paid": 0.0,
                    "pending": 0.0,
                    "sales": []
                }
            g = grupos[nombre]
            g["count"] += 1
            g["total"] += s.total
            g["paid"] += (s.amount_paid or 0)
            g["pending"] += max(0.0, s.total - (s.amount_paid or 0))
            g["sales"].append(s)
        return sorted(grupos.values(),
                      key=lambda x: (-x["pending"], x["customer_name"].lower()))

    def get_summary(self):
        cur = self.db.get_connection().cursor()
        hoy = datetime.now().strftime("%Y-%m-%d")
        mes = datetime.now().strftime("%Y-%m")
        cur.execute("SELECT COUNT(*) c, COALESCE(SUM(total),0) t FROM sales WHERE date LIKE ?",
                    (f"{hoy}%",))
        r = cur.fetchone(); ventas_hoy, total_hoy = r["c"], r["t"]
        cur.execute("SELECT COUNT(*) c, COALESCE(SUM(total),0) t FROM sales WHERE date LIKE ?",
                    (f"{mes}%",))
        r = cur.fetchone(); ventas_mes, total_mes = r["c"], r["t"]
        cur.execute("SELECT COUNT(*) c, COALESCE(SUM(total),0) t FROM sales")
        r = cur.fetchone(); ventas_tot, total_tot = r["c"], r["t"]
        cur.execute("SELECT COUNT(*) c, COALESCE(SUM(total - amount_paid),0) t "
                    "FROM sales WHERE is_credit = 1 AND is_paid = 0")
        r = cur.fetchone(); fiados_c, fiados_t = r["c"], r["t"]
        return {
            "hoy": (ventas_hoy, total_hoy),
            "mes": (ventas_mes, total_mes),
            "total": (ventas_tot, total_tot),
            "fiados": (fiados_c, fiados_t),
        }

    # ============ NUEVO: Reiniciar contador de ventas ============
    def reset_sales_counter(self):
        """
        Elimina TODAS las ventas y fiados, y reinicia el contador AUTOINCREMENT a 1.
        Los productos del inventario NO se tocan.
        """
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sale_items")
        cur.execute("DELETE FROM sales")
        # Resetear el contador AUTOINCREMENT (si existe la tabla)
        try:
            cur.execute("DELETE FROM sqlite_sequence WHERE name = 'sales'")
        except Exception:
            pass
        try:
            cur.execute("DELETE FROM sqlite_sequence WHERE name = 'sale_items'")
        except Exception:
            pass
        conn.commit()

    # ============ BORRADOR DE CARRITO ============
    def save_cart_draft(self, items):
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data = json.dumps(items, ensure_ascii=False)
            cur.execute(
                "INSERT OR REPLACE INTO cart_draft (id, data, updated_at) VALUES (1, ?, ?)",
                (data, now))
            conn.commit()
        except Exception:
            pass

    def load_cart_draft(self):
        try:
            cur = self.db.get_connection().cursor()
            cur.execute("SELECT data, updated_at FROM cart_draft WHERE id = 1")
            row = cur.fetchone()
            if not row:
                return None, None
            items = json.loads(row["data"])
            if not items:
                return None, None
            return items, row["updated_at"]
        except Exception:
            return None, None

    def clear_cart_draft(self):
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM cart_draft WHERE id = 1")
            conn.commit()
        except Exception:
            pass