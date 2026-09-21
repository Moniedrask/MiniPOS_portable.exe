import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap import Toplevel
from presentation.views.widgets import (
    apply_titlebar_theme, center_window, show_popup_smooth,
    get_menu_font, AutoCompleteEntry, MD, TreeviewTooltip,
    popup_is_open
)


class InventoryView(ttk.Frame):
    def __init__(self, parent, product_use_case, get_theme_func):
        super().__init__(parent, bootstyle="dark")
        self.product_use_case = product_use_case
        self.get_theme = get_theme_func
        self.sort_col = None
        self.sort_reverse = False
        self.filtered_products = []
        self.tooltip = None

        self.create_widgets()
        self.load_products()
        self.after(300, lambda: self.scan_entry.focus_set())
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

    def create_widgets(self):
        scan_frame = ttk.Frame(self, bootstyle="dark")
        scan_frame.pack(padx=10, pady=(15, 5), fill="x")
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
        search_frame.pack(padx=10, pady=5, fill="x")
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

        frame = ttk.Frame(self, bootstyle="dark")
        frame.pack(padx=10, pady=5, fill="both", expand=True)

        self.columns = [
            ("ID", "ID", 50, "center"),
            ("Name", "Producto", 220, "w"),
            ("Barcode", "Código de Barras", 150, "w"),
            ("Price", "Precio", 90, "e"),
            ("Unit", "Unidad", 70, "center"),
            ("Stock", "Stock", 70, "center"),
            ("Created", "Creado", 140, "center"),
            ("Updated", "Actualizado", 140, "center"),
        ]
        self.tree = ttk.Treeview(frame, columns=[c[0] for c in self.columns], show='headings')
        for key, label, w, anchor in self.columns:
            self.tree.heading(key, text=label + "  ⇅",
                              command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=w, anchor=anchor)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.view_product_popup)
        self.tree.bind("<Button-3>", self.show_context_menu)

        self.tooltip = TreeviewTooltip(self.tree, font_size=11)

        btn_frame = ttk.Frame(self, bootstyle="dark")
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="➕ Agregar Producto (F2)",
                   command=self.add_product_popup,
                   style="DarkGreen.TButton").pack(side="left", padx=5)

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
                "Barcode": lambda p: (p.barcode or ""),
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

    def load_products(self):
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
                if q in (p.name or "").lower() or q in str(p.barcode or "").lower()]
        self._render_products(self.filtered_products)

    def _insert_product_row(self, p):
        precio = f"${p.price:,.0f}".replace(",", ".")
        self.tree.insert("", "end", values=(
            p.product_id, p.name, p.barcode, precio, p.unit,
            f"{p.stock:g}", p.created_at or "-", p.updated_at or "-"))

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
        menu.add_separator()
        menu.add_command(label="🗑️  Eliminar producto", command=lambda: self.confirm_delete(item))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def view_product_popup(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        vals = self.tree.item(sel[0], 'values')
        pid, name, barcode, price, unit, stock = vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]
        created, updated = vals[6], vals[7]

        popup = Toplevel(self)
        popup.title("Detalle del Producto")
        popup.geometry("440x540")
        popup.transient(self.winfo_toplevel())
        popup.withdraw()

        header = ttk.Frame(popup, bootstyle="dark")
        header.pack(fill="x", pady=10)
        ttk.Label(header, text="📋 DETALLE DEL PRODUCTO",
                  font=("Arial", 12, "bold"), bootstyle="inverse-dark").pack()

        info = ttk.Frame(popup, bootstyle="dark")
        info.pack(fill="both", expand=True, padx=25, pady=15)
        for t, f in [(f"ID: {pid}", ("Arial", 10)),
                     (f"Nombre: {name}", ("Arial", 12, "bold")),
                     (f"Código de Barras: {barcode}", ("Arial", 10)),
                     (f"Precio: {price}", ("Arial", 12, "bold")),
                     (f"Unidad: {unit}", ("Arial", 11)),
                     (f"Stock: {stock}", ("Arial", 11)),
                     ("", ("Arial", 4)),
                     (f"📅 Creado: {created}", ("Arial", 10, "italic")),
                     (f"🔄 Actualizado: {updated}", ("Arial", 10, "italic"))]:
            ttk.Label(info, text=t, font=f, bootstyle="inverse-dark").pack(anchor="w", pady=4)

        ttk.Separator(popup, orient="horizontal").pack(fill="x", padx=20, pady=5)
        bf = ttk.Frame(popup, bootstyle="dark")
        bf.pack(pady=15)
        ttk.Button(bf, text="✏️ Editar",
                   command=lambda: [popup.destroy(), self.open_edit_from_item(sel[0])],
                   style="DarkGreen.TButton").pack(side="left", padx=5)
        ttk.Button(bf, text="Cerrar", command=popup.destroy).pack(side="left", padx=5)
        ttk.Button(bf, text="🗑",
                   command=lambda: [popup.destroy(), self.confirm_delete(sel[0])],
                   bootstyle="danger", width=3).pack(side="left", padx=15)
        try:
            popup.grab_set()
        except Exception:
            pass
        show_popup_smooth(popup)

    def confirm_delete(self, item):
        vals = self.tree.item(item, 'values')
        pid, name = vals[0], vals[1]
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
        name = vals[1]
        barcode = vals[2]
        price = float(vals[3].replace("$", "").replace(".", ""))
        unit = vals[4]
        stock = float(vals[5])
        unit_type = "unidad"
        if unit in ("kg", "gr", "mg"):
            unit_type = "peso"
        elif unit in ("Lt", "ml"):
            unit_type = "volumen"
        self.open_product_form("Editar Producto", pid, name, barcode, price,
                               stock, unit_type, unit)

    def add_product_popup(self, barcode_prefill="", auto_select=False):
        self.open_product_form("Agregar Producto", None, "", barcode_prefill,
                               0, 0, "unidad", "unidad", auto_select)

    def open_product_form(self, title, product_id, name, barcode, price, stock,
                          unit_type, unit, auto_select=False):
        popup = Toplevel(self)
        popup.title(title)
        popup.geometry("410x640")
        popup.transient(self.winfo_toplevel())
        popup.withdraw()

        ttk.Label(popup, text="Código de Barras / QR:").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=35)
        barcode_entry.pack(pady=5)
        if barcode:
            barcode_entry.insert(0, barcode)

        ttk.Label(popup, text="Nombre del Producto:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=35)
        name_entry.pack(pady=5)
        if name:
            name_entry.insert(0, name)

        ttk.Label(popup, text="Tipo de venta:", font=("Arial", 10, "bold")).pack(pady=(10, 3))
        type_var = tk.StringVar(value=unit_type)
        type_frame = ttk.Frame(popup)
        type_frame.pack()
        for val, txt in [("unidad", "📦 Por unidad"),
                         ("peso", "⚖️ Por peso"),
                         ("volumen", "💧 Por volumen")]:
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
        if price:
            price_entry.insert(0, str(int(price)))

        ttk.Label(popup, text="Stock (acepta decimales):").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=35)
        stock_entry.pack(pady=5)
        if stock:
            stock_entry.insert(0, f"{stock:g}")

        if barcode:
            name_entry.focus_set()
        else:
            barcode_entry.focus_set()

        def save():
            n = name_entry.get().strip()
            b = barcode_entry.get().strip()
            if not n:
                MD.show_error("El nombre es obligatorio", "Error", parent=popup)
                return
            try:
                pl = price_entry.get().replace("$", "").replace(".", "").replace(",", ".").strip()
                p = float(pl) if pl else 0.0
                ss = stock_entry.get().strip().replace(",", ".")
                s = float(ss) if ss else 0.0
            except ValueError:
                MD.show_error("Precio/Stock inválidos", "Error", parent=popup)
                return
            if product_id:
                self.product_use_case.update_product(product_id, n, b, p, s,
                                                     type_var.get(), unit_var.get())
            else:
                self.product_use_case.add_product(n, b, p, s,
                                                  type_var.get(), unit_var.get())
            self.load_products()
            popup.destroy()
            self.scan_entry.focus_set()
            if auto_select and b:
                for it in self.tree.get_children():
                    if str(self.tree.item(it, 'values')[2]).strip() == b:
                        self.tree.selection_set(it)
                        self.tree.focus(it)
                        self.tree.see(it)
                        break

        ttk.Button(popup, text="Guardar", command=save,
                   style="DarkGreen.TButton").pack(pady=20)
        try:
            popup.grab_set()
        except Exception:
            pass
        show_popup_smooth(popup)

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
                if str(self.tree.item(it, 'values')[2]).strip() == codigo:
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