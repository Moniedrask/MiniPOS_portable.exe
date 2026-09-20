# src/presentation/views/main_view.py
import tkinter as tk
from tkinter import ttk, filedialog
from ttkbootstrap import Style, Toplevel
from ttkbootstrap.dialogs import Messagebox
import os, shutil, sys
from application.use_case.product_use_case import ProductCase
from infrastucture.db.db_manager import DBManager

class MainView(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("INVENTARIO - MiniPOS Portable")
        self.geometry("950x680")
        
        self.current_theme = 'darkly'
        self.style = Style(theme=self.current_theme)
        self.configure(bg=self.style.colors.bg)

        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        self.db_path = os.path.join(base_dir, "data", "ventas.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self.db_manager = DBManager(self.db_path)
        self.product_use_case = ProductCase(self.db_manager)

        self.create_widgets()
        self.load_products()
        
        self.bind('<F2>', lambda event: self.add_product_popup())
        self.after(100, lambda: self.scan_entry.focus_set())

    def create_widgets(self):
        # --- MENÚ SUPERIOR DE OPCIONES ---
        menubar = tk.Menu(self, bg=self.style.colors.bg, fg=self.style.colors.fg,
                          activebackground=self.style.colors.selectbg,
                          activeforeground=self.style.colors.selectfg, bd=0)
        options_menu = tk.Menu(menubar, tearoff=0, bg=self.style.colors.bg, fg=self.style.colors.fg,
                               activebackground=self.style.colors.selectbg,
                               activeforeground=self.style.colors.selectfg)
        options_menu.add_command(label="🌓 Cambiar Tema", command=self.toggle_theme)
        options_menu.add_separator()
        options_menu.add_command(label="📤 Exportar Base de Datos", command=self.export_db)
        options_menu.add_command(label="📥 Importar Base de Datos", command=self.import_db)
        menubar.add_cascade(label="Opciones", menu=options_menu)
        self.config(menu=menubar)

        # --- BARRA DE ESCANEO ---
        scan_frame = ttk.Frame(self, bootstyle="dark")
        scan_frame.pack(padx=10, pady=(10, 5), fill="x")
        ttk.Label(scan_frame, text="📷 Escanear código aquí:", font=("Arial", 10, "bold"),
                  bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(scan_frame, textvariable=self.scan_var, width=35, font=("Arial", 11))
        self.scan_entry.pack(side="left", padx=5)
        self.scan_entry.bind("<Return>", self.lookup_barcode)
        ttk.Button(scan_frame, text="🔍 Buscar Código",
                   command=lambda: self.lookup_barcode(None)).pack(side="left", padx=5)

        # --- BÚSQUEDA MANUAL ---
        search_frame = ttk.Frame(self, bootstyle="dark")
        search_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(search_frame, text="🔍 Búsqueda manual (Nombre o Código):",
                  bootstyle="inverse-dark").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_products)

        # --- TABLA DE INVENTARIO ---
        frame = ttk.Frame(self, bootstyle="dark")
        frame.pack(padx=10, pady=5, fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=("ID", "Name", "Barcode", "Price", "Stock"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Producto")
        self.tree.heading("Barcode", text="Código de Barras / QR")
        self.tree.heading("Price", text="Precio")
        self.tree.heading("Stock", text="Stock")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=280)
        self.tree.column("Barcode", width=180)
        self.tree.column("Price", width=100, anchor="e")
        self.tree.column("Stock", width=80, anchor="center")
        self.tree.pack(fill="both", expand=True)
        # ✅ Doble clic = Ver detalle | ✅ Clic derecho = Menú contextual
        self.tree.bind("<Double-1>", self.view_product_popup)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # --- BOTONES INFERIORES ---
        btn_frame = ttk.Frame(self, bootstyle="dark")
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="➕ Agregar Producto (F2)",
                   command=self.add_product_popup).pack(side="left", padx=5)

    # ================== MENÚ CONTEXTUAL (CLIC DERECHO) ==================
    def show_context_menu(self, event):
        """Muestra un menú contextual oscuro al hacer clic derecho sobre un producto."""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        self.tree.focus(item)

        menu = tk.Menu(
            self, tearoff=0,
            bg=self.style.colors.bg,
            fg=self.style.colors.fg,
            activebackground=self.style.colors.selectbg,
            activeforeground=self.style.colors.selectfg,
            bd=1, relief="solid"
        )
        menu.add_command(label="👁️  Ver detalle", command=lambda: self.view_product_popup(None))
        menu.add_command(label="✏️  Editar producto", command=lambda: self.open_edit_from_item(item))
        menu.add_separator()
        menu.add_command(label="🗑️  Eliminar producto", command=lambda: self.confirm_delete(item))
        
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ================== VISTA DE DETALLE (DOBLE CLIC) ==================
    def view_product_popup(self, event=None):
        """Ventana de vista previa. Muestra los datos del producto y botones para editar o eliminar."""
        selected = self.tree.selection()
        if not selected:
            return
        vals = self.tree.item(selected[0], 'values')
        product_id, name, barcode, price, stock = vals[0], vals[1], vals[2], vals[3], vals[4]

        popup = Toplevel(self)
        popup.title("Detalle del Producto")
        popup.geometry("400x420")
        popup.transient(self)
        popup.grab_set()

        # Encabezado
        header = ttk.Frame(popup, bootstyle="dark")
        header.pack(fill="x", pady=10)
        ttk.Label(header, text="📋 DETALLE DEL PRODUCTO", font=("Arial", 12, "bold"),
                  bootstyle="inverse-dark").pack()

        # Información
        info = ttk.Frame(popup, bootstyle="dark")
        info.pack(fill="both", expand=True, padx=25, pady=15)

        ttk.Label(info, text=f"ID: {product_id}", font=("Arial", 10),
                  bootstyle="inverse-dark").pack(anchor="w", pady=4)
        ttk.Label(info, text=f"Nombre: {name}", font=("Arial", 12, "bold"),
                  bootstyle="inverse-dark").pack(anchor="w", pady=4)
        ttk.Label(info, text=f"Código de Barras: {barcode}", font=("Arial", 10),
                  bootstyle="inverse-dark").pack(anchor="w", pady=4)
        ttk.Label(info, text=f"Precio: {price}", font=("Arial", 12, "bold"),
                  bootstyle="inverse-dark").pack(anchor="w", pady=4)
        ttk.Label(info, text=f"Stock: {stock}", font=("Arial", 10),
                  bootstyle="inverse-dark").pack(anchor="w", pady=4)

        # Separador
        ttk.Separator(popup, orient="horizontal").pack(fill="x", padx=20, pady=5)

        # Botones
        btn_frame = ttk.Frame(popup, bootstyle="dark")
        btn_frame.pack(pady=15)

        ttk.Button(btn_frame, text="✏️ Editar",
                   command=lambda: [popup.destroy(), self.open_edit_from_item(selected[0])]
                   ).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cerrar", command=popup.destroy).pack(side="left", padx=5)
        # ✅ Botón eliminar pequeño (solo ícono) para evitar clics accidentales
        ttk.Button(btn_frame, text="🗑", command=lambda: [popup.destroy(), self.confirm_delete(selected[0])],
                   bootstyle="danger", width=3).pack(side="left", padx=15)

    # ================== ELIMINAR CON DOBLE CONFIRMACIÓN ==================
    def confirm_delete(self, item):
        """Elimina un producto con doble confirmación para evitar accidentes."""
        vals = self.tree.item(item, 'values')
        product_id, name = vals[0], vals[1]

        # Primera confirmación
        r1 = Messagebox.yesno(
            f"⚠️ ¿Deseas ELIMINAR este producto?\n\n"
            f"ID: {product_id}\n"
            f"Nombre: {name}\n\n"
            f"Esta acción no se puede deshacer.",
            "Confirmar Eliminación",
            parent=self
        )
        if r1 != "Yes":
            return

        # Segunda confirmación (última advertencia)
        r2 = Messagebox.yesno(
            f"🚨 ÚLTIMA ADVERTENCIA 🚨\n\n"
            f"¿Realmente deseas eliminar '{name}'?\n"
            f"Se perderá permanentemente del inventario.",
            "¿Estás completamente seguro?",
            parent=self
        )
        if r2 != "Yes":
            return

        self.product_use_case.delete_product(product_id)
        self.load_products()
        Messagebox.show_info(f"El producto '{name}' ha sido eliminado.", "Producto Eliminado", parent=self)
        self.scan_entry.focus_set()

    # ================== FORMULARIO DE EDICIÓN ==================
    def open_edit_from_item(self, item):
        """Abre el formulario de edición a partir de un item de la tabla."""
        vals = self.tree.item(item, 'values')
        product_id = vals[0]
        name = vals[1]
        barcode = vals[2]
        price = float(vals[3].replace("$", "").replace(".", ""))
        stock = int(vals[4])

        popup = Toplevel(self)
        popup.title("Editar Producto")
        popup.geometry("350x480")
        popup.transient(self); popup.grab_set()

        ttk.Label(popup, text=f"ID: {product_id} (No editable)").pack(pady=5)
        ttk.Label(popup, text="Nombre:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30); name_entry.insert(0, name); name_entry.pack(pady=5)
        ttk.Label(popup, text="Código de Barras:").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=30); barcode_entry.insert(0, barcode); barcode_entry.pack(pady=5)
        ttk.Label(popup, text="Precio:").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30); price_entry.insert(0, str(int(price))); price_entry.pack(pady=5)
        ttk.Label(popup, text="Stock:").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30); stock_entry.insert(0, str(stock)); stock_entry.pack(pady=5)

        def update():
            try:
                new_name = name_entry.get().strip()
                new_barcode = barcode_entry.get().strip()
                new_price = float(price_entry.get().replace("$", "").replace(".", "") or 0)
                new_stock = int(stock_entry.get() or 0)
            except ValueError:
                Messagebox.show_error("Datos inválidos", "Error", parent=popup); return
            self.product_use_case.update_product(product_id, new_name, new_barcode, new_price, new_stock)
            self.load_products(); popup.destroy()
            self.scan_entry.focus_set()

        ttk.Button(popup, text="Actualizar", command=update).pack(pady=15)

    # ================== ESCANEO AUTOMÁTICO ==================
    def lookup_barcode(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo:
            return
        productos = self.product_use_case.list_products()
        encontrado = None
        for p in productos:
            if str(p.barcode).strip() == codigo:
                encontrado = p
                break
        
        if encontrado:
            self.search_var.set("")
            self.load_products()
            for item in self.tree.get_children():
                valores = self.tree.item(item, 'values')
                if str(valores[2]).strip() == codigo:
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    self.tree.see(item)
                    break
            Messagebox.show_info(
                f"✅ {encontrado.name}\nPrecio: ${encontrado.price:,.0f}\nStock: {encontrado.stock}".replace(",", "."),
                "Producto Encontrado", parent=self)
            self.scan_var.set("")
        else:
            respuesta = Messagebox.yesno(
                f"⚠️ El código '{codigo}' NO está registrado en el inventario.\n\n¿Deseas agregarlo ahora?",
                "Producto No Registrado", parent=self)
            if respuesta == "Yes":
                self.add_product_popup(barcode_prefill=codigo)
            self.scan_var.set("")
        self.scan_entry.focus_set()

    # ================== AGREGAR PRODUCTO ==================
    def add_product_popup(self, barcode_prefill=""):
        popup = Toplevel(self)
        popup.title("Agregar Producto")
        popup.geometry("350x480")
        popup.transient(self); popup.grab_set()

        ttk.Label(popup, text="Código de Barras / QR:").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=30); barcode_entry.pack(pady=5)
        if barcode_prefill:
            barcode_entry.insert(0, barcode_prefill)

        ttk.Label(popup, text="Nombre del Producto:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30); name_entry.pack(pady=5)

        ttk.Label(popup, text="Precio (ej. 15000):").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30); price_entry.pack(pady=5)

        ttk.Label(popup, text="Stock (Opcional, deje vacío para 0):").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30); stock_entry.pack(pady=5)

        if barcode_prefill:
            name_entry.focus_set()
        else:
            barcode_entry.focus_set()

        def save():
            name = name_entry.get().strip()
            barcode = barcode_entry.get().strip()
            if not name:
                Messagebox.show_error("El nombre es obligatorio", "Error", parent=popup); return
            try:
                precio_limpio = price_entry.get().replace("$", "").replace(".", "").strip()
                price = float(precio_limpio) if precio_limpio else 0.0
                stock_str = stock_entry.get().strip()
                stock = int(stock_str) if stock_str else 0
            except ValueError:
                Messagebox.show_error("Precio y Stock deben ser números", "Error", parent=popup); return
            self.product_use_case.add_product(name, barcode, price, stock)
            self.load_products(); popup.destroy()
            self.scan_entry.focus_set()

        ttk.Button(popup, text="Guardar", command=save).pack(pady=15)

    # ================== UTILIDADES ==================
    def toggle_theme(self):
        if self.current_theme == 'darkly':
            self.current_theme = 'flatly'
        else:
            self.current_theme = 'darkly'
        self.style.theme_use(self.current_theme)
        self.configure(bg=self.style.colors.bg)

    def filter_products(self, event=None):
        query = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for product in self.product_use_case.list_products():
            if query in str(product.name).lower() or query in str(product.barcode).lower():
                precio = f"${product.price:,.0f}".replace(",", ".")
                self.tree.insert("", "end", values=(product.product_id, product.name, product.barcode, precio, product.stock))

    def load_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for product in self.product_use_case.list_products():
            precio = f"${product.price:,.0f}".replace(",", ".")
            self.tree.insert("", "end", values=(product.product_id, product.name, product.barcode, precio, product.stock))

    def export_db(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite", "*.db")])
        if archivo:
            self.db_manager.close_connection()
            shutil.copy2(self.db_path, archivo)
            Messagebox.show_info("Base de datos exportada correctamente.", "Éxito", parent=self)

    def import_db(self):
        archivo = filedialog.askopenfilename(filetypes=[("SQLite", "*.db")])
        if archivo and Messagebox.yesno("¿Reemplazar datos actuales?", "Confirmar", parent=self) == "Yes":
            self.db_manager.close_connection()
            shutil.copy2(archivo, self.db_path)
            self.load_products()
            Messagebox.show_info("Base de datos importada correctamente.", "Éxito", parent=self)
    def create_widgets(self):
        # --- MENÚ SUPERIOR DE OPCIONES (OSCURO) ---
        menubar = tk.Menu(
            self, 
            bg=self.style.colors.bg, 
            fg=self.style.colors.fg, 
            activebackground=self.style.colors.selectbg, 
            activeforeground=self.style.colors.selectfg,
            bd=0
        )
        options_menu = tk.Menu(
            menubar, tearoff=0,
            bg=self.style.colors.bg, 
            fg=self.style.colors.fg, 
            activebackground=self.style.colors.selectbg, 
            activeforeground=self.style.colors.selectfg
        )
        options_menu.add_command(label="🌓 Cambiar Tema", command=self.toggle_theme)
        options_menu.add_separator()
        options_menu.add_command(label="📤 Exportar Base de Datos", command=self.export_db)
        options_menu.add_command(label="📥 Importar Base de Datos", command=self.import_db)
        menubar.add_cascade(label="Opciones", menu=options_menu)
        self.config(menu=menubar)

        # --- BARRA DE ESCANEO AUTOMÁTICO ---
        scan_frame = ttk.Frame(self, bootstyle="dark")
        scan_frame.pack(padx=10, pady=(10, 5), fill="x")
        ttk.Label(scan_frame, text="📷 Escanear código aquí:", font=("Arial", 10, "bold"), bootstyle="inverse-dark").pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(scan_frame, textvariable=self.scan_var, width=35, font=("Arial", 11))
        self.scan_entry.pack(side="left", padx=5)
        self.scan_entry.bind("<Return>", self.lookup_barcode)
        ttk.Button(scan_frame, text="🔍 Buscar Código", command=lambda: self.lookup_barcode(None)).pack(side="left", padx=5)

        # --- BARRA DE BÚSQUEDA MANUAL ---
        search_frame = ttk.Frame(self, bootstyle="dark")
        search_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(search_frame, text="🔍 Búsqueda manual (Nombre o Código):", bootstyle="inverse-dark").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_products)

        # --- TABLA DE INVENTARIO ---
        frame = ttk.Frame(self, bootstyle="dark")
        frame.pack(padx=10, pady=5, fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=("ID", "Name", "Barcode", "Price", "Stock"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Producto")
        self.tree.heading("Barcode", text="Código de Barras / QR")
        self.tree.heading("Price", text="Precio")
        self.tree.heading("Stock", text="Stock")
        self.tree.column("ID", width=50, anchor="center")
        self.tree.column("Name", width=280)
        self.tree.column("Barcode", width=180)
        self.tree.column("Price", width=100, anchor="e")
        self.tree.column("Stock", width=80, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", self.edit_product_popup)

        # --- BOTONES INFERIORES ---
        btn_frame = ttk.Frame(self, bootstyle="dark")
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="➕ Agregar Producto (F2)", command=self.add_product_popup).pack(side="left", padx=5)

    def lookup_barcode(self, event=None):
        codigo = self.scan_var.get().strip()
        if not codigo:
            return
        
        productos = self.product_use_case.list_products()
        encontrado = None
        for p in productos:
            if str(p.barcode).strip() == codigo:
                encontrado = p
                break
        
        if encontrado:
            self.search_var.set("")
            self.load_products()
            for item in self.tree.get_children():
                valores = self.tree.item(item, 'values')
                if str(valores[2]).strip() == codigo:
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    self.tree.see(item)
                    break
            Messagebox.show_info(
                f"✅ {encontrado.name}\nPrecio: ${encontrado.price:,.0f}\nStock: {encontrado.stock}".replace(",", "."),
                "Producto Encontrado",
                parent=self
            )
            self.scan_var.set("")
        else:
            respuesta = Messagebox.yesno(
                f"⚠️ El código '{codigo}' NO está registrado en el inventario.\n\n¿Deseas agregarlo ahora?",
                "Producto No Registrado",
                parent=self
            )
            if respuesta == "Yes":
                self.add_product_popup(barcode_prefill=codigo)
            self.scan_var.set("")
        
        self.scan_entry.focus_set()

    def toggle_theme(self):
        if self.current_theme == 'darkly':
            self.current_theme = 'flatly'
        else:
            self.current_theme = 'darkly'
        self.style.theme_use(self.current_theme)
        # Reconfigurar fondo de la ventana
        self.configure(bg=self.style.colors.bg)

    def filter_products(self, event=None):
        query = self.search_var.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for product in self.product_use_case.list_products():
            if query in str(product.name).lower() or query in str(product.barcode).lower():
                precio = f"${product.price:,.0f}".replace(",", ".")
                self.tree.insert("", "end", values=(product.product_id, product.name, product.barcode, precio, product.stock))

    def load_products(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for product in self.product_use_case.list_products():
            precio = f"${product.price:,.0f}".replace(",", ".")
            self.tree.insert("", "end", values=(product.product_id, product.name, product.barcode, precio, product.stock))

    # --- AGREGAR PRODUCTO (con enfoque en código de barras) ---
    def add_product_popup(self, barcode_prefill=""):
        popup = Toplevel(self)
        popup.title("Agregar Producto")
        popup.geometry("350x480")
        popup.transient(self)
        popup.grab_set()

        # ✅ CAMPO DE CÓDIGO DE BARRAS PRIMERO (para escaneo automático)
        ttk.Label(popup, text="Código de Barras / QR:").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=30)
        barcode_entry.pack(pady=5)
        if barcode_prefill:
            barcode_entry.insert(0, barcode_prefill)

        ttk.Label(popup, text="Nombre del Producto:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30)
        name_entry.pack(pady=5)

        ttk.Label(popup, text="Precio (ej. 15000):").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30)
        price_entry.pack(pady=5)

        ttk.Label(popup, text="Stock (Opcional, deje vacío para 0):").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30)
        stock_entry.pack(pady=5)

        # ✅ Lógica de enfoque: si viene código pre-rellenado, ir al Nombre; si no, al Código
        if barcode_prefill:
            name_entry.focus_set()
        else:
            barcode_entry.focus_set()

        def save():
            name = name_entry.get().strip()
            barcode = barcode_entry.get().strip()
            if not name:
                Messagebox.show_error("El nombre es obligatorio", "Error", parent=popup)
                return
            try:
                precio_limpio = price_entry.get().replace("$", "").replace(".", "").strip()
                price = float(precio_limpio) if precio_limpio else 0.0
                stock_str = stock_entry.get().strip()
                stock = int(stock_str) if stock_str else 0
            except ValueError:
                Messagebox.show_error("Precio y Stock deben ser números", "Error", parent=popup)
                return
            self.product_use_case.add_product(name, barcode, price, stock)
            self.load_products()
            popup.destroy()
            self.scan_entry.focus_set()

        ttk.Button(popup, text="Guardar", command=save).pack(pady=15)

    def edit_product_popup(self, event):
        selected = self.tree.selection()
        if not selected: return
        vals = self.tree.item(selected[0], 'values')
        product_id, name, barcode = vals[0], vals[1], vals[2]
        price = float(vals[3].replace("$", "").replace(".", ""))
        stock = int(vals[4])

        popup = Toplevel(self)
        popup.title("Editar Producto")
        popup.geometry("350x480")
        popup.transient(self); popup.grab_set()

        ttk.Label(popup, text=f"ID: {product_id} (No editable)").pack(pady=5)
        ttk.Label(popup, text="Nombre:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30); name_entry.insert(0, name); name_entry.pack(pady=5)
        ttk.Label(popup, text="Código de Barras:").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=30); barcode_entry.insert(0, barcode); barcode_entry.pack(pady=5)
        ttk.Label(popup, text="Precio:").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30); price_entry.insert(0, str(int(price))); price_entry.pack(pady=5)
        ttk.Label(popup, text="Stock:").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30); stock_entry.insert(0, str(stock)); stock_entry.pack(pady=5)

        def update():
            try:
                new_name = name_entry.get().strip()
                new_barcode = barcode_entry.get().strip()
                new_price = float(price_entry.get().replace("$", "").replace(".", "") or 0)
                new_stock = int(stock_entry.get() or 0)
            except ValueError:
                Messagebox.show_error("Datos inválidos", "Error", parent=popup); return
            self.product_use_case.update_product(product_id, new_name, new_barcode, new_price, new_stock)
            self.load_products(); popup.destroy()
            self.scan_entry.focus_set()

        ttk.Button(popup, text="Actualizar", command=update).pack(pady=10)
        ttk.Button(popup, text="🗑 Eliminar", command=lambda: [self.product_use_case.delete_product(product_id), self.load_products(), popup.destroy()], bootstyle="danger").pack(pady=5)

    def export_db(self):
        archivo = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite", "*.db")])
        if archivo:
            self.db_manager.close_connection()
            shutil.copy2(self.db_path, archivo)
            Messagebox.show_info("Base de datos exportada correctamente.", "Éxito", parent=self)

    def import_db(self):
        archivo = filedialog.askopenfilename(filetypes=[("SQLite", "*.db")])
        if archivo and Messagebox.yesno("¿Reemplazar datos actuales?", "Confirmar", parent=self) == "Yes":
            self.db_manager.close_connection()
            shutil.copy2(archivo, self.db_path)
            self.load_products()
            Messagebox.show_info("Base de datos importada correctamente.", "Éxito", parent=self)
