import os
import sys
import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
from datetime import datetime
from tkinter import simpledialog

from presentation.views.widgets import (
    MD, show_popup_smooth, get_menu_font,
    AutoCompleteEntry, TreeviewTooltip, popup_is_open,
    make_scrolled_treeview,
)


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
        self._label_selection = set()

        self.create_widgets()
        self.load_products()
        self.after(300, lambda: self.scan_entry.focus_set())
        self.after(800, self._check_product_draft)
        self._keep_scanner_focused()

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
    # BORRADOR DE PRODUCTO
    # ============================================================
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
            float(data.get("price", 0) or 0),
            float(data.get("stock", 0) or 0),
            data.get("type", "unidad"),
            data.get("unit", "unidad"),
            auto_select=False,
            from_draft=True)

    # ============================================================
    # UI
    # ============================================================
    def create_widgets(self):
        # ---- Escanear ----
        scan_frame = ttk.Frame(self, bootstyle="dark")
        scan_frame.pack(padx=10, pady=(10, 5), fill="x")
        ttk.Label(scan_frame, text="📷 Escanear código:",
                  font=("Arial", 11, "bold"),
                  bootstyle="inverse-dark").pack(side="left", padx=5)
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
        search_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(search_frame, text="🔍 Búsqueda (autocompleta):",
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

        # ---- Filtros ----
        filt_frame = ttk.Frame(self, bootstyle="dark")
        filt_frame.pack(padx=10, pady=3, fill="x")

        ttk.Label(filt_frame, text="Grupo:",
                  bootstyle="inverse-dark").pack(side="left", padx=(0, 3))
        self.filter_group = ttk.Combobox(filt_frame, state="readonly", width=12)
        self.filter_group.pack(side="left", padx=3)
        self.filter_group.bind("<<ComboboxSelected>>",
                                lambda e: self.filter_products())

        ttk.Label(filt_frame, text="Estado:",
                  bootstyle="inverse-dark").pack(side="left", padx=(10, 3))
        self.filter_status = ttk.Combobox(
            filt_frame, state="readonly", width=14,
            values=["Todos", "Activos", "Pausados", "Por vencer",
                    "Vencidos", "En oferta"])
        self.filter_status.set("Todos")
        self.filter_status.pack(side="left", padx=3)
        self.filter_status.bind("<<ComboboxSelected>>",
                                 lambda e: self.filter_products())

        self.lbl_count = tk.Label(filt_frame, text="0 productos",
                                   font=("Arial", 9, "bold"),
                                   bootstyle="inverse-dark")
        self.lbl_count.pack(side="right", padx=6)

        # ---- Tabla ----
        frame = ttk.Frame(self, bootstyle="dark")
        frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.columns = [
            ("ID", "ID", 50, "center"),
            ("Name", "Producto", 220, "w"),
            ("Barcode", "Código", 130, "w"),
            ("Group", "Grupo", 90, "center"),
            ("Price", "Precio", 85, "e"),
            ("Rounded", "Redondeado", 95, "e"),
            ("Stock", "Stock", 70, "center"),
            ("Unit", "Unidad", 70, "center"),
            ("Expiry", "Vence", 90, "center"),
            ("Status", "Estado", 100, "center"),
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

        # Colores por estado
        self.tree.tag_configure("expired", background="#5c1a1a")
        self.tree.tag_configure("offer", background="#5c3a10")
        self.tree.tag_configure("warn2", background="#5c5c10")
        self.tree.tag_configure("warn1", background="#10405c")
        self.tree.tag_configure("paused", foreground="#888888")
        self.tree.tag_configure("low_stock", foreground="#ff8888")

        self.tree.bind("<Double-1>", self.view_product_popup)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<<TreeviewSelect>>",
                       lambda e: self._update_sel_count())

        self.tooltip = TreeviewTooltip(self.tree, font_size=11)

        # ---- Botonera ----
        btn_frame = ttk.Frame(self, bootstyle="dark")
        btn_frame.pack(fill="x", padx=10, pady=6)

        def mk_btn(text, cmd, bootstyle="secondary"):
            return ttk.Button(btn_frame, text=text, command=cmd,
                              bootstyle=bootstyle)

        mk_btn("➕ Agregar (F2)", self.add_product_popup,
               "success").pack(side="left", padx=3)
        mk_btn("✏️ Editar", self._edit_selected).pack(side="left", padx=3)
        mk_btn("🗑️ Eliminar", self._delete_selected,
               "danger").pack(side="left", padx=3)
        mk_btn("⏸️ Pausar/Reanudar", self._toggle_paused,
               "warning").pack(side="left", padx=3)
        mk_btn("📦 Agrupar", self._group_selected).pack(side="left", padx=3)
        mk_btn("🖨️ Etiquetas PDF", self.print_labels,
               "info").pack(side="left", padx=3)
        mk_btn("📊 Gráficos", self.open_charts,
               "info").pack(side="left", padx=3)
        mk_btn("🔔 Vencimientos", self.open_expiry_alerts,
               "danger").pack(side="left", padx=3)
        mk_btn("💰 Hist. precios", self.open_price_history_global,
               "secondary").pack(side="left", padx=3)
        mk_btn("↩️ Devoluciones", self.open_returns_window,
               "warning").pack(side="left", padx=3)

        self.lbl_sel = tk.Label(btn_frame, text="0 seleccionados",
                                 font=("Arial", 9),
                                 bootstyle="inverse-dark")
        self.lbl_sel.pack(side="right", padx=6)

    def _update_sel_count(self):
        try:
            n = len(self.tree.selection())
            self.lbl_sel.configure(text=f"{n} seleccionados")
        except Exception:
            pass

    # ============================================================
    # CARGA / FILTROS
    # ============================================================
    def load_products(self):
        try:
            self.filtered_products = self.product_use_case.list_products()
        except Exception:
            self.filtered_products = []
        self.populate_groups()
        self._render_products(self.filtered_products)

    def populate_groups(self):
        try:
            grupos = sorted({p.group_name for p in self.filtered_products
                             if getattr(p, "group_name", "")})
            self.filter_group["values"] = ["Todos"] + grupos
            if self.filter_group.get() not in self.filter_group["values"]:
                self.filter_group.set("Todos")
        except Exception:
            pass

    def filter_products(self, event=None):
        q = self.search_var.get().lower().strip()
        if "|" in q:
            q = q.split("|")[0].strip()
        grupo = self.filter_group.get() or "Todos"
        estado = self.filter_status.get() or "Todos"

        try:
            prods = self.product_use_case.list_products()
        except Exception:
            prods = []

        # Info de vencimiento
        expiring = {}
        try:
            for item in self.product_use_case.get_expiring_products():
                expiring[item["product"].product_id] = item
        except Exception:
            pass

        low_stock = 5
        try:
            low_stock = int(self.db_manager.get_setting(
                "low_stock_threshold", "5") or 5)
        except Exception:
            pass

        filtrados = []
        for p in prods:
            if q:
                if q not in (p.name or "").lower() and \
                        q not in str(p.barcode or "").lower():
                    continue
            if grupo != "Todos" and (p.group_name or "") != grupo:
                continue
            paused = getattr(p, "paused", 0)
            if estado == "Activos" and paused:
                continue
            if estado == "Pausados" and not paused:
                continue
            if estado in ("Por vencer", "Vencidos", "En oferta"):
                info = expiring.get(p.product_id)
                if not info:
                    continue
                st = info["status"]
                if estado == "Por vencer" and st not in ("warn1", "warn2"):
                    continue
                if estado == "Vencidos" and st != "expired":
                    continue
                if estado == "En oferta" and st != "offer":
                    continue
            filtrados.append(p)
        self.filtered_products = filtrados
        self._render_products(filtrados)
        try:
            self.lbl_count.configure(
                text=f"{len(filtrados)} de {len(prods)} productos")
        except Exception:
            pass

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

        # Expiring info
        expiring = {}
        try:
            for item in self.product_use_case.get_expiring_products():
                expiring[item["product"].product_id] = item
        except Exception:
            pass

        low_stock = 5
        try:
            low_stock = int(self.db_manager.get_setting(
                "low_stock_threshold", "5") or 5)
        except Exception:
            pass

        if self.sort_col:
            keys = {
                "ID": lambda p: p.product_id,
                "Name": lambda p: (p.name or "").lower(),
                "Barcode": lambda p: (p.barcode or ""),
                "Group": lambda p: (getattr(p, "group_name", "") or "").lower(),
                "Price": lambda p: p.price,
                "Rounded": lambda p: (getattr(p, "rounded_price", 0) or p.price),
                "Stock": lambda p: p.stock,
                "Unit": lambda p: (p.unit or ""),
                "Expiry": lambda p: (getattr(p, "expiry_date", "") or ""),
                "Status": lambda p: 1 if getattr(p, "paused", 0) else 0,
            }
            products = sorted(products,
                              key=keys.get(self.sort_col, lambda p: p.product_id),
                              reverse=self.sort_reverse)

        for p in products:
            self._insert_product_row(p, expiring, low_stock)

    def _insert_product_row(self, p, expiring, low_stock):
        precio = f"${p.price:,.0f}".replace(",", ".")
        rounded = getattr(p, "rounded_price", 0) or p.price
        rounded_txt = f"${rounded:,.0f}".replace(",", ".")
        exp = getattr(p, "expiry_date", "") or ""
        paused = getattr(p, "paused", 0)

        status_text = ""
        tag = ()
        if paused:
            status_text = "⏸️ Pausado"
            tag = ("paused",)
        else:
            info = expiring.get(p.product_id)
            if info:
                st = info["status"]
                d = info["days_left"]
                if st == "expired":
                    status_text = f"⚠️ Vencido ({abs(d)}d)"
                    tag = ("expired",)
                elif st == "offer":
                    status_text = f"🏷️ Oferta ({d}d)"
                    tag = ("offer",)
                elif st == "warn2":
                    status_text = f"⏰ {d}d"
                    tag = ("warn2",)
                elif st == "warn1":
                    status_text = f"⏳ {d}d"
                    tag = ("warn1",)
                else:
                    status_text = "OK"
            else:
                status_text = "OK"

        # Stock bajo
        try:
            if (p.stock or 0) <= low_stock and not paused:
                tag = tag + ("low_stock",)
        except Exception:
            pass

        self.tree.insert("", "end", iid=str(p.product_id), values=(
            p.product_id, p.name, p.barcode or "",
            getattr(p, "group_name", "") or "",
            precio, rounded_txt, f"{p.stock:g}",
            p.unit or "unidad", exp, status_text),
            tags=tag)

    def _get_product_labels(self):
        vals = []
        try:
            for p in self.product_use_case.list_products():
                txt = f"{p.name}  |  {p.barcode}" if p.barcode else p.name
                vals.append(txt)
        except Exception:
            pass
        return vals

    # ============================================================
    # CONTEXTO / SELECCIÓN
    # ============================================================
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.tree.focus(item)
        style = ttk.Style()
        menu = tk.Menu(self.winfo_toplevel(), tearoff=0,
                       bg=style.colors.bg, fg=style.colors.fg,
                       activebackground=style.colors.selectbg,
                       activeforeground=style.colors.selectfg,
                       bd=1, relief="solid", font=get_menu_font())
        menu.add_command(label="👁️  Ver detalle",
                         command=lambda: self.view_product_popup(None))
        menu.add_command(label="✏️  Editar",
                         command=lambda: self._edit_item(item))
        menu.add_command(label="⏸️  Pausar/Reanudar",
                         command=self._toggle_paused)
        menu.add_command(label="📦  Agrupar",
                         command=self._group_selected)
        menu.add_separator()
        menu.add_command(label="💰  Historial de precios",
                         command=self.open_price_history_global)
        menu.add_separator()
        menu.add_command(label="🗑️  Eliminar",
                         command=lambda: self._confirm_delete(item))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _edit_selected(self):
        sel = self.tree.selection()
        if len(sel) != 1:
            MD.show_info("Selecciona un solo producto.", "Editar", parent=self)
            return
        self._edit_item(sel[0])

    def _edit_item(self, item):
        vals = self.tree.item(item, 'values')
        pid = int(vals[0])
        p = self.product_use_case.get_product(pid)
        if not p:
            return
        self.open_product_form(
            "Editar Producto", pid,
            p.name, p.barcode, p.price, p.stock,
            p.unit_type, p.unit, product=p)

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        if MD.yesno(f"¿Eliminar {len(sel)} producto(s)?\n"
                    "Se borrará también su historial de precios.",
                    "Confirmar", parent=self) != "Yes":
            return
        if MD.yesno("🚨 ÚLTIMA ADVERTENCIA\n\n¿Realmente eliminar?",
                    "Confirmación final", parent=self) != "Yes":
            return
        for sid in sel:
            try:
                self.product_use_case.delete_product(int(sid))
            except Exception:
                pass
        self.load_products()
        self.scan_entry.focus_set()

    def _confirm_delete(self, item):
        vals = self.tree.item(item, 'values')
        pid = int(vals[0])
        name = vals[1]
        if MD.yesno(f"⚠️ ¿Eliminar '{name}'?", "Confirmar",
                    parent=self) != "Yes":
            return
        self.product_use_case.delete_product(pid)
        self.load_products()
        MD.show_info(f"'{name}' eliminado.", "Listo", parent=self)
        self.scan_entry.focus_set()

    def _toggle_paused(self):
        sel = self.tree.selection()
        if not sel:
            return
        alguno_activo = False
        for sid in sel:
            p = self.product_use_case.get_product(int(sid))
            if p and not getattr(p, "paused", 0):
                alguno_activo = True
                break
        nuevo = 1 if alguno_activo else 0
        try:
            self.product_use_case.set_paused_bulk([int(s) for s in sel], nuevo)
        except Exception:
            pass
        self.load_products()

    def _group_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        nombre = simpledialog.askstring(
            "Agrupar", "Nombre del grupo (vacío para quitar):",
            initialvalue="", parent=self)
        if nombre is None:
            return
        try:
            self.product_use_case.set_group_name(
                [int(s) for s in sel], nombre.strip())
        except Exception:
            pass
        self.load_products()

    # ============================================================
    # DETALLE
    # ============================================================
    def view_product_popup(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        p = self.product_use_case.get_product(pid)
        if not p:
            return

        popup = Toplevel(self)
        popup.title("Detalle del Producto")
        popup.geometry("480x620")
        popup.transient(self.winfo_toplevel())
        popup.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        ttk.Label(popup, text="📋 DETALLE DEL PRODUCTO",
                  font=("Arial", 13, "bold"),
                  bootstyle="inverse-dark").pack(pady=12)

        info = ttk.Frame(popup, bootstyle="dark")
        info.pack(fill="both", expand=True, padx=25, pady=15)

        campos = [
            ("ID", p.product_id),
            ("Nombre", p.name),
            ("Código", p.barcode or "—"),
            ("Grupo", getattr(p, "group_name", "") or "—"),
            ("Precio real", f"${p.price:,.0f}".replace(",", ".")),
            ("Precio redondeado",
             f"${(getattr(p, 'rounded_price', 0) or p.price):,.0f}".replace(",", ".")),
            ("Costo", f"${(getattr(p, 'cost', 0) or 0):,.0f}".replace(",", ".")),
            ("% Ganancia",
             f"{getattr(p, 'margin_percent', 20):.0f}%"),
            ("Stock", f"{p.stock:g}"),
            ("Unidad", p.unit or "unidad"),
            ("Vence", getattr(p, "expiry_date", "") or "—"),
            ("Pausado", "Sí" if getattr(p, "paused", 0) else "No"),
        ]
        if getattr(p, "is_package", 0):
            campos.append(("Costo paquete",
                           f"${(getattr(p, 'package_cost', 0) or 0):,.0f}".replace(",", ".")))
            campos.append(("Unidades paquete",
                           getattr(p, "package_units", 0)))

        for k, v in campos:
            f = ttk.Frame(info, bootstyle="dark")
            f.pack(fill="x", pady=2)
            ttk.Label(f, text=f"{k}:", font=("Arial", 10, "bold"),
                      width=18, anchor="w",
                      bootstyle="inverse-dark").pack(side="left")
            ttk.Label(f, text=str(v), font=("Arial", 10),
                      bootstyle="inverse-dark").pack(side="left")

        # Aviso de devoluciones
        try:
            veces = self.product_use_case._row_to_product  # dummy
        except Exception:
            veces = 0
        # Obtener devoluciones desde sale_use_case si está disponible
        try:
            from presentation.views.widgets import MD  # noqa
            sale_case = getattr(self, "_sale_case", None)
            if sale_case:
                veces = sale_case.get_product_return_count(
                    p.product_id, p.name)
                if veces > 0:
                    ttk.Label(info,
                              text=f"⚠️ Este producto se ha devuelto {veces} vez/veces",
                              font=("Arial", 10, "bold"),
                              bootstyle="danger").pack(pady=(10, 0))
        except Exception:
            pass

        bf = ttk.Frame(popup, bootstyle="dark")
        bf.pack(side="bottom", pady=12)

        ttk.Button(bf, text="💰 Historial de precios",
                   command=lambda: [popup.destroy(),
                                    self.open_price_history_for(pid)],
                   bootstyle="info").pack(side="left", padx=5)
        ttk.Button(bf, text="✏️ Editar",
                   command=lambda: [popup.destroy(),
                                    self._edit_item(sel[0])],
                   style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="Cerrar", command=popup.destroy,
                   bootstyle="secondary").pack(side="left", padx=5)

        show_popup_smooth(popup)
        try:
            popup.grab_set()
        except Exception:
            pass

    # ============================================================
    # FORMULARIO DE PRODUCTO
    # ============================================================
    def add_product_popup(self, barcode_prefill="", auto_select=False):
        self.open_product_form("Agregar Producto", None, "", barcode_prefill,
                               0, 0, "unidad", "unidad", auto_select)

    def open_product_form(self, title, product_id, name, barcode, price, stock,
                          unit_type, unit, auto_select=False,
                          from_draft=False, product=None):
        popup = Toplevel(self)
        popup.title(title)
        popup.geometry("560x820")
        popup.transient(self.winfo_toplevel())
        popup.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        # Scroll wrapper
        container = tk.Frame(popup, bg=bg)
        container.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(container, orient="vertical",
                                  style="DarkRed.Vertical.TScrollbar")
        scrollbar.pack(side="right", fill="y")
        canvas = tk.Canvas(container, bg=bg, highlightthickness=0)
        canvas.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(canvas, bg=bg)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_conf(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
        def _on_canvas_conf(e):
            canvas.itemconfigure(inner_id, width=e.width)
        inner.bind("<Configure>", _on_inner_conf)
        canvas.bind("<Configure>", _on_canvas_conf)
        scrollbar.config(command=canvas.yview)

        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        canvas.bind("<MouseWheel>", _on_mousewheel)
        inner.bind("<MouseWheel>", _on_mousewheel)

        # ---- Campos ----
        ttk.Label(inner, text="Código de Barras / QR:",
                  bootstyle="inverse-dark").pack(pady=(15, 3))
        barcode_entry = ttk.Entry(inner, width=35)
        barcode_entry.pack(pady=3)
        if barcode:
            barcode_entry.insert(0, barcode)

        ttk.Label(inner, text="Nombre del Producto:",
                  bootstyle="inverse-dark").pack(pady=(8, 3))
        name_entry = ttk.Entry(inner, width=35)
        name_entry.pack(pady=3)
        if name:
            name_entry.insert(0, name)

        # ---- Modo paquete ----
        pkg_frame = ttk.LabelFrame(inner, text="📦 Modo Paquete / Caja",
                                    bootstyle="dark")
        pkg_frame.pack(fill="x", padx=20, pady=10)
        pkg_var = tk.IntVar(value=1 if product and getattr(product, "is_package", 0) else 0)
        ttk.Checkbutton(pkg_frame, text="Viene en paquete/caja",
                        variable=pkg_var,
                        bootstyle="info-round-toggle",
                        command=lambda: toggle_pkg()).pack(anchor="w", padx=8, pady=6)

        pkg_body = tk.Frame(pkg_frame, bg=bg)
        pkg_body.pack(fill="x", padx=8, pady=4)

        pkg_cost_var = tk.StringVar(value=str(getattr(product, "package_cost", 0) if product else 0))
        pkg_units_var = tk.StringVar(value=str(getattr(product, "package_units", 0) if product else 0))
        pkg_qty_var = tk.StringVar(value="1")

        def pkg_row(label, var):
            f = tk.Frame(pkg_body, bg=bg)
            f.pack(fill="x", pady=2)
            tk.Label(f, text=label, width=22, anchor="w",
                     bg=bg, fg=fg, font=("Arial", 10)).pack(side="left")
            ttk.Entry(f, textvariable=var, width=12).pack(side="left")

        pkg_row("Costo del paquete:", pkg_cost_var)
        pkg_row("Unidades por paquete:", pkg_units_var)
        pkg_row("Cantidad de paquetes:", pkg_qty_var)

        # Costo unitario calculado
        tk.Label(pkg_body, text="Costo unitario:", bg=bg, fg=fg,
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(6, 0))
        cost_unit_lbl = tk.Label(pkg_body, text="$0", bg=bg, fg="#7dd87d",
                                 font=("Arial", 11, "bold"))
        cost_unit_lbl.pack(anchor="w")

        tk.Label(pkg_body, text="Stock total:", bg=bg, fg=fg,
                 font=("Arial", 10, "bold")).pack(anchor="w", pady=(4, 0))
        stock_total_lbl = tk.Label(pkg_body, text="0", bg=bg, fg="#7dd87d",
                                    font=("Arial", 11, "bold"))
        stock_total_lbl.pack(anchor="w")

        def recalc_pkg():
            try:
                pc = float(pkg_cost_var.get() or 0)
                pu = float(pkg_units_var.get() or 0)
                pq = float(pkg_qty_var.get() or 1)
                if pu > 0:
                    unit_cost = pc / pu
                    cost_unit_lbl.configure(text=f"${unit_cost:,.0f}".replace(",", "."))
                    stock_total_lbl.configure(text=f"{int(pu * pq)}")
                    cost_var.set(f"{unit_cost:.0f}")
            except Exception:
                pass

        for v in (pkg_cost_var, pkg_units_var, pkg_qty_var):
            v.trace_add("write", lambda *a: recalc_pkg())

        # ---- Tipo de venta ----
        ttk.Label(inner, text="Tipo de venta:",
                  bootstyle="inverse-dark").pack(pady=(10, 3))
        type_var = tk.StringVar(value=unit_type)
        type_frame = ttk.Frame(inner, bootstyle="dark")
        type_frame.pack()
        for val, txt in [("unidad", "📦 Unidad"), ("peso", "⚖️ Peso"),
                         ("volumen", "💧 Volumen")]:
            ttk.Radiobutton(type_frame, text=txt, variable=type_var,
                            value=val, bootstyle="info").pack(side="left", padx=5)

        ttk.Label(inner, text="Unidad de medida:",
                  bootstyle="inverse-dark").pack(pady=(10, 3))
        unit_var = tk.StringVar(value=unit)
        unit_combo = ttk.Combobox(inner, textvariable=unit_var,
                                   state="readonly", width=15)
        unit_combo.pack(pady=3)

        def refresh_units(*args):
            t = type_var.get()
            if t == "unidad":
                ops = ["unidad"]
            elif t == "peso":
                ops = ["kg", "gr", "mg"]
            else:
                ops = ["Lt", "ml"]
            unit_combo.configure(values=ops)
            if unit_var.get() not in ops:
                unit_var.set(ops[0])

        type_var.trace_add("write", refresh_units)
        refresh_units()

        # ---- Costo y margen ----
        f_cm = ttk.Frame(inner, bootstyle="dark")
        f_cm.pack(pady=8, fill="x", padx=20)
        ttk.Label(f_cm, text="Costo unitario:",
                  bootstyle="inverse-dark").pack(side="left")
        cost_var = tk.StringVar(value=str(int(getattr(product, "cost", 0) or 0) if product else 0))
        ttk.Entry(f_cm, textvariable=cost_var, width=12).pack(side="left", padx=6)
        ttk.Label(f_cm, text="  % Ganancia:",
                  bootstyle="inverse-dark").pack(side="left")
        margin_var = tk.StringVar(value=str(int(getattr(product, "margin_percent", 20) or 20) if product else 20))
        ttk.Entry(f_cm, textvariable=margin_var, width=8).pack(side="left", padx=6)

        # ---- Precio ----
        f_price = ttk.Frame(inner, bootstyle="dark")
        f_price.pack(pady=6, fill="x", padx=20)
        ttk.Label(f_price, text="Precio venta:",
                  bootstyle="inverse-dark").pack(side="left")
        price_var = tk.StringVar(value=str(int(price) if price else 0))
        ttk.Entry(f_price, textvariable=price_var, width=15).pack(side="left", padx=6)

        def recalcular_precio():
            try:
                c = float(cost_var.get() or 0)
                m = float(margin_var.get() or 0)
                p = c * (1 + m / 100.0)
                price_var.set(f"{p:.0f}")
                if round_var.get():
                    recalcular_redondeo()
            except Exception:
                pass

        ttk.Button(f_price, text="↻ Recalcular",
                   command=recalcular_precio,
                   bootstyle="info").pack(side="left", padx=6)

        # ---- Redondeo ----
        round_frame = ttk.LabelFrame(inner, text="🎯 Redondeo de precio",
                                      bootstyle="dark")
        round_frame.pack(fill="x", padx=20, pady=8)
        round_var = tk.IntVar(value=1 if product and getattr(product, "round_enabled", 0) else 0)
        ttk.Checkbutton(round_frame, text="Redondear precio final",
                        variable=round_var,
                        bootstyle="info-round-toggle",
                        command=lambda: recalcular_redondeo()
                        ).pack(anchor="w", padx=8, pady=4)

        f_round = tk.Frame(round_frame, bg=bg)
        f_round.pack(fill="x", padx=8, pady=4)
        tk.Label(f_round, text="Redondear al:", bg=bg, fg=fg,
                 font=("Arial", 10)).pack(side="left")
        round_to_var = tk.StringVar(value=str(getattr(product, "round_to", 100) if product else 100))
        ttk.Combobox(f_round, textvariable=round_to_var, state="readonly",
                     values=["10", "50", "100", "500", "1000"],
                     width=8).pack(side="left", padx=6)

        tk.Label(round_frame, text="Precio redondeado:", bg=bg, fg=fg,
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=8)
        rounded_var = tk.StringVar(value=str(getattr(product, "rounded_price", 0) if product else 0))
        ttk.Entry(round_frame, textvariable=rounded_var,
                  width=15).pack(anchor="w", padx=8, pady=4)

        def recalcular_redondeo():
            if not round_var.get():
                return
            try:
                p = float(price_var.get() or 0)
                rto = float(round_to_var.get() or 100)
                if rto <= 0:
                    return
                redondeado = round(p / rto) * rto
                rounded_var.set(f"{redondeado:.0f}")
            except Exception:
                pass

        def toggle_round():
            recalcular_redondeo()
        round_to_var.trace_add("write", lambda *a: recalcular_redondeo())
        price_var.trace_add("write", lambda *a: recalcular_redondeo())

        # ---- Stock ----
        f_stock = ttk.Frame(inner, bootstyle="dark")
        f_stock.pack(pady=6, fill="x", padx=20)
        ttk.Label(f_stock, text="Stock:",
                  bootstyle="inverse-dark").pack(side="left")
        stock_var = tk.StringVar(value=str(int(stock) if stock else 0))
        stock_entry = ttk.Entry(f_stock, textvariable=stock_var, width=12)
        stock_entry.pack(side="left", padx=6)

        def toggle_pkg():
            if pkg_var.get():
                for ch in pkg_body.winfo_children():
                    _set_state(ch, "normal")
                stock_entry.configure(state="disabled")
                recalc_pkg()
            else:
                for ch in pkg_body.winfo_children():
                    _set_state(ch, "disabled")
                stock_entry.configure(state="normal")

        def _set_state(widget, state):
            try:
                widget.configure(state=state)
            except Exception:
                pass
            for child in widget.winfo_children():
                _set_state(child, state)

        toggle_pkg()

        # ---- Vencimiento ----
        f_exp = ttk.Frame(inner, bootstyle="dark")
        f_exp.pack(pady=6, fill="x", padx=20)
        ttk.Label(f_exp, text="Vence (YYYY-MM-DD):",
                  bootstyle="inverse-dark").pack(side="left")
        expiry_var = tk.StringVar(value=getattr(product, "expiry_date", "") if product else "")
        ttk.Entry(f_exp, textvariable=expiry_var, width=15).pack(side="left", padx=6)

        # ---- Pausado ----
        paused_var = tk.IntVar(value=1 if product and getattr(product, "paused", 0) else 0)
        ttk.Checkbutton(inner,
                        text="⏸️ Producto pausado (no aparece en PAGOS)",
                        variable=paused_var,
                        bootstyle="warning-round-toggle").pack(pady=10)

        # ---- Sugerencia inteligente ----
        sugerencia_frame = tk.Frame(inner, bg="#3a3a10")
        sugerencia_lbl = tk.Label(sugerencia_frame, text="", bg="#3a3a10",
                                  fg="#ffd166", font=("Arial", 9),
                                  justify="left", wraplength=460)
        sugerencia_lbl.pack(side="left", padx=8, pady=6)
        sugerencia_data = {"data": None}

        def aplicar_sugerencia():
            d = sugerencia_data["data"]
            if not d:
                return
            pkg_var.set(1)
            pkg_cost_var.set(str(d["package_cost"]))
            pkg_units_var.set(str(d["package_units"]))
            pkg_qty_var.set("1")
            toggle_pkg()
            recalc_pkg()
            sugerencia_frame.pack_forget()

        ttk.Button(sugerencia_frame, text="Usar sugerencia",
                   command=aplicar_sugerencia,
                   bootstyle="warning").pack(side="right", padx=8, pady=6)

        def check_sugerencia(*args):
            if product_id:  # no sugerir al editar
                return
            n = name_entry.get().strip()
            if len(n) < 3:
                sugerencia_frame.pack_forget()
                return
            try:
                data = self.product_use_case.find_last_package_for_name(n)
            except Exception:
                data = None
            if not data:
                sugerencia_frame.pack_forget()
                return
            sugerencia_data["data"] = data
            txt = (f"💡 La última vez compraste «{data['name']}» a "
                   f"${data['package_cost']:,.0f} por paquete de "
                   f"{data['package_units']} unidades. ¿Quieres usar esos datos?")
            sugerencia_lbl.configure(text=txt)
            sugerencia_frame.pack(fill="x", padx=20, pady=6)

        name_entry.bind("<KeyRelease>", check_sugerencia, add="+")

        # ---- Guardar ----
        def guardar():
            n = name_entry.get().strip()
            if not n:
                MD.show_error("El nombre es obligatorio.", "Error", parent=popup)
                return
            try:
                pl = price_var.get().replace("$", "").replace(".", "").replace(",", ".").strip()
                p_val = float(pl) if pl else 0.0
                rto = int(float(round_to_var.get() or 100))
                rp_val = float(rounded_var.get() or p_val)
                r_enabled = 1 if round_var.get() else 0
                c_val = float(cost_var.get() or 0)
                m_val = float(margin_var.get() or 0)
                is_pkg = 1 if pkg_var.get() else 0
                pkg_c = float(pkg_cost_var.get() or 0)
                pkg_u = int(float(pkg_units_var.get() or 0))
                if is_pkg:
                    s_val = int(float(pkg_qty_var.get() or 1) * pkg_u)
                else:
                    s_val = float(stock_var.get().replace(",", ".") or 0)
            except ValueError:
                MD.show_error("Revisa los valores numéricos.", "Error",
                              parent=popup)
                return
            expiry = expiry_var.get().strip()
            if expiry:
                try:
                    datetime.strptime(expiry, "%Y-%m-%d")
                except ValueError:
                    MD.show_error("Fecha inválida. Usa YYYY-MM-DD.",
                                  "Error", parent=popup)
                    return

            try:
                if product_id:
                    self.product_use_case.update_product(
                        product_id, n, barcode_entry.get().strip(),
                        p_val, s_val,
                        unit_type=type_var.get(), unit=unit_var.get(),
                        group_name="", cost=c_val, margin_percent=m_val,
                        rounded_price=rp_val,
                        round_enabled=r_enabled, round_to=rto,
                        package_cost=pkg_c, package_units=pkg_u,
                        is_package=is_pkg,
                        paused=paused_var.get(),
                        expiry_date=expiry)
                else:
                    self.product_use_case.add_product(
                        n, barcode_entry.get().strip(),
                        p_val, s_val,
                        unit_type=type_var.get(), unit=unit_var.get(),
                        group_name="", cost=c_val, margin_percent=m_val,
                        rounded_price=rp_val,
                        round_enabled=r_enabled, round_to=rto,
                        package_cost=pkg_c, package_units=pkg_u,
                        is_package=is_pkg,
                        paused=paused_var.get(),
                        expiry_date=expiry)
                self.product_use_case.clear_product_draft()
            except Exception as e:
                MD.show_error(f"Error al guardar: {e}", "Error", parent=popup)
                return

            self.load_products()
            popup.destroy()
            self.scan_entry.focus_set()
            if auto_select and barcode_entry.get().strip():
                b = barcode_entry.get().strip()
                for it in self.tree.get_children():
                    if str(self.tree.item(it, 'values')[2]).strip() == b:
                        self.tree.selection_set(it)
                        self.tree.focus(it)
                        self.tree.see(it)
                        break

        bf = ttk.Frame(inner, bootstyle="dark")
        bf.pack(pady=15)
        ttk.Button(bf, text="💾 Guardar", command=guardar,
                   style="DarkGreen.TButton").pack(side="left", padx=6)
        ttk.Button(bf, text="❌ Cancelar",
                   command=popup.destroy).pack(side="left", padx=6)

        show_popup_smooth(popup)
        try:
            popup.grab_set()
        except Exception:
            pass

        if barcode:
            name_entry.focus_set()
        else:
            barcode_entry.focus_set()

    # ============================================================
    # SCAN
    # ============================================================
    def lookup_barcode(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo:
            return
        enc = None
        for p in self.product_use_case.list_products():
            if str(p.barcode).strip() == codigo:
                enc = p
                break
        if enc:
            self.search_var.set("")
            self.load_products()
            for it in self.tree.get_children():
                if str(self.tree.item(it, 'values')[2]).strip() == codigo:
                    self.tree.selection_set(it)
                    self.tree.focus(it)
                    self.tree.see(it)
                    break
            r = MD.yesno(
                f"✅ Producto encontrado:\n\n"
                f"Nombre: {enc.name}\n"
                f"Precio: ${enc.price:,.0f}\n"
                f"Stock: {enc.stock:g} {enc.unit}\n\n"
                f"¿Deseas EDITARLO?".replace(",", "."),
                "Producto Encontrado", parent=self)
            if r == "Yes":
                for it in self.tree.get_children():
                    if str(self.tree.item(it, 'values')[2]).strip() == codigo:
                        self._edit_item(it)
                        break
        else:
            r = MD.yesno(f"⚠️ '{codigo}' NO está registrado.\n\n¿Agregarlo?",
                         "No encontrado", parent=self)
            if r == "Yes":
                self.add_product_popup(barcode_prefill=codigo, auto_select=True)
        self.scan_var.set("")
        self.scan_entry.focus_set()

    # ============================================================
    # ACCIONES DE IDEAS
    # ============================================================
    def print_labels(self):
        from presentation.views.widgets import generate_labels_pdf
        from tkinter import filedialog
        if self._label_selection:
            productos = self.product_use_case.get_products_for_labels(
                list(self._label_selection))
        else:
            r = MD.yesno("No hay productos marcados.\n¿Generar etiquetas para TODOS los activos?",
                         "Etiquetas", parent=self)
            if r != "Yes":
                return
            productos = self.product_use_case.get_products_for_labels()
        if not productos:
            MD.show_warning("No hay productos para etiquetar.", "Etiquetas",
                            parent=self)
            return
        copias = simpledialog.askinteger(
            "Copias", "¿Cuántas copias por producto?",
            initialvalue=1, minvalue=1, maxvalue=50, parent=self)
        if not copias:
            copias = 1
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"etiquetas_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            parent=self)
        if not ruta:
            return
        try:
            generate_labels_pdf(productos, ruta, copies=copias)
            MD.show_info(f"PDF generado:\n{ruta}", "Etiquetas", parent=self)
            self._label_selection.clear()
        except Exception as e:
            MD.show_error(f"No se pudo generar el PDF:\n{e}", "Error", parent=self)

    def open_charts(self):
        from presentation.views.widgets import ChartsWindow
        sale_case = getattr(self, "_sale_case", None)
        if not sale_case:
            MD.show_warning("No disponible desde aquí.", "Gráficos", parent=self)
            return
        ChartsWindow(self, sale_case)

    def open_returns_window(self):
        from presentation.views.widgets import ReturnsWindow
        sale_case = getattr(self, "_sale_case", None)
        if not sale_case:
            MD.show_warning("No disponible desde aquí.", "Devoluciones",
                            parent=self)
            return
        ReturnsWindow(self, sale_case,
                      on_done=lambda: self.load_products())

    def open_expiry_alerts(self):
        # Reutilizamos un diálogo simple
        cfg = self.product_use_case.get_expiry_settings()
        pop = Toplevel(self)
        pop.title("📅 Alertas de vencimiento")
        pop.geometry("460x400")
        pop.transient(self.winfo_toplevel())
        pop.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        ttk.Label(pop, text="📅 Alertas de vencimiento",
                  font=("Arial", 14, "bold"),
                  bootstyle="inverse-dark").pack(pady=12)
        ttk.Label(pop, text="Configura los días de aviso antes del vencimiento.",
                  bootstyle="inverse-dark").pack(pady=4)

        def row_field(label, value):
            f = tk.Frame(pop, bg=bg)
            f.pack(fill="x", padx=20, pady=6)
            tk.Label(f, text=label, bg=bg, fg=fg,
                     width=28, anchor="w", font=("Arial", 10)).pack(side="left")
            v = tk.StringVar(value=str(value))
            ttk.Entry(f, textvariable=v, width=10,
                      justify="center").pack(side="left")
            return v

        v1 = row_field("🟠 Alerta temprana (días):", cfg["warn_days_1"])
        v2 = row_field("🟡 Alerta cercana (días):", cfg["warn_days_2"])
        v3 = row_field("💡 Zona de oferta (días):", cfg["offer_days"])
        v4 = row_field("🏷️ Descuento de oferta (%):", cfg["offer_discount"])

        def guardar():
            try:
                w1 = int(float(v1.get() or 15))
                w2 = int(float(v2.get() or 7))
                od = int(float(v3.get() or 2))
                disc = float(v4.get() or 20)
            except ValueError:
                MD.show_error("Valores inválidos.", "Error", parent=pop)
                return
            if not (w1 >= w2 >= od):
                MD.show_error("Los días deben cumplir: temprana ≥ cercana ≥ oferta.",
                              "Orden inválido", parent=pop)
                return
            self.product_use_case.set_expiry_settings(w1, w2, od, disc)
            MD.show_info("✅ Alertas configuradas.", "Listo", parent=pop)
            pop.destroy()
            self.load_products()

        bf = ttk.Frame(pop, bootstyle="dark")
        bf.pack(pady=14)
        ttk.Button(bf, text="💾 Guardar", command=guardar,
                   bootstyle="success").pack(side="left", padx=5)
        ttk.Button(bf, text="Ver productos con alerta",
                   command=lambda: [pop.destroy(),
                                    self.filter_status.set("Por vencer"),
                                    self.filter_products()],
                   bootstyle="info").pack(side="left", padx=5)
        ttk.Button(bf, text="Cerrar", command=pop.destroy,
                   bootstyle="secondary").pack(side="left", padx=5)

        show_popup_smooth(pop)
        try:
            pop.grab_set()
        except Exception:
            pass

    def open_price_history_global(self):
        self._open_price_history_window(product_id=None)

    def open_price_history_for(self, product_id):
        self._open_price_history_window(product_id=product_id)

    def _open_price_history_window(self, product_id=None):
        pop = Toplevel(self)
        pop.title("💰 Historial de precios")
        pop.geometry("900x560")
        pop.transient(self.winfo_toplevel())
        pop.withdraw()
        bg = ttk.Style().colors.bg
        fg = ttk.Style().colors.fg

        ttk.Label(pop, text="💰 Historial de precios",
                  font=("Arial", 14, "bold"),
                  bootstyle="inverse-dark").pack(pady=10)

        if product_id:
            data = self.product_use_case.get_price_history(product_id)
        else:
            data = self.product_use_case.get_all_price_history()

        frame, tree = make_scrolled_treeview(
            pop,
            columns=("Fecha", "Producto", "Antes", "Ahora", "AntesRed", "AhoraRed"),
            headings=[
                ("Fecha", "Fecha", 150, "center"),
                ("Producto", "Producto", 220, "w"),
                ("Antes", "Precio ant.", 100, "e"),
                ("Ahora", "Precio nuevo", 100, "e"),
                ("AntesRed", "Redond. ant.", 100, "e"),
                ("AhoraRed", "Redond. nuevo", 110, "e"),
            ],
            bootstyle="dark")
        frame.pack(fill="both", expand=True, padx=10, pady=8)

        for r in data:
            tree.insert("", "end", values=(
                r["date"],
                r.get("product_name", "-"),
                f"${r['old_price']:,.0f}".replace(",", "."),
                f"${r['new_price']:,.0f}".replace(",", "."),
                f"${r.get('old_rounded_price', 0):,.0f}".replace(",", "."),
                f"${r.get('new_rounded_price', 0):,.0f}".replace(",", ".")))

        def exportar():
            from tkinter import filedialog
            ruta = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Texto", "*.txt")],
                initialfile=f"historial_precios_{datetime.now().strftime('%Y%m%d')}.txt",
                parent=pop)
            if not ruta:
                return
            try:
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write("HISTORIAL DE PRECIOS\n" + "=" * 90 + "\n\n")
                    for r in data:
                        f.write(f"[{r['date']}] {r.get('product_name','-')}\n"
                                f"   Real: ${r['old_price']:,.0f} → ${r['new_price']:,.0f}\n"
                                f"   Redondeado: ${r.get('old_rounded_price',0):,.0f} → "
                                f"${r.get('new_rounded_price',0):,.0f}\n\n")
                MD.show_info(f"Exportado:\n{ruta}", "Listo", parent=pop)
            except Exception as e:
                MD.show_error(f"Error: {e}", "Error", parent=pop)

        bf = ttk.Frame(pop, bootstyle="dark")
        bf.pack(pady=8)
        ttk.Button(bf, text="📄 Exportar TXT", command=exportar,
                   bootstyle="info").pack(side="left", padx=5)
        ttk.Button(bf, text="Cerrar", command=pop.destroy,
                   bootstyle="secondary").pack(side="left", padx=5)

        show_popup_smooth(pop)
        try:
            pop.grab_set()
        except Exception:
            pass