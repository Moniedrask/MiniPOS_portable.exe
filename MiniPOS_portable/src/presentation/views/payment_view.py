import os
import sys
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
from datetime import datetime

from presentation.views.widgets import (
    MD, show_popup_smooth, get_menu_font,
    AutoCompleteEntry, TreeviewTooltip, popup_is_open,
    make_scrolled_treeview, get_business_info,
    get_theme_colors,
    generate_ticket_pdf,
)


class PaymentView(ttk.Frame):
    def __init__(self, parent, product_use_case, sale_use_case, db_manager,
                 get_theme_func, on_business_click=None):
        super().__init__(parent, bootstyle="dark")
        self.product_use_case = product_use_case
        self.sale_use_case = sale_use_case
        self.db_manager = db_manager
        self.get_theme = get_theme_func
        self.on_business_click = on_business_click

        self.cart = []
        self.tooltip = None
        self._draft_loaded = False
        self.last_ticket_path = None

        self.create_widgets()
        self.refresh_cart()
        self.after(300, lambda: self.scan_entry.focus_set())
        self.after(800, self._check_cart_draft)
        self._keep_scanner_focused()

    # ============================================================
    # ENFOQUE AUTOMÁTICO DEL SCANNER
    # ============================================================
    def _keep_scanner_focused(self):
        try:
            if not popup_is_open():
                fw = self.focus_get()
                if fw is not None and not isinstance(
                        fw, (ttk.Entry, tk.Entry, ttk.Combobox)):
                    try:
                        if fw.winfo_toplevel() is self.winfo_toplevel():
                            self.scan_entry.focus_set()
                    except Exception:
                        pass
        except Exception:
            pass
        self.after(700, self._keep_scanner_focused)

    # ============================================================
    # BORRADOR DE CARRITO
    # ============================================================
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

    # ============================================================
    # UI
    # ============================================================
    def create_widgets(self):
        top = ttk.Frame(self, bootstyle="dark")
        top.pack(padx=10, pady=(10, 5), fill="x")

        ttk.Label(top, text="📷 Escanear:", font=("Arial", 14, "bold"),
                  bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(top, textvariable=self.scan_var,
                                    width=22, font=("Arial", 14))
        self.scan_entry.pack(side="left", padx=5)
        self.scan_entry.bind("<Return>", self.on_barcode_scanned)

        ttk.Label(top, text="🔍 Buscar:", font=("Arial", 11),
                  bootstyle="inverse-dark").pack(side="left", padx=(15, 5))

        self.search_var = tk.StringVar()
        self.search_entry = AutoCompleteEntry(
            top,
            values_getter=self._get_product_labels,
            on_select=self.on_search_selected,
            width=25,
            font=("Arial", 11))
        self.search_entry.configure(textvariable=self.search_var)
        self.search_entry.pack(side="left", padx=5)

        ttk.Button(top, text="🔍 Ver producto",
                   command=self.on_search_clicked,
                   style="DarkGreen.TButton").pack(side="left", padx=5)

        body = ttk.Frame(self, bootstyle="dark")
        body.pack(padx=10, pady=5, fill="both", expand=True)

        cart_frame = ttk.Frame(body, bootstyle="dark")
        cart_frame.pack(side="left", fill="both", expand=True)

        self.tree_frame, self.tree = make_scrolled_treeview(
            cart_frame,
            columns=("ID", "Name", "Barcode", "Price", "Qty", "Subtotal"),
            headings=[
                ("ID", "ID", 50, "center"),
                ("Name", "Producto", 260, "w"),
                ("Barcode", "Código", 130, "w"),
                ("Price", "P. Unit.", 100, "e"),
                ("Qty", "Cantidad", 90, "center"),
                ("Subtotal", "Subtotal", 110, "e"),
            ],
            bootstyle="dark")
        self.tree_frame.pack(fill="both", expand=True)
        self.tree.bind("<Button-3>", self._cart_context_menu)
        self.tooltip = TreeviewTooltip(self.tree, font_size=11)

        self._build_recent_panel(body)

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

        ttk.Button(bf, text="🖨 Último Ticket",
                   command=self.open_last_ticket,
                   bootstyle="info").pack(side="left", padx=5, ipady=15)
        ttk.Button(bf, text="↩️ Devoluciones",
                   command=self.open_returns_window,
                   bootstyle="warning").pack(side="left", padx=5, ipady=15)
        ttk.Button(bf, text="💰 COBRAR (F12)", command=self.pay,
                   style="DarkGreen.TButton").pack(side="left", padx=5,
                                                   ipady=15, ipadx=15)
        ttk.Button(bf, text="❌ Cancelar", command=self.clear_cart,
                   bootstyle="danger").pack(side="left", padx=5, ipady=15)

        try:
            self.winfo_toplevel().bind('<F12>', lambda e: self.pay(), add="+")
        except Exception:
            pass

    # ============================================================
    # PANEL DE VENTAS RECIENTES
    # ============================================================
    def _build_recent_panel(self, parent):
        panel = ttk.Frame(parent, bootstyle="dark", width=280)
        panel.pack(side="right", fill="y", padx=(8, 0))
        panel.pack_propagate(False)

        ttk.Label(panel, text="🧾 Ventas recientes",
                  font=("Arial", 11, "bold"),
                  bootstyle="inverse-dark").pack(pady=(4, 6))

        btns = ttk.Frame(panel, bootstyle="dark")
        btns.pack(fill="x", pady=2)
        ttk.Button(btns, text="🔄", command=self._load_recent_sales,
                   bootstyle="secondary", width=3).pack(side="left", padx=2)
        ttk.Button(btns, text="🧾 Reimprimir",
                   command=self._reprint_selected,
                   bootstyle="info", width=12).pack(side="left", padx=2)
        ttk.Button(btns, text="↩️ Devolver",
                   command=self._return_selected,
                   bootstyle="warning", width=10).pack(side="left", padx=2)

        self.recent_frame, self.recent_tree = make_scrolled_treeview(
            panel,
            columns=("ID", "Hora", "Total"),
            headings=[
                ("ID", "#", 50, "center"),
                ("Hora", "Hora", 80, "center"),
                ("Total", "Total", 100, "e"),
            ],
            bootstyle="dark")
        self.recent_frame.pack(fill="both", expand=True, pady=4)
        self.recent_tree.bind("<Double-1>", lambda e: self._reprint_selected())

        self._load_recent_sales()

    def _load_recent_sales(self):
        try:
            for it in self.recent_tree.get_children():
                self.recent_tree.delete(it)
            hoy = datetime.now().strftime("%Y-%m-%d")
            sales = self.sale_use_case.get_sales_by_day(hoy)
            sales = sorted(sales, key=lambda s: s.sale_id, reverse=True)[:20]
            for s in sales:
                hora = s.date.split(" ")[1][:5] if " " in s.date else ""
                self.recent_tree.insert("", "end", iid=str(s.sale_id),
                    values=(f"#{s.display_number:02d}", hora,
                            f"${s.total:,.0f}"))
        except Exception:
            pass

    def _reprint_selected(self):
        sel = self.recent_tree.selection()
        if not sel:
            MD.show_warning("Selecciona una venta primero.", "Sin selección",
                            parent=self)
            return
        sale_id = int(sel[0])
        sale = self.sale_use_case.get_sale_by_id(sale_id)
        if not sale:
            return
        try:
            payments = self.sale_use_case.get_sale_payments(sale_id)
            info = get_business_info(self.db_manager)
            ruta = generate_ticket_pdf(
                sale, sale.items, payments=payments,
                business_name=info.get("name", "MI NEGOCIO"),
                business_phone=info.get("phone", ""),
                business_address=info.get("place", ""),
                cashier_name=self.db_manager.get_setting("cashier_name", ""))
            self.last_ticket_path = ruta
            r = MD.yesno(f"Ticket generado:\n{ruta}\n\n¿Abrirlo?",
                         "Ticket", parent=self)
            if r == "Yes":
                self._open_file(ruta)
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    def _return_selected(self):
        sel = self.recent_tree.selection()
        if not sel:
            MD.show_warning("Selecciona una venta para devolver.",
                            "Sin selección", parent=self)
            return
        sale_id = int(sel[0])
        sale = self.sale_use_case.get_sale_by_id(sale_id)
        if not sale:
            return
        from presentation.views.widgets import ReturnDialog
        ReturnDialog(self, self.sale_use_case, sale,
                     on_success=self._after_return)

    def _after_return(self):
        self._load_recent_sales()

    def open_returns_window(self):
        from presentation.views.widgets import ReturnsWindow
        ReturnsWindow(self, self.sale_use_case,
                      on_done=self._load_recent_sales)

    # ============================================================
    # BÚSQUEDA
    # ============================================================
    def _get_product_labels(self):
        vals = []
        try:
            for p in self.product_use_case.list_active_products():
                txt = f"{p.name}  |  {p.barcode}" if p.barcode else p.name
                vals.append(txt)
        except Exception:
            pass
        return vals

    def _find_by_barcode(self, codigo):
        try:
            return self.product_use_case.find_by_barcode(codigo)
        except Exception:
            return None

    def _find_by_name(self, query):
        """Busca por nombre exacto o aproximado."""
        q = query.strip().lower()
        if not q:
            return None
        try:
            products = self.product_use_case.list_active_products()
        except Exception:
            return None
        # Coincidencia exacta por nombre
        for p in products:
            if (p.name or "").lower() == q:
                return p
        # Coincidencia por barcode
        for p in products:
            if p.matches_barcode(q):
                return p
        # Coincidencia parcial
        for p in products:
            if q in (p.name or "").lower():
                return p
        return None

    # ============================================================
    # SCANNER — Muestra detalle del producto
    # ============================================================
    def on_barcode_scanned(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo:
            return
        self.scan_var.set("")
        enc = self._find_by_barcode(codigo)
        if not enc:
            r = MD.yesno(
                f"⚠️ El código '{codigo}' no está registrado.\n\n"
                f"¿Deseas agregarlo al inventario?",
                "No encontrado", parent=self)
            if r == "Yes":
                try:
                    top = self.winfo_toplevel()
                    if hasattr(top, "inventory_view"):
                        top.show_page("inventario")
                        top.inventory_view.add_product_popup(
                            barcode_prefill=codigo, auto_select=True)
                except Exception:
                    pass
            self.scan_entry.focus_set()
            return
        self._show_product_detail(enc)

    # ============================================================
    # BÚSQUEDA — Muestra detalle del producto
    # ============================================================
    def on_search_selected(self, value):
        """Se dispara al seleccionar del autocomplete."""
        self.after(10, lambda: self._process_search(value))

    def on_search_clicked(self, event=None):
        """Se dispara al hacer clic en el botón Ver producto."""
        raw = self.search_var.get().strip()
        if not raw:
            return
        self._process_search(raw)

    def _process_search(self, value):
        q = value.split("|")[0].strip() if "|" in value else value
        enc = self._find_by_barcode(q)
        if not enc:
            enc = self._find_by_name(q)
        if not enc:
            MD.show_warning(f"⚠️ No se encontró '{q}'.", "No encontrado",
                            parent=self)
            return
        self.search_var.set("")
        self._show_product_detail(enc)

    # ============================================================
    # DETALLE DE PRODUCTO — Antes de agregar al carrito
    # ============================================================
    def _show_product_detail(self, product):
        """Muestra una ventana con el detalle del producto y un botón para agregar al carrito."""
        bg, fg, _, _ = get_theme_colors()

        pop = Toplevel(self)
        pop.title(f"Detalle - {product.name}")
        pop.geometry("480x620")
        pop.transient(self.winfo_toplevel())
        pop.withdraw()
        pop.configure(bg=bg)

        # Título
        tk.Label(pop, text="📋 DETALLE DEL PRODUCTO",
                 font=("Arial", 15, "bold"), bg=bg, fg=fg).pack(pady=(15, 6))
        tk.Label(pop, text=product.name,
                 font=("Arial", 16, "bold"), bg=bg, fg="#a8e6a8",
                 wraplength=440, justify="center").pack(pady=(0, 10))

        # Info
        info = tk.Frame(pop, bg=bg)
        info.pack(fill="x", padx=30, pady=6)

        def row(label, value, value_color=None):
            f = tk.Frame(info, bg=bg)
            f.pack(fill="x", pady=3)
            tk.Label(f, text=f"{label}:", font=("Arial", 10, "bold"),
                     bg=bg, fg=fg, width=20, anchor="w").pack(side="left")
            tk.Label(f, text=str(value), font=("Arial", 10),
                     bg=bg, fg=value_color or fg).pack(side="left")

        row("Código 1", product.barcode or "—")
        barcode2 = getattr(product, "barcode2", "") or ""
        if barcode2:
            row("Código 2 (caja)", barcode2)
        row("Cantidad disponible", f"{product.stock:g} {product.unit or 'unidad'}")

        # Separador
        tk.Frame(pop, height=2, bg="#444444").pack(fill="x", padx=30, pady=8)

        # Precios GRANDES
        tk.Label(pop, text="💰 PRECIOS", font=("Arial", 12, "bold"),
                 bg=bg, fg=fg).pack(anchor="w", padx=30, pady=(0, 6))

        # Precio unitario
        precio_unit = getattr(product, "rounded_price", 0) or product.price
        f_unit = tk.Frame(pop, bg=bg)
        f_unit.pack(fill="x", padx=30, pady=4)
        tk.Label(f_unit, text="Precio por unidad:",
                 font=("Arial", 11, "bold"), bg=bg, fg=fg,
                 width=20, anchor="w").pack(side="left")
        tk.Label(f_unit, text=f"${precio_unit:,.0f}".replace(",", "."),
                 font=("Arial", 22, "bold"), bg=bg, fg="#7dd87d").pack(side="left", padx=8)

        # Precio del paquete (si aplica)
        if getattr(product, "is_package", 0):
            pkg_units = getattr(product, "package_units", 0) or 0
            precio_paquete = precio_unit * pkg_units
            f_pkg = tk.Frame(pop, bg=bg)
            f_pkg.pack(fill="x", padx=30, pady=4)
            tk.Label(f_pkg, text="Precio por paquete:",
                     font=("Arial", 11, "bold"), bg=bg, fg=fg,
                     width=20, anchor="w").pack(side="left")
            tk.Label(f_pkg, text=f"${precio_paquete:,.0f}".replace(",", "."),
                     font=("Arial", 22, "bold"), bg=bg, fg="#ffd166").pack(side="left", padx=8)
            f_pkg2 = tk.Frame(pop, bg=bg)
            f_pkg2.pack(fill="x", padx=30, pady=2)
            tk.Label(f_pkg2, text="Unidades por paquete:",
                     font=("Arial", 10), bg=bg, fg=fg,
                     width=20, anchor="w").pack(side="left")
            tk.Label(f_pkg2, text=f"{pkg_units}",
                     font=("Arial", 10), bg=bg, fg=fg).pack(side="left")
        else:
            f_pkg = tk.Frame(pop, bg=bg)
            f_pkg.pack(fill="x", padx=30, pady=4)
            tk.Label(f_pkg, text="Precio por paquete:",
                     font=("Arial", 11, "bold"), bg=bg, fg=fg,
                     width=20, anchor="w").pack(side="left")
            tk.Label(f_pkg, text="—",
                     font=("Arial", 22, "bold"), bg=bg, fg=fg).pack(side="left", padx=8)

        # Separador
        tk.Frame(pop, height=2, bg="#444444").pack(fill="x", padx=30, pady=8)

        # Tipo de venta
        is_peso_vol = product.unit_type in ("peso", "volumen")
        tk.Label(pop, text="Cantidad a agregar:",
                 font=("Arial", 11, "bold"), bg=bg, fg=fg).pack(pady=(4, 4))
        qty_var = tk.StringVar(value="1")
        e = ttk.Entry(pop, textvariable=qty_var, width=15,
                      font=("Arial", 16), justify="center")
        e.pack(pady=4)
        e.select_range(0, tk.END)
        e.focus_set()
        e.bind("<Return>", lambda ev: self._confirm_add(pop, product, qty_var))

        tk.Label(pop, text=f"({product.unit or 'unidad'})",
                 font=("Arial", 9, "italic"), bg=bg, fg="#888888").pack()

        # Botones
        bf = tk.Frame(pop, bg=bg)
        bf.pack(side="bottom", pady=15)

        ttk.Button(bf, text="➕ Agregar al carrito",
                   command=lambda: self._confirm_add(pop, product, qty_var),
                   style="DarkGreen.TButton").pack(side="left", padx=6)
        ttk.Button(bf, text="❌ Cancelar",
                   command=lambda: [pop.destroy(), self.scan_entry.focus_set()]
                   ).pack(side="left", padx=6)

        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

    def _confirm_add(self, popup, product, qty_var):
        try:
            qty = float(qty_var.get().replace(",", ".") or 0)
            if qty <= 0:
                raise ValueError
        except ValueError:
            MD.show_error("Cantidad inválida.", "Error", parent=popup)
            return
        popup.destroy()
        self.add_to_cart(product, qty)
        self.scan_entry.focus_set()

    # ============================================================
    # CARRITO
    # ============================================================
    def add_to_cart(self, product, cantidad):
        for it in self.cart:
            if it["product_id"] == product.product_id:
                it["quantity"] += cantidad
                it["subtotal"] = it["quantity"] * it["unit_price"]
                self.refresh_cart()
                self._save_cart_draft()
                return
        precio = getattr(product, "effective_price", None)
        if precio is None:
            precio = (product.rounded_price
                      if getattr(product, "rounded_price", 0) else product.price)
        self.cart.append({
            "product_id": product.product_id,
            "product_name": product.name,
            "barcode": product.barcode or "",
            "unit": product.unit or "unidad",
            "unit_price": precio,
            "quantity": cantidad,
            "subtotal": cantidad * precio,
        })
        self.refresh_cart()
        self._save_cart_draft()

    def refresh_cart(self):
        for r in self.tree.get_children():
            self.tree.delete(r)
        for it in self.cart:
            qt = (f"{it['quantity']:g} {it['unit']}"
                  if it.get("unit", "unidad") != "unidad"
                  else f"{int(it['quantity'])}")
            self.tree.insert("", "end", values=(
                it["product_id"], it["product_name"], it["barcode"],
                f"${it['unit_price']:,.0f}", qt,
                f"${it['subtotal']:,.0f}"))
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

    # ============================================================
    # MENÚ CONTEXTUAL DEL CARRITO
    # ============================================================
    def _cart_context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self.tree.focus(row)
        vals = self.tree.item(row, 'values')
        pid = int(vals[0])
        name = vals[1]
        bg, fg, sel_bg, sel_fg = get_theme_colors()
        m = tk.Menu(self, tearoff=0,
                    bg=bg, fg=fg,
                    activebackground=sel_bg,
                    activeforeground=sel_fg,
                    bd=1, relief="solid", font=get_menu_font())
        m.add_command(label="➖ Quitar 1",
                      command=lambda: self._remove_one(pid, name))
        m.add_command(label="🗑️  Quitar completo",
                      command=lambda: self._remove_all(pid, name))
        m.add_separator()
        m.add_command(label="🧹 Vaciar carrito", command=self.clear_cart)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    def _remove_one(self, pid, name):
        if MD.yesno(f"¿Quitar 1 de '{name}'?", "Confirmar", parent=self) != "Yes":
            return
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

    def _remove_all(self, pid, name):
        if MD.yesno(f"¿Quitar TODO '{name}'?", "Confirmar", parent=self) != "Yes":
            return
        self.cart = [i for i in self.cart if i["product_id"] != pid]
        self.refresh_cart()
        self._save_cart_draft()
        self.scan_entry.focus_set()

    # ============================================================
    # COBRAR
    # ============================================================
    def pay(self):
        try:
            self._pay_internal()
        except Exception as e:
            import traceback
            traceback.print_exc()
            MD.show_error(f"Error al cobrar: {e}", "Error", parent=self)

    def _pay_internal(self):
        if not self.cart:
            MD.show_warning("El carrito está vacío.", "Nada que cobrar",
                            parent=self)
            return
        total = sum(i["subtotal"] for i in self.cart)

        bg, fg, _, _ = get_theme_colors()
        pop = Toplevel(self)
        pop.title("Confirmar Pago")
        pop.geometry("640x780")
        pop.transient(self.winfo_toplevel())
        pop.withdraw()
        pop.configure(bg=bg)

        tk.Label(pop, text="💰 CONFIRMAR PAGO",
                 font=("Arial", 15, "bold"), bg=bg, fg=fg).pack(pady=(10, 3))

        total_frame = tk.Frame(pop, bg="#0a4d1f", padx=20, pady=8)
        total_frame.pack(pady=(0, 6))
        tk.Label(total_frame, text="TOTAL A PAGAR",
                 font=("Arial", 9, "bold"),
                 bg="#0a4d1f", fg="#a8e6a8").pack()
        tk.Label(total_frame, text=f"${total:,.0f}".replace(",", "."),
                 font=("Arial", 24, "bold"),
                 bg="#0a4d1f", fg="#a8e6a8").pack()

        tk.Label(pop, text="Nombre del cliente (opcional):",
                 font=("Arial", 10), bg=bg, fg=fg).pack(pady=(3, 2))
        nombre_var = tk.StringVar()
        ttk.Entry(pop, textvariable=nombre_var, width=40,
                  font=("Arial", 11)).pack(pady=3, padx=20)

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

        mixed_frame = tk.Frame(pop, bg=bg)
        mixed_frame.pack(fill="x", pady=(8, 2), padx=20)
        mixed_var = tk.BooleanVar(value=False)
        chk_mixed = ttk.Checkbutton(
            mixed_frame, text="💳 Pago dividido (múltiples métodos)",
            variable=mixed_var, bootstyle="info-round-toggle")
        chk_mixed.pack(anchor="w")

        rows_frame = tk.Frame(pop, bg=bg)
        rows_frame.pack(fill="x", padx=20, pady=4)
        payment_rows = []

        def add_pay_row():
            idx = len(payment_rows) + 1
            f = tk.Frame(rows_frame, bg=bg)
            f.pack(fill="x", pady=2)
            tk.Label(f, text=f"Método {idx}:", bg=bg, fg=fg,
                     width=10, anchor="w").pack(side="left")
            mv = tk.StringVar(value="Efectivo")
            ttk.Combobox(f, textvariable=mv, state="readonly",
                         values=["Efectivo", "Transferencia", "Tarjeta"],
                         width=15).pack(side="left", padx=4)
            av = tk.StringVar(value="0")
            ttk.Entry(f, textvariable=av, width=12,
                      justify="center").pack(side="left", padx=4)
            row = {"frame": f, "method": mv, "amount": av}
            payment_rows.append(row)
            av.trace_add("write", lambda *a: update_faltan())

            def quitar():
                if row in payment_rows:
                    payment_rows.remove(row)
                    f.destroy()
                    update_faltan()

            ttk.Button(f, text="✖", command=quitar,
                       bootstyle="danger", width=3).pack(side="left", padx=4)
            update_faltan()

        faltan_lbl = tk.Label(pop, text="", font=("Arial", 11, "bold"),
                              bg=bg, fg="#ffd166")
        faltan_lbl.pack(pady=4)

        def update_faltan():
            try:
                suma = sum(float(r["amount"].get() or 0) for r in payment_rows)
            except ValueError:
                suma = 0.0
            diff = total - suma
            if abs(diff) < 0.5:
                faltan_lbl.configure(text="✅ Cubierto", fg="#7dd87d")
            elif diff > 0:
                faltan_lbl.configure(text=f"Faltan: ${diff:,.0f}".replace(",", "."),
                                     fg="#ff8888")
            else:
                faltan_lbl.configure(text=f"Vuelto: ${abs(diff):,.0f}".replace(",", "."),
                                     fg="#7dd87d")

        def toggle_mixed():
            if mixed_var.get():
                for w in rows_frame.winfo_children():
                    w.destroy()
                payment_rows.clear()
                add_pay_row()
                add_pay_row()
            else:
                for w in rows_frame.winfo_children():
                    w.destroy()
                payment_rows.clear()
                faltan_lbl.configure(text="")

        mixed_var.trace_add("write", lambda *a: toggle_mixed())

        ttk.Button(rows_frame, text="➕ Agregar método",
                   command=add_pay_row, bootstyle="secondary").pack(pady=4)

        deuda_lbl = tk.Label(pop, text="", font=("Arial", 10, "bold"),
                             bg=bg, fg="#ffd166",
                             wraplength=580, justify="center")
        deuda_lbl.pack(pady=3, padx=10)

        tk.Label(pop, text="Notas (opcional):",
                 font=("Arial", 10), bg=bg, fg=fg).pack(pady=(4, 2))
        notas_var = tk.StringVar()
        ttk.Entry(pop, textvariable=notas_var, width=40,
                  font=("Arial", 11)).pack(pady=3, padx=20)

        bottom_container = tk.Frame(pop, bg=bg)
        bottom_container.pack(side="bottom", fill="x", pady=8)

        bf = tk.Frame(bottom_container, bg=bg)
        bf.pack(side="bottom", pady=4)

        saldo_lbl = tk.Label(bottom_container, text="",
                             font=("Arial", 11, "bold"),
                             bg=bg, fg="#a8e6a8",
                             wraplength=580, justify="center")

        abono_frame = tk.Frame(bottom_container, bg=bg)
        abono_var = tk.BooleanVar(value=False)
        abono_monto_var = tk.StringVar(value="")

        chk_abono = ttk.Checkbutton(
            abono_frame, text="💵 Abonar",
            variable=abono_var, bootstyle="success-round-toggle")
        chk_abono.pack(side="left", padx=5)

        tk.Label(abono_frame, text="Monto:", bg=bg, fg=fg,
                 font=("Arial", 10)).pack(side="left", padx=5)
        ttk.Entry(abono_frame, textvariable=abono_monto_var,
                  width=12, font=("Arial", 11),
                  justify="center").pack(side="left", padx=5)

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
                        text=f"📌 FIADO a: {nombre}  |  Deuda anterior: "
                             f"${deuda:,.0f} + Venta: ${total:,.0f} = "
                             f"${total_nuevo:,.0f}".replace(",", "."),
                        fg="#ffd166")
                else:
                    deuda_lbl.configure(
                        text=f"📌 FIADO a: {nombre}  |  Total: "
                             f"${total:,.0f}".replace(",", "."),
                        fg="#ffd166")
            else:
                if deuda > 0:
                    deuda_lbl.configure(
                        text=f"⚠️ {nombre} debe ${deuda:,.0f} de fiados previos "
                             f"(esta venta es aparte).".replace(",", "."),
                        fg="#ffd166")
                else:
                    deuda_lbl.configure(
                        text=f"ℹ️ {nombre} no tiene deudas previas.",
                        fg="#a8e6a8")

            if not (deuda > 0 or es_fiado):
                return

            saldo_lbl.pack(side="bottom", pady=2)
            abono_frame.pack(side="bottom", pady=4)

            try:
                monto = 0.0
                if abono_var.get():
                    try:
                        monto = float(abono_monto_var.get()
                                      .replace("$", "").replace(".", "")
                                      .replace(",", ".") or 0)
                    except ValueError:
                        monto = 0.0
                    if monto > deuda:
                        monto = deuda
                if es_fiado:
                    total_acum = deuda + total
                    saldo = max(0, total_acum - monto)
                    if abono_var.get() and monto > 0:
                        saldo_lbl.configure(
                            text=f"💵 Nueva deuda después del abono: "
                                 f"${saldo:,.0f}".replace(",", "."))
                    else:
                        saldo_lbl.configure(
                            text=f"💵 Nueva deuda total: "
                                 f"${total_acum:,.0f}".replace(",", "."))
                else:
                    if abono_var.get() and monto > 0:
                        saldo = max(0, deuda - monto)
                        saldo_lbl.configure(
                            text=f"💵 Saldo de la deuda anterior: "
                                 f"${saldo:,.0f}".replace(",", "."))
                    else:
                        saldo_lbl.configure(
                            text=f"💵 Deuda anterior: "
                                 f"${deuda:,.0f}".replace(",", "."))
            except Exception:
                saldo_lbl.configure(text="")

        nombre_var.trace_add("write", refresh_ui)
        metodo_var.trace_add("write", refresh_ui)
        abono_var.trace_add("write", refresh_ui)
        abono_monto_var.trace_add("write", refresh_ui)

        def confirmar():
            nombre = nombre_var.get().strip()
            metodo = metodo_var.get()
            es_fiado = (metodo == "Fiado")
            monto_abono = 0.0
            if abono_var.get() and nombre:
                try:
                    monto_abono = float(
                        abono_monto_var.get()
                        .replace("$", "").replace(".", "")
                        .replace(",", ".") or 0)
                except ValueError:
                    monto_abono = 0.0

            payments = None
            if mixed_var.get() and payment_rows:
                payments = []
                for r in payment_rows:
                    try:
                        amt = float(r["amount"].get() or 0)
                    except ValueError:
                        amt = 0.0
                    if amt > 0:
                        payments.append({"method": r["method"].get(),
                                          "amount": amt})
                if payments:
                    suma = sum(p["amount"] for p in payments)
                    if suma < total - 0.5:
                        MD.show_warning(
                            f"Faltan ${total - suma:,.0f} en el pago."
                            .replace(",", "."),
                            "Pago incompleto", parent=pop)
                        return
                    metodo = max(payments, key=lambda x: x["amount"])["method"]

            try:
                _sid, tot, display_num = self.sale_use_case.create_sale(
                    self.cart,
                    payment_method=metodo,
                    notes=notas_var.get().strip(),
                    customer_name=nombre,
                    is_credit=es_fiado,
                    payments=payments)
                msg = f"✅ Venta #{display_num:02d} registrada.\n"
                msg += f"Total: ${tot:,.0f}".replace(",", ".")
                if es_fiado:
                    quien = nombre if nombre else "(sin nombre)"
                    deuda = (self.sale_use_case.get_pending_by_customer(quien)
                             if nombre else tot)
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

                self.last_sale_id = _sid
                self.cart = []
                self.refresh_cart()
                self.sale_use_case.clear_cart_draft()
                pop.destroy()

                MD.show_info(msg, "Venta Exitosa", parent=self)

                try:
                    copias = int(self.db_manager.get_setting("ticket_copies", "0") or 0)
                    if copias >= 1:
                        self._print_ticket_for_sale(_sid)
                except Exception:
                    pass

                self._load_recent_sales()
                self.scan_entry.focus_set()
            except Exception as e:
                import traceback
                traceback.print_exc()
                MD.show_error(f"Error: {e}", "Error", parent=pop)

        ttk.Button(bf, text="✅ Confirmar Pago", command=confirmar,
                   style="DarkGreen.TButton").pack(side="left", padx=8,
                                                   ipady=8, ipadx=15)
        ttk.Button(bf, text="Cancelar",
                   command=pop.destroy).pack(side="left", padx=8, ipady=8)

        show_popup_smooth(pop)
        try:
            pop.grab_set()
            pop.focus_force()
        except Exception:
            pass

    # ============================================================
    # TICKET
    # ============================================================
    def _print_ticket_for_sale(self, sale_id, is_copy=False):
        try:
            sale = self.sale_use_case.get_sale_by_id(sale_id)
            if not sale:
                return
            payments = self.sale_use_case.get_sale_payments(sale_id)
            info = get_business_info(self.db_manager)
            ruta = generate_ticket_pdf(
                sale, sale.items, payments=payments,
                business_name=info.get("name", "MI NEGOCIO"),
                business_phone=info.get("phone", ""),
                business_address=info.get("place", ""),
                cashier_name=self.db_manager.get_setting("cashier_name", ""),
                is_copy=is_copy)
            self.last_ticket_path = ruta
            return ruta
        except Exception as e:
            print(f"Error ticket: {e}")
            return None

    def open_last_ticket(self):
        if not self.last_ticket_path or not os.path.exists(self.last_ticket_path):
            try:
                sales = self.sale_use_case.get_all_sales(limit=1)
                if not sales:
                    MD.show_info("No hay tickets aún.", "Sin ticket", parent=self)
                    return
                ruta = self._print_ticket_for_sale(sales[0].sale_id)
                if not ruta:
                    MD.show_info("No se pudo generar el ticket.", "Error",
                                 parent=self)
                    return
            except Exception as e:
                MD.show_error(f"Error: {e}", "Error", parent=self)
                return
        r = MD.yesno(f"Ticket:\n{self.last_ticket_path}\n\n¿Abrirlo?",
                     "Último ticket", parent=self)
        if r == "Yes":
            self._open_file(self.last_ticket_path)

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