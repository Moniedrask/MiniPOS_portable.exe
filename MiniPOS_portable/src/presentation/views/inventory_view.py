import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import os
import sys
from datetime import datetime, timedelta

# Asegurar imports desde src
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from application.use_case.product_use_case import ProductCase
from application.use_case.sale_use_case import SaleCase


class InventoryView(tk.Toplevel):
    def __init__(self, master, product_case: ProductCase, sale_case: SaleCase = None):
        super().__init__(master)
        self.product_case = product_case
        self.sale_case = sale_case

        self.title("Inventario")
        self.geometry("1200x700")
        self.minsize(1000, 600)

        # Estilos
        self._configure_styles()

        # Datos
        self.all_products = []
        self.filtered_products = []
        self._sort_column = None
        self._sort_reverse = False
        self._label_selection = set()  # para selección múltiple de etiquetas

        # ===== Barra superior =====
        top = tk.Frame(self, bg="#f0f0f0", height=50)
        top.pack(side="top", fill="x")

        tk.Label(top, text="🔍", bg="#f0f0f0", font=("Segoe UI", 12)).pack(side="left", padx=(10, 2), pady=10)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.apply_filter())
        tk.Entry(top, textvariable=self.search_var, font=("Segoe UI", 11), width=30)\
            .pack(side="left", padx=5, pady=10)

        # Filtros
        tk.Label(top, text="Grupo:", bg="#f0f0f0").pack(side="left", padx=(10, 2))
        self.filter_group = ttk.Combobox(top, state="readonly", width=15)
        self.filter_group.pack(side="left")
        self.filter_group.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        tk.Label(top, text="Estado:", bg="#f0f0f0").pack(side="left", padx=(10, 2))
        self.filter_status = ttk.Combobox(
            top, state="readonly", width=15,
            values=["Todos", "Activos", "Pausados", "Por vencer", "Vencidos", "En oferta"])
        self.filter_status.set("Todos")
        self.filter_status.pack(side="left")
        self.filter_status.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())

        # Contadores
        self.lbl_count = tk.Label(top, text="0 productos", bg="#f0f0f0",
                                  font=("Segoe UI", 10, "bold"), fg="#333")
        self.lbl_count.pack(side="right", padx=10)

        # ===== Barra de botones =====
        btns = tk.Frame(self, bg="#e8e8e8")
        btns.pack(side="top", fill="x")

        def mk_btn(text, cmd, bg="#4CAF50"):
            b = tk.Button(btns, text=text, command=cmd, bg=bg, fg="white",
                          font=("Segoe UI", 9, "bold"), padx=12, pady=6,
                          relief="flat", cursor="hand2")
            b.pack(side="left", padx=4, pady=6)
            return b

        mk_btn("➕ Agregar", self.open_add_dialog, "#4CAF50")
        mk_btn("✏️ Editar", self.open_edit_dialog, "#2196F3")
        mk_btn("🗑️ Eliminar", self.delete_selected, "#f44336")
        mk_btn("⏸️ Pausar / Reactivar", self.toggle_paused, "#FF9800")
        mk_btn("📦 Agrupar", self.group_selected, "#9C27B0")
        mk_btn("🖨️ Etiquetas PDF", self.print_labels, "#607D8B")
        mk_btn("📊 Gráficos", self.open_charts, "#00BCD4")
        mk_btn("🔔 Vencimientos", self.open_expiry_alerts, "#E91E63")
        mk_btn("💰 Hist. precios", self.open_price_history_global, "#795548")
        mk_btn("🔄 Refrescar", self.refresh, "#555555")

        # ===== Tabla =====
        table_frame = tk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=8, pady=8)

        columns = ("id", "name", "barcode", "group", "price", "rounded", "cost",
                   "margin", "stock", "unit", "expiry", "status")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings",
                                 selectmode="extended")

        headers = {
            "id": ("ID", 50),
            "name": ("Nombre", 220),
            "barcode": ("Código", 120),
            "group": ("Grupo", 100),
            "price": ("Precio", 90),
            "rounded": ("P. Redondeado", 110),
            "cost": ("Costo", 90),
            "margin": ("% Gan.", 70),
            "stock": ("Stock", 70),
            "unit": ("Unidad", 80),
            "expiry": ("Vence", 100),
            "status": ("Estado", 100),
        }
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text,
                              command=lambda c=col: self.sort_by(c))
            anchor = "w" if col in ("name", "barcode", "group") else "center"
            self.tree.column(col, width=width, anchor=anchor)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # Colores por estado
        self.tree.tag_configure("expired", background="#ffcdd2")
        self.tree.tag_configure("offer", background="#ffe0b2")
        self.tree.tag_configure("warn2", background="#fff9c4")
        self.tree.tag_configure("warn1", background="#e1f5fe")
        self.tree.tag_configure("paused", foreground="#888888", background="#eeeeee")

        # Doble clic → editar
        self.tree.bind("<Double-1>", lambda e: self.open_edit_dialog())

        # ===== Barra inferior de acciones seleccionadas =====
        bottom = tk.Frame(self, bg="#f0f0f0")
        bottom.pack(side="bottom", fill="x")

        self.lbl_sel = tk.Label(bottom, text="0 seleccionados", bg="#f0f0f0",
                                font=("Segoe UI", 9))
        self.lbl_sel.pack(side="left", padx=10, pady=5)

        tk.Button(bottom, text="📋 Ver detalle", command=self.open_detail_dialog,
                  bg="#3F51B5", fg="white", relief="flat", padx=10, pady=4,
                  cursor="hand2").pack(side="right", padx=5, pady=4)
        tk.Button(bottom, text="🏷️ Seleccionar para etiquetas",
                  command=self.toggle_label_selection,
                  bg="#607D8B", fg="white", relief="flat", padx=10, pady=4,
                  cursor="hand2").pack(side="right", padx=5, pady=4)

        self.tree.bind("<<TreeviewSelect>>", lambda e: self.update_sel_count())

        # Cargar
        self.refresh()

    # ============================================================
    # ESTILOS
    # ============================================================
    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Treeview", rowheight=26, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"))

    # ============================================================
    # CARGA Y FILTROS
    # ============================================================
    def refresh(self):
        self.all_products = self.product_case.list_products()
        self.populate_groups()
        self.apply_filter()

    def populate_groups(self):
        grupos = sorted({p.group_name for p in self.all_products if p.group_name})
        self.filter_group["values"] = ["Todos"] + grupos
        if self.filter_group.get() not in self.filter_group["values"]:
            self.filter_group.set("Todos")

    def apply_filter(self):
        q = self.search_var.get().strip().lower()
        grupo = self.filter_group.get() or "Todos"
        estado = self.filter_status.get() or "Todos"

        expiring = {}
        if estado in ("Por vencer", "Vencidos", "En oferta"):
            for item in self.product_case.get_expiring_products():
                expiring[item["product"].product_id] = item

        hoy = datetime.now().date()
        filtrados = []
        for p in self.all_products:
            # Búsqueda
            if q:
                texto = f"{p.name} {p.barcode} {p.group_name}".lower()
                if q not in texto:
                    continue
            # Grupo
            if grupo != "Todos" and p.group_name != grupo:
                continue
            # Estado
            if estado == "Activos" and p.paused:
                continue
            if estado == "Pausados" and not p.paused:
                continue
            if estado in ("Por vencer", "Vencidos", "En oferta"):
                info = expiring.get(p.product_id)
                if not info:
                    continue
                if estado == "Por vencer" and info["status"] not in ("warn1", "warn2"):
                    continue
                if estado == "Vencidos" and info["status"] != "expired":
                    continue
                if estado == "En oferta" and info["status"] != "offer":
                    continue

            filtrados.append(p)

        self.filtered_products = filtrados
        self.render_table()
        self.lbl_count.config(text=f"{len(filtrados)} de {len(self.all_products)} productos")

    def render_table(self):
        self.tree.delete(*self.tree.get_children())

        # Cache de estado de vencimiento
        expiring = {item["product"].product_id: item
                    for item in self.product_case.get_expiring_products()}
        hoy = datetime.now().date()

        for p in self.filtered_products:
            info = expiring.get(p.product_id)
            status_text = ""
            tag = ()

            if p.paused:
                status_text = "⏸️ Pausado"
                tag = ("paused",)
            elif info:
                s = info["status"]
                d = info["days_left"]
                if s == "expired":
                    status_text = f"⚠️ Vencido ({abs(d)}d)"
                    tag = ("expired",)
                elif s == "offer":
                    status_text = f"🏷️ Oferta ({d}d)"
                    tag = ("offer",)
                elif s == "warn2":
                    status_text = f"⏰ {d}d"
                    tag = ("warn2",)
                elif s == "warn1":
                    status_text = f"⏳ {d}d"
                    tag = ("warn1",)
                else:
                    status_text = "OK"
            else:
                status_text = "OK"

            unidad = p.unit or "unidad"
            self.tree.insert("", "end", iid=str(p.product_id),
                             values=(
                                 p.product_id,
                                 p.name,
                                 p.barcode or "",
                                 p.group_name or "",
                                 f"${p.price:,.0f}",
                                 f"${(p.rounded_price or p.price):,.0f}",
                                 f"${(p.cost or 0):,.0f}",
                                 f"{p.margin_percent or 0:.0f}%",
                                 p.stock,
                                 unidad,
                                 p.expiry_date or "",
                                 status_text,
                             ),
                             tags=tag)

        self.update_sel_count()

    def update_sel_count(self):
        n = len(self.tree.selection())
        self.lbl_sel.config(text=f"{n} seleccionados")

    def sort_by(self, col):
        if self._sort_column == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_column = col
            self._sort_reverse = False

        def key_func(p):
            val = {
                "id": p.product_id,
                "name": (p.name or "").lower(),
                "barcode": (p.barcode or "").lower(),
                "group": (p.group_name or "").lower(),
                "price": p.price or 0,
                "rounded": p.rounded_price or 0,
                "cost": p.cost or 0,
                "margin": p.margin_percent or 0,
                "stock": p.stock or 0,
                "unit": (p.unit or "").lower(),
                "expiry": p.expiry_date or "",
                "status": 1 if p.paused else 0,
            }.get(col, "")
            return val

        self.filtered_products.sort(key=key_func, reverse=self._sort_reverse)
        self.render_table()

    # ============================================================
    # AGREGAR / EDITAR / ELIMINAR
    # ============================================================
    def open_add_dialog(self):
        ProductFormDialog(self, self.product_case, product=None,
                          on_save=self.refresh)

    def open_edit_dialog(self):
        sel = self.tree.selection()
        if len(sel) != 1:
            messagebox.showinfo("Editar", "Selecciona un solo producto.")
            return
        pid = int(sel[0])
        prod = self.product_case.get_product(pid)
        if not prod:
            return
        ProductFormDialog(self, self.product_case, product=prod,
                          on_save=self.refresh)

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        if not messagebox.askyesno("Eliminar",
                                   f"¿Eliminar {len(sel)} producto(s)?\n"
                                   "Se borrará también su historial de precios."):
            return
        for sid in sel:
            self.product_case.delete_product(int(sid))
        self.refresh()

    def toggle_paused(self):
        sel = self.tree.selection()
        if not sel:
            return
        # Si al menos uno está activo → pausar; si todos pausados → activar
        alguno_activo = False
        for sid in sel:
            p = self.product_case.get_product(int(sid))
            if p and not p.paused:
                alguno_activo = True
                break
        nuevo_estado = 1 if alguno_activo else 0
        self.product_case.set_paused_bulk([int(s) for s in sel], nuevo_estado)
        self.refresh()

    def group_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        nombre = simpledialog.askstring(
            "Agrupar", "Nombre del grupo (vacío para quitar):",
            initialvalue=self.product_case.get_product(int(sel[0])).group_name or "")
        if nombre is None:
            return
        self.product_case.set_group_name([int(s) for s in sel], nombre.strip())
        self.refresh()

    # ============================================================
    # IDEA 5: ETIQUETAS PDF
    # ============================================================
    def toggle_label_selection(self):
        sel = self.tree.selection()
        if not sel:
            return
        for sid in sel:
            pid = int(sid)
            if pid in self._label_selection:
                self._label_selection.remove(pid)
            else:
                self._label_selection.add(pid)
        messagebox.showinfo("Etiquetas",
                            f"{len(self._label_selection)} producto(s) marcados para etiquetas.\n"
                            "Presiona '🖨️ Etiquetas PDF' para generarlas.")

    def print_labels(self):
        from presentation.views.widgets import generate_labels_pdf

        if self._label_selection:
            productos = self.product_case.get_products_for_labels(
                list(self._label_selection))
        else:
            resp = messagebox.askyesno(
                "Etiquetas",
                "No hay productos seleccionados.\n¿Generar etiquetas para TODOS los activos?")
            if not resp:
                return
            productos = self.product_case.get_products_for_labels()

        if not productos:
            messagebox.showwarning("Etiquetas", "No hay productos para etiquetar.")
            return

        # Pedir cantidad de copias de cada etiqueta
        copias = simpledialog.askinteger(
            "Copias", "¿Cuántas copias por producto?", initialvalue=1, minvalue=1, maxvalue=50)
        if not copias:
            copias = 1

        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"etiquetas_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf")
        if not ruta:
            return

        try:
            generate_labels_pdf(productos, ruta, copies=copias)
            messagebox.showinfo("Etiquetas", f"PDF generado:\n{ruta}")
            # Limpiar selección
            self._label_selection.clear()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el PDF:\n{e}")

    # ============================================================
    # IDEA 11: GRÁFICOS
    # ============================================================
    def open_charts(self):
        if not self.sale_case:
            messagebox.showwarning("Gráficos", "SaleCase no disponible.")
            return
        from presentation.views.widgets import ChartsWindow
        ChartsWindow(self, self.sale_case)

    # ============================================================
    # IDEA 16: ALERTAS DE VENCIMIENTO
    # ============================================================
    def open_expiry_alerts(self):
        ExpiryAlertsWindow(self, self.product_case, on_change=self.refresh)

    # ============================================================
    # IDEA 28: HISTORIAL DE PRECIOS GLOBAL
    # ============================================================
    def open_price_history_global(self):
        PriceHistoryWindow(self, self.product_case)

    # ============================================================
    # DETALLE
    # ============================================================
    def open_detail_dialog(self):
        sel = self.tree.selection()
        if len(sel) != 1:
            messagebox.showinfo("Detalle", "Selecciona un producto.")
            return
        pid = int(sel[0])
        prod = self.product_case.get_product(pid)
        if not prod:
            return
        ProductDetailDialog(self, self.product_case, prod,
                            sale_case=self.sale_case, on_change=self.refresh)


# ================================================================
# DIALOGO DE PRODUCTO (FORMULARIO)
# ================================================================
class ProductFormDialog(tk.Toplevel):
    def __init__(self, master, product_case, product=None, on_save=None):
        super().__init__(master)
        self.product_case = product_case
        self.product = product
        self.on_save = on_save

        self.title("Editar producto" if product else "Agregar producto")
        self.geometry("560x720")
        self.resizable(False, True)
        self.transient(master)
        self.grab_set()

        self._build()

        if product:
            self._load(product)
        else:
            self._try_load_draft()

    def _build(self):
        cont = tk.Frame(self, padx=15, pady=15)
        cont.pack(fill="both", expand=True)

        def row(label, widget_builder, hint=None):
            f = tk.Frame(cont)
            f.pack(fill="x", pady=4)
            tk.Label(f, text=label, width=18, anchor="w",
                     font=("Segoe UI", 9, "bold")).pack(side="left")
            widget_builder(f)
            if hint:
                tk.Label(cont, text=hint, fg="#666",
                         font=("Segoe UI", 8, "italic")).pack(anchor="w", padx=(140, 0))

        # Nombre
        self.var_name = tk.StringVar()
        row("Nombre*", lambda f: tk.Entry(f, textvariable=self.var_name,
                                          font=("Segoe UI", 10), width=30).pack(side="left"))

        # Código de barras
        self.var_barcode = tk.StringVar()
        row("Código de barras", lambda f: tk.Entry(f, textvariable=self.var_barcode,
                                                    font=("Segoe UI", 10), width=30).pack(side="left"))

        # Grupo
        self.var_group = tk.StringVar()
        row("Grupo", lambda f: tk.Entry(f, textvariable=self.var_group,
                                        font=("Segoe UI", 10), width=30).pack(side="left"))

        # ============ MODO PAQUETE (idea 25) ============
        self.var_is_package = tk.IntVar(value=0)
        pkg_frame = tk.LabelFrame(cont, text="📦 Modo Paquete / Caja",
                                  font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        pkg_frame.pack(fill="x", pady=8)

        tk.Checkbutton(pkg_frame, text="Viene en paquete/caja",
                       variable=self.var_is_package,
                       command=self._toggle_package,
                       font=("Segoe UI", 9)).pack(anchor="w")

        pkg_body = tk.Frame(pkg_frame)
        pkg_body.pack(fill="x", pady=(4, 0))
        self.pkg_body = pkg_body

        def pkg_row(label, var, width=12):
            f = tk.Frame(pkg_body)
            f.pack(fill="x", pady=2)
            tk.Label(f, text=label, width=22, anchor="w",
                     font=("Segoe UI", 9)).pack(side="left")
            tk.Entry(f, textvariable=var, width=width,
                     font=("Segoe UI", 9)).pack(side="left")

        self.var_pkg_cost = tk.StringVar(value="0")
        self.var_pkg_units = tk.StringVar(value="0")
        self.var_pkg_qty = tk.StringVar(value="1")
        self.var_cost_unit = tk.StringVar(value="0")
        self.var_stock_total = tk.StringVar(value="0")

        pkg_row("Costo del paquete:", self.var_pkg_cost)
        pkg_row("Unidades por paquete:", self.var_pkg_units)
        pkg_row("Cantidad de paquetes:", self.var_pkg_qty)

        tk.Frame(pkg_body, height=1, bg="#ccc").pack(fill="x", pady=4)

        f_costo = tk.Frame(pkg_body); f_costo.pack(fill="x", pady=2)
        tk.Label(f_costo, text="Costo unitario:", width=22, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(f_costo, textvariable=self.var_cost_unit,
                 font=("Segoe UI", 10, "bold"), fg="#00695c").pack(side="left")

        f_stock = tk.Frame(pkg_body); f_stock.pack(fill="x", pady=2)
        tk.Label(f_stock, text="Stock total:", width=22, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        tk.Label(f_stock, textvariable=self.var_stock_total,
                 font=("Segoe UI", 10, "bold"), fg="#1565c0").pack(side="left")

        # Trazabilidad de cálculos
        for v in (self.var_pkg_cost, self.var_pkg_units, self.var_pkg_qty,
                  self.var_margin if hasattr(self, "var_margin") else self.var_pkg_cost):
            try:
                v.trace_add("write", lambda *a: self._recalc_package())
            except Exception:
                pass

        # Sugerencia inteligente (idea 27)
        self.sugerencia_frame = tk.Frame(cont, bg="#fff8e1",
                                         highlightthickness=1,
                                         highlightbackground="#ffc107")
        self.sugerencia_label = tk.Label(
            self.sugerencia_frame, text="", bg="#fff8e1",
            font=("Segoe UI", 9), justify="left", wraplength=460)
        self.sugerencia_label.pack(side="left", padx=8, pady=6)
        self.btn_sugerencia = tk.Button(
            self.sugerencia_frame, text="Usar sugerencia",
            command=self._apply_suggestion, bg="#ffc107", relief="flat",
            font=("Segoe UI", 8, "bold"))
        self.btn_sugerencia.pack(side="right", padx=8, pady=6)
        self._sugerencia_data = None

        self.var_name.trace_add("write", lambda *a: self._check_suggestion())
        # No empaquetar todavía; se muestra si hay sugerencia

        # ============ COSTO Y MARGEN ============
        margin_frame = tk.Frame(cont)
        margin_frame.pack(fill="x", pady=4)
        tk.Label(margin_frame, text="Costo real:", width=18, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_cost = tk.StringVar(value="0")
        tk.Entry(margin_frame, textvariable=self.var_cost, width=15,
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Label(margin_frame, text="  % Ganancia:", width=12, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_margin = tk.StringVar(value="20")
        tk.Entry(margin_frame, textvariable=self.var_margin, width=8,
                 font=("Segoe UI", 9)).pack(side="left")

        self.var_cost.trace_add("write", lambda *a: self._recalc_price())
        self.var_margin.trace_add("write", lambda *a: self._recalc_price())

        # ============ PRECIO ============
        price_frame = tk.Frame(cont)
        price_frame.pack(fill="x", pady=4)
        tk.Label(price_frame, text="Precio venta:", width=18, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_price = tk.StringVar(value="0")
        tk.Entry(price_frame, textvariable=self.var_price, width=15,
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Button(price_frame, text="↻ Recalcular", command=self._recalc_price,
                  bg="#2196F3", fg="white", relief="flat",
                  font=("Segoe UI", 8)).pack(side="left", padx=6)

        # ============ REDONDEO (idea 26) ============
        red_frame = tk.LabelFrame(cont, text="🎯 Redondeo de precio",
                                  font=("Segoe UI", 9, "bold"), padx=8, pady=6)
        red_frame.pack(fill="x", pady=8)

        self.var_round_enabled = tk.IntVar(value=0)
        tk.Checkbutton(red_frame, text="Redondear precio final",
                       variable=self.var_round_enabled,
                       command=self._toggle_round,
                       font=("Segoe UI", 9)).pack(anchor="w")

        self.round_body = tk.Frame(red_frame)
        self.round_body.pack(fill="x", pady=(4, 0))

        f_round = tk.Frame(self.round_body)
        f_round.pack(fill="x", pady=2)
        tk.Label(f_round, text="Redondear al:", width=18, anchor="w",
                 font=("Segoe UI", 9)).pack(side="left")

        self.var_round_to = tk.StringVar(value="100")
        self.cmb_round = ttk.Combobox(
            f_round, textvariable=self.var_round_to, width=10, state="readonly",
            values=["10", "50", "100", "500", "1000"])
        self.cmb_round.pack(side="left")
        self.cmb_round.bind("<<ComboboxSelected>>", lambda e: self._recalc_price())

        # Precio redondeado resultante
        f_result = tk.Frame(self.round_body)
        f_result.pack(fill="x", pady=4)
        tk.Label(f_result, text="Precio redondeado:", width=18, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_rounded = tk.StringVar(value="0")
        tk.Entry(f_result, textvariable=self.var_rounded, width=15,
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Button(f_result, text="Calcular", command=self._recalc_rounded,
                  bg="#FF9800", fg="white", relief="flat",
                  font=("Segoe UI", 8)).pack(side="left", padx=6)

        # ============ STOCK Y UNIDAD ============
        stock_frame = tk.Frame(cont)
        stock_frame.pack(fill="x", pady=4)
        tk.Label(stock_frame, text="Stock:", width=18, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_stock = tk.StringVar(value="0")
        self.entry_stock = tk.Entry(stock_frame, textvariable=self.var_stock, width=15,
                                     font=("Segoe UI", 9))
        self.entry_stock.pack(side="left")

        tk.Label(stock_frame, text="  Unidad:", width=10, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_unit = tk.StringVar(value="unidad")
        ttk.Combobox(stock_frame, textvariable=self.var_unit, width=10,
                     values=["unidad", "kg", "g", "lt", "ml", "caja", "paquete"])\
            .pack(side="left")

        # ============ VENCIMIENTO (idea 16) ============
        exp_frame = tk.Frame(cont)
        exp_frame.pack(fill="x", pady=4)
        tk.Label(exp_frame, text="Fecha vencimiento:", width=18, anchor="w",
                 font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_expiry = tk.StringVar(value="")
        tk.Entry(exp_frame, textvariable=self.var_expiry, width=15,
                 font=("Segoe UI", 9)).pack(side="left")
        tk.Label(exp_frame, text="  (YYYY-MM-DD, vacío = sin vencimiento)",
                 fg="#666", font=("Segoe UI", 8, "italic")).pack(side="left")

        # ============ PAUSADO (idea 4) ============
        self.var_paused = tk.IntVar(value=0)
        tk.Checkbutton(cont, text="⏸️ Producto pausado (no aparece en PAGOS)",
                       variable=self.var_paused,
                       font=("Segoe UI", 9)).pack(anchor="w", pady=6)

        # ============ BOTONES ============
        btn_frame = tk.Frame(cont)
        btn_frame.pack(fill="x", pady=(15, 0))
        tk.Button(btn_frame, text="💾 Guardar", command=self.save,
                  bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"),
                  padx=20, pady=8, relief="flat").pack(side="right", padx=5)
        tk.Button(btn_frame, text="❌ Cancelar", command=self.destroy,
                  bg="#f44336", fg="white", font=("Segoe UI", 10, "bold"),
                  padx=20, pady=8, relief="flat").pack(side="right", padx=5)

        self._toggle_package()
        self._toggle_round()

    # ============================================================
    # UTILIDADES DE FORMULARIO
    # ============================================================
    def _toggle_package(self):
        activo = self.var_is_package.get() == 1
        for child in self.pkg_body.winfo_children():
            self._set_state_recursive(child, "normal" if activo else "disabled")
        self.entry_stock.config(state="disabled" if activo else "normal")
        if activo:
            self._recalc_package()

    def _set_state_recursive(self, widget, state):
        try:
            widget.configure(state=state)
        except Exception:
            pass
        for child in widget.winfo_children():
            self._set_state_recursive(child, state)

    def _toggle_round(self):
        activo = self.var_round_enabled.get() == 1
        for child in self.round_body.winfo_children():
            self._set_state_recursive(child, "normal" if activo else "disabled")
        if activo:
            self._recalc_price()

    def _recalc_package(self):
        try:
            pkg_cost = float(self.var_pkg_cost.get() or 0)
            pkg_units = float(self.var_pkg_units.get() or 0)
            pkg_qty = float(self.var_pkg_qty.get() or 1)
            if pkg_units <= 0:
                self.var_cost_unit.set("$0")
                self.var_stock_total.set("0")
                return
            unit_cost = pkg_cost / pkg_units
            total_stock = int(pkg_units * pkg_qty)
            self.var_cost_unit.set(f"${unit_cost:,.2f}")
            self.var_stock_total.set(str(total_stock))
            # Actualizar costo y precio sugerido
            self.var_cost.set(f"{unit_cost:.2f}")
        except Exception:
            pass

    def _recalc_price(self):
        try:
            costo = float(self.var_cost.get() or 0)
            margen = float(self.var_margin.get() or 0)
            precio = costo * (1 + margen / 100.0)
            self.var_price.set(f"{precio:.2f}")
            if self.var_round_enabled.get() == 1:
                self._recalc_rounded()
        except Exception:
            pass

    def _recalc_rounded(self):
        try:
            precio = float(self.var_price.get() or 0)
            red_to = float(self.var_round_to.get() or 100)
            if red_to <= 0:
                self.var_rounded.set(f"{precio:.2f}")
                return
            redondeado = round(precio / red_to) * red_to
            self.var_rounded.set(f"{redondeado:.2f}")
        except Exception:
            pass

    # ============================================================
    # SUGERENCIA INTELIGENTE (idea 27)
    # ============================================================
    def _check_suggestion(self):
        if self.product:  # no sugerir al editar
            return
        nombre = self.var_name.get().strip()
        if len(nombre) < 3:
            self.sugerencia_frame.pack_forget()
            self._sugerencia_data = None
            return
        data = self.product_case.find_last_package_for_name(nombre)
        if not data:
            self.sugerencia_frame.pack_forget()
            self._sugerencia_data = None
            return
        self._sugerencia_data = data
        txt = (f"💡 La última vez compraste «{data['name']}» a "
               f"${data['package_cost']:,.0f} por paquete de "
               f"{data['package_units']} unidades. ¿Quieres usar esos datos?")
        self.sugerencia_label.config(text=txt)
        self.sugerencia_frame.pack(fill="x", pady=6, before=self.sugerencia_frame.master.winfo_children()[-1])

    def _apply_suggestion(self):
        if not self._sugerencia_data:
            return
        d = self._sugerencia_data
        self.var_is_package.set(1)
        self.var_pkg_cost.set(str(d["package_cost"]))
        self.var_pkg_units.set(str(d["package_units"]))
        self.var_pkg_qty.set("1")
        self._toggle_package()
        self._recalc_package()
        self.sugerencia_frame.pack_forget()

    # ============================================================
    # CARGA Y GUARDADO
    # ============================================================
    def _load(self, p):
        self.var_name.set(p.name or "")
        self.var_barcode.set(p.barcode or "")
        self.var_group.set(p.group_name or "")
        self.var_cost.set(f"{p.cost or 0:.2f}")
        self.var_margin.set(f"{p.margin_percent or 0:.2f}")
        self.var_price.set(f"{p.price or 0:.2f}")
        self.var_rounded.set(f"{p.rounded_price or p.price or 0:.2f}")
        self.var_round_enabled.set(1 if p.round_enabled else 0)
        self.var_round_to.set(str(p.round_to or 100))
        self.var_stock.set(str(p.stock or 0))
        self.var_unit.set(p.unit or "unidad")
        self.var_paused.set(1 if p.paused else 0)
        self.var_expiry.set(p.expiry_date or "")
        self.var_is_package.set(1 if p.is_package else 0)
        self.var_pkg_cost.set(f"{p.package_cost or 0:.2f}")
        self.var_pkg_units.set(str(p.package_units or 0))
        self._toggle_package()
        self._toggle_round()

    def _try_load_draft(self):
        try:
            data, when = self.product_case.load_product_draft()
            if not data:
                return
            if not messagebox.askyesno(
                    "Borrador",
                    f"Hay un borrador guardado el {when}.\n¿Deseas recuperarlo?"):
                return
            self.var_name.set(data.get("name", ""))
            self.var_barcode.set(data.get("barcode", ""))
            self.var_group.set(data.get("group", ""))
            self.var_cost.set(str(data.get("cost", "0")))
            self.var_margin.set(str(data.get("margin", "20")))
            self.var_price.set(str(data.get("price", "0")))
            self.var_rounded.set(str(data.get("rounded", "0")))
            self.var_round_enabled.set(int(data.get("round_enabled", 0)))
            self.var_round_to.set(str(data.get("round_to", "100")))
            self.var_stock.set(str(data.get("stock", "0")))
            self.var_unit.set(data.get("unit", "unidad"))
            self.var_expiry.set(data.get("expiry", ""))
            self.var_is_package.set(int(data.get("is_package", 0)))
            self.var_pkg_cost.set(str(data.get("pkg_cost", "0")))
            self.var_pkg_units.set(str(data.get("pkg_units", "0")))
            self._toggle_package()
            self._toggle_round()
        except Exception:
            pass

    def _save_draft(self):
        try:
            data = {
                "name": self.var_name.get(),
                "barcode": self.var_barcode.get(),
                "group": self.var_group.get(),
                "cost": self.var_cost.get(),
                "margin": self.var_margin.get(),
                "price": self.var_price.get(),
                "rounded": self.var_rounded.get(),
                "round_enabled": self.var_round_enabled.get(),
                "round_to": self.var_round_to.get(),
                "stock": self.var_stock.get(),
                "unit": self.var_unit.get(),
                "expiry": self.var_expiry.get(),
                "is_package": self.var_is_package.get(),
                "pkg_cost": self.var_pkg_cost.get(),
                "pkg_units": self.var_pkg_units.get(),
            }
            self.product_case.save_product_draft(data)
        except Exception:
            pass

    def save(self):
        nombre = self.var_name.get().strip()
        if not nombre:
            messagebox.showwarning("Falta", "El nombre es obligatorio.")
            return
        try:
            precio = float(self.var_price.get() or 0)
            costo = float(self.var_cost.get() or 0)
            margen = float(self.var_margin.get() or 0)
            rounded = float(self.var_rounded.get() or precio)
            round_enabled = self.var_round_enabled.get()
            round_to = int(float(self.var_round_to.get() or 100))
            pkg_cost = float(self.var_pkg_cost.get() or 0)
            pkg_units = int(float(self.var_pkg_units.get() or 0))
            is_package = self.var_is_package.get()
            if is_package:
                stock = int(float(self.var_pkg_qty.get() or 1) * pkg_units)
            else:
                stock = int(float(self.var_stock.get() or 0))
        except ValueError:
            messagebox.showerror("Error", "Revisa los valores numéricos.")
            return

        # Validar fecha
        expiry = self.var_expiry.get().strip()
        if expiry:
            try:
                datetime.strptime(expiry, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Error", "Fecha de vencimiento inválida. Usa YYYY-MM-DD.")
                return

        if self.product:
            self.product_case.update_product(
                self.product.product_id, nombre, self.var_barcode.get().strip(),
                precio, stock,
                unit_type=self.product.unit_type, unit=self.var_unit.get(),
                group_name=self.var_group.get().strip(),
                cost=costo, margin_percent=margen,
                rounded_price=rounded,
                round_enabled=round_enabled, round_to=round_to,
                package_cost=pkg_cost, package_units=pkg_units,
                is_package=is_package,
                paused=self.var_paused.get(),
                expiry_date=expiry,
                register_history=True,
            )
        else:
            self.product_case.add_product(
                nombre, self.var_barcode.get().strip(), precio, stock,
                unit_type="unidad", unit=self.var_unit.get(),
                group_name=self.var_group.get().strip(),
                cost=costo, margin_percent=margen,
                rounded_price=rounded,
                round_enabled=round_enabled, round_to=round_to,
                package_cost=pkg_cost, package_units=pkg_units,
                is_package=is_package,
                paused=self.var_paused.get(),
                expiry_date=expiry,
            )
        self.product_case.clear_product_draft()

        if self.on_save:
            self.on_save()
        self.destroy()


# ================================================================
# VENTANA DE DETALLE DEL PRODUCTO
# ================================================================
class ProductDetailDialog(tk.Toplevel):
    def __init__(self, master, product_case, product, sale_case=None, on_change=None):
        super().__init__(master)
        self.product_case = product_case
        self.product = product
        self.sale_case = sale_case
        self.on_change = on_change

        self.title(f"Detalle: {product.name}")
        self.geometry("640x600")
        self.transient(master)
        self.grab_set()

        cont = tk.Frame(self, padx=15, pady=15)
        cont.pack(fill="both", expand=True)

        # Info
        info = [
            ("ID", product.product_id),
            ("Nombre", product.name),
            ("Código", product.barcode or "—"),
            ("Grupo", product.group_name or "—"),
            ("Precio real", f"${product.price:,.2f}"),
            ("Precio redondeado", f"${(product.rounded_price or product.price):,.2f}"),
            ("Costo", f"${(product.cost or 0):,.2f}"),
            ("Margen", f"{product.margin_percent or 0:.2f}%"),
            ("Stock", product.stock),
            ("Unidad", product.unit or "unidad"),
            ("Vencimiento", product.expiry_date or "—"),
            ("Pausado", "Sí" if product.paused else "No"),
        ]
        if product.is_package:
            info.append(("Costo paquete", f"${(product.package_cost or 0):,.2f}"))
            info.append(("Unidades paquete", product.package_units))
        info.append(("Creado", product.created_at or "—"))
        info.append(("Actualizado", product.updated_at or "—"))

        for i, (k, v) in enumerate(info):
            tk.Label(cont, text=f"{k}:", font=("Segoe UI", 9, "bold"),
                     anchor="w", width=18).grid(row=i, column=0, sticky="w", pady=2)
            tk.Label(cont, text=str(v), font=("Segoe UI", 9),
                     anchor="w").grid(row=i, column=1, sticky="w", pady=2)

        # Aviso de devoluciones (idea 10)
        if self.sale_case:
            veces = self.sale_case.get_product_return_count(
                product.product_id, product.name)
            if veces > 0:
                tk.Label(cont,
                         text=f"⚠️ Este producto se ha devuelto {veces} vez/veces",
                         fg="#c62828", font=("Segoe UI", 9, "bold"))\
                    .grid(row=len(info), column=0, columnspan=2,
                          sticky="w", pady=(10, 0))

        # Botones
        btns = tk.Frame(cont)
        btns.grid(row=len(info) + 3, column=0, columnspan=2, sticky="ew", pady=(20, 0))

        tk.Button(btns, text="📈 Historial de precios",
                  command=self._show_price_history,
                  bg="#795548", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10, pady=6)\
            .pack(side="left", padx=4)
        tk.Button(btns, text="✏️ Editar", command=self._edit,
                  bg="#2196F3", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10, pady=6)\
            .pack(side="left", padx=4)
        tk.Button(btns, text="Cerrar", command=self.destroy,
                  bg="#9E9E9E", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10, pady=6)\
            .pack(side="right", padx=4)

    def _show_price_history(self):
        PriceHistoryWindow(self, self.product_case,
                           product_id=self.product.product_id)

    def _edit(self):
        self.destroy()
        ProductFormDialog(self.master, self.product_case,
                          product=self.product, on_save=self.on_change)


# ================================================================
# VENTANA DE HISTORIAL DE PRECIOS (idea 28)
# ================================================================
class PriceHistoryWindow(tk.Toplevel):
    def __init__(self, master, product_case, product_id=None):
        super().__init__(master)
        self.product_case = product_case
        self.product_id = product_id

        self.title("Historial de precios")
        self.geometry("900x600")
        self.transient(master)

        # Filtros
        top = tk.Frame(self, padx=10, pady=10)
        top.pack(fill="x")

        tk.Label(top, text="Desde:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_from = tk.StringVar()
        tk.Entry(top, textvariable=self.var_from, width=12).pack(side="left", padx=4)

        tk.Label(top, text="Hasta:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_to = tk.StringVar()
        tk.Entry(top, textvariable=self.var_to, width=12).pack(side="left", padx=4)

        tk.Button(top, text="🔍 Filtrar", command=self.load,
                  bg="#2196F3", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10).pack(side="left", padx=8)

        tk.Button(top, text="📄 Exportar TXT", command=lambda: self.export("txt"),
                  bg="#607D8B", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10).pack(side="right", padx=4)
        tk.Button(top, text="📊 Exportar Excel", command=lambda: self.export("xlsx"),
                  bg="#4CAF50", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10).pack(side="right", padx=4)
        tk.Button(top, text="📕 Exportar PDF", command=lambda: self.export("pdf"),
                  bg="#f44336", fg="white", relief="flat",
                  font=("Segoe UI", 9, "bold"), padx=10).pack(side="right", padx=4)

        # Tabla
        cols = ("date", "product", "barcode", "old", "new", "old_r", "new_r")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for c, t, w in [
            ("date", "Fecha", 140), ("product", "Producto", 220),
            ("barcode", "Código", 120), ("old", "Precio ant.", 100),
            ("new", "Precio nuevo", 100), ("old_r", "Redond. ant.", 100),
            ("new_r", "Redond. nuevo", 100),
        ]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.data = []
        self.load()

    def load(self):
        self.tree.delete(*self.tree.get_children())
        d_from = self.var_from.get().strip() or None
        d_to = self.var_to.get().strip() or None

        if self.product_id:
            self.data = self.product_case.get_price_history(self.product_id)
        else:
            self.data = self.product_case.get_all_price_history(d_from, d_to)

        for r in self.data:
            self.tree.insert("", "end", values=(
                r["date"],
                r.get("product_name", "—") if not self.product_id else "—",
                r.get("product_barcode", "—") if not self.product_id else "—",
                f"${r['old_price']:,.2f}",
                f"${r['new_price']:,.2f}",
                f"${r.get('old_rounded_price', 0):,.2f}",
                f"${r.get('new_rounded_price', 0):,.2f}",
            ))

    def export(self, fmt):
        if not self.data:
            messagebox.showinfo("Exportar", "No hay datos.")
            return
        ext_map = {"txt": ".txt", "xlsx": ".xlsx", "pdf": ".pdf"}
        ruta = filedialog.asksaveasfilename(
            defaultextension=ext_map[fmt],
            filetypes=[(fmt.upper(), f"*{ext_map[fmt]}")],
            initialfile=f"historial_precios_{datetime.now().strftime('%Y%m%d_%H%M')}{ext_map[fmt]}")
        if not ruta:
            return
        try:
            if fmt == "txt":
                self._export_txt(ruta)
            elif fmt == "xlsx":
                self._export_xlsx(ruta)
            elif fmt == "pdf":
                self._export_pdf(ruta)
            messagebox.showinfo("Exportar", f"Archivo generado:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar:\n{e}")

    def _export_txt(self, ruta):
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("HISTORIAL DE PRECIOS\n")
            f.write("=" * 90 + "\n")
            f.write(f"{'Fecha':<20}{'Producto':<30}{'Ant.':>12}{'Nuevo':>12}{'Red.Ant':>12}{'Red.Nuevo':>12}\n")
            f.write("-" * 90 + "\n")
            for r in self.data:
                f.write(f"{r['date']:<20}{r.get('product_name','')[:28]:<30}"
                        f"{r['old_price']:>12,.0f}{r['new_price']:>12,.0f}"
                        f"{r.get('old_rounded_price',0):>12,.0f}{r.get('new_rounded_price',0):>12,.0f}\n")

    def _export_xlsx(self, ruta):
        try:
            from openpyxl import Workbook
        except ImportError:
            raise Exception("Instala openpyxl: pip install openpyxl")
        wb = Workbook()
        ws = wb.active
        ws.title = "Historial"
        ws.append(["Fecha", "Producto", "Código", "Precio ant.", "Precio nuevo",
                   "Redondeado ant.", "Redondeado nuevo"])
        for r in self.data:
            ws.append([r["date"], r.get("product_name", ""), r.get("product_barcode", ""),
                       r["old_price"], r["new_price"],
                       r.get("old_rounded_price", 0), r.get("new_rounded_price", 0)])
        wb.save(ruta)

    def _export_pdf(self, ruta):
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
        except ImportError:
            raise Exception("Instala reportlab: pip install reportlab")

        doc = SimpleDocTemplate(ruta, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = [Paragraph("Historial de precios", styles["Title"])]

        data = [["Fecha", "Producto", "Ant.", "Nuevo", "Red. ant.", "Red. nuevo"]]
        for r in self.data:
            data.append([
                r["date"], r.get("product_name", "")[:30],
                f"${r['old_price']:,.0f}", f"${r['new_price']:,.0f}",
                f"${r.get('old_rounded_price', 0):,.0f}",
                f"${r.get('new_rounded_price', 0):,.0f}",
            ])

        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4CAF50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(t)
        doc.build(elements)


# ================================================================
# VENTANA DE ALERTAS DE VENCIMIENTO (idea 16)
# ================================================================
class ExpiryAlertsWindow(tk.Toplevel):
    def __init__(self, master, product_case, on_change=None):
        super().__init__(master)
        self.product_case = product_case
        self.on_change = on_change

        self.title("Alertas de vencimiento")
        self.geometry("800x600")
        self.transient(master)

        # Configuración
        cfg = self.product_case.get_expiry_settings()

        conf = tk.LabelFrame(self, text="⚙️ Configuración de alertas",
                             font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        conf.pack(fill="x", padx=10, pady=10)

        f1 = tk.Frame(conf); f1.pack(fill="x", pady=2)
        tk.Label(f1, text="Aviso 1 (días):", width=18, anchor="w").pack(side="left")
        self.var_d1 = tk.StringVar(value=str(cfg["warn_days_1"]))
        tk.Entry(f1, textvariable=self.var_d1, width=6).pack(side="left")
        tk.Label(f1, text="  Aviso 2 (días):").pack(side="left")
        self.var_d2 = tk.StringVar(value=str(cfg["warn_days_2"]))
        tk.Entry(f1, textvariable=self.var_d2, width=6).pack(side="left")

        f2 = tk.Frame(conf); f2.pack(fill="x", pady=2)
        tk.Label(f2, text="Oferta cuando falten (días):", width=24, anchor="w").pack(side="left")
        self.var_do = tk.StringVar(value=str(cfg["offer_days"]))
        tk.Entry(f2, textvariable=self.var_do, width=6).pack(side="left")
        tk.Label(f2, text="  Descuento (%):").pack(side="left")
        self.var_disc = tk.StringVar(value=str(cfg["offer_discount"]))
        tk.Entry(f2, textvariable=self.var_disc, width=6).pack(side="left")

        tk.Button(conf, text="💾 Guardar configuración", command=self.save_cfg,
                  bg="#4CAF50", fg="white", relief="flat", padx=10, pady=4,
                  font=("Segoe UI", 9, "bold")).pack(anchor="e", pady=(6, 0))

        # Filtro rápido
        ff = tk.Frame(self)
        ff.pack(fill="x", padx=10)
        tk.Label(ff, text="Mostrar:", font=("Segoe UI", 9, "bold")).pack(side="left")
        self.var_filter = tk.StringVar(value="Todos")
        ttk.Combobox(ff, textvariable=self.var_filter, state="readonly",
                     values=["Todos", "Vencidos", "En oferta", "Aviso 7d", "Aviso 15d"],
                     width=15).pack(side="left", padx=6)
        self.var_filter.trace_add("write", lambda *a: self.load())
        tk.Button(ff, text="🔄 Refrescar", command=self.load,
                  bg="#607D8B", fg="white", relief="flat", padx=10)\
            .pack(side="right")

        # Tabla
        cols = ("status", "name", "stock", "expiry", "days", "action")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for c, t, w in [("status", "Estado", 100), ("name", "Producto", 220),
                        ("stock", "Stock", 70), ("expiry", "Vence", 100),
                        ("days", "Días", 70), ("action", "Acción", 200)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree.bind("<Double-1>", self._double_click)

        tk.Button(self, text="🏷️ Aplicar oferta al seleccionado",
                  command=self.apply_offer, bg="#FF9800", fg="white",
                  relief="flat", padx=12, pady=6,
                  font=("Segoe UI", 9, "bold")).pack(pady=(0, 10))

        self.load()

    def save_cfg(self):
        try:
            self.product_case.set_expiry_settings(
                int(self.var_d1.get()), int(self.var_d2.get()),
                int(self.var_do.get()), float(self.var_disc.get()))
            messagebox.showinfo("OK", "Configuración guardada.")
            self.load()
        except ValueError:
            messagebox.showerror("Error", "Valores inválidos.")

    def load(self):
        self.tree.delete(*self.tree.get_children())
        data = self.product_case.get_expiring_products()
        filtro = self.var_filter.get()

        for item in data:
            p = item["product"]
            s = item["status"]
            d = item["days_left"]

            if filtro == "Vencidos" and s != "expired":
                continue
            if filtro == "En oferta" and s != "offer":
                continue
            if filtro == "Aviso 7d" and s != "warn2":
                continue
            if filtro == "Aviso 15d" and s != "warn1":
                continue

            if s == "expired":
                estado = f"⚠️ VENCIDO"
                accion = "Retirar / revisar"
            elif s == "offer":
                estado = "🏷️ En oferta"
                accion = "Ya se aplicó descuento"
            elif s == "warn2":
                estado = "⏰ Aviso 7d"
                accion = "Próximo a vencer"
            else:
                estado = "⏳ Aviso 15d"
                accion = "Monitorear"

            self.tree.insert("", "end", iid=str(p.product_id), values=(
                estado, p.name, p.stock, p.expiry_date, d, accion))

    def apply_offer(self):
        sel = self.tree.selection()
        if not sel:
            return
        if not messagebox.askyesno("Oferta",
                                   f"¿Aplicar descuento a {len(sel)} producto(s)?"):
            return
        for sid in sel:
            ok, msg = self.product_case.apply_offer_discount(int(sid))
        self.load()
        if self.on_change:
            self.on_change()

    def _double_click(self, event):
        sel = self.tree.selection()
        if sel:
            self.apply_offer()
