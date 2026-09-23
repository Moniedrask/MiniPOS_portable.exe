import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from application.use_case.sale_use_case import SaleCase
from application.use_case.product_use_case import ProductCase


class PaymentView(tk.Toplevel):
    def __init__(self, master, sale_case: SaleCase, product_case: ProductCase,
                 on_sale_done=None, cashier_name=""):
        super().__init__(master)
        self.sale_case = sale_case
        self.product_case = product_case
        self.on_sale_done = on_sale_done
        self.cashier_name = cashier_name

        self.title("Punto de Venta")
        self.geometry("1200x720")
        self.minsize(1000, 600)

        # Estado
        self.cart = []  # lista de dicts
        self.last_sale_id = None
        self.last_sale = None
        self.last_sale_items = []

        self._build()

        # Cargar borrador si existe
        self._try_load_draft()

        # Aviso de caja
        self._check_cash_session()

    # ============================================================
    # INTERFAZ
    # ============================================================
    def _build(self):
        # ===== Barra superior =====
        top = tk.Frame(self, bg="#1e88e5", height=50)
        top.pack(fill="x")

        tk.Label(top, text="🛒 PUNTO DE VENTA", bg="#1e88e5", fg="white",
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=15, pady=10)

        self.lbl_cash_status = tk.Label(top, text="", bg="#1e88e5", fg="white",
                                        font=("Segoe UI", 10, "bold"))
        self.lbl_cash_status.pack(side="right", padx=15)

        # ===== Cuerpo dividido =====
        body = tk.Frame(self)
        body.pack(fill="both", expand=True)

        # ----- Izquierda: búsqueda y productos -----
        left = tk.Frame(body, bg="#f5f5f5")
        left.pack(side="left", fill="both", expand=True)

        # Búsqueda
        search_frame = tk.Frame(left, bg="#f5f5f5")
        search_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(search_frame, text="🔍 Buscar (F3):", bg="#f5f5f5",
                 font=("Segoe UI", 10, "bold")).pack(side="left")
        self.var_search = tk.StringVar()
        self.var_search.trace_add("write", lambda *a: self.apply_filter())
        self.entry_search = tk.Entry(search_frame, textvariable=self.var_search,
                                      font=("Segoe UI", 12), width=35)
        self.entry_search.pack(side="left", padx=8)
        self.entry_search.bind("<Return>", lambda e: self.add_first_filtered())

        tk.Button(search_frame, text="➕ Agregar", command=self.add_first_filtered,
                  bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                  padx=12, pady=4, relief="flat").pack(side="left", padx=4)

        # Lista de productos
        list_frame = tk.Frame(left)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = ("id", "name", "price", "stock", "unit")
        self.tree_products = ttk.Treeview(list_frame, columns=cols,
                                          show="headings", selectmode="browse")
        for c, t, w in [("id", "ID", 50), ("name", "Producto", 260),
                        ("price", "Precio", 100), ("stock", "Stock", 70),
                        ("unit", "Unidad", 70)]:
            self.tree_products.heading(c, text=t)
            self.tree_products.column(c, width=w,
                                       anchor="w" if c == "name" else "center")
        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                            command=self.tree_products.yview)
        self.tree_products.configure(yscrollcommand=vsb.set)
        self.tree_products.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree_products.bind("<Double-1>", lambda e: self.add_selected())
        self.tree_products.bind("<Return>", lambda e: self.add_selected())

        # ----- Derecha: carrito y cobro -----
        right = tk.Frame(body, bg="#ffffff", width=420)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="🧾 Carrito", bg="#ffffff",
                 font=("Segoe UI", 12, "bold")).pack(pady=8)

        cart_frame = tk.Frame(right)
        cart_frame.pack(fill="both", expand=True, padx=8)

        ccols = ("name", "qty", "price", "sub")
        self.tree_cart = ttk.Treeview(cart_frame, columns=ccols,
                                       show="headings", height=15)
        for c, t, w in [("name", "Producto", 140), ("qty", "Cant.", 50),
                        ("price", "P. Unit.", 70), ("sub", "Subtotal", 80)]:
            self.tree_cart.heading(c, text=t)
            self.tree_cart.column(c, width=w,
                                   anchor="w" if c == "name" else "center")
        self.tree_cart.pack(fill="both", expand=True)

        self.tree_cart.bind("<Double-1>", lambda e: self.remove_selected())
        self.tree_cart.bind("<Delete>", lambda e: self.remove_selected())

        # Totales
        totals = tk.Frame(right, bg="#ffffff")
        totals.pack(fill="x", padx=8, pady=6)

        tk.Label(totals, text="Subtotal:", bg="#ffffff",
                 font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        self.lbl_subtotal = tk.Label(totals, text="$0", bg="#ffffff",
                                      font=("Segoe UI", 10, "bold"))
        self.lbl_subtotal.grid(row=0, column=1, sticky="e")

        tk.Label(totals, text="Descuento:", bg="#ffffff",
                 font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w")
        self.var_discount = tk.StringVar(value="0")
        self.var_discount.trace_add("write", lambda *a: self.update_totals())
        tk.Entry(totals, textvariable=self.var_discount, width=10,
                 font=("Segoe UI", 10)).grid(row=1, column=1, sticky="e")

        tk.Label(totals, text="TOTAL:", bg="#ffffff",
                 font=("Segoe UI", 14, "bold")).grid(row=2, column=0,
                                                      sticky="w", pady=(6, 0))
        self.lbl_total = tk.Label(totals, text="$0", bg="#ffffff",
                                   font=("Segoe UI", 16, "bold"), fg="#1e88e5")
        self.lbl_total.grid(row=2, column=1, sticky="e", pady=(6, 0))

        totals.columnconfigure(1, weight=1)

        # Botones
        btns = tk.Frame(right, bg="#ffffff")
        btns.pack(fill="x", padx=8, pady=8)

        tk.Button(btns, text="🗑️ Vaciar carrito", command=self.clear_cart,
                  bg="#f44336", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", pady=6).pack(fill="x", pady=2)

        tk.Button(btns, text="💳 COBRAR", command=self.open_payment_dialog,
                  bg="#4CAF50", fg="white", font=("Segoe UI", 13, "bold"),
                  relief="flat", pady=12).pack(fill="x", pady=4)

        # Último ticket
        tk.Button(btns, text="🖨️ Reimprimir último ticket",
                  command=self.reprint_last_ticket,
                  bg="#607D8B", fg="white", font=("Segoe UI", 9, "bold"),
                  relief="flat", pady=4).pack(fill="x", pady=2)

        # Atajos
        self.bind("<F3>", lambda e: self.entry_search.focus_set())
        self.bind("<F12>", lambda e: self.open_payment_dialog())

        # Cargar productos
        self.refresh_products()

    # ============================================================
    # CAJA (idea 2)
    # ============================================================
    def _check_cash_session(self):
        session = self.sale_case.get_current_cash_session()
        if session:
            self.lbl_cash_status.config(
                text=f"💰 Caja abierta (base ${session['initial_amount']:,.0f})",
                fg="#a5d6a7")
        else:
            self.lbl_cash_status.config(
                text="⚠️ Caja NO abierta", fg="#ffeb3b")

    # ============================================================
    # PRODUCTOS
    # ============================================================
    def refresh_products(self):
        self.all_products = self.product_case.list_active_products()
        self.apply_filter()

    def apply_filter(self):
        q = self.var_search.get().strip().lower()
        self.tree_products.delete(*self.tree_products.get_children())
        self.filtered = []
        for p in self.all_products:
            if q:
                txt = f"{p.name} {p.barcode or ''}".lower()
                if q not in txt:
                    continue
            self.filtered.append(p)
            precio = p.rounded_price if p.rounded_price else p.price
            self.tree_products.insert("", "end", iid=str(p.product_id),
                values=(p.product_id, p.name, f"${precio:,.0f}",
                        p.stock, p.unit or "unidad"))
            if len(self.filtered) >= 200:
                break

    def add_first_filtered(self):
        if self.filtered:
            self.add_to_cart(self.filtered[0])

    def add_selected(self):
        sel = self.tree_products.selection()
        if not sel:
            return
        pid = int(sel[0])
        prod = next((p for p in self.all_products if p.product_id == pid), None)
        if prod:
            self.add_to_cart(prod)

    def add_to_cart(self, product, qty=1):
        for it in self.cart:
            if it["product_id"] == product.product_id:
                it["quantity"] += qty
                self.render_cart()
                return
        precio = product.rounded_price if product.rounded_price else product.price
        self.cart.append({
            "product_id": product.product_id,
            "product_name": product.name,
            "barcode": product.barcode or "",
            "quantity": qty,
            "unit": product.unit or "unidad",
            "unit_price": precio,
        })
        self.render_cart()
        self.save_draft()

    def render_cart(self):
        self.tree_cart.delete(*self.tree_cart.get_children())
        for i, it in enumerate(self.cart):
            sub = it["quantity"] * it["unit_price"]
            self.tree_cart.insert("", "end", iid=str(i),
                values=(it["product_name"], f"{it['quantity']:g}",
                        f"${it['unit_price']:,.0f}", f"${sub:,.0f}"))
        self.update_totals()

    def remove_selected(self):
        sel = self.tree_cart.selection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.cart):
            del self.cart[idx]
            self.render_cart()
            self.save_draft()

    def clear_cart(self):
        if self.cart and not messagebox.askyesno("Vaciar", "¿Vaciar carrito?"):
            return
        self.cart.clear()
        self.render_cart()
        self.save_draft()

    def update_totals(self):
        subtotal = sum(it["quantity"] * it["unit_price"] for it in self.cart)
        try:
            desc = float(self.var_discount.get() or 0)
        except ValueError:
            desc = 0.0
        desc = max(0.0, min(desc, subtotal))
        total = subtotal - desc
        self.lbl_subtotal.config(text=f"${subtotal:,.0f}")
        self.lbl_total.config(text=f"${total:,.0f}")
        return subtotal, desc, total

    # ============================================================
    # COBRO / PAGO MIXTO (idea 3)
    # ============================================================
    def open_payment_dialog(self):
        if not self.cart:
            messagebox.showinfo("Cobrar", "El carrito está vacío.")
            return

        # Aviso de caja
        if not self.sale_case.has_open_cash_session():
            if not messagebox.askyesno(
                    "Caja cerrada",
                    "⚠️ No has abierto la caja hoy.\n¿Deseas continuar de todas formas?"):
                return

        subtotal, desc, total = self.update_totals()
        PaymentDialog(self, self.sale_case, self.cart, subtotal, desc, total,
                      on_success=self._on_sale_success,
                      cashier_name=self.cashier_name)

    def _on_sale_success(self, sale_id, total, display_number,
                         items, payments):
        """Callback llamado tras cobrar."""
        # Guardar para reimprimir
        self.last_sale_id = sale_id
        self.last_sale = self.sale_case.get_sale_by_id(sale_id)
        self.last_sale_items = items
        self._last_payments = payments

        # Generar ticket automáticamente
        try:
            from presentation.views.widgets import generate_ticket_pdf
            ruta = generate_ticket_pdf(
                self.last_sale, items, payments=payments,
                business_name="MI NEGOCIO",
                cashier_name=self.cashier_name)
            # Preguntar si desea abrir
            if messagebox.askyesno("Ticket",
                                   f"Venta #{display_number} registrada.\n"
                                   f"Ticket generado:\n{ruta}\n\n¿Abrir el PDF?"):
                self._open_file(ruta)
        except Exception as e:
            print(f"Error generando ticket: {e}")

        self.cart.clear()
        self.var_discount.set("0")
        self.render_cart()
        self.save_draft()
        self.refresh_products()
        self._check_cash_session()

        if self.on_sale_done:
            self.on_sale_done()

    def reprint_last_ticket(self):
        if not self.last_sale:
            messagebox.showinfo("Reimprimir", "No hay ticket reciente.")
            return
        try:
            from presentation.views.widgets import generate_ticket_pdf
            ruta = generate_ticket_pdf(
                self.last_sale, self.last_sale_items,
                payments=getattr(self, "_last_payments", None),
                business_name="MI NEGOCIO",
                cashier_name=self.cashier_name,
                is_copy=True)
            if messagebox.askyesno("Reimprimir",
                                   f"Copia generada:\n{ruta}\n\n¿Abrir?"):
                self._open_file(ruta)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar: {e}")

    def _open_file(self, ruta):
        try:
            if sys.platform.startswith("win"):
                os.startfile(ruta)
            elif sys.platform == "darwin":
                os.system(f'open "{ruta}"')
            else:
                os.system(f'xdg-open "{ruta}"')
        except Exception:
            pass

    # ============================================================
    # BORRADOR
    # ============================================================
    def save_draft(self):
        try:
            self.sale_case.save_cart_draft(self.cart)
        except Exception:
            pass

    def _try_load_draft(self):
        try:
            items, when = self.sale_case.load_cart_draft()
            if not items:
                return
            if messagebox.askyesno(
                    "Borrador",
                    f"Hay un carrito sin cobrar del {when}.\n¿Recuperarlo?"):
                self.cart = items
                self.render_cart()
        except Exception:
            pass


# ================================================================
# DIÁLOGO DE PAGO (con pago mixto)
# ================================================================
class PaymentDialog(tk.Toplevel):
    def __init__(self, master, sale_case, items, subtotal, discount, total,
                 on_success=None, cashier_name=""):
        super().__init__(master)
        self.sale_case = sale_case
        self.items = items
        self.subtotal = subtotal
        self.discount = discount
        self.total = total
        self.on_success = on_success
        self.cashier_name = cashier_name

        self.title("Cobrar venta")
        self.geometry("560x720")
        self.transient(master)
        self.grab_set()
        self.resizable(False, True)

        self.payment_rows = []  # lista de dicts
        self._build()

    def _build(self):
        cont = tk.Frame(self, padx=15, pady=15)
        cont.pack(fill="both", expand=True)

        # Total grande
        tk.Label(cont, text="TOTAL A COBRAR", font=("Segoe UI", 10, "bold"),
                 fg="#666").pack()
        tk.Label(cont, text=f"${self.total:,.0f}",
                 font=("Segoe UI", 26, "bold"), fg="#1e88e5").pack(pady=(0, 10))

        if self.discount > 0:
            tk.Label(cont, text=f"Subtotal: ${self.subtotal:,.0f}  "
                                f"Descuento: -${self.discount:,.0f}",
                     font=("Segoe UI", 9), fg="#666").pack()

        # ===== Datos del cliente =====
        cli_frame = tk.LabelFrame(cont, text="Datos del cliente (opcional)",
                                  font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        cli_frame.pack(fill="x", pady=10)

        f = tk.Frame(cli_frame); f.pack(fill="x")
        tk.Label(f, text="Cliente:", width=10, anchor="w").pack(side="left")
        self.var_customer = tk.StringVar()
        tk.Entry(f, textvariable=self.var_customer, width=30,
                 font=("Segoe UI", 10)).pack(side="left")

        f2 = tk.Frame(cli_frame); f2.pack(fill="x", pady=(4, 0))
        tk.Label(f2, text="Notas:", width=10, anchor="w").pack(side="left")
        self.var_notes = tk.StringVar()
        tk.Entry(f2, textvariable=self.var_notes, width=30,
                 font=("Segoe UI", 10)).pack(side="left")

        # ===== Fiado =====
        self.var_is_credit = tk.IntVar(value=0)
        tk.Checkbutton(cli_frame, text="🔴 Venta a crédito (FIADO)",
                       variable=self.var_is_credit, font=("Segoe UI", 9, "bold"),
                       fg="#c62828").pack(anchor="w", pady=(6, 0))

        # ===== Pago mixto =====
        self.var_mixed = tk.IntVar(value=0)
        mixed_frame = tk.LabelFrame(cont, text="Forma de pago",
                                     font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        mixed_frame.pack(fill="x", pady=10)

        tk.Checkbutton(mixed_frame, text="💳 Pago dividido (múltiples métodos)",
                       variable=self.var_mixed, command=self._toggle_mixed,
                       font=("Segoe UI", 9)).pack(anchor="w")

        self.mixed_body = tk.Frame(mixed_frame)
        self.mixed_body.pack(fill="x", pady=(6, 0))

        # Fila simple (método único)
        self.simple_frame = tk.Frame(mixed_frame)
        self.simple_frame.pack(fill="x", pady=4)
        tk.Label(self.simple_frame, text="Método:", width=10,
                 anchor="w").pack(side="left")
        self.var_simple_method = tk.StringVar(value="Efectivo")
        ttk.Combobox(self.simple_frame, textvariable=self.var_simple_method,
                     values=["Efectivo", "Transferencia", "Tarjeta"],
                     state="readonly", width=20).pack(side="left")

        # Filas de pago mixto
        self.rows_container = tk.Frame(self.mixed_body)
        self.rows_container.pack(fill="x")

        tk.Button(self.mixed_body, text="➕ Agregar método",
                  command=lambda: self._add_row(), bg="#2196F3", fg="white",
                  relief="flat", font=("Segoe UI", 9)).pack(pady=4)

        # Label "Faltan"
        self.lbl_faltan = tk.Label(mixed_frame, text="", font=("Segoe UI", 10, "bold"))
        self.lbl_faltan.pack(anchor="w", pady=(6, 0))

        self._toggle_mixed()

        # ===== BOTONES =====
        btns = tk.Frame(cont)
        btns.pack(fill="x", pady=(15, 0))
        tk.Button(btns, text="💵 COBRAR", command=self.do_payment,
                  bg="#4CAF50", fg="white", font=("Segoe UI", 12, "bold"),
                  padx=25, pady=10, relief="flat").pack(side="right", padx=4)
        tk.Button(btns, text="Cancelar", command=self.destroy,
                  bg="#9E9E9E", fg="white", font=("Segoe UI", 10, "bold"),
                  padx=20, pady=10, relief="flat").pack(side="right", padx=4)

    # ============================================================
    # PAGO MIXTO
    # ============================================================
    def _toggle_mixed(self):
        activo = self.var_mixed.get() == 1
        for child in self.simple_frame.winfo_children():
            try:
                child.configure(state="disabled" if activo else "normal")
            except Exception:
                pass
        for child in self.mixed_body.winfo_children():
            if child is self.rows_container or isinstance(child, tk.Button):
                try:
                    child.configure(state="normal" if activo else "disabled")
                except Exception:
                    pass
        if activo and not self.payment_rows:
            self._add_row()
            self._add_row()
        if not activo:
            for w in self.rows_container.winfo_children():
                w.destroy()
            self.payment_rows.clear()
            self.lbl_faltan.config(text="")
        else:
            self._update_faltan()

    def _add_row(self):
        idx = len(self.payment_rows)
        f = tk.Frame(self.rows_container, pady=3)
        f.pack(fill="x")

        tk.Label(f, text=f"Método {idx+1}:", width=10, anchor="w").pack(side="left")
        var_m = tk.StringVar(value="Efectivo")
        ttk.Combobox(f, textvariable=var_m,
                     values=["Efectivo", "Transferencia", "Tarjeta"],
                     state="readonly", width=15).pack(side="left", padx=4)

        tk.Label(f, text="$").pack(side="left")
        var_a = tk.StringVar(value="0")
        ent = tk.Entry(f, textvariable=var_a, width=12, font=("Segoe UI", 10))
        ent.pack(side="left", padx=4)

        row = {"frame": f, "method": var_m, "amount": var_a, "widget": f}
        self.payment_rows.append(row)

        var_a.trace_add("write", lambda *a: self._update_faltan())
        # Limpiar botón
        tk.Button(f, text="✖", command=lambda r=row: self._remove_row(r),
                  bg="#f44336", fg="white", relief="flat",
                  font=("Segoe UI", 8), padx=4).pack(side="left", padx=2)

        self._update_faltan()

    def _remove_row(self, row):
        if row in self.payment_rows:
            row["frame"].destroy()
            self.payment_rows.remove(row)
            self._update_faltan()

    def _update_faltan(self):
        try:
            suma = sum(float(r["amount"].get() or 0) for r in self.payment_rows)
        except ValueError:
            suma = 0.0
        faltan = self.total - suma
        if abs(faltan) < 0.5:
            self.lbl_faltan.config(text="✅ Cubierto", fg="#2e7d32")
        elif faltan > 0:
            self.lbl_faltan.config(text=f"Faltan: ${faltan:,.0f}", fg="#c62828")
        else:
            self.lbl_faltan.config(text=f"Vuelto: ${abs(faltan):,.0f}", fg="#1565c0")

    # ============================================================
    # COBRAR
    # ============================================================
    def do_payment(self):
        is_credit = self.var_is_credit.get() == 1
        customer = self.var_customer.get().strip()
        notes = self.var_notes.get().strip()

        if is_credit and not customer:
            messagebox.showwarning("Fiado", "Escribe el nombre del cliente para el fiado.")
            return

        # Preparar items para sale_case
        items_data = [{
            "product_id": it["product_id"],
            "product_name": it["product_name"],
            "barcode": it.get("barcode", ""),
            "quantity": it["quantity"],
            "unit": it.get("unit", "unidad"),
            "unit_price": it["unit_price"],
        } for it in self.items]

        # Pago mixto
        payments = None
        principal_method = self.var_simple_method.get()

        if self.var_mixed.get() == 1 and self.payment_rows:
            payments = []
            for r in self.payment_rows:
                try:
                    amt = float(r["amount"].get() or 0)
                except ValueError:
                    amt = 0.0
                if amt > 0:
                    payments.append({"method": r["method"].get(), "amount": amt})
            if not payments:
                messagebox.showwarning("Pago", "Ingresa montos en los métodos.")
                return
            suma = sum(p["amount"] for p in payments)
            if suma < self.total - 0.5:
                messagebox.showwarning("Pago", f"Faltan ${self.total - suma:,.0f}")
                return
            # Método principal: el de mayor monto
            principal_method = max(payments, key=lambda x: x["amount"])["method"]

        # Crear venta
        try:
            sale_id, total, display_number = self.sale_case.create_sale(
                items_data,
                payment_method=principal_method,
                notes=notes,
                customer_name=customer,
                is_credit=is_credit,
                discount=self.discount,
                payments=payments,
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo registrar:\n{e}")
            return

        messagebox.showinfo("Venta registrada",
                            f"✅ Venta #{display_number}\nTotal: ${total:,.0f}")

        if self.on_success:
            self.on_success(sale_id, total, display_number, items_data, payments)
        self.destroy()
