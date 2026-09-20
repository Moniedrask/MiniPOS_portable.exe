# src/presentation/views/main_view.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from ttkbootstrap import Style, Toplevel
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

        # Ruta portable
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
        
        # Atajo F2 para Agregar Producto
        self.bind('<F2>', lambda event: self.add_product_popup())
        # Enfocar el campo de escaneo al iniciar
        self.after(100, lambda: self.scan_entry.focus_set())

    def create_widgets(self):
        # --- MENÚ SUPERIOR DE OPCIONES ---
        menubar = tk.Menu(self)
        options_menu = tk.Menu(menubar, tearoff=0)
        options_menu.add_command(label="🌓 Cambiar Tema", command=self.toggle_theme)
        options_menu.add_separator()
        options_menu.add_command(label="📤 Exportar Base de Datos", command=self.export_db)
        options_menu.add_command(label="📥 Importar Base de Datos", command=self.import_db)
        menubar.add_cascade(label="Opciones", menu=options_menu)
        self.config(menu=menubar)

        # --- BARRA DE ESCANEO AUTOMÁTICO (Lector QR) ---
        scan_frame = ttk.Frame(self)
        scan_frame.pack(padx=10, pady=(10, 5), fill="x")
        ttk.Label(scan_frame, text="📷 Escanear código aquí:", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        self.scan_var = tk.StringVar()
        self.scan_entry = ttk.Entry(scan_frame, textvariable=self.scan_var, width=35, font=("Arial", 11))
        self.scan_entry.pack(side="left", padx=5)
        # Cuando el lector presiona "Enter" al final, se dispara la búsqueda
        self.scan_entry.bind("<Return>", self.lookup_barcode)
        ttk.Button(scan_frame, text="🔍 Buscar Código", command=lambda: self.lookup_barcode(None)).pack(side="left", padx=5)

        # --- BARRA DE BÚSQUEDA MANUAL ---
        search_frame = ttk.Frame(self)
        search_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(search_frame, text="🔍 Búsqueda manual (Nombre o Código):").pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", self.filter_products)

        # --- TABLA DE INVENTARIO ---
        frame = ttk.Frame(self)
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
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="➕ Agregar Producto (F2)", command=self.add_product_popup).pack(side="left", padx=5)

    # --- NUEVA FUNCIÓN: Detección automática del lector de códigos ---
    def lookup_barcode(self, event=None):
        """Busca un producto por su código de barras. Si existe, lo selecciona. Si no, ofrece agregarlo."""
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
            # Seleccionar y resaltar el producto en la tabla
            self.search_var.set("")  # Limpiar la búsqueda manual
            self.load_products()
            for item in self.tree.get_children():
                valores = self.tree.item(item, 'values')
                if str(valores[2]).strip() == codigo:
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    self.tree.see(item)
                    break
            messagebox.showinfo("Producto Encontrado", 
                f"✅ {encontrado.name}\nPrecio: ${encontrado.price:,.0f}\nStock: {encontrado.stock}".replace(",", "."), 
                parent=self)
            self.scan_var.set("")  # Limpiar el campo para el siguiente escaneo
        else:
            # Producto no encontrado: preguntar si desea agregarlo
            respuesta = messagebox.askyesno("Producto No Registrado", 
                f"⚠️ El código '{codigo}' NO está registrado en el inventario.\n\n¿Deseas agregarlo ahora?", 
                parent=self)
            if respuesta:
                self.add_product_popup(barcode_prefill=codigo)
            self.scan_var.set("")
        
        # Devolver el foco al campo de escaneo
        self.scan_entry.focus_set()

    def toggle_theme(self):
        if self.current_theme == 'darkly':
            self.current_theme = 'flatly'
        else:
            self.current_theme = 'darkly'
        self.style.theme_use(self.current_theme)

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

    # --- AGREGAR PRODUCTO (con opción de pre-rellenar el código de barras) ---
    def add_product_popup(self, barcode_prefill=""):
        popup = Toplevel(self)
        popup.title("Agregar Producto")
        popup.geometry("350x450")
        popup.transient(self)
        popup.grab_set()

        ttk.Label(popup, text="Nombre del Producto:").pack(pady=5)
        name_entry = ttk.Entry(popup, width=30)
        name_entry.pack(pady=5)
        name_entry.focus_set()

        ttk.Label(popup, text="Código de Barras / QR (Opcional):").pack(pady=5)
        barcode_entry = ttk.Entry(popup, width=30)
        barcode_entry.pack(pady=5)
        if barcode_prefill:
            barcode_entry.insert(0, barcode_prefill)

        ttk.Label(popup, text="Precio (ej. 15000):").pack(pady=5)
        price_entry = ttk.Entry(popup, width=30)
        price_entry.pack(pady=5)

        ttk.Label(popup, text="Stock (Opcional, deje vacío para 0):").pack(pady=5)
        stock_entry = ttk.Entry(popup, width=30)
        stock_entry.pack(pady=5)

        def save():
            name = name_entry.get().strip()
            barcode = barcode_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "El nombre es obligatorio", parent=popup)
                return
            try:
                precio_limpio = price_entry.get().replace("$", "").replace(".", "").strip()
                price = float(precio_limpio) if precio_limpio else 0.0
                stock_str = stock_entry.get().strip()
                stock = int(stock_str) if stock_str else 0
            except ValueError:
                messagebox.showerror("Error", "Precio y Stock deben ser números", parent=popup)
                return
            self.product_use_case.add_product(name, barcode, price, stock)
            self.load_products()
            popup.destroy()
            self.scan_entry.focus_set()  # Devolver foco al campo de escaneo

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
                messagebox.showerror("Error", "Datos inválidos", parent=popup); return
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
            messagebox.showinfo("Éxito", "Base de datos exportada.")

    def import_db(self):
        archivo = filedialog.askopenfilename(filetypes=[("SQLite", "*.db")])
        if archivo and messagebox.askyesno("Confirmar", "¿Reemplazar datos actuales?"):
            self.db_manager.close_connection()
            shutil.copy2(archivo, self.db_path)
            self.load_products()
            messagebox.showinfo("Éxito", "Base de datos importada.")
