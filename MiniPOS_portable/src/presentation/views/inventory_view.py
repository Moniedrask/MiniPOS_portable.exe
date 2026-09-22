import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
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
        self.low_stock_threshold = self._get_low_stock_threshold()

        self.create_widgets()
        self.load_products()
        self.after(300, lambda: self.scan_entry.focus_set())
        self.after(800, self._check_product_draft)
        self._keep_scanner_focused()

    def _get_low_stock_threshold(self):
        try:
            return int(self.db_manager.get_setting("low_stock_threshold", "5") or "5")
        except Exception:
            return 5

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
            margin_percent=_parse_float(data.get("margin_percent", 20)))

    def create_widgets(self):
        scan_frame = ttk.Frame(self, bootstyle="dark")
        scan_frame.pack(padx=10, pady=(10, 3), fill="x")
        ttk.Label(scan_frame, text="📷 Escanear código:",
                  font=("Arial", 11, "bold"), bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(scan_frame, textvariable=self.scan_var,
                                    width=35, font=("Arial", 11))
        self.scan_entry.pack(side="left", padx=5)
        self.scan_entry.bind("<Return>", self.lookup_barcode)
        ttk.Button(scan_frame, text="🔍 Buscar Código",
                   command=lambda: self.lookup_barcode(None),
                   style="DarkGreen.TButton").pack(side="left", padx=5)

        search_frame = ttk.Frame(self, bootstyle="dark")
        search_frame.pack(padx=10, pady=3, fill="x")
        ttk.Label(search_frame, text="🔍 Búsqueda (autocompleta):",
                  bootstyle="inverse-dark").pack(side="left", padx=5)

        self.search_var = tk.StringVar()
        self.search_entry = AutoCompleteEntry(
            search_frame,
            values_getter=self._get_product_labels,
            on_select=self._on_search_select,
            width=40,
            font=("Arial", 11))
        self.search_entry.configure(textvariable=self.search_var)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind('<KeyRelease>', self._on_search_key, add='+')

        ttk.Button(search_frame, text="Limpiar", command=self._clear_search,
                   bootstyle="secondary").pack(side="left", padx=5)

        # Info alerta stock bajo
        self.low_stock_lbl = tk.Label(
            self, text="", font=("Arial", 10, "italic"),
            bg=ttk.Style().colors.bg, fg="#ffbbbb")
        self.low_stock_lbl.pack(padx=10, pady=1, anchor="w")

        btn_frame = ttk.Frame(self, bootstyle="dark")
        btn_frame.pack(side="bottom", pady=6, fill="x")
        ttk.Button(btn_frame, text="➕ Agregar Producto (F2)",
                   command=self.add_product_popup,
                   style="DarkGreen.TButton").pack(side="left", padx=5)

        frame = ttk.Frame(self, bootstyle="dark")
        frame.pack(padx=10, pady=3, fill="both", expand=True)

        self.columns = [
            ("ID", "ID", 45, "center"),
            ("Name", "Producto", 190, "w"),
            ("Group", "Grupo", 110, "w"),
            ("Barcode", "Código", 125, "w"),
            ("Cost", "Costo", 80, "e"),
            ("Margin", "% Gan.", 70, "center"),
            ("Price", "Precio", 90, "e"),
            ("Unit", "Unidad", 65, "center"),
            ("Stock", "Stock", 70, "center"),
            ("Created", "Creado", 125, "center"),
            ("Updated", "Actualizado", 125, "center"),
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

        # Tag para stock bajo
        try:
            self.tree.tag_configure("low_stock", background="#5c1a1a", foreground="#ffcccc")
        except Exception:
            pass

        self.tree.bind("<Double-1>", self.view_product_popup)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tooltip = TreeviewTooltip(self.tree, font_size=11)

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
                "Unit": lambda p: (p.unit or ""),
                "Stock": lambda p: p.stock,
                "Created": lambda p: p.created_at or "",
                "Updated": lambda p: p.updated_at or "",
            }
            products = sorted(products,
                              key=keys.get(self.sort_col, lambda p: p.product_id),
                              reverse=self.sort_reverse)
        for p in products:
            self._insert_product_row(p)
        self._update_low_stock_label(products)

    def _update_low_stock_label(self, products):
        try:
            bajos = [p for p in products if p.stock <= self.low_stock_threshold]
            if bajos:
                self.low_stock_lbl.configure(
                    text=f"⚠️ {len(bajos)} producto(s) con stock bajo (≤ {self.low_stock_threshold})")
            else:
                self.low_stock_lbl.configure(text="")
        except Exception:
            pass

    def load_products(self):
        self.low_stock_threshold = self._get_low_stock_threshold()
        self.filtered_products = self.product_use_case.list_products()
        self._render_products(self.filtered_products)

    def filter_products(self, event=None):
        q = self.search_var.get().lower().strip()
        if "|" in q:
            q = q.split("|")[0].strip()
        prods = self.product_use_case.list_products()
        if not q:
            self.filtered_products = prods
        else:
            self.filtered_products = [
                p for p in prods
                if q in (p.name or "").lower()
                or q in str(p.barcode or "").lower()
                or q in (p.group_name or "").lower()]
        self._render_products(self.filtered_products)

    def _insert_product_row(self, p):
        precio = f"${p.price:,.0f}".replace(",", ".")
        costo = f"${p.cost:,.0f}".replace(",", ".") if p.cost > 0 else "-"
        margen = f"{p.margin_percent:.0f}%" if p.margin_percent else "-"
        tags = ()
        icono = ""
        if p.stock <= self.low_stock_threshold:
            tags = ("low_stock",)
            icono = "⚠ "
        self.tree.insert("", "end", values=(
            p.product_id, icono + (p.name or ""), p.group_name or "-", p.barcode,
            costo, margen, precio, p.unit, f"{p.stock:g}",
            p.created_at or "-", p.updated_at or "-"), tags=tags)

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
        menu.add_command(label="🔗  Agrupar similares", command=lambda: self.group_from_item(item))
        menu.add_separator()
        menu.add_command(label="🗑️  Eliminar producto", command=lambda: self.confirm_delete(item))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

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

    def view_product_popup(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], 'values')
        pid = vals[0]
        name = vals[1].replace("⚠ ", "")
        group = vals[2]
        barcode = vals[3]
        cost = vals[4]
        margin = vals[5]
        price = vals[6]
        unit = vals[7]
        stock = vals[8]
        created, updated = vals[9], vals[10]

        popup = Toplevel(self)
        popup.title("Detalle del Producto")
        popup.geometry("500x620")
        popup.transient(self.winfo_toplevel())
        popup.withdraw()

        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        tk.Label(popup, text="📋 DETALLE DEL PRODUCTO",
                 font=("Arial", 13, "bold"), bg=bg, fg=fg).pack(pady=(12, 6))

        container = tk.Frame(popup, bg=bg)
        container.pack(fill="both", expand=True, padx=10, pady=5)

        def build_content(parent):
            for t, f in [(f"ID: {pid}", ("Arial", 10)),
                         (f"Nombre: {name}", ("Arial", 12, "bold")),
                         (f"Grupo: {group if group != '-' else '(sin grupo)'}", ("Arial", 10, "italic")),
                         (f"Código de Barras: {barcode}", ("Arial", 10)),
                         (f"Costo: {cost}", ("Arial", 11)),
                         (f"Margen de ganancia: {margin}", ("Arial", 11)),
                         (f"Precio de venta: {price}", ("Arial", 12, "bold")),
                         (f"Unidad: {unit}", ("Arial", 11)),
                         (f"Stock: {stock}", ("Arial", 11)),
                         ("", ("Arial", 4)),
                         (f"📅 Creado: {created}", ("Arial", 10, "italic")),
                         (f"🔄 Actualizado: {updated}", ("Arial", 10, "italic"))]:
                tk.Label(parent, text=t, font=f, bg=bg, fg=fg,
                         anchor="w", justify="left").pack(fill="x", pady=4, padx=10)

        def build_bottom(parent):
            bf = tk.Frame(parent, bg=bg)
            bf.pack(pady=8)
            ttk.Button(bf, text="✏️ Editar",
                       command=lambda: [popup.destroy(), self.open_edit_from_item(sel[0])],
                       style="DarkGreen.TButton").pack(side="left", padx=5)
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

    def confirm_delete(self, item):
        vals = self.tree.item(item, 'values')
        pid, name = vals[0], vals[1].replace("⚠ ", "")
        if MD.yesno(f"⚠️ ¿ELIMINAR '{name}'?", "Confirmar", parent=self) != "Yes":
            return
        if MD.yesno(f"🚨 ÚLTIMA ADVERTENCIA\n\n¿Realmente eliminar '{name}'?",
                    "Confirmación final", parent=self) != "Yes":
            return
        self.product_use_case.delete_product(pid)
        self.load_products()
        MD.show_info(f"'{name}' eliminado.", "Listo", parent=self)
        self.scan_entry.focus_set()

    def open_edit_from_item(self, item):
        vals = self.tree.item(item, 'values')
        pid = vals[0]
        name = vals[1].replace("⚠ ", "")
        group = vals[2] if vals[2] != "-" else ""
        barcode = vals[3]
        cost = _parse_float(vals[4]) if vals[4] != "-" else 0.0
        margin = _parse_float(vals[5].replace("%", "")) if vals[5] != "-" else 20.0
        price = _parse_float(vals[6])
        unit = vals[7]
        stock = _parse_float(vals[8])
        unit_type = "unidad"
        if unit in ("kg", "gr", "mg"):
            unit_type = "peso"
        elif unit in ("Lt", "ml"):
            unit_type = "volumen"
        self.open_product_form("Editar Producto", pid, name, barcode, price,
                               stock, unit_type, unit, group_name=group,
                               cost=cost, margin_percent=margin)

    def add_product_popup(self, barcode_prefill="", auto_select=False):
        try:
            default_margin = _parse_float(
                self.db_manager.get_setting("default_margin", "20") or 20)
        except Exception:
            default_margin = 20.0
        self.open_product_form("Agregar Producto", None, "", barcode_prefill,
                               0, 0, "unidad", "unidad", auto_select,
                               cost=0.0, margin_percent=default_margin)

    # =========================================================
    # FORMULARIO DE PRODUCTO (con cost, margin, price)
    # =========================================================
    def open_product_form(self, title, product_id, name, barcode, price, stock,
                          unit_type, unit, auto_select=False, from_draft=False,
                          group_name="", cost=0.0, margin_percent=20.0):
        popup = Toplevel(self)
        popup.title(title)
        popup.geometry("500x800")
        popup.transient(self.winfo_toplevel())
        popup.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        refs = {}
        state = {
            "draft_timer": None,
            "pending_group_ids": [],
            "updating": False,  # ← para evitar loops en traces
        }

        def build_content(parent):
            # Código
            ttk.Label(parent, text="Código de Barras / QR:").pack(pady=(10, 3))
            barcode_entry = ttk.Entry(parent, width=42)
            barcode_entry.pack(pady=3)
            if barcode:
                barcode_entry.insert(0, barcode)

            # Nombre
            ttk.Label(parent, text="Nombre del Producto:").pack(pady=(10, 3))
            name_entry = ttk.Entry(parent, width=42)
            name_entry.pack(pady=3)
            if name:
                name_entry.insert(0, name)

            similar_lbl = tk.Label(parent, text="", font=("Arial", 9, "italic"),
                                   bg=bg, fg="#a8e6a8", cursor="hand2")
            similar_lbl.pack(pady=2)

            # Grupo
            ttk.Label(parent, text="Grupo (opcional):").pack(pady=(10, 3))
            group_entry = ttk.Entry(parent, width=42)
            group_entry.pack(pady=3)
            if group_name:
                group_entry.insert(0, group_name)

            # Tipo de venta
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

            # Unidad
            ttk.Label(parent, text="Unidad de medida:").pack(pady=(10, 3))
            unit_var = tk.StringVar(value=unit)
            unit_combo = ttk.Combobox(parent, textvariable=unit_var, state="readonly", width=15)
            unit_combo.pack(pady=3)
            self._refresh_unit_options(unit_var, unit_combo, type_var)

            # === COSTO / % / PRECIO ===
            ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=8)

            tk.Label(parent, text="💰 Precio y ganancia",
                     font=("Arial", 11, "bold"), bg=bg, fg=fg).pack(pady=(2, 4))

            # Costo
            ttk.Label(parent, text="Precio de costo (lo que te cuesta):").pack(pady=(6, 3))
            cost_var = tk.StringVar(value=f"{cost:g}" if cost else "")
            cost_entry = ttk.Entry(parent, textvariable=cost_var, width=42)
            cost_entry.pack(pady=3)

            # % Margen
            ttk.Label(parent, text="% Ganancia (si lo dejas vacío, se usa el % por defecto):").pack(pady=(6, 3))
            margin_var = tk.StringVar(value=f"{margin_percent:g}" if margin_percent else "")
            margin_entry = ttk.Entry(parent, textvariable=margin_var, width=42)
            margin_entry.pack(pady=3)

            # Precio venta
            ttk.Label(parent, text="Precio de venta al público (calculado):").pack(pady=(6, 3))
            price_var = tk.StringVar(value=f"{price:g}" if price else "")
            price_entry = ttk.Entry(parent, textvariable=price_var, width=42)
            price_entry.pack(pady=3)

            # Ayuda
            tk.Label(parent,
                     text="💡 Al cambiar costo o %, el precio se recalcula.\n"
                          "   Si escribes un precio nuevo a mano, se recalcula el %.",
                     font=("Arial", 8, "italic"), bg=bg, fg="#a8e6a8",
                     justify="left").pack(pady=4, padx=15)

            ttk.Separator(parent, orient="horizontal").pack(fill="x", pady=8)

            # Stock
            ttk.Label(parent, text="Stock (acepta decimales):").pack(pady=(6, 3))
            stock_var = tk.StringVar(value=f"{stock:g}" if stock else "")
            stock_entry = ttk.Entry(parent, textvariable=stock_var, width=42)
            stock_entry.pack(pady=3)

            refs["barcode_entry"] = barcode_entry
            refs["name_entry"] = name_entry
            refs["similar_lbl"] = similar_lbl
            refs["group_entry"] = group_entry
            refs["type_var"] = type_var
            refs["unit_var"] = unit_var
            refs["unit_combo"] = unit_combo
            refs["cost_var"] = cost_var
            refs["margin_var"] = margin_var
            refs["price_var"] = price_var
            refs["stock_var"] = stock_var
            refs["cost_entry"] = cost_entry
            refs["margin_entry"] = margin_entry
            refs["price_entry"] = price_entry
            refs["stock_entry"] = stock_entry

            # === TRACES para recálculo ===
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

            if barcode:
                name_entry.focus_set()
            else:
                barcode_entry.focus_set()

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
                try:
                    MD.show_info(
                        f"✅ Se agruparán {len(ids)} producto(s) al guardar.\n"
                        f"Grupo: {group}",
                        "Agrupación preparada", parent=popup)
                except Exception:
                    pass

            refs["_apply_group_from_form"] = _apply_group_from_form

            ttk.Button(bf, text="🔗 Buscar similares", command=buscar_similares,
                       bootstyle="info").pack(side="left", padx=4)
            ttk.Button(bf, text="💾 Guardar", command=lambda: save(),
                       style="DarkGreen.TButton").pack(side="right", padx=4)
            ttk.Button(bf, text="Cancelar",
                       command=lambda: _cancel()).pack(side="right", padx=4)

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

        def update_similar_label():
            try:
                n = refs["name_entry"].get().strip()
                if len(n) < 4:
                    refs["similar_lbl"].configure(text="")
                    return
                products = self.product_use_case.list_products()
                similares = find_similar_products(n, products, threshold=0.55)
                if product_id:
                    similares = [(p, s) for p, s in similares if p.product_id != product_id]
                if similares:
                    refs["similar_lbl"].configure(
                        text=f"🔗 Se encontraron {len(similares)} similares. Clic aquí para agrupar.")
                else:
                    refs["similar_lbl"].configure(text="")
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

        def save():
            n = refs["name_entry"].get().strip()
            b = refs["barcode_entry"].get().strip()
            g = refs["group_entry"].get().strip()
            if not n:
                MD.show_error("El nombre es obligatorio", "Error", parent=popup)
                return
            c = _parse_float(refs["cost_var"].get())
            m = _parse_float(refs["margin_var"].get())
            p = _parse_float(refs["price_var"].get())
            s = _parse_float(refs["stock_var"].get())

            # Si no hay precio pero sí costo y margen, calculamos
            if p <= 0 and c > 0:
                p = c * (1 + m / 100.0)

            if p <= 0:
                MD.show_error("El precio de venta debe ser mayor a 0",
                              "Error", parent=popup)
                return

            cancel_pending()

            try:
                if product_id:
                    self.product_use_case.update_product(
                        product_id, n, b, p, s,
                        refs["type_var"].get(), refs["unit_var"].get(),
                        g, c, m)
                    if state["pending_group_ids"]:
                        self.product_use_case.set_group_name(
                            state["pending_group_ids"], g)
                else:
                    new_pid = self.product_use_case.add_product(
                        n, b, p, s,
                        refs["type_var"].get(), refs["unit_var"].get(),
                        g, c, m)
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

        container = tk.Frame(popup, bg=bg)
        container.pack(fill="both", expand=True)
        make_scrollable(container, build_content, build_bottom, bg=bg)

        try:
            refs["name_entry"].bind("<KeyRelease>", schedule_save, add="+")
            refs["name_entry"].bind("<KeyRelease>", lambda e: update_similar_label(), add="+")
            refs["barcode_entry"].bind("<KeyRelease>", schedule_save, add="+")
            refs["cost_entry"].bind("<KeyRelease>", schedule_save, add="+")
            refs["margin_entry"].bind("<KeyRelease>", schedule_save, add="+")
            refs["price_entry"].bind("<KeyRelease>", schedule_save, add="+")
            refs["stock_entry"].bind("<KeyRelease>", schedule_save, add="+")
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

        def _on_mousewheel(event):
            try:
                tree.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        tree.bind("<MouseWheel>", _on_mousewheel)

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

        def cancelar():
            dialog.destroy()

        bf = tk.Frame(dialog, bg=bg)
        bf.pack(side="bottom", pady=10)
        ttk.Button(bf, text="🔗 Agrupar seleccionados",
                   command=aplicar, style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar", command=cancelar).pack(side="left", padx=5)

        dialog.bind("<Escape>", lambda e: cancelar())

        show_popup_smooth(dialog)
        try:
            dialog.grab_set()
            dialog.focus_force()
        except Exception:
            pass

        dialog.after(100, lambda: group_entry.focus_set() if dialog.winfo_exists() else None)

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
                f"Precio: ${enc.price:,.0f}\n"
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