import json
from datetime import datetime, timedelta
from domain.models.sale import Sale, SaleItem


class SaleCase:
    def __init__(self, db_manager):
        self.db = db_manager

    # ============================================================
    # CONTADOR VISUAL DE VENTAS
    # ============================================================
    def get_sale_number_offset(self):
        try:
            val = self.db.get_setting("sale_number_offset", "0")
            return int(val or "0")
        except Exception:
            return 0

    def set_sale_number_offset(self, value):
        try:
            self.db.set_setting("sale_number_offset", str(int(value)))
        except Exception:
            pass

    def reset_sale_number_counter(self):
        """Reinicia el contador VISUAL a #01 sin borrar datos."""
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT COALESCE(MAX(sale_id), 0) m FROM sales")
        max_id = cur.fetchone()["m"]
        self.set_sale_number_offset(max_id)

    # ============================================================
    # AUTO-RESET DIARIO (Fase 2)
    # ============================================================
    def is_auto_reset_enabled(self):
        try:
            return self.db.get_setting("auto_reset_enabled", "1") == "1"
        except Exception:
            return True

    def enable_auto_reset(self, enabled):
        try:
            self.db.set_setting("auto_reset_enabled", "1" if enabled else "0")
        except Exception:
            pass

    def get_last_reset_date(self):
        try:
            return self.db.get_setting("last_sale_reset_date", "") or ""
        except Exception:
            return ""

    def set_last_reset_date(self, date_str):
        try:
            self.db.set_setting("last_sale_reset_date", date_str)
        except Exception:
            pass

    def auto_reset_if_new_day(self):
        try:
            if not self.is_auto_reset_enabled():
                return False
            hoy = datetime.now().strftime("%Y-%m-%d")
            last = self.get_last_reset_date()
            if last == hoy:
                return False
            self.reset_sale_number_counter()
            self.set_last_reset_date(hoy)
            return True
        except Exception:
            return False

    # ============================================================
    # CREAR VENTA (con pago mixto, idea 3)
    # ============================================================
    def create_sale(self, items, payment_method="Efectivo", notes="",
                    customer_name="", is_credit=False, discount=0.0,
                    payments=None):
        """
        payments: lista opcional de dicts [{"method": "Efectivo", "amount": 5000}, ...]
        Si se pasa con >1 método, se guarda el desglose en sale_payments.
        """
        conn = self.db.get_connection()
        cur = conn.cursor()
        subtotal = sum(i["quantity"] * i["unit_price"] for i in items)
        discount = max(0.0, float(discount or 0))
        if discount > subtotal:
            discount = subtotal
        total = subtotal - discount
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        is_paid = 0 if is_credit else 1
        amount_paid = 0.0 if is_credit else total
        offset = self.get_sale_number_offset()

        cur.execute(
            "INSERT INTO sales (date, total, subtotal, discount, payment_method, "
            "notes, customer_name, is_credit, is_paid, amount_paid, display_offset) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (now, total, subtotal, discount, payment_method, notes, customer_name,
             1 if is_credit else 0, is_paid, amount_paid, offset))
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

        # Desglose de pagos mixtos
        if payments and len(payments) > 1:
            for p in payments:
                cur.execute(
                    "INSERT INTO sale_payments (sale_id, method, amount) VALUES (?,?,?)",
                    (sale_id, p.get("method", "Otro"), p.get("amount", 0)))

        conn.commit()
        display_number = sale_id - offset
        return sale_id, total, display_number

    def get_sale_payments(self, sale_id):
        """Devuelve lista de pagos de una venta."""
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT method, amount FROM sale_payments WHERE sale_id = ?", (sale_id,))
        return [{"method": r["method"], "amount": r["amount"]} for r in cur.fetchall()]

    # ============================================================
    # CONVERSIÓN FILAS → OBJETOS
    # ============================================================
    def _rows_to_sales(self, rows):
        conn = self.db.get_connection()
        cur = conn.cursor()
        sales = []
        for s in rows:
            cur.execute("SELECT * FROM sale_items WHERE sale_id = ?", (s["sale_id"],))
            items = []
            for r in cur.fetchall():
                keys = r.keys()
                items.append(SaleItem(
                    r["item_id"], r["sale_id"], r["product_id"], r["product_name"],
                    r["barcode"] if "barcode" in keys else "",
                    r["quantity"], r["unit_price"], r["subtotal"],
                    r["returned_qty"] if "returned_qty" in keys else 0))
            sale = Sale(s["sale_id"], s["date"], s["total"],
                        s["payment_method"], s["notes"], items)
            keys = s.keys()
            sale.customer_name = s["customer_name"] if "customer_name" in keys else ""
            sale.is_credit = s["is_credit"] if "is_credit" in keys else 0
            sale.is_paid = s["is_paid"] if "is_paid" in keys else 1
            sale.amount_paid = s["amount_paid"] if "amount_paid" in keys else 0.0
            offset = s["display_offset"] if "display_offset" in keys else 0
            sale.display_number = s["sale_id"] - (offset or 0)
            sale.discount = s["discount"] if "discount" in keys else 0.0
            sale.subtotal = s["subtotal"] if "subtotal" in keys else s["total"]
            sale.is_returned = s["is_returned"] if "is_returned" in keys else 0
            sales.append(sale)
        return sales

    # ============================================================
    # CONSULTAS DE VENTAS
    # ============================================================
    def get_sales_by_day(self, date_str):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM sales WHERE date LIKE ? ORDER BY date", (f"{date_str}%",))
        return self._rows_to_sales(cur.fetchall())

    def get_sales_by_month(self, ym):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM sales WHERE date LIKE ? ORDER BY date", (f"{ym}%",))
        return self._rows_to_sales(cur.fetchall())

    def get_sales_by_range(self, start_date, end_date):
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT * FROM sales WHERE date(date) BETWEEN ? AND ? ORDER BY date",
            (start_date, end_date))
        return self._rows_to_sales(cur.fetchall())

    def get_all_sales(self, limit=500):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM sales ORDER BY sale_id DESC LIMIT ?", (limit,))
        return self._rows_to_sales(cur.fetchall())

    def get_sale_by_id(self, sale_id):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM sales WHERE sale_id = ?", (sale_id,))
        rows = cur.fetchall()
        if not rows:
            return None
        sales = self._rows_to_sales(rows)
        return sales[0] if sales else None

    def get_credit_sales(self, only_unpaid=True):
        cur = self.db.get_connection().cursor()
        if only_unpaid:
            cur.execute("SELECT * FROM sales WHERE is_credit = 1 AND is_paid = 0 "
                        "ORDER BY customer_name, date")
        else:
            cur.execute("SELECT * FROM sales WHERE is_credit = 1 ORDER BY customer_name, date")
        return self._rows_to_sales(cur.fetchall())

    # ============================================================
    # FIADOS / ABONOS
    # ============================================================
    def mark_as_paid(self, sale_id):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE sales SET is_paid = 1, amount_paid = total WHERE sale_id = ?",
                    (sale_id,))
        conn.commit()

    def add_payment(self, sale_id, amount, method=None, customer_name=""):
        """Registra un abono a una venta (fiado)."""
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

    # ============================================================
    # ELIMINAR VENTA
    # ============================================================
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
        cur.execute("DELETE FROM sale_payments WHERE sale_id = ?", (sale_id,))
        cur.execute("DELETE FROM returns WHERE sale_id = ?", (sale_id,))
        cur.execute("DELETE FROM sales WHERE sale_id = ?", (sale_id,))
        conn.commit()

    # ============================================================
    # IDEA 10: DEVOLUCIONES
    # ============================================================
    def register_return(self, sale_id, items_to_return, reason="", return_type="producto"):
        """
        items_to_return: [{"item_id": X, "quantity": N}, ...]
        Restaura stock, actualiza returned_qty, guarda en returns/return_items.
        Si todos los items quedan devueltos, marca venta como is_returned=1.
        Devuelve (ok, mensaje, total_devuelto).
        """
        conn = self.db.get_connection()
        cur = conn.cursor()

        cur.execute("SELECT sale_id FROM sales WHERE sale_id = ?", (sale_id,))
        if not cur.fetchone():
            return False, "Venta no encontrada", 0.0
        if not items_to_return:
            return False, "No hay productos para devolver", 0.0

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_devuelto = 0.0
        items_validos = []

        for it in items_to_return:
            item_id = it.get("item_id")
            qty = float(it.get("quantity", 0) or 0)
            if qty <= 0:
                continue
            cur.execute("SELECT * FROM sale_items WHERE item_id = ? AND sale_id = ?",
                        (item_id, sale_id))
            row = cur.fetchone()
            if not row:
                continue
            keys = row.keys()
            ya_devuelto = row["returned_qty"] if "returned_qty" in keys else 0
            pendiente = row["quantity"] - (ya_devuelto or 0)
            if qty > pendiente:
                qty = pendiente
            if qty <= 0:
                continue
            sub = qty * row["unit_price"]
            total_devuelto += sub
            items_validos.append({
                "item_id": item_id,
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "quantity": qty,
                "unit_price": row["unit_price"],
                "subtotal": sub,
            })

        if not items_validos:
            return False, "Nada por devolver (ya devuelto o cantidades inválidas)", 0.0

        cur.execute(
            "INSERT INTO returns (sale_id, date, reason, total_returned, return_type) "
            "VALUES (?,?,?,?,?)",
            (sale_id, now, reason, total_devuelto, return_type))
        return_id = cur.lastrowid

        for it in items_validos:
            cur.execute(
                "INSERT INTO return_items (return_id, product_id, product_name, "
                "quantity, unit_price, subtotal) VALUES (?,?,?,?,?,?)",
                (return_id, it["product_id"], it["product_name"],
                 it["quantity"], it["unit_price"], it["subtotal"]))
            cur.execute(
                "UPDATE sale_items SET returned_qty = COALESCE(returned_qty, 0) + ? "
                "WHERE item_id = ?",
                (it["quantity"], it["item_id"]))
            if it["product_id"]:
                cur.execute("UPDATE products SET stock = stock + ? WHERE product_id = ?",
                            (it["quantity"], it["product_id"]))

        cur.execute(
            "SELECT COUNT(*) c FROM sale_items "
            "WHERE sale_id = ? AND COALESCE(returned_qty, 0) < quantity",
            (sale_id,))
        pendientes = cur.fetchone()["c"]
        if pendientes == 0:
            cur.execute("UPDATE sales SET is_returned = 1 WHERE sale_id = ?", (sale_id,))

        conn.commit()
        return True, f"Devolución registrada (${total_devuelto:,.0f})", total_devuelto

    def get_returns_by_sale(self, sale_id):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM returns WHERE sale_id = ? ORDER BY date DESC", (sale_id,))
        rows = cur.fetchall()
        result = []
        for r in rows:
            cur.execute("SELECT * FROM return_items WHERE return_id = ?", (r["return_id"],))
            items = [dict(x) for x in cur.fetchall()]
            result.append({
                "return_id": r["return_id"],
                "sale_id": r["sale_id"],
                "date": r["date"],
                "reason": r["reason"],
                "total_returned": r["total_returned"],
                "return_type": r["return_type"],
                "items": items,
            })
        return result

    def get_returns_by_day(self, date_str):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM returns WHERE date LIKE ? ORDER BY date", (f"{date_str}%",))
        return [dict(r) for r in cur.fetchall()]

    def get_returns_by_range(self, start_date, end_date):
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT * FROM returns WHERE date(date) BETWEEN ? AND ? ORDER BY date",
            (start_date, end_date))
        return [dict(r) for r in cur.fetchall()]

    def get_product_return_count(self, product_id, product_name=None):
        """Cuenta cuántas veces se ha devuelto un producto."""
        cur = self.db.get_connection().cursor()
        if product_id:
            cur.execute(
                "SELECT COUNT(*) c FROM return_items WHERE product_id = ?", (product_id,))
        else:
            cur.execute(
                "SELECT COUNT(*) c FROM return_items WHERE product_name = ?",
                (product_name or "",))
        row = cur.fetchone()
        return row["c"] if row else 0

    def get_returned_total_by_day(self, date_str):
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT COALESCE(SUM(total_returned), 0) t FROM returns WHERE date LIKE ?",
            (f"{date_str}%",))
        return cur.fetchone()["t"]

    # ============================================================
    # RESUMEN
    # ============================================================
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

    # ============================================================
    # CIERRE DE CAJA (Fase 6)
    # ============================================================
    def get_cash_closing(self, date_str):
        try:
            sales = self.get_sales_by_day(date_str)
        except Exception:
            sales = []

        metodos = {}
        total_ventas = 0.0
        total_subtotal = 0.0
        total_descuento = 0.0
        total_fiado_nuevo = 0.0
        total_abonos = 0.0
        cantidad_ventas = len(sales)
        productos_vendidos = 0

        for s in sales:
            total_ventas += s.total
            total_subtotal += (s.subtotal if hasattr(s, "subtotal") else s.total)
            total_descuento += (s.discount if hasattr(s, "discount") else 0.0)
            productos_vendidos += sum(it.quantity for it in s.items)

            pagos = self.get_sale_payments(s.sale_id)
            if pagos:
                for p in pagos:
                    m = p["method"]
                    if m not in metodos:
                        metodos[m] = {"count": 0, "total": 0.0}
                    metodos[m]["total"] += p["amount"]
                principal = s.payment_method or "Otro"
                if principal not in metodos:
                    metodos[principal] = {"count": 0, "total": 0.0}
                metodos[principal]["count"] += 1
            else:
                metodo = s.payment_method or "Otro"
                if metodo not in metodos:
                    metodos[metodo] = {"count": 0, "total": 0.0}
                metodos[metodo]["count"] += 1
                metodos[metodo]["total"] += s.total

            if s.is_credit:
                total_fiado_nuevo += s.total
            else:
                total_abonos += (s.amount_paid or 0.0)

        # Sesión de caja y movimientos
        session = self.get_cash_session_by_date(date_str)
        initial_cash = session["initial_amount"] if session else 0.0
        counted_cash = session["final_counted"] if session else 0.0
        mov = self.get_cash_movements_by_date(date_str)
        ingresos = sum(m["amount"] for m in mov if m["type"] == "ingreso")
        retiros = sum(m["amount"] for m in mov if m["type"] == "retiro")
        gastos = sum(m["amount"] for m in mov if m["type"] == "gasto")

        efectivo_ventas = metodos.get("Efectivo", {}).get("total", 0.0)
        abonos_efectivo = 0.0  # Se puede refinar con pagos de abonos
        total_devuelto = self.get_returned_total_by_day(date_str)

        # Efectivo esperado
        efectivo_esperado = (initial_cash + efectivo_ventas + abonos_efectivo
                             + ingresos - retiros - gastos - total_devuelto)

        difference = (counted_cash - efectivo_esperado) if counted_cash else 0.0

        return {
            "date": date_str,
            "cantidad_ventas": cantidad_ventas,
            "total_ventas": total_ventas,
            "total_subtotal": total_subtotal,
            "total_descuento": total_descuento,
            "productos_vendidos": productos_vendidos,
            "metodos": metodos,
            "total_fiado_nuevo": total_fiado_nuevo,
            "total_abonos": total_abonos,
            "total_devuelto": total_devuelto,
            "efectivo_esperado": efectivo_esperado,
            "initial_cash": initial_cash,
            "counted_cash": counted_cash,
            "difference": difference,
            "ingresos": ingresos,
            "retiros": retiros,
            "gastos": gastos,
        }

    # ============================================================
    # SESIONES DE CAJA (idea 2)
    # ============================================================
    def get_current_cash_session(self):
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM cash_sessions WHERE is_open = 1 "
                    "ORDER BY session_id DESC LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None
        return {
            "session_id": row["session_id"],
            "open_date": row["open_date"],
            "close_date": row["close_date"],
            "initial_amount": row["initial_amount"],
            "final_expected": row["final_expected"],
            "final_counted": row["final_counted"],
            "difference": row["difference"],
            "notes": row["notes"],
            "is_open": row["is_open"],
        }

    def get_cash_session_by_date(self, date_str):
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT * FROM cash_sessions WHERE date(open_date) = ? "
            "ORDER BY session_id DESC LIMIT 1", (date_str,))
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)

    def get_or_create_today_cash_session(self):
        """Devuelve la sesión abierta de hoy o la crea con base 0."""
        hoy = datetime.now().strftime("%Y-%m-%d")
        # Buscar sesión de hoy (abierta o cerrada)
        session = self.get_cash_session_by_date(hoy)
        if session:
            return session
        # Buscar sesión abierta de un día anterior (y cerrarla)
        current = self.get_current_cash_session()
        if current:
            return current
        # Crear nueva
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO cash_sessions (open_date, initial_amount, notes, is_open) "
            "VALUES (?,?,?,1)",
            (now, 0.0, ""))
        conn.commit()
        return self.get_cash_session_by_date(hoy)

    def open_cash_session(self, initial_amount, notes=""):
        current = self.get_current_cash_session()
        if current:
            return current
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO cash_sessions (open_date, initial_amount, notes, is_open) "
            "VALUES (?,?,?,1)",
            (now, float(initial_amount or 0), notes))
        conn.commit()
        return self.get_current_cash_session()

    def update_counted_cash(self, session_id, counted_amount, notes=""):
        """Registra el efectivo contado en una sesión."""
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT initial_amount, open_date FROM cash_sessions WHERE session_id = ?",
            (session_id,))
        row = cur.fetchone()
        if not row:
            return False, "Sesión no encontrada"
        # Calcular esperado
        date_str = row["open_date"][:10]
        closing = self.get_cash_closing(date_str)
        expected = closing["efectivo_esperado"]
        difference = float(counted_amount or 0) - expected
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "UPDATE cash_sessions SET close_date=?, final_expected=?, "
            "final_counted=?, difference=?, notes=? WHERE session_id=?",
            (now, expected, float(counted_amount or 0), difference,
             notes or "", session_id))
        conn.commit()
        return True, "Efectivo contado registrado"

    def close_cash_session(self, counted_amount, notes=""):
        session = self.get_current_cash_session()
        if not session:
            return None
        hoy = datetime.now().strftime("%Y-%m-%d")
        closing = self.get_cash_closing(hoy)
        esperado = closing["efectivo_esperado"]
        diferencia = float(counted_amount or 0) - esperado

        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "UPDATE cash_sessions SET close_date=?, final_expected=?, "
            "final_counted=?, difference=?, notes=?, is_open=0 WHERE session_id=?",
            (now, esperado, float(counted_amount or 0), diferencia,
             notes or session["notes"], session["session_id"]))
        conn.commit()
        return {
            "session_id": session["session_id"],
            "open_date": session["open_date"],
            "close_date": now,
            "initial_amount": session["initial_amount"],
            "final_expected": esperado,
            "final_counted": float(counted_amount or 0),
            "difference": diferencia,
            "notes": notes,
        }

    def has_open_cash_session(self):
        return self.get_current_cash_session() is not None

    def get_cash_sessions_by_range(self, start_date, end_date):
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT * FROM cash_sessions WHERE date(open_date) BETWEEN ? AND ? "
            "ORDER BY open_date DESC", (start_date, end_date))
        return [dict(r) for r in cur.fetchall()]

    def get_cash_session_summary(self, session_id=None):
        """Resumen de la sesión de caja (para cuadre)."""
        if session_id:
            cur = self.db.get_connection().cursor()
            cur.execute("SELECT * FROM cash_sessions WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            if not row:
                return None
            date_str = row["open_date"][:10]
        else:
            session = self.get_current_cash_session()
            if not session:
                return None
            session_id = session["session_id"]
            date_str = session["open_date"][:10]

        closing = self.get_cash_closing(date_str)
        return {
            "session_id": session_id,
            "date": date_str,
            "expected_cash": closing["efectivo_esperado"],
            "initial_cash": closing["initial_cash"],
            "counted_cash": closing["counted_cash"],
            "difference": closing["difference"],
            "movements": self.get_cash_movements(session_id),
        }

    # ============================================================
    # MOVIMIENTOS DE CAJA (Fase 6)
    # ============================================================
    def register_cash_movement(self, type_, amount, notes=""):
        """Registra un movimiento: 'ingreso', 'retiro' o 'gasto'."""
        if type_ not in ("ingreso", "retiro", "gasto"):
            return False, "Tipo inválido"
        amount = float(amount or 0)
        if amount <= 0:
            return False, "Monto inválido"
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        session = self.get_current_cash_session()
        session_id = session["session_id"] if session else None
        cur.execute(
            "INSERT INTO cash_movements (session_id, date, type, amount, notes) "
            "VALUES (?,?,?,?,?)",
            (session_id, now, type_, amount, notes))
        conn.commit()
        return True, "Movimiento registrado"

    def get_cash_movements(self, session_id=None):
        cur = self.db.get_connection().cursor()
        if session_id:
            cur.execute("SELECT * FROM cash_movements WHERE session_id = ? ORDER BY date",
                        (session_id,))
        else:
            cur.execute("SELECT * FROM cash_movements ORDER BY date DESC LIMIT 100")
        return [dict(r) for r in cur.fetchall()]

    def get_cash_movements_by_date(self, date_str):
        cur = self.db.get_connection().cursor()
        cur.execute(
            "SELECT * FROM cash_movements WHERE date LIKE ? ORDER BY date",
            (f"{date_str}%",))
        return [dict(r) for r in cur.fetchall()]

    # ============================================================
    # IDEA 11: DATOS PARA GRÁFICOS
    # ============================================================
    def get_top_products(self, limit=10, start_date=None, end_date=None):
        """Top N productos por cantidad vendida."""
        cur = self.db.get_connection().cursor()
        sql = '''
            SELECT si.product_id,
                   si.product_name,
                   SUM(si.quantity) AS quantity,
                   SUM(si.subtotal) AS total
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
        '''
        params = []
        where = []
        if start_date and end_date:
            where.append("date(s.date) BETWEEN ? AND ?")
            params.extend([start_date, end_date])
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " GROUP BY si.product_id, si.product_name ORDER BY quantity DESC LIMIT ?"
        params.append(int(limit))

        cur.execute(sql, params)
        rows = cur.fetchall()

        result = []
        for r in rows:
            profit = 0.0
            if r["product_id"]:
                cur.execute("SELECT cost FROM products WHERE product_id = ?",
                            (r["product_id"],))
                pr = cur.fetchone()
                cost = pr["cost"] if pr else 0.0
                profit = (r["total"] or 0) - (cost * (r["quantity"] or 0))
            result.append({
                "product_id": r["product_id"],
                "product_name": r["product_name"],
                "quantity": r["quantity"] or 0,
                "total": r["total"] or 0.0,
                "profit": profit,
            })
        return result

    def get_sales_last_days(self, days=7):
        hoy = datetime.now().date()
        resultado = []
        for i in range(days - 1, -1, -1):
            dia = hoy - timedelta(days=i)
            ds = dia.strftime("%Y-%m-%d")
            cur = self.db.get_connection().cursor()
            cur.execute(
                "SELECT COUNT(*) c, COALESCE(SUM(total),0) t FROM sales "
                "WHERE date(date) = ?", (ds,))
            r = cur.fetchone()
            resultado.append({
                "date": ds,
                "count": r["c"] or 0,
                "total": r["t"] or 0.0,
            })
        return resultado

    def get_sales_by_hour(self, start_date=None, end_date=None):
        cur = self.db.get_connection().cursor()
        sql = '''
            SELECT strftime('%H', date) AS hour,
                   COUNT(*) AS count,
                   COALESCE(SUM(total), 0) AS total
            FROM sales
        '''
        params = []
        if start_date and end_date:
            sql += " WHERE date(date) BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        sql += " GROUP BY hour"

        cur.execute(sql, params)
        rows = cur.fetchall()
        data = {int(r["hour"]): {"count": r["count"], "total": r["total"]}
                for r in rows if r["hour"] is not None}
        return [{
            "hour": h,
            "count": data.get(h, {}).get("count", 0),
            "total": data.get(h, {}).get("total", 0.0),
        } for h in range(24)]

    def get_profit_summary(self, start_date=None, end_date=None):
        """Ganancias reales: venta - costo, en un rango."""
        cur = self.db.get_connection().cursor()
        sql = '''
            SELECT si.product_id, si.quantity, si.subtotal
            FROM sale_items si
            JOIN sales s ON si.sale_id = s.sale_id
        '''
        params = []
        if start_date and end_date:
            sql += " WHERE date(s.date) BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        cur.execute(sql, params)
        rows = cur.fetchall()

        total_sales = 0.0
        total_cost = 0.0
        for r in rows:
            total_sales += r["subtotal"] or 0.0
            if r["product_id"]:
                cur.execute("SELECT cost FROM products WHERE product_id = ?",
                            (r["product_id"],))
                pr = cur.fetchone()
                cost = pr["cost"] if pr else 0.0
                total_cost += cost * (r["quantity"] or 0)

        # Restar devoluciones
        sql_dev = "SELECT COALESCE(SUM(total_returned), 0) t FROM returns"
        params_dev = []
        if start_date and end_date:
            sql_dev += " WHERE date(date) BETWEEN ? AND ?"
            params_dev.extend([start_date, end_date])
        cur.execute(sql_dev, params_dev)
        total_returns = cur.fetchone()["t"] or 0.0

        total_profit = total_sales - total_cost
        net_profit = total_profit - total_returns

        return {
            "total_sales": total_sales,
            "total_cost": total_cost,
            "total_profit": total_profit,
            "total_returns": total_returns,
            "net_profit": net_profit,
        }

    def get_daily_profit_last_days(self, days=7):
        hoy = datetime.now().date()
        resultado = []
        for i in range(days - 1, -1, -1):
            dia = hoy - timedelta(days=i)
            ds = dia.strftime("%Y-%m-%d")
            res = self.get_profit_summary(ds, ds)
            resultado.append({
                "date": ds,
                "sales": res["total_sales"],
                "cost": res["total_cost"],
                "profit": res["total_profit"],
            })
        return resultado

    # ============================================================
    # TICKET PDF (método interno de SaleCase)
    # ============================================================
    def generate_ticket_pdf(self, sale_id, base_dir=None):
        """Genera un PDF del ticket de una venta. Devuelve la ruta."""
        try:
            sale = self.get_sale_by_id(sale_id)
            if not sale:
                return None
            payments = self.get_sale_payments(sale_id)
            from presentation.views.widgets import generate_ticket_pdf as _gen
            return _gen(sale, sale.items, payments=payments,
                        output_path=None)
        except Exception as e:
            print(f"Error generate_ticket_pdf: {e}")
            return None

    # ============================================================
    # BORRADOR DE CARRITO
    # ============================================================
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