import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
from ttkbootstrap.dialogs import Messagebox


def apply_titlebar_theme(window, is_dark):
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        v = ctypes.c_int(1 if is_dark else 0)
        for a in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, a, ctypes.byref(v), ctypes.sizeof(v))
    except Exception:
        pass


def center_window(win):
    win.update_idletasks()
    w, h = win.winfo_width(), win.winfo_height()
    sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
    x, y = (sw - w) // 2, (sh - h) // 2
    win.geometry(f"+{x}+{y}")


class PaymentView(ttk.Frame):
    def __init__(self, parent, product_use_case, sale_use_case, get_theme_func):
        super().__init__(parent, bootstyle="dark")
        self.product_use_case = product_use_case
        self.sale_use_case = sale_use_case
        self.get_theme = get_theme_func
        self.cart = []
        self.create_widgets()
        self.refresh_cart()
        self.after(300, lambda: self.scan_entry.focus_set())
        self._keep_scanner_focused()

    def _keep_scanner_focused(self):
        try:
            fw = self.focus_get()
            if fw is not None and not isinstance(fw, (ttk.Entry, tk.Entry, ttk.Combobox)):
                self.scan_entry.focus_set()
        except Exception:
            pass
        self.after(700, self._keep_scanner_focused)

    # ================= UI =================
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
        self.search_entry = ttk.Combobox(top, textvariable=self.search_var,
                                         width=30, font=("Arial", 11))
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<<ComboboxSelected>>", self.add_by_search)
        self.search_entry.bind("<Return>", self.add_by_search)

        ttk.Button(top, text="Agregar", command=self.add_by_search,
                   bootstyle="info").pack(side="left", padx=5)

        # --- CARRITO ---
        cart_frame = ttk.Frame(self, bootstyle="dark")
        cart_frame.pack(padx=10, pady=5, fill="both", expand=True)
        self.tree = ttk.Treeview(cart_frame,
                                 columns=("ID", "Name", "Barcode", "Price", "Qty", "Subtotal"),
                                 show='headings')
        for c, t, w, a in [("ID", "ID", 50, "center"),
                           ("Name", "Producto", 300, "w"),
                           ("Barcode", "Código", 150, "w"),
                           ("Price", "P. Unit.", 110, "e"),
                           ("Qty", "Cantidad", 110, "center"),
                           ("Subtotal", "Subtotal", 120, "e")]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor=a)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Button-3>", self._cart_context_menu)

        # --- TOTAL Y BOTONES ---
        bottom = ttk.Frame(self, bootstyle="dark")
        bottom.pack(fill="x", padx=10, pady=10)
        tf = ttk.Frame(bottom, bootstyle="dark")
        tf.pack(side="left")
        ttk.Label(tf, text="TOTAL A PAGAR:", font=("Arial", 14, "bold"),
                  bootstyle="inverse-dark").pack(anchor="w")
        # ✅ Verde oscuro con letra clara para mejor legibilidad
        self.total_label = ttk.Label(tf, text="$0", font=("Arial", 36, "bold"),
                                     background="#0a4d1f", foreground="#a8e6a8",
                                     anchor="center", padding=10)
        self.total_label.pack(anchor="w")

        bf = ttk.Frame(bottom, bootstyle="dark")
        bf.pack(side="right")
        # ✅ Botón COBRAR con verde más oscuro
        cobrar_btn = ttk.Button(bf, text="💰 COBRAR", command=self.pay)
        cobrar_btn.configure(bootstyle="success")
        cobrar_btn.pack(side="left", padx=5, ipady=15, ipadx=20)
        ttk.Button(bf, text="❌ Cancelar", command=self.clear_cart,
                   bootstyle="danger").pack(side="left", padx=5, ipady=15)

        self._refresh_autocomplete()

    # ================= AUTOCOMPLETAR =================
    def _refresh_autocomplete(self, filter_text=""):
        prods = self.product_use_case.list_products()
        ft = filter_text.lower()
        valores = []
        for p in prods:
            texto = f"{p.name}  |  {p.barcode}" if p.barcode else p.name
            if not ft or ft in p.name.lower() or ft in str(p.barcode).lower():
                valores.append(texto)
        self.search_entry['values'] = valores[:200]

    def _on_search_key(self, event=None):
        """Al escribir, actualiza sugerencias y abre el dropdown automáticamente."""
        self._refresh_autocomplete(self.search_var.get())
        # ✅ Forzar apertura del dropdown para ver sugerencias al escribir
        if self.search_var.get():
            try:
                self.search_entry.event_generate('<Down>')
                # Volver a poner el cursor al final para seguir escribiendo
                self.search_entry.icursor(tk.END)
            except Exception:
                pass

    # ================= MENÚ CONTEXTUAL CARRITO =================
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
                    bd=1, relief="solid")
        m.add_command(label="➖ Quitar 1",
                      command=lambda: self._confirm_remove_one(pid, name))
        m.add_command(label="🗑️  Quitar producto completo",
                      command=lambda: self._confirm_remove_all(pid, name))
        m.add_separator()
        m.add_command(label="🧹 Vaciar carrito", command=self.clear_cart)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _confirm_remove_one(self, pid, name):
        if Messagebox.yesno(f"¿Quitar 1 de '{name}' del carrito?",
                            "Confirmar", parent=self) == "Yes":
            for i, it in enumerate(self.cart):
                if it["product_id"] == pid:
                    it["quantity"] -= 1
                    if it["quantity"] <= 0:
                        self.cart.pop(i)
                    else:
                        it["subtotal"] = it["quantity"] * it["unit_price"]
                    break
            self.refresh_cart()
            self.scan_entry.focus_set()

    def _confirm_remove_all(self, pid, name):
        if Messagebox.yesno(f"¿Quitar TODO '{name}' del carrito?",
                            "Confirmar", parent=self) == "Yes":
            self.cart = [i for i in self.cart if i["product_id"] != pid]
            self.refresh_cart()
            self.scan_entry.focus_set()

    # ================= AGREGAR AL CARRITO =================
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
            Messagebox.show_warning(f"⚠️ '{codigo}' no registrado.",
                                    "No encontrado", parent=self)
            self.scan_var.set("")
            self.scan_entry.focus_set()
            return
        self.scan_var.set("")
        self.scan_entry.focus_set()
        if enc.unit_type in ("peso", "volumen"):
            self.ask_amount(enc)
        else:
            self.add_to_cart(enc, 1)

    def add_by_search(self, event=None):
        raw = self.search_var.get().strip()
        if not raw:
            return
        q = raw.split("|")[0].strip() if "|" in raw else raw
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
            Messagebox.show_warning(f"⚠️ No se encontró '{q}'.",
                                    "No encontrado", parent=self)
            return
        self.search_var.set("")
        self._refresh_autocomplete()
        if enc.unit_type in ("peso", "volumen"):
            self.ask_amount(enc)
        else:
            self.add_to_cart(enc, 1)
        self.scan_entry.focus_set()

    def ask_amount(self, product):
        pop = Toplevel(self)
        pop.title(f"Cantidad - {product.name}")
        pop.geometry("400x320")
        pop.transient(self.winfo_toplevel())
        pop.grab_set()
        ttk.Label(pop, text=product.name, font=("Arial", 16, "bold")).pack(pady=12)
        ttk.Label(pop, text=f"Precio: ${product.price:,.0f}/{product.unit}".replace(",", "."),
                  font=("Arial", 12)).pack(pady=5)
        ttk.Label(pop, text=f"Ingrese la cantidad en {product.unit}:",
                  font=("Arial", 11)).pack(pady=10)
        v = tk.StringVar(value="1")
        e = ttk.Entry(pop, textvariable=v, width=15, font=("Arial", 20), justify="center")
        e.pack(pady=5)
        e.select_range(0, tk.END)
        e.focus_set()

        def ok():
            try:
                c = float(v.get().replace(",", "."))
                if c <= 0:
                    raise ValueError
            except ValueError:
                Messagebox.show_error("Cantidad inválida", "Error", parent=pop)
                return
            pop.destroy()
            self.add_to_cart(product, c)
            self.scan_entry.focus_set()

        bf = ttk.Frame(pop)
        bf.pack(pady=15)
        ttk.Button(bf, text="Agregar", command=ok, bootstyle="success").pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar",
                   command=lambda: [pop.destroy(), self.scan_entry.focus_set()]).pack(side="left", padx=5)
        e.bind("<Return>", lambda e: ok())
        pop.after(100, lambda: center_window(pop))
        pop.after(200, lambda: apply_titlebar_theme(pop, self.get_theme() == 'darkly'))

    def add_to_cart(self, product, cantidad):
        for it in self.cart:
            if it["product_id"] == product.product_id:
                it["quantity"] += cantidad
                it["subtotal"] = it["quantity"] * it["unit_price"]
                self.refresh_cart()
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

    def refresh_cart(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for it in self.cart:
            qt = f"{it['quantity']:g} {it['unit']}" if it["unit"] != "unidad" else f"{int(it['quantity'])}"
            self.tree.insert("", "end", values=(
                it["product_id"],
                it["product_name"],
                it["barcode"],
                f"${it['unit_price']:,.0f}".replace(",", "."),
                qt,
                f"${it['subtotal']:,.0f}".replace(",", ".")))
        tot = sum(i["subtotal"] for i in self.cart)
        self.total_label.configure(text=f"${tot:,.0f}".replace(",", "."))

    def clear_cart(self):
        if not self.cart:
            return
        if Messagebox.yesno("¿Vaciar el carrito?", "Confirmar", parent=self) == "Yes":
            self.cart = []
            self.refresh_cart()
            self.scan_entry.focus_set()

    # ================= COBRAR =================
    def pay(self):
        if not self.cart:
            Messagebox.show_warning("El carrito está vacío.", "Nada que cobrar", parent=self)
            return
        total = sum(i["subtotal"] for i in self.cart)

        pop = Toplevel(self)
        pop.title("Confirmar Pago")
        pop.geometry("560x620")
        pop.transient(self.winfo_toplevel())
        pop.grab_set()

        ttk.Label(pop, text="💰 CONFIRMAR PAGO", font=("Arial", 20, "bold")).pack(pady=15)
        ttk.Label(pop, text="TOTAL A PAGAR", font=("Arial", 14),
                  bootstyle="inverse-secondary").pack()
        ttk.Label(pop, text=f"${total:,.0f}".replace(",", "."),
                  font=("Arial", 40, "bold"),
                  background="#0a4d1f", foreground="#a8e6a8",
                  anchor="center", padding=15).pack(pady=10)

        ttk.Label(pop, text="Nombre del cliente (opcional):",
                  font=("Arial", 11)).pack(pady=(15, 3))
        nombre_var = tk.StringVar()
        ttk.Entry(pop, textvariable=nombre_var, width=40,
                  font=("Arial", 12)).pack(pady=5)

        ttk.Label(pop, text="Método de pago:", font=("Arial", 11)).pack(pady=(10, 3))
        metodo_var = tk.StringVar(value="Efectivo")
        mf = ttk.Frame(pop)
        mf.pack(pady=5)
        for i, m in enumerate(["Efectivo", "Transferencia", "Tarjeta", "Otro", "Fiado"]):
            ttk.Radiobutton(mf, text=m, variable=metodo_var, value=m,
                            bootstyle="info").grid(row=i // 3, column=i % 3, padx=8, pady=3, sticky="w")

        ttk.Label(pop, text="Notas (opcional):").pack(pady=(10, 3))
        notas_var = tk.StringVar()
        ttk.Entry(pop, textvariable=notas_var, width=40).pack(pady=5)

        def confirmar():
            nombre = nombre_var.get().strip()
            metodo = metodo_var.get()
            es_fiado = (metodo == "Fiado")
            if es_fiado and not nombre:
                Messagebox.show_error("Para fiado debes ingresar el nombre del cliente.",
                                      "Falta nombre", parent=pop)
                return
            try:
                sid, tot = self.sale_use_case.create_sale(
                    self.cart,
                    payment_method=metodo,
                    notes=notas_var.get().strip(),
                    customer_name=nombre,
                    is_credit=es_fiado)
                pop.destroy()
                msg = f"✅ Venta #{sid} registrada.\nTotal: ${tot:,.0f}".replace(",", ".")
                if es_fiado:
                    msg += f"\n\n📌 FIADO a: {nombre}\n(Recuerda cobrarle)"
                Messagebox.show_info(msg, "Venta Exitosa", parent=self)
                self.cart = []
                self.refresh_cart()
                self.scan_entry.focus_set()
            except Exception as e:
                Messagebox.show_error(f"Error: {e}", "Error", parent=pop)

        bf = ttk.Frame(pop)
        bf.pack(pady=20)
        ttk.Button(bf, text="✅ Confirmar Pago", command=confirmar,
                   bootstyle="success").pack(side="left", padx=10, ipady=10, ipadx=20)
        ttk.Button(bf, text="Cancelar", command=pop.destroy).pack(side="left", padx=10, ipady=10)
        pop.after(100, lambda: center_window(pop))
        pop.after(200, lambda: apply_titlebar_theme(pop, self.get_theme() == 'darkly'))