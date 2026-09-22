import json
import os
from datetime import datetime, timedelta
from domain.models.sale import Sale, SaleItem


class SaleCase:
    def __init__(self, db_manager):
        self.db = db_manager

    # ============ CONTADOR VISUAL DE VENTAS ============
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
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT COALESCE(MAX(sale_id), 0) m FROM sales")
        max_id = cur.fetchone()["m"]
        self.set_sale_number_offset(max_id)

    # ============ AUTO-RESET DIARIO ============
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

    # ============ CAJA (FASE 6) ============
    def get_or_create_today_cash_session(self):
        """Devuelve la sesión de caja de hoy. La crea si no existe."""
        hoy = datetime.now().strftime("%Y-%m-%d")
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM cash_sessions WHERE date = ?", (hoy,))
        row = cur.fetchone()
        if row:
            return dict(row)
        # Crear nueva sesión
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO cash_sessions (date, opened_at, initial_cash) VALUES (?,?,?)",
            (hoy, now, 0.0))
        conn.commit()
        session_id = cur.lastrowid
        return {
            "session_id": session_id,
            "date": hoy,
            "opened_at": now,
            "closed_at": "",
            "initial_cash": 0.0,
            "counted_cash": 0.0,
            "difference": 0.0,
            "notes": "",
        }

    def update_initial_cash(self, session_id, amount):
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE cash_sessions SET initial_cash = ? WHERE session_id = ?",
                    (float(amount), session_id))
        conn.commit()

    def update_counted_cash(self, session_id, amount, notes=""):
        """Guarda el efectivo contado y calcula la diferencia."""
        try:
            summary = self.get_cash_session_summary(session_id)
            expected = summary["expected_cash"]
            difference = float(amount) - expected
            conn = self.db.get_connection()
            cur = conn.cursor()
            cur.execute(
                "UPDATE cash_sessions SET counted_cash = ?, difference = ?, notes = ? "
                "WHERE session_id = ?",
                (float(amount), difference, notes, session_id))
            conn.commit()
            return difference
        except Exception:
            return 0.0

    def register_cash_movement(self, movement_type, amount, notes=""):
        """
        movement_type: 'retiro', 'gasto' o 'ingreso'
        """
        conn = self.db.get_connection()
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO cash_movements (date, type, amount, notes) VALUES (?,?,?,?)",
            (now, movement_type, float(amount), notes))
        conn.commit()

    def get_cash_session_summary(self, session_id=None, date_str=None):
        """
        Devuelve el cuadre completo de caja del día.
        Si no se pasa session_id, usa la sesión de hoy.
        """
        conn = self.db.get_connection()
        cur = conn.cursor()

        if session_id is not None:
            cur.execute("SELECT * FROM cash_sessions WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            if not row:
                return None
            session = dict(row)
        else:
            session = self.get_or_create_today_cash_session()

        date_str = date_str or session["date"]

        # Ventas en efectivo del día: sumar sale_payments con method = Efectivo
        cur.execute(
            "SELECT COALESCE(SUM(amount),0) t FROM sale_payments "
            "WHERE method = 'Efectivo' AND date LIKE ?", (f"{date_str}%",))
        ventas_efectivo = cur.fetchone()["t"]

        # Abonos en efectivo del día
        cur.execute(
            "SELECT COALESCE(SUM(amount),0) t FROM customer_payments "
            "WHERE method = 'Efectivo' AND date LIKE ?", (f"{date_str}%",))
        abonos_efectivo = cur.fetchone()["t"]

        # Retiros
        cur.execute(
            "SELECT COALESCE(SUM(amount),0) t FROM cash_movements "
            "WHERE type = 'retiro' AND date LIKE ?", (f"{date_str}%",))
        retiros = cur.fetchone()["t"]

        # Gastos
        cur.execute(
            "SELECT COALESCE(SUM(amount),0) t FROM cash_movements "
            "WHERE type = 'gasto' AND date LIKE ?", (f"{date_str}%",))
        gastos = cur.fetchone()["t"]

        # Ingresos manuales
        cur.execute(
            "SELECT COALESCE(SUM(amount),0) t FROM cash_movements "
            "WHERE type = 'ingreso' AND date LIKE ?", (f"{date_str}%",))
        ingresos = cur.fetchone()["t"]

        # Número de ventas del día
        cur.execute(
            "SELECT COUNT(*) c FROM sales WHERE date LIKE ?", (f"{date_str}%",))
        total_ventas_count = cur.fetchone()["c"]

        initial_cash = session.get("initial_cash", 0.0)
        expected = (initial_cash + ventas_efectivo + abonos_efectivo
                    + ingresos - retiros - gastos)

        return {
            "session_id": session["session_id"],
            "date": date_str,
            "opened_at": session.get("opened_at", ""),
            "closed_at": session.get("closed_at", ""),
            "initial_cash": initial_cash,
            "ventas_efectivo": ventas_efectivo,
            "abonos_efectivo": abonos_efectivo,
            "retiros": retiros,
            "gastos": gastos,
            "ingresos": ingresos,
            "expected_cash": expected,
            "counted_cash": session.get("counted_cash", 0.0),
            "difference": session.get("difference", 0.0),
            "total_ventas_count": total_ventas_count,
            "notes": session.get("notes", ""),
        }

    # ============ CREAR VENTA CON PAGOS MIXTOS ============
    def create_sale(self, items, payments=None,
                    payment_method="Efectivo", notes="",
                    customer_name="", is_credit=False, discount=0.0,
                    register_customer_payment_amount=0.0):
        """
        payments: lista de dicts [{method, amount}, ...] para pago mixto.
                  Si es None, se usa payment_method + amount_paid por defecto.
        register_customer_payment_amount: si > 0, registra un abono a deuda
                                          del cliente con el método principal.
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
            "INSERT INTO sales (date, total, payment_method, notes, customer_name, "
            "is_credit, is_paid, amount_paid, display_offset, discount, subtotal) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (now, total, payment_method, notes, customer_name,
             1 if is_credit else 0, is_paid, amount_paid, offset, discount, subtotal))
        sale_id = cur.lastrowid

        # Detalle de la venta
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

        # Detalle de pagos (mixto)
        if not payments:
            # Pago único (compatibilidad)
            payments = [{"method": payment_method, "amount": total}]

        for p in payments:
            m = p.get("method", "Efectivo")
            a = float(p.get("amount", 0))
            if a <= 0:
                continue
            cur.execute(
                "INSERT INTO sale_payments (sale_id, method, amount, date) "
                "VALUES (?,?,?,?)",
                (sale_id, m, a, now))

        conn.commit()
        display_number = sale_id - offset

        # Registrar abono a deuda del cliente (si aplica)
        if register_customer_payment_amount > 0 and customer_name:
            self.register_customer_payment(
                customer_name, register_customer_payment_amount,
                payment_method, None)

        return sale_id, total, display_number

    def register_customer_payment(self, customer_name, amount, method="Efectivo",
                                  sale_id=None):
        """Registra un abono a la deuda de un cliente."""
        try:
            conn = self.db.get_connection()
            cur = conn.cursor()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO customer_payments (date, customer_name, sale_id, method, amount) "
                "VALUES (?,?,?,?,?)",
                (now, customer_name, sale_id, method, float(amount)))
            conn.commit()
        except Exception:
            pass

    # ============ GENERAR TICKET PDF (FASE 6) ============
    def generate_ticket_pdf(self, sale_id, base_dir=None, action="save"):
        """
        Genera un PDF del ticket. Tamaño Carta.
        Devuelve la ruta del archivo o None.
        """
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import cm
            from reportlab.lib import colors
        except ImportError:
            return None

        # Obtener venta
        conn = self.db.get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM sales WHERE sale_id = ?", (sale_id,))
        s = cur.fetchone()
        if not s:
            return None
        keys = s.keys()

        cur.execute("SELECT * FROM sale_items WHERE sale_id = ?", (sale_id,))
        items = cur.fetchall()

        # Datos del negocio
        biz = {
            "type": self.db.get_setting("biz_type", "") or "",
            "name": self.db.get_setting("biz_name", "") or "",
            "owner": self.db.get_setting("biz_owner", "") or "",
            "place": self.db.get_setting("biz_place", "") or "",
            "phone": self.db.get_setting("biz_phone", "") or "",
        }
        biz_titulo = f"{biz['type']}, {biz['name']}" if biz['type'] and biz['name'] else (biz['name'] or "MiniPOS")

        # Ruta destino
        if base_dir is None:
            base_dir = os.path.join(os.path.dirname(self.db.db_path), "tickets")
        fecha_corta = (s["date"] or "").split(" ")[0]
        carpeta = os.path.join(base_dir, fecha_corta)
        os.makedirs(carpeta, exist_ok=True)
        display_num = s["sale_id"] - (s["display_offset"] if "display_offset" in keys else 0)
        archivo = os.path.join(carpeta, f"ticket_{display_num:04d}.pdf")

        # Crear PDF
        c = canvas.Canvas(archivo, pagesize=letter)
        w, h = letter

        # Encabezado
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(w / 2, h - 2 * cm, biz_titulo)

        c.setFont("Helvetica", 11)
        y = h - 3 * cm
        if biz["place"]:
            c.drawCentredString(w / 2, y, biz["place"]); y -= 0.5 * cm
        if biz["phone"]:
            c.drawCentredString(w / 2, y, f"Tel: {biz['phone']}"); y -= 0.5 * cm
        if biz["owner"]:
            c.drawCentredString(w / 2, y, f"Atendido por: {biz['owner']}"); y -= 0.5 * cm

        y -= 0.3 * cm
        c.setLineWidth(1)
        c.line(2 * cm, y, w - 2 * cm, y)
        y -= 0.6 * cm

        # Info de la venta
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, f"TICKET DE VENTA #{display_num:02d}")
        y -= 0.6 * cm
        c.setFont("Helvetica", 10)
        c.drawString(2 * cm, y, f"Fecha: {s['date']}")
        c.drawString(w - 8 * cm, y, f"Método principal: {s['payment_method']}")
        y -= 0.5 * cm
        if s["customer_name"]:
            c.drawString(2 * cm, y, f"Cliente: {s['customer_name']}")
            y -= 0.5 * cm
        if s["is_credit"]:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(2 * cm, y, f"*** VENTA FIADA ***")
            y -= 0.5 * cm
            c.setFont("Helvetica", 10)

        y -= 0.3 * cm
        c.line(2 * cm, y, w - 2 * cm, y)
        y -= 0.6 * cm

        # Encabezados de la tabla
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2 * cm, y, "Cant.")
        c.drawString(4 * cm, y, "Producto")
        c.drawRightString(w - 4.5 * cm, y, "P.Unit")
        c.drawRightString(w - 2 * cm, y, "Subtotal")
        y -= 0.4 * cm
        c.line(2 * cm, y, w - 2 * cm, y)
        y -= 0.5 * cm

        c.setFont("Helvetica", 10)
        for it in items:
            cantidad = it["quantity"]
            nombre = it["product_name"] or ""
            if len(nombre) > 40:
                nombre = nombre[:38] + "..."
            c.drawString(2 * cm, y, f"{cantidad:g}")
            c.drawString(4 * cm, y, nombre)
            c.drawRightString(w - 4.5 * cm, y,
                              f"${it['unit_price']:,.0f}".replace(",", "."))
            c.drawRightString(w - 2 * cm, y,
                              f"${it['subtotal']:,.0f}".replace(",", "."))
            y -= 0.55 * cm
            if y < 4 * cm:
                c.showPage()
                y = h - 2 * cm
                c.setFont("Helvetica", 10)

        y -= 0.2 * cm
        c.line(2 * cm, y, w - 2 * cm, y)
        y -= 0.7 * cm

        # Totales
        c.setFont("Helvetica", 11)
        subtotal = s["subtotal"] if "subtotal" in keys else s["total"]
        descuento = s["discount"] if "discount" in keys else 0.0
        c.drawRightString(w - 4.5 * cm, y, "Subtotal:")
        c.drawRightString(w - 2 * cm, y, f"${subtotal:,.0f}".replace(",", "."))
        y -= 0.6 * cm
        if descuento and descuento > 0:
            c.drawRightString(w - 4.5 * cm, y, "Descuento:")
            c.drawRightString(w - 2 * cm, y, f"-${descuento:,.0f}".replace(",", "."))
            y -= 0.6 * cm
        c.setFont("Helvetica-Bold", 14)
        c.drawRightString(w - 4.5 * cm, y, "TOTAL:")
        c.drawRightString(w - 2 * cm, y, f"${s['total']:,.0f}".replace(",", "."))
        y -= 1 * cm

        # Desglose de pagos (si es mixto)
        cur.execute("SELECT method, amount FROM sale_payments WHERE sale_id = ?",
                    (sale_id,))
        pagos = cur.fetchall()
        if pagos:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(2 * cm, y, "Formas de pago:")
            y -= 0.5 * cm
            c.setFont("Helvetica", 10)
            for p in pagos:
                c.drawString(3 * cm, y, f"• {p['method']}")
                c.drawRightString(w - 2 * cm, y,
                                  f"${p['amount']:,.0f}".replace(",", "."))
                y -= 0.5 * cm

        # Pie
        c.setFont("Helvetica-Oblique", 9)
        c.drawCentredString(w / 2, 2 * cm, "¡Gracias por su compra!")

        c.save()
        return archivo

    # ============ RESTO DE MÉTODOS (existentes) ============
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
            offset = s["display_offset"] if "display_offset" in keys else 0
            sale.display_number = s["sale_id"] - (offset or 0)
            sale.discount = s["discount"] if "discount" in keys else 0.0
            sale.subtotal = s["subtotal"] if "subtotal" in keys else s["total"]
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

    def add_payment(self, sale_id, amount, method="Efectivo", customer_name=""):
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
        # Registrar el abono
        if customer_name:
            self.register_customer_payment(customer_name, amount, method, sale_id)
        return True, "Abono registrado"

    def apply_payment_to_customer(self, name, amount, method="Efectivo"):
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
        # Registrar el abono en customer_payments
        self.register_customer_payment(name, aplicado, method, None)
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
        cur.execute("DELETE FROM sale_payments WHERE sale_id = ?", (sale_id,))
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

    def get_cash_closing(self, date_str):
        """Cierre de caja (del día pedido). Reutiliza get_cash_session_summary."""
        # Buscar sesión por fecha
        cur = self.db.get_connection().cursor()
        cur.execute("SELECT * FROM cash_sessions WHERE date = ?", (date_str,))
        row = cur.fetchone()
        if row:
            summary = self.get_cash_session_summary(session_id=row["session_id"])
        else:
            summary = self.get_cash_session_summary(date_str=date_str)

        # Agregar datos adicionales para compatibilidad
        sales = self.get_sales_by_day(date_str)
        metodos = {}
        for s in sales:
            cur.execute("SELECT method, amount FROM sale_payments WHERE sale_id = ?",
                        (s.sale_id,))
            pagos = cur.fetchall()
            for p in pagos:
                m = p["method"] or "Otro"
                if m not in metodos:
                    metodos[m] = {"count": 0, "total": 0.0}
                metodos[m]["total"] += p["amount"]
            # Contar por venta
            if s.payment_method not in metodos:
                metodos[s.payment_method] = {"count": 0, "total": 0.0}
            metodos[s.payment_method]["count"] += 1

        total_ventas = sum(s.total for s in sales)
        total_subtotal = sum(getattr(s, "subtotal", s.total) for s in sales)
        total_descuento = sum(getattr(s, "discount", 0.0) for s in sales)
        productos_vendidos = sum(sum(it.quantity for it in s.items) for s in sales)
        total_fiado_nuevo = sum(s.total for s in sales if s.is_credit)
        total_abonos = sum(s.amount_paid for s in sales if not s.is_credit)

        return {
            "date": date_str,
            "cantidad_ventas": len(sales),
            "total_ventas": total_ventas,
            "total_subtotal": total_subtotal,
            "total_descuento": total_descuento,
            "productos_vendidos": productos_vendidos,
            "metodos": metodos,
            "total_fiado_nuevo": total_fiado_nuevo,
            "total_abonos": total_abonos,
            "efectivo_esperado": summary["expected_cash"] if summary else 0.0,
            # Extras de la sesión
            "initial_cash": summary["initial_cash"] if summary else 0.0,
            "retiros": summary["retiros"] if summary else 0.0,
            "gastos": summary["gastos"] if summary else 0.0,
            "ingresos": summary["ingresos"] if summary else 0.0,
            "counted_cash": summary["counted_cash"] if summary else 0.0,
            "difference": summary["difference"] if summary else 0.0,
        }

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