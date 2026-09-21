import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
from presentation.views.widgets import (
    apply_titlebar_theme, center_window, show_popup_smooth,
    get_menu_font, AutoCompleteEntry, MD, TreeviewTooltip,
    popup_is_open, make_scrolled_treeview
)


class PaymentView(ttk.Frame):
    def __init__(self, parent, product_use_case, sale_use_case, get_theme_func):
        super().__init__(parent, bootstyle="dark")
        self.product_use_case = product_use_case
        self.sale_use_case = sale_use_case
        self.get_theme = get_theme_func
        self.cart = []
        self.tooltip = None
        self._draft_loaded = False
        self.create_widgets()
        self.refresh_cart()
        self.after(300, lambda: self.scan_entry.focus_set())
        self.after(800, self._check_cart_draft)
        self._keep_scanner_focused()

    def _is_dark(self):
        return True

    def _keep_scanner_focused(self):
        try:
            if not popup_is_open():
                fw = self.focus_get()
                if fw is not None and not isinstance(fw, (ttk.Entry, tk.Entry, ttk.Combobox)):
                    try:
                        if fw.winfo_toplevel() is self.winfo_toplevel():
                            self.scan_entry.focus_set()
                    except Exception:
                        pass
        except Exception:
            pass
        self.after(700, self._keep_scanner_focused)

    def _check_cart_draft(self):
        if self._draft_loaded:
            return
        try:
            if not self.winfo_ismapped():
                self.after(500, self._check_cart_draft)
                return
        except Exception:
            pass
        self._draft_loaded = True
        try:
            items, updated = self.sale_use_case.load_cart_draft()
        except Exception:
            return
        if not items:
            return
        try:
            total = sum(i["quantity"] * i["unit_price"] for i in items)
            n = len(items)
            fecha = updated or "(sin fecha)"
            r = MD.yesno(
                f"🛒 Se encontró un carrito sin cobrar:\n\n"
                f"Productos: {n}\n"
                f"Total: ${total:,.0f}\n"
                f"Guardado: {fecha}\n\n"
                f"¿Deseas recuperarlo?".replace(",", "."),
                "Recuperar carrito", parent=self)
            if r == "Yes":
                self.cart = items
                self.refresh_cart()
                self.scan_entry.focus_set()
            else:
                self.sale_use_case.clear_cart_draft()
                self.cart = []
                self.refresh_cart()
        except Exception:
            pass

    def _save_cart_draft(self):
        try:
            if self.cart:
                self.sale_use_case.save_cart_draft(self.cart)
            else:
                self.sale_use_case.clear_cart_draft()
        except Exception:
            pass

    def create_widgets(self):
        top = ttk.Frame(self, bootstyle="dark")
        top.pack(padx=10, pady=(15, 5), fill="x")

        ttk.Label(top, text="📷 Escanear:", font=("Arial", 14, "bold"),
                  bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(top, textvariable=self.scan_var, width=25, font=("Arial", 14))
        self.scan_entry.pack(side="left", padx=5)
        self.scan_entry.bind("<Return>", self.add_by_barcode)

        ttk.Label(top, text="🔍 Buscar:", font=("Arial", 11),
                  bootstyle="inverse-dark").pack(side="left", padx=(20, 5))

        self.search_var = tk.StringVar()
        self.search_entry = AutoCompleteEntry(
            top,
            values_getter=self._get_product_labels,
            on_select=self.add_by_search_value,
            width=30,
            font=("Arial", 11))
        self.search_entry.configure(textvariable=self.search_var)
        self.search_entry.pack(side="left", padx=5)

        ttk.Button(top, text="Agregar", command=self.add_by_search,
                   style="DarkGreen.TButton").pack(side="left", padx=5)

        cart_frame = ttk.Frame(self, bootstyle="dark")
        cart_frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.tree_frame, self.tree = make_scrolled_treeview(
            cart_frame,
            columns=("ID", "Name", "Barcode", "Price", "Qty", "Subtotal"),
            headings=[
                ("ID", "ID", 50, "center"),
                ("Name", "Producto", 300, "w"),
                ("Barcode", "Código", 150, "w"),
                ("Price", "P. Unit.", 110, "e"),
                ("Qty", "Cantidad", 110, "center"),
                ("Subtotal", "Subtotal", 120, "e"),
            ],
            bootstyle="dark")
        self.tree_frame.pack(fill="both", expand=True)
        self.tree.bind("<Button-3>", self._cart_context_menu)

        self.tooltip = TreeviewTooltip(self.tree, font_size=11)

        bottom = ttk.Frame(self, bootstyle="dark")
        bottom.pack(fill="x", padx=10, pady=10)
        tf = ttk.Frame(bottom, bootstyle="dark")
        tf.pack(side="left")
        ttk.Label(tf, text="TOTAL A PAGAR:", font=("Arial", 14, "bold"),
                  bootstyle="inverse-dark").pack(anchor="w")
        self.total_label = ttk.Label(tf, text="$0", font=("Arial", 36, "bold"),
                                     background="#0a4d1f", foreground="#a8e6a8",
                                     anchor="center", padding=10)
        self.total_label.pack(anchor="w")

        bf = ttk.Frame(bottom, bootstyle="dark")
        bf.pack(side="right")
        ttk.Button(bf, text="💰 COBRAR", command=self.pay,
                   style="DarkGreen.TButton").pack(side="left", padx=5, ipady=15, ipadx=20)
        ttk.Button(bf, text="❌ Cancelar", command=self.clear_cart,
                   bootstyle="danger").pack(side="left", padx=5, ipady=15)

    def _get_product_labels(self):
        vals = []
        for p in self.product_use_case.list_products():
            txt = f"{p.name}  |  {p.barcode}" if p.barcode else p.name
            vals.append(txt)
        return vals

    def add_by_search_value(self, value):
        self.after(10, lambda: self._do_add_by_search(value))

    def _do_add_by_search(self, value):
        q = value.split("|")[0].strip() if "|" in value else value
        q_lower = q.lower()
        enc = None
        for p in self.product_use_case.list_products():
            if str(p.barcode).strip() == q or p.name.lower() == q_lower:
                enc = p
                break
        if not enc:
            for p in self.product_use_case.list_products():
                if q_lower in p.name.lower():
                    enc = p
                    break
        if not enc:
            MD.show_warning(f"⚠️ No se encontró '{q}'.", "No encontrado", parent=self)
            return
        self.search_var.set("")
        if enc.unit_type in ("peso", "volumen"):
            self.ask_amount(enc)
        else:
            self.add_to_cart(enc, 1)
        self.scan_entry.focus_set()

    def add_by_search(self, event=None):
        raw = self.search_var.get().strip()
        if not raw:
            return
        self._do_add_by_search(raw)

    def _cart_context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self.tree.focus(row)
        pid = int(self.tree.item(row, 'values')[0])
        name = self.tree.item(row, 'values')[1]
        style = ttk.Style()
        m = tk.Menu(self, tearoff=0,
                    bg=style.colors.bg, fg=style.colors.fg,
                    activebackground=style.colors.selectbg,
                    activeforeground=style.colors.selectfg,
                    bd=1, relief="solid",
                    font=get_menu_font())
        m.add_command(label="➖ Quitar 1", command=lambda: self._confirm_remove_one(pid, name))
        m.add_command(label="🗑️  Quitar producto completo",
                      command=lambda: self._confirm_remove_all(pid, name))
        m.add_separator()
        m.add_command(label="🧹 Vaciar carrito", command=self.clear_cart)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _confirm_remove_one(self, pid, name):
        if MD.yesno(f"¿Quitar 1 de '{name}' del carrito?", "Confirmar", parent=self) == "Yes":
            for i, it in enumerate(self.cart):
                if it["product_id"] == pid:
                    it["quantity"] -= 1
                    if it["quantity"] <= 0:
                        self.cart.pop(i)
                    else:
                        it["subtotal"] = it["quantity"] * it["unit_price"]
                    break
            self.refresh_cart()
            self._save_cart_draft()
            self.scan_entry.focus_set()

    def _confirm_remove_all(self, pid, name):
        if MD.yesno(f"¿Quitar TODO '{name}' del carrito?", "Confirmar", parent=self) == "Yes":
            self.cart = [i for i in self.cart if i["product_id"] != pid]
            self.refresh_cart()
            self._save_cart_draft()
            self.scan_entry.focus_set()

    def add_by_barcode(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo:
            return
        enc = None
        for p in self.product_use_case.list_products():
            if str(p.barcode).strip() == codigo:
                enc = p
                break
        if not enc:
            MD.show_warning(f"⚠️ '{codigo}' no registrado.", "No encontrado", parent=self)
            self.scan_var.set("")
            self.scan_entry.focus_set()
            return
        self.scan_var.set("")
        self.scan_entry.focus_set()
        if enc.unit_type in ("peso", "volumen"):
            self.ask_amount(enc)
        else:
            self.add_to_cart(enc, 1)

    def ask_amount(self, product):
        pop = Toplevel(self)
        pop.title(f"Cantidad - {product.name}")
        pop.geometry("400x320")
        pop.transient(self.winfo_toplevel())
        pop.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(pop, text=product.name, font=("Arial", 16, "bold"),
                 bg=bg, fg=fg).pack(pady=12)
        tk.Label(pop, text=f"Precio: ${product.price:,.0f}/{product.unit}".replace(",", "."),
                 font=("Arial", 12), bg=bg, fg=fg).pack(pady=5)
        tk.Label(pop, text=f"Ingrese la cantidad en {product.unit}:",
                 font=("Arial", 11), bg=bg, fg=fg).pack(pady=10)
        v = tk.StringVar(value="1")
        e = ttk.Entry(pop, textvariable=v, width=15, font=("Arial", 20), justify="center")
        e.pack(pady=5)
        e.select_range(0, tk.END)
        e.focus_set()

        def ok(ev=None):
            try:
                c = float(v.get().replace(",", "."))
                if c <= 0:
                    raise ValueError
            except ValueError:
                MD.show_error("Cantidad inválida", "Error", parent=pop)
                return "break"
            pop.destroy()
            self.add_to_cart(product, c)
            self.scan_entry.focus_set()
            return "break"

        bf = tk.Frame(pop, bg=bg)
        bf.pack(pady=15)
        ttk.Button(bf, text="Agregar", command=ok, style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar",
                   command=lambda: [pop.destroy(), self.scan_entry.focus_set()]).pack(side="left", padx=5)
        e.bind("<Return>", ok)
        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

    def add_to_cart(self, product, cantidad):
        for it in self.cart:
            if it["product_id"] == product.product_id:
                it["quantity"] += cantidad
                it["subtotal"] = it["quantity"] * it["unit_price"]
                self.refresh_cart()
                self._save_cart_draft()
                return
        self.cart.append({
            "product_id": product.product_id,
            "product_name": product.name,
            "barcode": product.barcode,
            "unit": product.unit,
            "unit_price": product.price,
            "quantity": cantidad,
            "subtotal": cantidad * product.price,
        })
        self.refresh_cart()
        self._save_cart_draft()

    def refresh_cart(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for it in self.cart:
            qt = f"{it['quantity']:g} {it['unit']}" if it["unit"] != "unidad" else f"{int(it['quantity'])}"
            self.tree.insert("", "end", values=(
                it["product_id"], it["product_name"], it["barcode"],
                f"${it['unit_price']:,.0f}".replace(",", "."), qt,
                f"${it['subtotal']:,.0f}".replace(",", ".")))
        tot = sum(i["subtotal"] for i in self.cart)
        self.total_label.configure(text=f"${tot:,.0f}".replace(",", "."))

    def clear_cart(self):
        if not self.cart:
            return
        if MD.yesno("¿Vaciar el carrito?", "Confirmar", parent=self) == "Yes":
            self.cart = []
            self.refresh_cart()
            self.sale_use_case.clear_cart_draft()
            self.scan_entry.focus_set()

    # ============ COBRAR ============
    def pay(self):
        try:
            self._pay_internal()
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                MD.show_error(f"Error al abrir el pago:\n{e}", "Error", parent=self)
            except Exception:
                pass

    def _pay_internal(self):
        if not self.cart:
            MD.show_warning("El carrito está vacío.", "Nada que cobrar", parent=self)
            return
        total = sum(i["subtotal"] for i in self.cart)

        pop = Toplevel(self)
        pop.title("Confirmar Pago")
        pop.geometry("620x680")
        pop.transient(self.winfo_toplevel())
        pop.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        # ===== Título =====
        tk.Label(pop, text="💰 CONFIRMAR PAGO",
                 font=("Arial", 15, "bold"), bg=bg, fg=fg).pack(pady=(10, 3))

        # ===== Total (verde) =====
        total_frame = tk.Frame(pop, bg="#0a4d1f", padx=20, pady=8)
        total_frame.pack(pady=(0, 6))
        tk.Label(total_frame, text="TOTAL A PAGAR",
                 font=("Arial", 9, "bold"),
                 bg="#0a4d1f", fg="#a8e6a8").pack()
        tk.Label(total_frame, text=f"${total:,.0f}".replace(",", "."),
                 font=("Arial", 24, "bold"),
                 bg="#0a4d1f", fg="#a8e6a8").pack()

        # ===== Cliente =====
        tk.Label(pop, text="Nombre del cliente (opcional):",
                 font=("Arial", 10), bg=bg, fg=fg).pack(pady=(3, 2))
        nombre_var = tk.StringVar()
        ttk.Entry(pop, textvariable=nombre_var, width=40,
                  font=("Arial", 11)).pack(pady=3, padx=20)

        # ===== Método =====
        tk.Label(pop, text="Método de pago:",
                 font=("Arial", 10), bg=bg, fg=fg).pack(pady=(4, 2))
        metodo_var = tk.StringVar(value="Efectivo")
        mf = tk.Frame(pop, bg=bg)
        mf.pack(pady=2)
        for i, m in enumerate(["Efectivo", "Transferencia", "Tarjeta", "Otro", "Fiado"]):
            r = i // 3
            c = i % 3
            ttk.Radiobutton(mf, text=m, variable=metodo_var, value=m,
                            bootstyle="info").grid(row=r, column=c,
                                                    padx=6, pady=1, sticky="w")

        # ===== Aviso deuda =====
        deuda_lbl = tk.Label(pop, text="", font=("Arial", 10, "bold"),
                             bg=bg, fg="#ffd166", wraplength=580, justify="center")
        deuda_lbl.pack(pady=3, padx=10)

        # ===== Notas =====
        tk.Label(pop, text="Notas (opcional):",
                 font=("Arial", 10), bg=bg, fg=fg).pack(pady=(4, 2))
        notas_var = tk.StringVar()
        ttk.Entry(pop, textvariable=notas_var, width=40,
                  font=("Arial", 11)).pack(pady=3, padx=20)

        # ===== Contenedor inferior: botones → saldo → abono =====
        bottom_container = tk.Frame(pop, bg=bg)
        bottom_container.pack(side="bottom", fill="x", pady=8)

        bf = tk.Frame(bottom_container, bg=bg)
        bf.pack(side="bottom", pady=4)

        saldo_lbl = tk.Label(bottom_container, text="", font=("Arial", 11, "bold"),
                             bg=bg, fg="#a8e6a8", wraplength=580, justify="center")

        abono_frame = tk.Frame(bottom_container, bg=bg)
        abono_var = tk.BooleanVar(value=False)
        abono_monto_var = tk.StringVar(value="")

        chk_abono = ttk.Checkbutton(
            abono_frame, text="💵 Abonar",
            variable=abono_var, bootstyle="success-round-toggle")
        chk_abono.pack(side="left", padx=5)

        tk.Label(abono_frame, text="Monto:", bg=bg, fg=fg,
                 font=("Arial", 10)).pack(side="left", padx=5)
        ent_abono = ttk.Entry(abono_frame, textvariable=abono_monto_var,
                              width=12, font=("Arial", 11), justify="center")
        ent_abono.pack(side="left", padx=5)

        # ===== Confirmar =====
        def confirmar():
            nombre = nombre_var.get().strip()
            metodo = metodo_var.get()
            es_fiado = (metodo == "Fiado")
            monto_abono = 0.0
            if abono_var.get() and nombre:
                try:
                    monto_abono = float(
                        abono_monto_var.get().replace("$", "").replace(".", "").replace(",", ".") or 0)
                except ValueError:
                    monto_abono = 0.0
            try:
                sid, tot, display_num = self.sale_use_case.create_sale(
                    self.cart,
                    payment_method=metodo,
                    notes=notas_var.get().strip(),
                    customer_name=nombre,
                    is_credit=es_fiado)
                msg = f"✅ Venta #{display_num:02d} registrada.\n"
                msg += f"Total: ${tot:,.0f}".replace(",", ".")
                if es_fiado:
                    quien = nombre if nombre else "(sin nombre)"
                    deuda = self.sale_use_case.get_pending_by_customer(quien) if nombre else tot
                    msg += f"\n\n📌 FIADO a: {quien}"
                    msg += f"\n💰 Nueva deuda total: ${deuda:,.0f}".replace(",", ".")
                if monto_abono > 0 and nombre:
                    aplicado, saldo = self.sale_use_case.apply_payment_to_customer(
                        nombre, monto_abono)
                    msg += f"\n\n💵 Abono aplicado: ${aplicado:,.0f}".replace(",", ".")
                    if saldo <= 0.01:
                        msg += "\n✅ Deuda SALDADA por completo."
                    else:
                        msg += f"\n📌 Saldo pendiente: ${saldo:,.0f}".replace(",", ".")
                self.cart = []
                self.refresh_cart()
                self.sale_use_case.clear_cart_draft()
                pop.destroy()
                MD.show_info(msg, "Venta Exitosa", parent=self)
                self.scan_entry.focus_set()
            except Exception as e:
                MD.show_error(f"Error: {e}", "Error", parent=pop)

        ttk.Button(bf, text="✅ Confirmar Pago", command=confirmar,
                   style="DarkGreen.TButton").pack(side="left", padx=8, ipady=8, ipadx=15)
        ttk.Button(bf, text="Cancelar",
                   command=pop.destroy).pack(side="left", padx=8, ipady=8)

        def refresh_ui(*args):
            nombre = nombre_var.get().strip()
            es_fiado = (metodo_var.get() == "Fiado")
            abono_frame.pack_forget()
            saldo_lbl.pack_forget()

            if not nombre:
                deuda_lbl.configure(text="")
                return

            try:
                deuda = self.sale_use_case.get_pending_by_customer(nombre)
            except Exception:
                deuda = 0

            if es_fiado:
                if deuda > 0:
                    total_nuevo = deuda + total
                    deuda_lbl.configure(
                        text=f"📌 FIADO a: {nombre}  |  Deuda: ${deuda:,.0f} + Venta: ${total:,.0f} = ${total_nuevo:,.0f}".replace(",", "."),
                        fg="#ffd166")
                else:
                    deuda_lbl.configure(
                        text=f"📌 FIADO a: {nombre}  |  Total: ${total:,.0f}".replace(",", "."),
                        fg="#ffd166")
            else:
                if deuda > 0:
                    deuda_lbl.configure(
                        text=f"⚠️ {nombre} debe ${deuda:,.0f} de fiados anteriores (esta venta es aparte).".replace(",", "."),
                        fg="#ffd166")
                else:
                    deuda_lbl.configure(
                        text=f"ℹ️ {nombre} no tiene deudas previas.", fg="#a8e6a8")

            if not (deuda > 0 or es_fiado):
                return

            saldo_lbl.pack(side="bottom", pady=2)
            abono_frame.pack(side="bottom", pady=4)

            try:
                monto = 0.0
                if abono_var.get():
                    try:
                        monto = float(abono_monto_var.get()
                                      .replace("$", "").replace(".", "").replace(",", ".") or 0)
                    except ValueError:
                        monto = 0.0
                    if monto > deuda:
                        monto = deuda

                if es_fiado:
                    total_acum = deuda + total
                    saldo = max(0, total_acum - monto)
                    if abono_var.get() and monto > 0:
                        saldo_lbl.configure(
                            text=f"💵 Nueva deuda después del abono: ${saldo:,.0f}".replace(",", "."))
                    else:
                        saldo_lbl.configure(
                            text=f"💵 Nueva deuda total: ${total_acum:,.0f}".replace(",", "."))
                else:
                    if abono_var.get() and monto > 0:
                        saldo = max(0, deuda - monto)
                        saldo_lbl.configure(
                            text=f"💵 Saldo de la deuda anterior: ${saldo:,.0f}".replace(",", "."))
                    else:
                        saldo_lbl.configure(
                            text=f"💵 Deuda anterior: ${deuda:,.0f}".replace(",", "."))
            except Exception:
                saldo_lbl.configure(text="")

        nombre_var.trace_add("write", refresh_ui)
        metodo_var.trace_add("write", refresh_ui)
        abono_var.trace_add("write", refresh_ui)
        abono_monto_var.trace_add("write", refresh_ui)

        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass