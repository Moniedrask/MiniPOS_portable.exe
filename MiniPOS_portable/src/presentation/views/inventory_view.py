import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
from ttkbootstrap.dialogs import Messagebox


def apply_titlebar_theme(window, is_dark):
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        value = ctypes.c_int(1 if is_dark else 0)
        for attr in (20, 19):
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass


class InventoryView(ttk.Frame):
    """Módulo de INVENTARIO como Frame embebido."""

    def __init__(self, parent, product_use_case, get_theme_func):
        super().__init__(parent, bootstyle="dark")
        self.product_use_case = product_use_case
        self.get_theme = get_theme_func

        self.create_widgets()
        self.load_products()
        self.after(300, lambda: self.scan_entry.focus_set())

    def create_widgets(self):
        # --- BARRA DE ESCANEO ---
        scan_frame = ttk.Frame(self, bootstyle="dark")
        scan_frame.pack(padx=10, pady=(15, 5), fill="x")
        ttk.Label(scan_frame, text="📷 Escanear código:",
                  font=("Arial", 11, "bold"), bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(scan_frame, textvariable=self.scan_var, width=35, font=("Arial", 11))
        self.scan_entry.pack(side="left", padx=5)
        self.scan_entry.bind("<Return>", self.lookup_barcode)
        ttk.Button(scan_frame, text="🔍 Buscar Código", command=lambda: self.lookup_barcode(None)).pack(side="left", padx=5)

        # --- BÚSQUEDA MANUAL ---
        search_frame = ttk.Frame(self, bootstyle="dark")
        search_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(search_frame, text="🔍 Búsqueda manual:",
                  bootstyle="inverse-dark").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_products)

        # --- TABLA ---
        frame = ttk.Frame(self, bootstyle="dark")
        frame.pack(padx=10, pady=5, fill="both", expand=True)
        self.tree = ttk.Treeview(frame,
                                 columns=("ID", "Name", "Barcode", "Price", "Unit", "Stock"),
                                 show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Producto")
        self.tree.heading("Barcode", text="Código de Barras / QR")
        self.tree.heading("Price", text="Precio")
        self.tree.heading("Unit", text="Unidad")
        self.tree.heading("Stock", text="Stock")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=250)
        self.tree.column("Barcode", width=170)
        self.tree.column("Price", width=100, anchor="e")
        self.tree.column("Unit", width=80, anchor="center")
        self.tree.column("Stock", width=80, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.view_product_popup)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # --- BOTONES ---
        btn_frame = ttk.Frame(self, bootstyle="dark")
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="➕ Agregar Producto (F2)",
                   command=self.add_product_popup).pack(side="left", padx=5)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if not item: return
        self.tree.selection_set(item); self.tree.focus(item)
        parent = self.winfo_toplevel()
        style = ttk.Style()
        menu = tk.Menu(parent, tearoff=0, bg=style.colors.bg, fg=style.colors.fg,
                       activebackground=style.colors.selectbg, activeforeground=style.colors.selectfg,
                       bd=1, relief="solid")
        menu.add_command(label="👁️  Ver detalle", command=lambda: self.view_product_popup(None))
        menu.add_command(label="✏️  Editar producto", command=lambda: self.open_edit_from_item(item))
        menu.add_separator()
        menu.add_command(label="🗑️  Eliminar producto", command=lambda: self.confirm_delete(item))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def view_product_popup(self, event=None):
        sel = self.tree.selection()
        if not sel: return
        vals = self.tree.item(sel[0], 'values')
        pid, name, barcode, price, unit, stock = vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]

        popup = Toplevel(self)
        popup.title("Detalle del Producto")
        popup.geometry("420x470")
        popup.transient(self.winfo_toplevel()); popup.grab_set()

        header = ttk.Frame(popup, bootstyle="dark"); header.pack(fill="x", pady=10)
        ttk.Label(header, text="📋 DETALLE DEL PRODUCTO", font=("Arial", 12, "bold"),
                  bootstyle="inverse-dark").pack()
        info = ttk.Frame(popup, bootstyle="dark"); info.pack(fill="both", expand=True, padx=25, pady=15)
        for t, f in [(f"ID: {pid}", ("Arial", 10)),
                     (f"Nombre: {name}", ("Arial", 12, "bold")),
                     (f"Código: {barcode}", ("Arial", 10)),
                     (f"Precio: {price}", ("Arial", 12, "bold")),
                     (f"Unidad: {unit}", ("Arial", 11)),
                     (f"Stock: {stock}", ("Arial", 11))]:
            ttk.Label(info, text=t, font=f, bootstyle="inverse-dark").pack(anchor="w", pady=4)

        ttk.Separator(popup, orient="horizontal").pack(fill="x", padx=20, pady=5)
        bf = ttk.Frame(popup, bootstyle="dark"); bf.pack(pady=15)
        ttk.Button(bf, text="✏️ Editar",
                   command=lambda: [popup.destroy(), self.open_edit_from_item(sel[0])]).pack(side="left", padx=5)
        ttk.Button(bf, text="Cerrar", command=popup.destroy).pack(side="left", padx=5)
        ttk.Button(bf, text="🗑", command=lambda: [popup.destroy(), self.confirm_delete(sel[0])],
                   bootstyle="danger", width=3).pack(side="left", padx=15)
        popup.after(200, lambda: apply_titlebar_theme(popup, self.get_theme() == 'darkly'))

    def confirm_delete(self, item):
        vals = self.tree.item(item, 'values')
        pid, name = vals[0], vals[1]
        if Messagebox.yesno(f"⚠️ ¿ELIMINAR '{name}'?", "Confirmar", parent=self) != "Yes":
            return
        if Messagebox.yesno(f"🚨 ÚLTIMA ADVERTENCIA\n\n¿Realmente eliminar '{name}'?",
                            "Confirmación final", parent=self) != "Yes":
            return
        self.product_use_case.delete_product(pid)
        self.load_products()
        Messagebox.show_info(f"'{name}' eliminado.", "Listo", parent=self)
        self.scan_entry.focus_set()

    def open_edit_from_item(self, item):
        vals = self.tree.item(item, 'values')
        pid = vals[0]; name = vals[1]; barcode = vals[2]
        price = float(vals[3].replace("$", "").replace(".", ""))
        unit = vals[4]
        stock = float(vals[5])
        unit_type = "unidad"
        if unit in ("kg", "gr", "mg"): unit_type = "peso"
        elif unit in ("Lt", "ml"): unit_type = "volumen"
        self.open_product_form("Editar Producto", pid, name, barcode, price, stock, unit_type, unit)

    def add_product_popup(self, barcode_prefill="", auto_select=False):
        self.open_product_form("Agregar Producto", None, "", barcode_prefill, 0, 0,
                               "unidad", "unidad", auto_select)

    # ============ FORMULARIO COMPARTIDO (Agregar / Editar) ============
    def open_product_form(self, title, product_id, name, barcode, price, stock,
                          unit_type, unit, auto_select=False):
        popup = Toplevel(self)
        popup.title(title)
        popup.geometry("400x600")
        popup.transient(self.winfo_toplevel()); popup.grab_set()

        ttk.Label(popup, text="Código de Barras / QR:").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=35); barcode_entry.pack(pady=5)
        if barcode: barcode_entry.insert(0, barcode)

        ttk.Label(popup, text="Nombre del Producto:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=35); name_entry.pack(pady=5)
        if name: name_entry.insert(0, name)

        # --- TIPO DE VENTA ---
        ttk.Label(popup, text="Tipo de venta:", font=("Arial", 10, "bold")).pack(pady=(10, 3))
        type_var = tk.StringVar(value=unit_type)
        type_frame = ttk.Frame(popup); type_frame.pack()
        for val, txt in [("unidad", "📦 Por unidad"), ("peso", "⚖️ Por peso"), ("volumen", "💧 Por volumen")]:
            ttk.Radiobutton(type_frame, text=txt, variable=type_var, value=val,
                            command=lambda: self._refresh_unit_options(unit_var, unit_combo, type_var)
                            ).pack(side="left", padx=5)

        ttk.Label(popup, text="Unidad de medida:").pack(pady=(10, 3))
        unit_var = tk.StringVar(value=unit)
        unit_combo = ttk.Combobox(popup, textvariable=unit_var, state="readonly", width=15)
        unit_combo.pack(pady=5)
        self._refresh_unit_options(unit_var, unit_combo, type_var)

        ttk.Label(popup, text="Precio por unidad:").pack(pady=5)
        price_entry = ttk.Entry(popup, width=35)
        price_entry.pack(pady=5)
        if price: price_entry.insert(0, str(int(price)))

        ttk.Label(popup, text="Stock (acepta decimales para peso/volumen):").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=35)
        stock_entry.pack(pady=5)
        if stock: stock_entry.insert(0, f"{stock:g}")

        if not product_id and barcode:
            name_entry.focus_set()
        elif product_id:
            name_entry.focus_set()
        else:
            barcode_entry.focus_set()

        def save():
            n = name_entry.get().strip()
            b = barcode_entry.get().strip()
            if not n:
                Messagebox.show_error("El nombre es obligatorio", "Error", parent=popup); return
            try:
                pl = price_entry.get().replace("$", "").replace(".", "").replace(",", ".").strip()
                p = float(pl) if pl else 0.0
                ss = stock_entry.get().strip().replace(",", ".")
                s = float(ss) if ss else 0.0
            except ValueError:
                Messagebox.show_error("Precio/Stock inválidos", "Error", parent=popup); return

            if product_id:
                self.product_use_case.update_product(product_id, n, b, p, s, type_var.get(), unit_var.get())
            else:
                self.product_use_case.add_product(n, b, p, s, type_var.get(), unit_var.get())
            self.load_products()
            popup.destroy()
            self.scan_entry.focus_set()
            if auto_select and b:
                for it in self.tree.get_children():
                    if str(self.tree.item(it, 'values')[2]).strip() == b:
                        self.tree.selection_set(it); self.tree.focus(it); self.tree.see(it); break

        ttk.Button(popup, text="Guardar", command=save, bootstyle="success").pack(pady=20)
        popup.after(200, lambda: apply_titlebar_theme(popup, self.get_theme() == 'darkly'))

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

    # ============ ESCANEO / BÚSQUEDA ============
    def lookup_barcode(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo: return
        enc = None
        for p in self.product_use_case.list_products():
            if str(p.barcode).strip() == codigo:
                enc = p; break
        if enc:
            self.search_var.set("")
            self.load_products()
            for it in self.tree.get_children():
                if str(self.tree.item(it, 'values')[2]).strip() == codigo:
                    self.tree.selection_set(it); self.tree.focus(it); self.tree.see(it); break
            Messagebox.show_info(f"✅ {enc.name}\nPrecio: ${enc.price:,.0f}\nStock: {enc.stock:g} {enc.unit}".replace(",", "."),
                                 "Encontrado", parent=self)
        else:
            r = Messagebox.yesno(f"⚠️ '{codigo}' NO está registrado.\n\n¿Agregarlo?",
                                 "No encontrado", parent=self)
            if r == "Yes":
                self.add_product_popup(barcode_prefill=codigo, auto_select=True)
        self.scan_var.set(""); self.scan_entry.focus_set()

    def filter_products(self, event=None):
        q = self.search_var.get().lower()
        for it in self.tree.get_children(): self.tree.delete(it)
        for p in self.product_use_case.list_products():
            if q in str(p.name).lower() or q in str(p.barcode).lower():
                self._insert_product_row(p)

    def load_products(self):
        for it in self.tree.get_children(): self.tree.delete(it)
        for p in self.product_use_case.list_products():
            self._insert_product_row(p)

    def _insert_product_row(self, p):
        precio = f"${p.price:,.0f}".replace(",", ".")
        stock_txt = f"{p.stock:g}"
        self.tree.insert("", "end", values=(p.product_id, p.name, p.barcode, precio, p.unit, stock_txt))