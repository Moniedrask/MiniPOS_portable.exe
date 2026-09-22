import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
from ttkbootstrap.dialogs import Messagebox
from datetime import datetime, timedelta
import os
from presentation.views.widgets import (
    apply_titlebar_theme, center_window, show_popup_smooth,
    get_menu_font, AutoCompleteEntry, MD, TreeviewTooltip,
    popup_is_open, make_scrolled_treeview, make_scrollable,
    find_similar_products,
)


def _parse_float(s):
    try:
        return float(str(s).replace("$", "").replace(".", "").replace(",", ".").strip() or 0)
    except Exception:
        return 0.0


def _round_up(value, to):
    """Redondea un precio hacia arriba al múltiplo más cercano."""
    try:
        if to <= 0:
            return value
        return int(((value + to - 1) // to) * to)
    except Exception:
        return int(value)


class InventoryView(ttk.Frame):
    def __init__(self, parent, product_use_case, db_manager,
                 get_theme_func, on_business_click=None):
        super().__init__(parent, bootstyle="dark")
        self.product_use_case = product_use_case
        self.db_manager = db_manager
        self.get_theme = get_theme_func
        self.on_business_click = on_business_click
        self.sort_col = None
        self.sort_reverse = False
        self.filtered_products = []
        self.tooltip = None
        self._draft_checked = False

        self.low_stock_threshold = self._get_int_setting("low_stock_threshold", 5)
        self.expiry_days_warning = self._get_int_setting("expiry_days_warning", 15)
        self.expiry_days_soon = self._get_int_setting("expiry_days_soon", 7)
        self.expiry_days_offer = self._get_int_setting("expiry_days_offer", 2)

        self.create_widgets()
        self.load_products()
        self.after(300, lambda: self.scan_entry.focus_set())
        self.after(800, self._check_product_draft)
        self._keep_scanner_focused()

    def _get_int_setting(self, key, default):
        try:
            return int(self.db_manager.get_setting(key, str(default)) or default)
        except Exception:
            return default

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

    def _check_product_draft(self):
        if self._draft_checked:
            return
        try:
            if not self.winfo_ismapped():
                self.after(500, self._check_product_draft)
                return
        except Exception:
            pass
        self._draft_checked = True
        try:
            data, updated = self.product_use_case.load_product_draft()
        except Exception:
            return
        if not data:
            return
        name = (data.get("name") or "").strip()
        barcode = (data.get("barcode") or "").strip()
        if not name and not barcode:
            self.product_use_case.clear_product_draft()
            return
        try:
            mode = data.get("mode", "create")
            titulo = "editar" if mode == "edit" else "agregar"
            fecha = updated or "(sin fecha)"
            r = MD.yesno(
                f"📝 Se encontró un producto a medio {titulo}:\n\n"
                f"Nombre: {name or '(vacío)'}\n"
                f"Código: {barcode or '(vacío)'}\n"
                f"Guardado: {fecha}\n\n"
                f"¿Deseas recuperarlo?",
                "Recuperar borrador", parent=self)
            if r == "Yes":
                self._open_draft(data)
            else:
                self.product_use_case.clear_product_draft()
        except Exception:
            pass

    def _open_draft(self, data):
        mode = data.get("mode", "create")
        pid = data.get("product_id")
        self.open_product_form(
            "Editar Producto" if mode == "edit" else "Agregar Producto",
            pid,
            data.get("name", ""),
            data.get("barcode", ""),
            _parse_float(data.get("price", 0)),
            _parse_float(data.get("stock", 0)),
            data.get("type", "unidad"),
            data.get("unit", "unidad"),
            auto_select=False,
            from_draft=True,
            group_name=data.get("group_name", ""),
            cost=_parse_float(data.get("cost", 0)),
            margin_percent=_parse_float(data.get("margin_percent", 20)),
            rounded_price=_parse_float(data.get("rounded_price", 0)),
            round_enabled=1 if data.get("round_enabled") else 0,
            round_to=int(_parse_float(data.get("round_to", 100))),
            package_cost=_parse_float(data.get("package_cost", 0)),
            package_units=int(_parse_float(data.get("package_units", 0))),
            is_package=1 if data.get("is_package") else 0,
            paused=1 if data.get("paused") else 0,
            expiry_date=data.get("expiry_date", ""))

    def create_widgets(self):
        # ---- Barra escaneo ----
        scan_frame = ttk.Frame(self, bootstyle="dark")
        scan_frame.pack(padx=10, pady=(8, 3), fill="x")
        ttk.Label(scan_frame, text="📷 Escanear:",
                  font=("Arial", 11, "bold"), bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(scan_frame, textvariable=self.scan_var,
                                    width=30, font=("Arial", 11))
        self.scan_entry.pack(side="left", padx=5)
        self.scan_entry.bind("<Return>", self.lookup_barcode)
        ttk.Button(scan_frame, text="🔍 Buscar Código",
                   command=lambda: self.lookup_barcode(None),
                   style="DarkGreen.TButton").pack(side="left", padx=5)

        # ---- Búsqueda ----
        search_frame = ttk.Frame(self, bootstyle="dark")
        search_frame.pack(padx=10, pady=3, fill="x")
        ttk.Label(search_frame, text="🔍 Búsqueda:",
                  bootstyle="inverse-dark").pack(side="left", padx=5)

        self.search_var = tk.StringVar()
        self.search_entry = AutoCompleteEntry(
            search_frame,
            values_getter=self._get_product_labels,
            on_select=self._on_search_select,
            width=35,
            font=("Arial", 11))
        self.search_entry.configure(textvariable=self.search_var)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind('<KeyRelease>', self._on_search_key, add='+')

        ttk.Button(search_frame, text="Limpiar", command=self._clear_search,
                   bootstyle="secondary").pack(side="left", padx=5)
        self.chk_paused = tk.BooleanVar(value=False)
        ttk.Checkbutton(search_frame, text="👁 Incluir pausados",
                        variable=self.chk_paused,
                        command=self.load_products,
                        bootstyle="info-round-toggle").pack(side="left", padx=10)

        # ---- Alerta de vencimiento / stock ----
        self.alert_lbl = tk.Label(
            self, text="", font=("Arial", 10, "italic"),
            bg=ttk.Style().colors.bg, fg="#ffbbbb", justify="left", anchor="w")
        self.alert_lbl.pack(padx=10, pady=1, fill="x")

        # ---- Botón agregar (abajo) ----
        btn_frame = ttk.Frame(self, bootstyle="dark")
        btn_frame.pack(side="bottom", pady=6, fill="x")
        ttk.Button(btn_frame, text="➕ Agregar Producto (F2)",
                   command=self.add_product_popup,
                   style="DarkGreen.TButton").pack(side="left", padx=5)

        # ---- Tabla ----
        frame = ttk.Frame(self, bootstyle="dark")
        frame.pack(padx=10, pady=3, fill="both", expand=True)

        self.columns = [
            ("ID", "ID", 40, "center"),
            ("Name", "Producto", 170, "w"),
            ("Group", "Grupo", 100, "w"),
            ("Barcode", "Código", 115, "w"),
            ("Cost", "Costo", 75, "e"),
            ("Margin", "%", 55, "center"),
            ("Price", "Precio", 80, "e"),
            ("Rounded", "Redondeado", 90, "e"),
            ("Stock", "Stock", 60, "center"),
            ("Expiry", "Vence", 95, "center"),
            ("Status", "Estado", 80, "center"),
        ]

        self.tree_frame, self.tree = make_scrolled_treeview(
            frame,
            columns=[c[0] for c in self.columns],
            headings=[(c[0], c[1] + "  ⇅", c[2], c[3]) for c in self.columns],
            bootstyle="dark")
        self.tree_frame.pack(fill="both", expand=True)

        for key, label, w, anchor in self.columns:
            self.tree.heading(key, text=label + "  ⇅",
                              command=lambda k=key: self.sort_by(k))

        # Tags de color
        try:
            self.tree.tag_configure("low_stock",
                                    background="#5c1a1a", foreground="#ffcccc")
            self.tree.tag_configure("expired",
                                    background="#6e1515", foreground="#ffffff")
            self.tree.tag_configure("expiring_soon",
                                    background="#5c3d0f", foreground="#ffd166")
            self.tree.tag_configure("paused",
                                    background="#333333", foreground="#888888")
        except Exception:
            pass

        self.tree.bind("<Double-1>", self.view_product_popup)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tooltip = TreeviewTooltip(self.tree, font_size=11)

    # =========================================================
    # UTILIDADES DE PRODUCTOS
    # =========================================================
    def _get_product_labels(self):
        vals = []
        for p in self.product_use_case.list_products():
            txt = f"{p.name}  |  {p.barcode}" if p.barcode else p.name
            vals.append(txt)
        return vals

    def _on_search_key(self, event=None):
        self.filter_products()

    def _on_search_select(self, value):
        self.filter_products()

    def _clear_search(self):
        self.search_var.set("")
        self.load_products()
        self.scan_entry.focus_set()

    def sort_by(self, col):
        if self.sort_col == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_col = col
            self.sort_reverse = False
        self._update_headings()
        self._render_products(self.filtered_products)

    def _update_headings(self):
        for key, label, w, anchor in self.columns:
            if self.sort_col == key:
                arrow = " ▼" if self.sort_reverse else " ▲"
                self.tree.heading(key, text=label + arrow)
            else:
                self.tree.heading(key, text=label + "  ⇅")

    def _render_products(self, products):
        for it in self.tree.get_children():
            self.tree.delete(it)
        if self.sort_col:
            keys = {
                "ID": lambda p: p.product_id,
                "Name": lambda p: (p.name or "").lower(),
                "Group": lambda p: (p.group_name or "").lower(),
                "Barcode": lambda p: (p.barcode or ""),
                "Cost": lambda p: p.cost,
                "Margin": lambda p: p.margin_percent,
                "Price": lambda p: p.price,
                "Rounded": lambda p: p.rounded_price,
                "Stock": lambda p: p.stock,
                "Expiry": lambda p: p.expiry_date or "",
                "Status": lambda p: p.paused,
            }
            products = sorted(products,
                              key=keys.get(self.sort_col, lambda p: p.product_id),
                              reverse=self.sort_reverse)
        for p in products:
            self._insert_product_row(p)
        self._update_alerts(products)

    def _update_alerts(self, products):
        try:
            alertas = []
            # Stock bajo
            bajos = [p for p in products
                     if not p.paused and p.stock <= self.low_stock_threshold]
            if bajos:
                alertas.append(f"⚠️ {len(bajos)} producto(s) con stock bajo (≤ {self.low_stock_threshold})")
            # Vencimiento
            hoy = datetime.now().date()
            vencidos = 0
            por_vencer = 0
            para_oferta = 0
            for p in products:
                if not p.expiry_date or p.paused:
                    continue
                try:
                    fecha = datetime.strptime(p.expiry_date, "%Y-%m-%d").date()
                except Exception:
                    continue
                dias = (fecha - hoy).days
                if dias < 0:
                    vencidos += 1
                elif dias <= self.expiry_days_warning:
                    por_vencer += 1
                if 0 <= dias <= self.expiry_days_offer:
                    para_oferta += 1
            if vencidos:
                alertas.append(f"🔴 {vencidos} producto(s) VENCIDO(S)")
            if por_vencer:
                alertas.append(f"🟡 {por_vencer} producto(s) por vencer (≤ {self.expiry_days_warning} días)")
            if para_oferta:
                alertas.append(f"💡 {para_oferta} producto(s) en zona de oferta (≤ {self.expiry_days_offer} días)")
            self.alert_lbl.configure(text="  |  ".join(alertas) if alertas else "")
        except Exception:
            pass

    def load_products(self):
        if getattr(self, "chk_paused", None) and self.chk_paused.get():
            self.filtered_products = self.product_use_case.list_products()
        else:
            self.filtered_products = self.product_use_case.list_active_products()
        # Aplicar filtro de búsqueda si hay
        self._render_products(self.filtered_products)

    def filter_products(self, event=None):
        q = self.search_var.get().lower().strip()
        if "|" in q:
            q = q.split("|")[0].strip()
        base = self.product_use_case.list_active_products() \
            if not (getattr(self, "chk_paused", None) and self.chk_paused.get()) \
            else self.product_use_case.list_products()
        if not q:
            self.filtered_products = base
        else:
            self.filtered_products = [
                p for p in base
                if q in (p.name or "").lower()
                or q in str(p.barcode or "").lower()
                or q in (p.group_name or "").lower()]
        self._render_products(self.filtered_products)

    def _insert_product_row(self, p):
        precio = f"${p.price:,.0f}".replace(",", ".")
        redondeado = f"${p.rounded_price:,.0f}".replace(",", ".") if p.rounded_price else "-"
        costo = f"${p.cost:,.0f}".replace(",", ".") if p.cost > 0 else "-"
        margen = f"{p.margin_percent:.0f}%" if p.margin_percent else "-"

        # Vencimiento
        venc = p.expiry_date or "-"
        estado = "Activo"
        tags = ()
        icono = ""

        if p.paused:
            estado = "⏸ Pausado"
            tags = ("paused",)
        else:
            # Vencimiento
            if p.expiry_date:
                try:
                    fecha = datetime.strptime(p.expiry_date, "%Y-%m-%d").date()
                    dias = (fecha - datetime.now().date()).days
                    if dias < 0:
                        estado = "🔴 Vencido"
                        tags = ("expired",)
                    elif dias <= self.expiry_days_soon:
                        estado = f"🟡 Vence en {dias}d"
                        tags = ("expiring_soon",)
                    elif dias <= self.expiry_days_warning:
                        estado = f"🟠 Vence en {dias}d"
                        tags = ("expiring_soon",)
                    else:
                        estado = "✅ OK"
                except Exception:
                    pass
            # Stock bajo (solo si no está vencido)
            if not tags and p.stock <= self.low_stock_threshold:
                tags = ("low_stock",)
                icono = "⚠ "

        self.tree.insert("", "end", values=(
            p.product_id, icono + (p.name or ""), p.group_name or "-", p.barcode or "-",
            costo, margen, precio, redondeado, f"{p.stock:g}",
            venc, estado), tags=tags)

    # =========================================================
    # MENÚ CONTEXTUAL
    # =========================================================
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.tree.focus(item)
        parent = self.winfo_toplevel()
        style = ttk.Style()
        menu = tk.Menu(parent, tearoff=0,
                       bg=style.colors.bg, fg=style.colors.fg,
                       activebackground=style.colors.selectbg,
                       activeforeground=style.colors.selectfg,
                       bd=1, relief="solid",
                       font=get_menu_font())
        menu.add_command(label="👁️  Ver detalle", command=lambda: self.view_product_popup(None))
        menu.add_command(label="✏️  Editar producto", command=lambda: self.open_edit_from_item(item))
        menu.add_command(label="📜  Historial de precios", command=lambda: self.open_price_history(item))
        menu.add_command(label="🔗  Agrupar similares", command=lambda: self.group_from_item(item))
        menu.add_separator()
        # Pausar/Reanudar
        try:
            vals = self.tree.item(item, 'values')
            pid = vals[0]
            prod = self.product_use_case.get_product(pid)
            if prod:
                if prod.paused:
                    menu.add_command(label="▶️  Reactivar producto",
                                     command=lambda: self.toggle_pause(pid, 0))
                else:
                    menu.add_command(label="⏸  Pausar producto",
                                     command=lambda: self.toggle_pause(pid, 1))
        except Exception:
            pass
        menu.add_separator()
        menu.add_command(label="🗑️  Eliminar producto", command=lambda: self.confirm_delete(item))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def toggle_pause(self, product_id, paused):
        try:
            p = self.product_use_case.get_product(product_id)
            if not p:
                return
            self.product_use_case.update_product(
                product_id, p.name, p.barcode, p.price, p.stock,
                p.unit_type, p.unit, p.group_name, p.cost, p.margin_percent,
                p.rounded_price, p.round_enabled, p.round_to,
                p.package_cost, p.package_units, p.is_package,
                paused, p.expiry_date, register_history=False)
            self.load_products()
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    def group_from_item(self, item):
        try:
            vals = self.tree.item(item, 'values')
            name = vals[1].replace("⚠ ", "")
        except Exception:
            return
        self._open_similar_dialog(
            base_name=name,
            current_product_id=None,
            parent_toplevel=self.winfo_toplevel(),
            on_apply=lambda ids, group: self._apply_group_to_ids(ids, group, reload=True))

    def _apply_group_to_ids(self, ids, group, reload=False):
        try:
            if ids and group:
                self.product_use_case.set_group_name(ids, group)
        except Exception:
            pass
        if reload:
            self.load_products()

    # =========================================================
    # DETALLE DEL PRODUCTO (con historial de precios)
    # =========================================================
    def view_product_popup(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], 'values')
        pid = vals[0]

        prod = self.product_use_case.get_product(pid)
        if not prod:
            return

        popup = Toplevel(self)
        popup.title("Detalle del Producto")
        popup.geometry("560x760")
        popup.transient(self.winfo_toplevel())
        popup.withdraw()

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(popup, text="📋 DETALLE DEL PRODUCTO",
                 font=("Arial", 14, "bold"), bg=bg, fg=fg).pack(pady=(12, 6))

        container = tk.Frame(popup, bg=bg)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        def build_content(parent):
            # ---------- Info básica ----------
            info_frame = tk.Frame(parent, bg=bg)
            info_frame.pack(fill="x", padx=10, pady=(5, 10))

            def add_row(label, value, bold=False, color=None):
                row = tk.Frame(info_frame, bg=bg)
                row.pack(fill="x", pady=2)
                tk.Label(row, text=label, font=("Arial", 10),
                         bg=bg, fg="#888888", width=22, anchor="w").pack(side="left")
                tk.Label(row, text=str(value),
                         font=("Arial", 11, "bold") if bold else ("Arial", 10),
                         bg=bg, fg=color or fg, anchor="w",
                         justify="left", wraplength=320).pack(side="left", fill="x", expand=True)

            add_row("ID:", prod.product_id)
            add_row("Nombre:", prod.name, bold=True)
            add_row("Grupo:", prod.group_name or "(sin grupo)")
            add_row("Código de Barras:", prod.barcode or "(vacío)")
            add_row("Unidad:", prod.unit)
            add_row("Costo:", f"${prod.cost:,.0f}".replace(",", ".") if prod.cost else "-")
            add_row("Margen %:", f"{prod.margin_percent:.0f}%" if prod.margin_percent else "-")
            add_row("Precio real:", f"${prod.price:,.0f}".replace(",", "."), bold=True)
            if prod.round_enabled and prod.rounded_price != prod.price:
                add_row("Precio redondeado:",
                        f"${prod.rounded_price:,.0f}".replace(",", "."),
                        bold=True, color="#7dd87d")
                add_row("(Se cobra el redondeado)",
                        f"al {prod.round_to}", color="#7dd87d")
            if prod.is_package and prod.package_units > 0:
                add_row("📦 Costo paquete:",
                        f"${prod.package_cost:,.0f}".replace(",", "."))
                add_row("📦 Unidades x paquete:",
                        f"{prod.package_units}")
                try:
                    unit_cost = prod.package_cost / prod.package_units
                    add_row("📦 Costo unitario:",
                            f"${unit_cost:,.2f}".replace(",", "."))
                except Exception:
                    pass
            add_row("Stock:", f"{prod.stock:g}")
            if prod.expiry_date:
                add_row("📅 Vence:", prod.expiry_date)
                try:
                    fecha = datetime.strptime(prod.expiry_date, "%Y-%m-%d").date()
                    dias = (fecha - datetime.now().date()).days
                    if dias < 0:
                        add_row("Estado vencimiento:",
                                f"🔴 VENCIDO (hace {abs(dias)} días)",
                                color="#ff6b6b")
                    elif dias == 0:
                        add_row("Estado vencimiento:",
                                "🔴 Vence HOY", color="#ff6b6b")
                    elif dias <= self.expiry_days_offer:
                        add_row("Estado vencimiento:",
                                f"🔴 Vence en {dias} días - ¡PONER EN OFERTA!",
                                color="#ff6b6b")
                    elif dias <= self.expiry_days_soon:
                        add_row("Estado vencimiento:",
                                f"🟡 Vence en {dias} días", color="#ffd166")
                    elif dias <= self.expiry_days_warning:
                        add_row("Estado vencimiento:",
                                f"🟠 Vence en {dias} días", color="#ffa94d")
                    else:
                        add_row("Estado vencimiento:",
                                f"✅ OK (vence en {dias} días)", color="#7dd87d")
                except Exception:
                    pass
            if prod.paused:
                add_row("Estado:", "⏸ PAUSADO (no se vende)", color="#ffa94d")
            add_row("Creado:", prod.created_at or "-")
            add_row("Actualizado:", prod.updated_at or "-")

            # ---------- Historial de precios ----------
            sep = ttk.Separator(parent, orient="horizontal")
            sep.pack(fill="x", padx=10, pady=8)

            hist_frame = tk.Frame(parent, bg=bg)
            hist_frame.pack(fill="both", expand=True, padx=10, pady=5)

            tk.Label(hist_frame, text="📜 Historial de cambios de precio",
                     font=("Arial", 12, "bold"), bg=bg, fg=fg).pack(pady=(0, 5))

            hist = self.product_use_case.get_price_history(prod.product_id)

            if not hist:
                tk.Label(hist_frame, text="(Sin cambios registrados)",
                         font=("Arial", 10, "italic"),
                         bg=bg, fg="#888888").pack(pady=10)
            else:
                tf, tree = make_scrolled_treeview(
                    hist_frame,
                    columns=("Fecha", "Antes", "Ahora", "Dif"),
                    headings=[
                        ("Fecha", "Fecha", 145, "center"),
                        ("Antes", "Antes", 95, "e"),
                        ("Ahora", "Ahora", 95, "e"),
                        ("Dif", "Dif.", 90, "e"),
                    ],
                    bootstyle="dark")
                tf.pack(fill="both", expand=True)

                for h in hist:
                    dif = h["new_price"] - h["old_price"]
                    signo = "+" if dif > 0 else ""
                    color_tag = "up" if dif > 0 else "down" if dif < 0 else ""
                    try:
                        tree.tag_configure("up", foreground="#ff6b6b")
                        tree.tag_configure("down", foreground="#7dd87d")
                    except Exception:
                        pass
                    tree.insert("", "end", values=(
                        h["date"],
                        f"${h['old_price']:,.0f}".replace(",", "."),
                        f"${h['new_price']:,.0f}".replace(",", "."),
                        f"{signo}${dif:,.0f}".replace(",", ".")
                    ), tags=(color_tag,))

        def build_bottom(parent):
            bf = tk.Frame(parent, bg=bg)
            bf.pack(pady=8)
            ttk.Button(bf, text="✏️ Editar",
                       command=lambda: [popup.destroy(), self.open_edit_from_item(sel[0])],
                       style="DarkGreen.TButton").pack(side="left", padx=5)
            ttk.Button(bf, text="📜 Exportar historial",
                       command=lambda: self._export_history_for_product(prod),
                       bootstyle="info").pack(side="left", padx=5)
            ttk.Button(bf, text="Cerrar", command=popup.destroy).pack(side="left", padx=5)
            ttk.Button(bf, text="🗑",
                       command=lambda: [popup.destroy(), self.confirm_delete(sel[0])],
                       bootstyle="danger", width=3).pack(side="left", padx=10)

        make_scrollable(container, build_content, build_bottom, bg=bg)

        show_popup_smooth(popup)
        try:
            popup.grab_set()
            popup.focus_force()
        except Exception:
            pass

    def _export_history_for_product(self, prod):
        from tkinter import filedialog
        arch = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=f"historial_{prod.name[:20]}.txt",
            filetypes=[("Texto", "*.txt")])
        if not arch:
            return
        hist = self.product_use_case.get_price_history(prod.product_id)
        if not hist:
            MD.show_info("Este producto no tiene historial de precios.",
                         "Sin datos", parent=self)
            return
        lineas = [f"HISTORIAL DE PRECIOS — {prod.name}",
                  f"ID: {prod.product_id}   Código: {prod.barcode or '-'}",
                  "=" * 60]
        for h in hist:
            dif = h["new_price"] - h["old_price"]
            signo = "+" if dif > 0 else ""
            lineas.append(
                f"{h['date']}  |  Antes: ${h['old_price']:,.0f}  ->  "
                f"Ahora: ${h['new_price']:,.0f}  ({signo}${dif:,.0f})"
                .replace(",", "."))
        try:
            with open(arch, "w", encoding="utf-8") as f:
                f.write("\n".join(lineas))
            MD.show_info(f"Guardado:\n{arch}", "Listo", parent=self)
        except Exception as e:
            MD.show_error(f"Error: {e}", "Error", parent=self)

    def open_price_history(self, item):
        """Abre el historial desde el menú contextual."""
        try:
            vals = self.tree.item(item, 'values')
            pid = vals[0]
        except Exception:
            return
        # Seleccionar y llamar al detalle
        self.tree.selection_set(item)
        self.view_product_popup(None)

    # =========================================================
    # ELIMINAR
    # =========================================================
    def confirm_delete(self, item):
        vals = self.tree.item(item, 'values')
        pid, name = vals[0], vals[1].replace("⚠ ", "")
        if MD.yesno(f"⚠️ ¿ELIMINAR '{name}'?", "Confirmar", parent=self) != "Yes":
            return
        if MD.yesno(f"🚨 ÚLTIMA ADVERTENCIA\n\n¿Realmente eliminar '{name}'?\n\n"
                    f"También se borrará su historial de precios.",
                    "Confirmación final", parent=self) != "Yes":
            return
        self.product_use_case.delete_product(pid)
        self.load_products()
        MD.show_info(f"'{name}' eliminado.", "Listo", parent=self)
        self.scan_entry.focus_set()

    # =========================================================
    # EDITAR
    # =========================================================
    def open_edit_from_item(self, item):
        vals = self.tree.item(item, 'values')
        pid = vals[0]
        prod = self.product_use_case.get_product(pid)
        if not prod:
            return
        self.open_product_form(
            "Editar Producto", prod.product_id, prod.name, prod.barcode,
            prod.price, prod.stock, prod.unit_type, prod.unit,
            group_name=prod.group_name, cost=prod.cost,
            margin_percent=prod.margin_percent,
            rounded_price=prod.rounded_price,
            round_enabled=prod.round_enabled,
            round_to=prod.round_to,
            package_cost=prod.package_cost,
            package_units=prod.package_units,
            is_package=prod.is_package,
            paused=prod.paused,
            expiry_date=prod.expiry_date)

    def add_product_popup(self, barcode_prefill="", auto_select=False):
        try:
            default_margin = _parse_float(
                self.db_manager.get_setting("default_margin", "20") or 20)
            default_round_to = self._get_int_setting("default_round_to", 100)
        except Exception:
            default_margin = 20.0
            default_round_to = 100

        self.open_product_form(
            "Agregar Producto", None, "", barcode_prefill,
            0, 0, "unidad", "unidad", auto_select,
            cost=0.0, margin_percent=default_margin,
            rounded_price=0.0, round_enabled=0, round_to=default_round_to,
            package_cost=0.0, package_units=0, is_package=0,
            paused=0, expiry_date="")

    # =========================================================
    # FORMULARIO DE PRODUCTO (FASE 5)
    # =========================================================
    def open_product_form(self, title, product_id, name, barcode, price, stock,
                          unit_type, unit, auto_select=False, from_draft=False,
                          group_name="", cost=0.0, margin_percent=20.0,
                          rounded_price=0.0, round_enabled=0, round_to=100,
                          package_cost=0.0, package_units=0, is_package=0,
                          paused=0, expiry_date=""):
        popup = Toplevel(self)
        popup.title(title)
        popup.geometry("560x900")
        popup.transient(self.winfo_toplevel())
        popup.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        refs = {}
        state = {
            "draft_timer": None,
            "pending_group_ids": [],
            "updating": False,
            "package_active": bool(is_package),
            "round_active": bool(round_enabled),
        }

        # ---------- CONTENIDO ----------
        def build_content(parent):
            # --- Código ---
            ttk.Label(parent, text="Código de Barras / QR:").pack(pady=(10, 3))
            barcode_entry = ttk.Entry(parent, width=46)
            barcode_entry.pack(pady=3)
            if barcode:
                barcode_entry.insert(0, barcode)

            # --- Nombre ---
            ttk.Label(parent, text="Nombre del Producto:").pack(pady=(10, 3))
            name_entry = ttk.Entry(parent, width=46)
            name_entry.pack(pady=3)
            if name:
                name_entry.insert(0, name)

            similar_lbl = tk.Label(parent, text="", font=("Arial", 9, "italic"),
                                   bg=bg, fg="#a8e6a8", cursor="hand2")
            similar_lbl.pack(pady=2)

            # Aviso de paquete previo
            package_hint = tk.Label(parent, text="", font=("Arial", 9, "italic"),
                                    bg=bg, fg="#ffd166", justify="left")
            package_hint.pack(pady=2)

            # --- Grupo ---
            ttk.Label(parent, text="Grupo (opcional):").pack(pady=(10, 3))
            group_entry = ttk.Entry(parent, width=46)
            group_entry.pack(pady=3)
            if group_name:
                group_entry.insert(0, group_name)

            # --- Tipo de venta ---
            ttk.Label(parent, text="Tipo de venta:",
                      font=("Arial", 10, "bold")).pack(pady=(10, 3))
            type_var = tk.StringVar(value=unit_type)
            type_frame = ttk.Frame(parent)
            type_frame.pack()
            for val, txt in [("unidad", "📦 Por unidad"),
                             ("peso", "⚖️ Por peso"),
                             ("volumen", "💧 Por volumen")]:
                ttk.Radiobutton(type_frame, text=txt, variable=type_var, value=val,
                                command=lambda: self._refresh_unit_options(unit_var, unit_combo, type_var)
                                ).pack(side="left", padx=5)

            ttk.Label(parent, text="Unidad de medida:").pack(pady=(10, 3))
            unit_var = tk.StringVar(value=unit)
            unit_combo = ttk.Combobox(parent, textvariable=unit_var,
                                      state="readonly", width=15)
            unit_combo.pack(pady=3)
            self._refresh_unit_options(unit_var, unit_combo, type_var)

            # ==========================================================
            # 📦 MODO PAQUETE / CAJA
            # ==========================================================
            ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=10)

            is_package_var = tk.BooleanVar(value=bool(is_package))
            ttk.Checkbutton(
                parent,
                text="📦 Viene en paquete / caja (comprar al por mayor)",
                variable=is_package_var,
                command=lambda: toggle_package(),
                bootstyle="warning-round-toggle").pack(pady=6, padx=20, anchor="w")

            package_frame = tk.Frame(parent, bg=bg)

            def build_package_fields(pf):
                tk.Label(pf, text="📦 Cálculo por paquete / caja",
                         font=("Arial", 11, "bold"),
                         bg=bg, fg="#ffd166").pack(pady=(5, 8))

                # Costo paquete
                tk.Label(pf, text="Costo del paquete (lo que pagaste):",
                         font=("Arial", 10), bg=bg, fg=fg).pack(anchor="w", padx=15)
                package_cost_var = tk.StringVar(value=f"{package_cost:g}" if package_cost else "")
                package_cost_entry = ttk.Entry(pf, textvariable=package_cost_var, width=30)
                package_cost_entry.pack(pady=3, padx=15)

                # Unidades por paquete
                tk.Label(pf, text="Unidades por paquete:",
                         font=("Arial", 10), bg=bg, fg=fg).pack(anchor="w", padx=15, pady=(8, 0))
                package_units_var = tk.StringVar(value=f"{package_units}" if package_units else "")
                package_units_entry = ttk.Entry(pf, textvariable=package_units_var, width=30)
                package_units_entry.pack(pady=3, padx=15)

                # Cantidad de paquetes
                tk.Label(pf, text="¿Cuántos paquetes compraste?:",
                         font=("Arial", 10), bg=bg, fg=fg).pack(anchor="w", padx=15, pady=(8, 0))
                package_qty_var = tk.StringVar(value="1")
                package_qty_entry = ttk.Entry(pf, textvariable=package_qty_var, width=30)
                package_qty_entry.pack(pady=3, padx=15)

                # Resultado
                result_lbl = tk.Label(pf, text="", font=("Arial", 10, "bold"),
                                      bg="#0a4d1f", fg="#a8e6a8",
                                      justify="left", anchor="w",
                                      padx=10, pady=8, wraplength=460)
                result_lbl.pack(fill="x", padx=15, pady=(10, 5))

                refs["package_cost_var"] = package_cost_var
                refs["package_units_var"] = package_units_var
                refs["package_qty_var"] = package_qty_var
                refs["package_cost_entry"] = package_cost_entry
                refs["package_units_entry"] = package_units_entry
                refs["package_qty_entry"] = package_qty_entry
                refs["package_result_lbl"] = result_lbl

                # Calcular resultado
                def recalc_package(*args):
                    try:
                        pc = _parse_float(package_cost_var.get())
                        pu = int(_parse_float(package_units_var.get()))
                        pq = int(_parse_float(package_qty_var.get()) or 1)
                        if pu <= 0:
                            result_lbl.configure(text="Ingresa las unidades por paquete")
                            return
                        unit_cost = pc / pu
                        m = _parse_float(margin_var.get())
                        unit_sell = unit_cost * (1 + m / 100.0)
                        stock_total = pu * pq
                        texto = (
                            f"Costo unitario:      ${unit_cost:,.2f}\n"
                            f"Precio unitario +{m:g}%: ${unit_sell:,.2f}\n"
                            f"Stock que se sumará:  {stock_total} unidades"
                        ).replace(",", ".")
                        result_lbl.configure(text=texto)
                    except Exception:
                        result_lbl.configure(text="")

                for var in (package_cost_var, package_units_var, package_qty_var):
                    var.trace_add("write", recalc_package)

                # Llamar una vez al abrir
                popup.after(100, recalc_package)

            refs["build_package_fields"] = build_package_fields
            refs["package_frame"] = package_frame
            refs["is_package_var"] = is_package_var

            # ==========================================================
            # 💰 PRECIO Y GANANCIA
            # ==========================================================
            ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=10)

            tk.Label(parent, text="💰 Precio y ganancia",
                     font=("Arial", 11, "bold"), bg=bg, fg=fg).pack(pady=(2, 4))

            # Costo
            ttk.Label(parent, text="Precio de costo unitario:").pack(pady=(6, 3))
            cost_var = tk.StringVar(value=f"{cost:g}" if cost else "")
            cost_entry = ttk.Entry(parent, textvariable=cost_var, width=46)
            cost_entry.pack(pady=3)

            # % Margen
            ttk.Label(parent, text="% Ganancia:").pack(pady=(6, 3))
            margin_var = tk.StringVar(value=f"{margin_percent:g}" if margin_percent else "")
            margin_entry = ttk.Entry(parent, textvariable=margin_var, width=46)
            margin_entry.pack(pady=3)

            # Precio real
            ttk.Label(parent, text="Precio real de venta (antes de redondear):").pack(pady=(6, 3))
            price_var = tk.StringVar(value=f"{price:g}" if price else "")
            price_entry = ttk.Entry(parent, textvariable=price_var, width=46)
            price_entry.pack(pady=3)

            # ==========================================================
            # 🎯 REDONDEO
            # ==========================================================
            ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=10)

            round_enabled_var = tk.BooleanVar(value=bool(round_enabled))
            ttk.Checkbutton(
                parent,
                text="🎯 Redondear precio final (se cobrará el redondeado)",
                variable=round_enabled_var,
                command=lambda: toggle_round(),
                bootstyle="success-round-toggle").pack(pady=6, padx=20, anchor="w")

            round_frame = tk.Frame(parent, bg=bg)

            def build_round_fields(rf):
                tk.Label(rf, text="Redondear hacia arriba al:",
                         font=("Arial", 10), bg=bg, fg=fg).pack(anchor="w", padx=15)
                round_to_var = tk.StringVar(value=str(round_to) if round_to else "100")
                round_combo = ttk.Combobox(
                    rf, textvariable=round_to_var, state="readonly",
                    values=["10", "50", "100", "200", "500", "1000"],
                    width=15)
                round_combo.pack(pady=3, padx=15, anchor="w")

                rounded_lbl = tk.Label(rf, text="", font=("Arial", 11, "bold"),
                                       bg="#0a4d1f", fg="#a8e6a8",
                                       padx=10, pady=6)
                rounded_lbl.pack(padx=15, pady=(5, 3), anchor="w")

                refs["round_to_var"] = round_to_var
                refs["round_combo"] = round_combo
                refs["rounded_lbl"] = rounded_lbl

                def recalc_rounded(*args):
                    try:
                        p = _parse_float(price_var.get())
                        to = int(_parse_float(round_to_var.get()) or 100)
                        r = _round_up(p, to)
                        rounded_lbl.configure(
                            text=f"Precio a cobrar: ${r:,.0f}".replace(",", "."))
                    except Exception:
                        rounded_lbl.configure(text="")

                round_to_var.trace_add("write", recalc_rounded)
                price_var.trace_add("write", recalc_rounded)
                popup.after(100, recalc_rounded)

            refs["build_round_fields"] = build_round_fields
            refs["round_frame"] = round_frame
            refs["round_enabled_var"] = round_enabled_var
            refs["round_to_var"] = round_to_var
            refs["round_combo"] = round_combo
            refs["rounded_lbl"] = rounded_lbl

            # ==========================================================
            # STOCK, VENCIMIENTO, PAUSADO
            # ==========================================================
            ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=10)

            # Stock
            ttk.Label(parent, text="Stock (acepta decimales):").pack(pady=(6, 3))
            stock_var = tk.StringVar(value=f"{stock:g}" if stock else "")
            stock_entry = ttk.Entry(parent, textvariable=stock_var, width=46)
            stock_entry.pack(pady=3)

            # Vencimiento
            ttk.Label(parent, text="Fecha de vencimiento (opcional, formato YYYY-MM-DD):").pack(pady=(10, 3))
            expiry_var = tk.StringVar(value=expiry_date or "")
            expiry_entry = ttk.Entry(parent, textvariable=expiry_var, width=46)
            expiry_entry.pack(pady=3)

            # Pausado
            paused_var = tk.BooleanVar(value=bool(paused))
            ttk.Checkbutton(
                parent,
                text="⏸ Producto pausado (no se vende, no se borra)",
                variable=paused_var,
                bootstyle="danger-round-toggle").pack(pady=8, padx=20, anchor="w")

            # Guardar referencias
            refs["barcode_entry"] = barcode_entry
            refs["name_entry"] = name_entry
            refs["similar_lbl"] = similar_lbl
            refs["package_hint"] = package_hint
            refs["group_entry"] = group_entry
            refs["type_var"] = type_var
            refs["unit_var"] = unit_var
            refs["unit_combo"] = unit_combo
            refs["cost_var"] = cost_var
            refs["margin_var"] = margin_var
            refs["price_var"] = price_var
            refs["stock_var"] = stock_var
            refs["expiry_var"] = expiry_var
            refs["paused_var"] = paused_var

            # ==========================================================
            # TRACES para recálculo
            # ==========================================================
            def recalc_from_cost_margin(*args):
                if state["updating"]:
                    return
                try:
                    c = _parse_float(cost_var.get())
                    m = _parse_float(margin_var.get())
                    if c <= 0:
                        return
                    new_price = c * (1 + m / 100.0)
                    state["updating"] = True
                    price_var.set(f"{int(round(new_price))}")
                    state["updating"] = False
                except Exception:
                    state["updating"] = False

            def recalc_margin_from_price(*args):
                if state["updating"]:
                    return
                try:
                    c = _parse_float(cost_var.get())
                    p = _parse_float(price_var.get())
                    if c <= 0 or p <= 0:
                        return
                    new_margin = ((p - c) / c) * 100.0
                    txt = f"{new_margin:.2f}".rstrip("0").rstrip(".")
                    state["updating"] = True
                    margin_var.set(txt)
                    state["updating"] = False
                except Exception:
                    state["updating"] = False

            cost_var.trace_add("write", recalc_from_cost_margin)
            margin_var.trace_add("write", recalc_from_cost_margin)
            price_var.trace_add("write", recalc_margin_from_price)

            # Foco inicial
            if barcode:
                name_entry.focus_set()
            else:
                barcode_entry.focus_set()

            # Aplicar estado inicial
            popup.after(80, lambda: toggle_package())
            popup.after(80, lambda: toggle_round())

        # ==========================================================
        # TOGGLE PAQUETE
        # ==========================================================
        def toggle_package():
            activo = refs["is_package_var"].get()
            state["package_active"] = activo
            refs["package_frame"].pack_forget()
            if activo:
                # Desactivar stock manual
                try:
                    refs["stock_var"].set("0")
                    refs["stock_entry"].configure(state="disabled")
                except Exception:
                    pass
                # Construir/llenar campos
                for w in refs["package_frame"].winfo_children():
                    w.destroy()
                refs["build_package_fields"](refs["package_frame"])
                refs["package_frame"].pack(fill="x", padx=15, pady=5)
            else:
                try:
                    refs["stock_entry"].configure(state="normal")
                except Exception:
                    pass

        # ==========================================================
        # TOGGLE REDONDEO
        # ==========================================================
        def toggle_round():
            activo = refs["round_enabled_var"].get()
            state["round_active"] = activo
            refs["round_frame"].pack_forget()
            if activo:
                for w in refs["round_frame"].winfo_children():
                    w.destroy()
                refs["build_round_fields"](refs["round_frame"])
                refs["round_frame"].pack(fill="x", padx=15, pady=5)

        # ==========================================================
        # BOTONES
        # ==========================================================
        def build_bottom(parent):
            bf = tk.Frame(parent, bg=bg)
            bf.pack(pady=10, fill="x")

            def buscar_similares():
                n = refs["name_entry"].get().strip()
                if not n:
                    MD.show_warning("Escribe primero el nombre del producto.",
                                    "Sin nombre", parent=popup)
                    return
                self._open_similar_dialog(
                    base_name=n,
                    current_product_id=product_id,
                    parent_toplevel=popup,
                    on_apply=lambda ids, group: _apply_group_from_form(ids, group))

            def _apply_group_from_form(ids, group):
                try:
                    if group:
                        refs["group_entry"].delete(0, tk.END)
                        refs["group_entry"].insert(0, group)
                except Exception:
                    pass
                state["pending_group_ids"] = list(ids) if ids else []

            refs["_apply_group_from_form"] = _apply_group_from_form

            ttk.Button(bf, text="🔗 Buscar similares", command=buscar_similares,
                       bootstyle="info").pack(side="left", padx=4)
            ttk.Button(bf, text="💾 Guardar", command=lambda: save(),
                       style="DarkGreen.TButton").pack(side="right", padx=4)
            ttk.Button(bf, text="Cancelar",
                       command=lambda: _cancel()).pack(side="right", padx=4)

        # ==========================================================
        # BORRADOR
        # ==========================================================
        def collect_draft():
            return {
                "mode": "edit" if product_id else "create",
                "product_id": product_id,
                "barcode": refs["barcode_entry"].get(),
                "name": refs["name_entry"].get(),
                "group_name": refs["group_entry"].get(),
                "type": refs["type_var"].get(),
                "unit": refs["unit_var"].get(),
                "cost": refs["cost_var"].get(),
                "margin_percent": refs["margin_var"].get(),
                "price": refs["price_var"].get(),
                "stock": refs["stock_var"].get(),
                "expiry_date": refs["expiry_var"].get(),
                "paused": 1 if refs["paused_var"].get() else 0,
                "is_package": 1 if refs["is_package_var"].get() else 0,
                "package_cost": refs.get("package_cost_var").get() if "package_cost_var" in refs else "",
                "package_units": refs.get("package_units_var").get() if "package_units_var" in refs else "",
                "round_enabled": 1 if refs["round_enabled_var"].get() else 0,
                "round_to": refs.get("round_to_var").get() if "round_to_var" in refs else "",
            }

        def save_draft_now():
            state["draft_timer"] = None
            try:
                data = collect_draft()
                if not data["name"] and not data["barcode"]:
                    return
                self.product_use_case.save_product_draft(data)
            except Exception:
                pass

        def schedule_save(*args):
            if state["draft_timer"]:
                try:
                    popup.after_cancel(state["draft_timer"])
                except Exception:
                    pass
            state["draft_timer"] = popup.after(800, save_draft_now)

        def cancel_pending():
            if state["draft_timer"]:
                try:
                    popup.after_cancel(state["draft_timer"])
                except Exception:
                    pass
                state["draft_timer"] = None

        # ==========================================================
        # DETECCIÓN DE SIMILARES Y PAQUETE PREVIO
        # ==========================================================
        def update_similar_label():
            try:
                n = refs["name_entry"].get().strip()
                if len(n) < 4:
                    refs["similar_lbl"].configure(text="")
                    refs["package_hint"].configure(text="")
                    return

                # Similares
                products = self.product_use_case.list_products()
                similares = find_similar_products(n, products, threshold=0.55)
                if product_id:
                    similares = [(p, s) for p, s in similares if p.product_id != product_id]
                if similares:
                    refs["similar_lbl"].configure(
                        text=f"🔗 Se encontraron {len(similares)} similares. Clic aquí para agrupar.")
                else:
                    refs["similar_lbl"].configure(text="")

                # Paquete previo
                if not state["package_active"]:
                    pkg = self.product_use_case.find_last_package_for_name(n)
                    if pkg and pkg["package_units"] > 0:
                        refs["package_hint"].configure(
                            text=f"💡 La última vez compraste \"{pkg['name']}\" a "
                                 f"${pkg['package_cost']:,.0f} por paquete de "
                                 f"{pkg['package_units']} unidades.\n"
                                 f"   Activa el 📦 Modo Paquete si quieres usar esos datos."
                                 .replace(",", "."))
                    else:
                        refs["package_hint"].configure(text="")
            except Exception:
                pass

        def on_similar_click(event):
            try:
                n = refs["name_entry"].get().strip()
                if not n:
                    return
                self._open_similar_dialog(
                    base_name=n,
                    current_product_id=product_id,
                    parent_toplevel=popup,
                    on_apply=lambda ids, group: refs["_apply_group_from_form"](ids, group))
            except Exception:
                pass

        # ==========================================================
        # GUARDAR
        # ==========================================================
        def save():
            n = refs["name_entry"].get().strip()
            b = refs["barcode_entry"].get().strip()
            g = refs["group_entry"].get().strip()
            if not n:
                MD.show_error("El nombre es obligatorio", "Error", parent=popup)
                return

            # Modo paquete
            activo_paquete = refs["is_package_var"].get()
            final_cost = _parse_float(refs["cost_var"].get())
            final_margin = _parse_float(refs["margin_var"].get())
            final_price = _parse_float(refs["price_var"].get())
            final_stock = _parse_float(refs["stock_var"].get())
            pkg_cost = 0.0
            pkg_units = 0

            if activo_paquete:
                pkg_cost = _parse_float(refs.get("package_cost_var").get())
                pkg_units = int(_parse_float(refs.get("package_units_var").get()))
                pkg_qty = int(_parse_float(refs.get("package_qty_var").get()) or 1)
                if pkg_units <= 0:
                    MD.show_error("Las unidades por paquete deben ser mayor a 0",
                                  "Error", parent=popup)
                    return
                if pkg_cost <= 0:
                    MD.show_error("El costo del paquete debe ser mayor a 0",
                                  "Error", parent=popup)
                    return
                # Calcular unitario
                final_cost = pkg_cost / pkg_units
                final_price = final_cost * (1 + final_margin / 100.0)
                final_stock = pkg_units * pkg_qty
            else:
                if final_price <= 0 and final_cost > 0:
                    final_price = final_cost * (1 + final_margin / 100.0)
                if final_price <= 0:
                    MD.show_error("El precio de venta debe ser mayor a 0",
                                  "Error", parent=popup)
                    return

            # Redondeo
            round_enabled = 1 if refs["round_enabled_var"].get() else 0
            round_to_val = int(_parse_float(refs.get("round_to_var", tk.StringVar(value="100")).get()) or 100)
            if round_enabled:
                rounded = _round_up(final_price, round_to_val)
            else:
                rounded = int(round(final_price))

            # Vencimiento
            expiry = refs["expiry_var"].get().strip()
            if expiry:
                try:
                    datetime.strptime(expiry, "%Y-%m-%d")
                except Exception:
                    MD.show_error("Fecha de vencimiento inválida. Usa YYYY-MM-DD",
                                  "Error", parent=popup)
                    return

            paused_val = 1 if refs["paused_var"].get() else 0

            cancel_pending()

            try:
                if product_id:
                    self.product_use_case.update_product(
                        product_id, n, b, final_price, final_stock,
                        refs["type_var"].get(), refs["unit_var"].get(),
                        g, final_cost, final_margin,
                        rounded, round_enabled, round_to_val,
                        pkg_cost, pkg_units, 1 if activo_paquete else 0,
                        paused_val, expiry)
                    if state["pending_group_ids"]:
                        self.product_use_case.set_group_name(
                            state["pending_group_ids"], g)
                else:
                    new_pid = self.product_use_case.add_product(
                        n, b, final_price, final_stock,
                        refs["type_var"].get(), refs["unit_var"].get(),
                        g, final_cost, final_margin,
                        rounded, round_enabled, round_to_val,
                        pkg_cost, pkg_units, 1 if activo_paquete else 0,
                        paused_val, expiry)
                    if state["pending_group_ids"] or g:
                        ids = list(state["pending_group_ids"])
                        if g and new_pid not in ids:
                            ids.append(new_pid)
                        if ids:
                            self.product_use_case.set_group_name(ids, g)

                self.product_use_case.clear_product_draft()
            except Exception as e:
                MD.show_error(f"Error al guardar: {e}", "Error", parent=popup)
                return

            self.load_products()
            popup.destroy()
            self.scan_entry.focus_set()

            if auto_select and b:
                for it in self.tree.get_children():
                    if str(self.tree.item(it, 'values')[3]).strip() == b:
                        self.tree.selection_set(it)
                        self.tree.focus(it)
                        self.tree.see(it)
                        break

        def _cancel():
            cancel_pending()
            save_draft_now()
            popup.destroy()
            self.scan_entry.focus_set()

        # ==========================================================
        # CONSTRUIR
        # ==========================================================
        container = tk.Frame(popup, bg=bg)
        container.pack(fill="both", expand=True)
        make_scrollable(container, build_content, build_bottom, bg=bg)

        # Bindings después de construir
        try:
            refs["name_entry"].bind("<KeyRelease>", schedule_save, add="+")
            refs["name_entry"].bind("<KeyRelease>", lambda e: update_similar_label(), add="+")
            refs["barcode_entry"].bind("<KeyRelease>", schedule_save, add="+")
            refs["cost_var"].trace_add("write", schedule_save)
            refs["margin_var"].trace_add("write", schedule_save)
            refs["price_var"].trace_add("write", schedule_save)
            refs["stock_var"].trace_add("write", schedule_save)
            refs["expiry_var"].trace_add("write", schedule_save)
            refs["group_entry"].bind("<KeyRelease>", schedule_save, add="+")
            refs["type_var"].trace_add("write", schedule_save)
            refs["unit_var"].trace_add("write", schedule_save)
            refs["similar_lbl"].bind("<Button-1>", on_similar_click)
            popup.protocol("WM_DELETE_WINDOW", _cancel)
            if from_draft:
                schedule_save()
                update_similar_label()
        except Exception:
            pass

        show_popup_smooth(popup)
        try:
            popup.grab_set()
            popup.focus_force()
        except Exception:
            pass

    # =========================================================
    # DIALOG SIMILARES (sin cambios)
    # =========================================================
    def _open_similar_dialog(self, base_name, current_product_id,
                             parent_toplevel, on_apply):
        try:
            products = self.product_use_case.list_products()
            similares = find_similar_products(base_name, products, threshold=0.45)
            if current_product_id:
                similares = [(p, s) for p, s in similares if p.product_id != current_product_id]
        except Exception:
            similares = []

        if not similares:
            MD.show_info(
                f"No se encontraron productos similares a:\n\n{base_name}",
                "Sin coincidencias", parent=parent_toplevel)
            return

        dialog = Toplevel(parent_toplevel)
        dialog.title("🔗 Agrupar productos similares")
        dialog.geometry("720x560")
        dialog.transient(parent_toplevel)
        dialog.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(dialog, text="🔗 PRODUCTOS SIMILARES",
                 font=("Arial", 14, "bold"), bg=bg, fg=fg).pack(pady=(12, 4))
        tk.Label(dialog, text=f"Producto base: {base_name}",
                 font=("Arial", 10, "italic"), bg=bg, fg="#a8e6a8").pack(pady=2)

        sugerencia = self._suggest_group_name(similares, base_name)
        tk.Label(dialog, text="Nombre del grupo:",
                 font=("Arial", 10, "bold"), bg=bg, fg=fg).pack(pady=(8, 2))
        group_var = tk.StringVar(value=sugerencia)
        group_entry = ttk.Entry(dialog, textvariable=group_var, width=50,
                                font=("Arial", 11), justify="center")
        group_entry.pack(pady=2)

        tk.Label(dialog, text="Marca los productos que quieras agrupar:",
                 font=("Arial", 10), bg=bg, fg=fg).pack(pady=(8, 2))

        frame = ttk.Frame(dialog, bootstyle="dark")
        frame.pack(fill="both", expand=True, padx=12, pady=4)

        tree_frame, tree = make_scrolled_treeview(
            frame,
            columns=("Sel", "ID", "Nombre", "Precio"),
            headings=[
                ("Sel", "☐", 40, "center"),
                ("ID", "ID", 50, "center"),
                ("Nombre", "Producto", 400, "w"),
                ("Precio", "Precio", 100, "e"),
            ],
            bootstyle="dark")
        tree_frame.pack(fill="both", expand=True)

        marcados = set()
        item_to_pid = {}

        def toggle_mark(iid):
            if iid in marcados:
                marcados.discard(iid)
                try:
                    tree.set(iid, "Sel", "☐")
                except Exception:
                    pass
            else:
                marcados.add(iid)
                try:
                    tree.set(iid, "Sel", "☑")
                except Exception:
                    pass

        def toggle_all():
            if not item_to_pid:
                return
            if len(marcados) >= len(item_to_pid):
                marcados.clear()
                for iid in item_to_pid:
                    try:
                        tree.set(iid, "Sel", "☐")
                    except Exception:
                        pass
            else:
                marcados.clear()
                for iid in item_to_pid:
                    marcados.add(iid)
                    try:
                        tree.set(iid, "Sel", "☑")
                    except Exception:
                        pass

        tree.heading("Sel", text="☐", command=toggle_all)

        for p, score in similares:
            iid = tree.insert("", "end", values=(
                "☐", p.product_id, p.name,
                f"${p.price:,.0f}".replace(",", ".")))
            item_to_pid[iid] = p.product_id

        def on_click(event):
            try:
                region = tree.identify("region", event.x, event.y)
                if region != "cell":
                    return
                col = tree.identify_column(event.x)
                row = tree.identify_row(event.y)
                if not row:
                    return
                if col == "#1":
                    toggle_mark(row)
            except Exception:
                pass

        tree.bind("<Button-1>", on_click, add="+")

        def aplicar():
            if not marcados:
                MD.show_warning("Marca al menos un producto.",
                                "Sin selección", parent=dialog)
                return
            group = group_var.get().strip()
            if not group:
                MD.show_warning("Escribe el nombre del grupo.",
                                "Sin nombre de grupo", parent=dialog)
                return
            ids = [item_to_pid[i] for i in marcados if i in item_to_pid]
            dialog.destroy()
            try:
                on_apply(ids, group)
            except Exception:
                pass

        bf = tk.Frame(dialog, bg=bg)
        bf.pack(side="bottom", pady=10)
        ttk.Button(bf, text="🔗 Agrupar seleccionados",
                   command=aplicar, style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar", command=dialog.destroy).pack(side="left", padx=5)

        dialog.bind("<Escape>", lambda e: dialog.destroy())

        show_popup_smooth(dialog)
        try:
            dialog.grab_set()
            dialog.focus_force()
        except Exception:
            pass

    def _suggest_group_name(self, similares, base_name):
        try:
            names = [p.name for p, _ in similares] + [base_name]
            if not names:
                return base_name
            candidatos = sorted(names, key=lambda x: len(x))
            return candidatos[0]
        except Exception:
            return base_name

    def _refresh_unit_options(self, unit_var, combo, type_var):
        t = type_var.get()
        if t == "unidad":
            opciones = ["unidad"]
        elif t == "peso":
            opciones = ["kg", "gr", "mg"]
        else:
            opciones = ["Lt", "ml"]
        combo.configure(values=opciones)
        if unit_var.get() not in opciones:
            unit_var.set(opciones[0])

    # =========================================================
    # ESCANEO
    # =========================================================
    def lookup_barcode(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo:
            return
        enc = None
        enc_item = None
        for p in self.product_use_case.list_products():
            if str(p.barcode).strip() == codigo:
                enc = p
                break
        if enc:
            self.search_var.set("")
            self.load_products()
            for it in self.tree.get_children():
                if str(self.tree.item(it, 'values')[3]).strip() == codigo:
                    self.tree.selection_set(it)
                    self.tree.focus(it)
                    self.tree.see(it)
                    enc_item = it
                    break
            r = MD.yesno(
                f"✅ Producto encontrado:\n\n"
                f"Nombre: {enc.name}\n"
                f"Precio real: ${enc.price:,.0f}\n"
                f"Precio redondeado: ${enc.rounded_price:,.0f}\n"
                f"Stock: {enc.stock:g} {enc.unit}\n\n"
                f"¿Deseas EDITAR este producto?".replace(",", "."),
                "Producto Encontrado", parent=self)
            if r == "Yes" and enc_item:
                self.open_edit_from_item(enc_item)
        else:
            r = MD.yesno(f"⚠️ '{codigo}' NO está registrado.\n\n¿Agregarlo?",
                         "No encontrado", parent=self)
            if r == "Yes":
                self.add_product_popup(barcode_prefill=codigo, auto_select=True)
        self.scan_var.set("")
        self.scan_entry.focus_set()